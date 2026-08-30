"""exp004 — apply the pre-registered bar and write the verdicts.

The bar is exp001's, reused verbatim: a paired difference is distinguishable iff
its magnitude exceeds BOTH the seed-to-seed spread AND 2% of the reference arm's
mean. Reference arm is F, the fixture, because the question is whether the render
behaves like it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

HERE = Path(__file__).parent
MATERIALITY = 0.02
METRICS = ("median", "p90")


def paired(rows: list[dict], stratum: str, metric: str) -> dict[str, Any]:
    """The declared test on one stratum and one metric, over seeds."""
    f = np.array([r["strata"][stratum]["F"][metric] for r in rows], dtype=float)
    r = np.array([r["strata"][stratum]["R"][metric] for r in rows], dtype=float)
    d = r - f
    mean_d = float(np.mean(d))
    spread = float(np.std(d, ddof=1))
    floor = MATERIALITY * float(np.mean(f))
    bar = max(spread, floor)
    return {
        "F_mean": float(np.mean(f)),
        "R_mean": float(np.mean(r)),
        "mean_diff": mean_d,
        "sd_diff": spread,
        "materiality_floor": floor,
        "bar": bar,
        "x_bar": abs(mean_d) / bar if bar > 0 else float("inf"),
        "distinguishable": bool(abs(mean_d) > bar),
        "direction": "R_worse" if mean_d > 0 else ("R_better" if mean_d < 0 else "tie"),
        "clause_1_exceeds_spread": bool(abs(mean_d) > spread),
        "clause_2_exceeds_floor": bool(abs(mean_d) > floor),
    }


def sweep(rows: list[dict], prefix: str, metric: str) -> dict[str, Any]:
    """The same test at every swept threshold, so a fragile verdict is visible."""
    out: dict[str, Any] = {}
    for key in rows[0]["sweep"]:
        if not key.startswith(prefix):
            continue
        f = np.array([r["sweep"][key]["F"][metric] for r in rows], dtype=float)
        r = np.array([r["sweep"][key]["R"][metric] for r in rows], dtype=float)
        d = r - f
        bar = max(float(np.std(d, ddof=1)), MATERIALITY * float(np.mean(f)))
        out[key] = {
            "mean_diff": float(np.mean(d)),
            "bar": bar,
            "x_bar": abs(float(np.mean(d))) / bar if bar > 0 else float("inf"),
            "distinguishable": bool(abs(float(np.mean(d))) > bar),
            "direction": "R_worse" if float(np.mean(d)) > 0 else "R_better",
        }
    return out


def main() -> None:
    data = json.loads((HERE / "results.json").read_text())
    rows = data["per_seed"]

    verdicts: dict[str, Any] = {
        "experiment": data["experiment"],
        "seeds": data["seeds"],
        "policy": data["policy"],
        "steps": data["steps"],
        "thresholds": data["thresholds"],
        "rendered_with": data["rendered_with"],
        "environment": data["environment"],
        "primary": {},
        "sweep": {},
        "coverage": {},
        "excluded": {},
        "pooled_CONFOUNDED": {},
        "front_end_POST_HOC": {},
    }

    for stratum in ("AWAY", "AT", "ALL"):
        verdicts["primary"][stratum] = {m: paired(rows, stratum, m) for m in METRICS}

    for prefix in ("AWAY_", "AT_"):
        verdicts["sweep"][prefix.rstrip("_")] = {m: sweep(rows, prefix, m) for m in METRICS}

    cov = {k: [r["coverage"][k] for r in rows] for k in rows[0]["coverage"]}
    verdicts["coverage"] = {
        k: {"mean": float(np.mean(v)), "min": int(np.min(v)), "max": int(np.max(v))}
        for k, v in cov.items()
    }
    verdicts["coverage"]["R_minus_F_valid_mean"] = float(
        np.mean(np.array(cov["R_valid"]) - np.array(cov["F_valid"]))
    )

    for key in ("F_only", "R_only"):
        verdicts["excluded"][key] = {
            m: float(np.mean([r["excluded"][key][m] for r in rows])) for m in ("n", "median", "p90")
        }

    for stratum in ("AWAY", "AT"):
        verdicts["pooled_CONFOUNDED"][stratum] = {
            arm: {
                m: float(np.mean([r["pooled_CONFOUNDED"][stratum][arm][m] for r in rows]))
                for m in ("n", "median", "p90")
            }
            for arm in ("F", "R")
        }
        verdicts["front_end_POST_HOC"][stratum] = {
            arm: {
                m: float(np.mean([r["front_end_POST_HOC"][stratum][arm][m] for r in rows]))
                for m in ("valid_fraction", "median_px", "gross_fraction")
            }
            for arm in ("F", "R")
        }

    verdicts["common_scanpath_CONTROL_POST_HOC"] = {}
    for stratum in ("AWAY", "AT"):
        f = np.array([r["common_scanpath_CONTROL_POST_HOC"][stratum]["F"]["p90"] for r in rows])
        g = np.array(
            [r["common_scanpath_CONTROL_POST_HOC"][stratum]["R_forced"]["p90"] for r in rows]
        )
        d = g - f
        bar = max(float(np.std(d, ddof=1)), MATERIALITY * float(np.mean(f)))
        verdicts["common_scanpath_CONTROL_POST_HOC"][stratum] = {
            "metric": "p90",
            "F_mean": float(np.mean(f)),
            "R_forced_mean": float(np.mean(g)),
            "mean_diff": float(np.mean(d)),
            "bar": bar,
            "x_bar": abs(float(np.mean(d))) / bar if bar > 0 else float("inf"),
            "distinguishable": bool(abs(float(np.mean(d))) > bar),
        }
    verdicts["scanpath_agreement_mean"] = float(np.mean([r["scanpath_agreement"] for r in rows]))

    # --- the three falsifiers, decided by the declared rule ------------------
    away = verdicts["primary"]["AWAY"]
    at = verdicts["primary"]["AT"]
    verdicts["falsifiers"] = {
        "1_away_indistinguishable": {
            "required": "indistinguishable on BOTH primary metrics",
            "median": away["median"]["distinguishable"],
            "p90": away["p90"]["distinguishable"],
            "fired": bool(away["median"]["distinguishable"] or away["p90"]["distinguishable"]),
        },
        "2_at_diverges_R_worse": {
            "required": "distinguishable on at least one metric, with R worse",
            "median": {
                "distinguishable": at["median"]["distinguishable"],
                "direction": at["median"]["direction"],
            },
            "p90": {
                "distinguishable": at["p90"]["distinguishable"],
                "direction": at["p90"]["direction"],
            },
            "diverged": bool(at["median"]["distinguishable"] or at["p90"]["distinguishable"]),
            "R_worse": bool(at["median"]["direction"] == "R_worse"),
        },
    }

    (HERE / "verdicts.json").write_text(json.dumps(verdicts, indent=2))
    dest = Path(__file__).resolve().parents[2] / "results" / "exp004_scene_model_check"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "verdicts.json").write_text(json.dumps(verdicts, indent=2))

    # --- readable summary ----------------------------------------------------
    print(f"exp004 — {len(rows)} seeds, policy {data['policy']}, {data['steps']} fixations")
    print(f"rendered with Blender {data['rendered_with'].get('blender_version')}\n")
    for stratum in ("AWAY", "AT"):
        print(f"[{stratum}]  (intersection of both valid sets)")
        for m in METRICS:
            v = verdicts["primary"][stratum][m]
            mark = "DISTINGUISHABLE" if v["distinguishable"] else "indistinguishable"
            print(
                f"   {m:6s} F={v['F_mean']:.5f} R={v['R_mean']:.5f} "
                f"diff={v['mean_diff']:+.5f} bar={v['bar']:.5f} "
                f"({v['x_bar']:.2f}x) {mark} {v['direction']}"
            )
    print("\n[coverage]")
    c = verdicts["coverage"]
    print(
        f"   F valid {c['F_valid']['mean']:.0f}  R valid {c['R_valid']['mean']:.0f}  "
        f"intersection {c['intersection']['mean']:.0f}  "
        f"R-F {c['R_minus_F_valid_mean']:+.0f}"
    )
    print(
        f"   F-only n={verdicts['excluded']['F_only']['n']:.0f} "
        f"median={verdicts['excluded']['F_only']['median']:.4f}"
    )
    print(
        f"   R-only n={verdicts['excluded']['R_only']['n']:.0f} "
        f"median={verdicts['excluded']['R_only']['median']:.4f}"
    )
    print("\n[front end, POST-HOC — the matcher alone, before any fixation]")
    for stratum in ("AWAY", "AT"):
        fe = verdicts["front_end_POST_HOC"][stratum]
        print(
            f"   {stratum:4s} F: valid {fe['F']['valid_fraction']:.3f} "
            f"median {fe['F']['median_px']:.4f}px gross>2px {fe['F']['gross_fraction']:.3f}   "
            f"R: valid {fe['R']['valid_fraction']:.3f} "
            f"median {fe['R']['median_px']:.4f}px gross>2px {fe['R']['gross_fraction']:.3f}"
        )
    print("\n[common-scanpath CONTROL, POST-HOC — p90, policy held fixed]")
    for stratum in ("AWAY", "AT"):
        c = verdicts["common_scanpath_CONTROL_POST_HOC"][stratum]
        print(
            f"   {stratum:4s} F={c['F_mean']:.5f} R_forced={c['R_forced_mean']:.5f} "
            f"diff={c['mean_diff']:+.5f} bar={c['bar']:.5f} ({c['x_bar']:.2f}x) "
            f"{'DISTINGUISHABLE' if c['distinguishable'] else 'indistinguishable'}"
        )
    print(
        f"   fixations identical between free-running arms: "
        f"{verdicts['scanpath_agreement_mean']:.2f} of {data['steps']}"
    )
    print("\n[falsifiers]")
    f1 = verdicts["falsifiers"]["1_away_indistinguishable"]
    f2 = verdicts["falsifiers"]["2_at_diverges_R_worse"]
    print(f"   1 AWAY indistinguishable: {'FIRED' if f1['fired'] else 'did_not_fire'}")
    print(f"   2 AT diverges, R worse  : diverged={f2['diverged']} R_worse={f2['R_worse']}")
    print(f"\nwrote {HERE / 'verdicts.json'}")


if __name__ == "__main__":
    main()
