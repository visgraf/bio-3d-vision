"""exp005 — apply exp001's bar within each band and write the verdicts.

The bar is exp001's, reused verbatim. What is new is that every comparison is
reported in four pixel sets, and that ``mean_diff``, ``sd_diff`` and the
materiality floor are all recorded beside ``x_bar``.

That last point is the whole reason this file is not three lines. In the AWAY
band both the mean difference and the seed-to-seed spread may shrink, and a
ratio alone cannot separate "the effect was real and masked" from "everything got
smaller together". ``binds`` names which clause set the bar, so a verdict that
turns on the materiality floor is visibly different from one that turns on the
spread.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import numpy as np

HERE = pathlib.Path(__file__).parent
REPO = HERE.resolve().parents[1]
MATERIALITY = 0.02
METRICS = ("median_abs_err", "p90")
BANDS = ("AT", "MIDDLE", "AWAY", "POOLED")

# Reference arm is A', as in exp001 and exp002.
REFERENCE = "A_prime"
COMPARISONS = {
    "exp001": [("C", "A_prime"), ("B", "C"), ("A", "A_prime")],
    "exp002": [("E", "A_prime"), ("D", "E"), ("C", "A_prime")],
}


def by_arm(rows: list[dict]) -> dict[str, dict[int, dict]]:
    out: dict[str, dict[int, dict]] = {}
    for r in rows:
        out.setdefault(r["arm"], {})[r["seed"]] = r
    return out


def compare(
    arms: dict[str, dict[int, dict]], x: str, y: str, band: str, metric: str
) -> dict[str, Any] | None:
    """exp001's two-clause bar on ``x`` minus ``y``, within one band.

    The reference for the materiality floor is ``y`` — the second named arm — which
    matches how exp001 wrote every comparison (differences are taken against the
    arm the floor is scaled by).
    """
    if x not in arms or y not in arms:
        return None
    seeds = sorted(set(arms[x]) & set(arms[y]))
    a = np.array([arms[x][s]["final"][band][metric] for s in seeds], dtype=float)
    b = np.array([arms[y][s]["final"][band][metric] for s in seeds], dtype=float)
    if not (np.isfinite(a).all() and np.isfinite(b).all()):
        return None
    d = a - b
    mean_d = float(np.mean(d))
    spread = float(np.std(d, ddof=1))
    floor = MATERIALITY * float(np.mean(b))
    bar = max(spread, floor)
    return {
        "seeds": len(seeds),
        f"{x}_mean": float(np.mean(a)),
        f"{y}_mean": float(np.mean(b)),
        "mean_diff": mean_d,
        "sd_diff": spread,
        "materiality_floor": floor,
        "bar": bar,
        "binds": "spread" if spread >= floor else "materiality",
        "x_bar": abs(mean_d) / bar if bar > 0 else float("inf"),
        "distinguishable": bool(abs(mean_d) > bar),
        "direction": f"{x}_worse" if mean_d > 0 else f"{x}_better",
        "n_pixels": float(np.mean([arms[y][s]["final"][band]["n"] for s in seeds])),
    }


def block(rows: list[dict], comparisons: list[tuple[str, str]]) -> dict[str, Any]:
    arms = by_arm(rows)
    out: dict[str, Any] = {}
    for x, y in comparisons:
        key = f"{x}_vs_{y}"
        out[key] = {band: {m: compare(arms, x, y, band, m) for m in METRICS} for band in BANDS}
    out["_arm_means"] = {
        arm: {
            band: {
                m: float(np.mean([r["final"][band][m] for r in seeds.values()])) for m in METRICS
            }
            for band in BANDS
        }
        for arm, seeds in arms.items()
    }
    out["_termination"] = {
        arm: {
            "steps_taken_mean": float(np.mean([r["steps_taken"] for r in seeds.values()])),
            "terminated_early": int(
                sum(1 for r in seeds.values() if r["terminated_at"] is not None)
            ),
            "distinct_fixations_mean": float(
                np.mean([r["distinct_fixations"] for r in seeds.values()])
            ),
        }
        for arm, seeds in arms.items()
    }
    return out


def scanpath_agreement(free: list[dict], masked: list[dict]) -> dict[str, Any]:
    """Fraction of fixations the masked and unmasked arms share, as exp001 reported."""
    f, m = by_arm(free), by_arm(masked)
    out: dict[str, Any] = {}
    for arm in sorted(set(f) & set(m)):
        agree = total = 0
        for seed in sorted(set(f[arm]) & set(m[arm])):
            a = [tuple(p) for p in f[arm][seed]["scanpath"]]
            b = [tuple(p) for p in m[arm][seed]["scanpath"]]
            n = min(len(a), len(b))
            agree += sum(1 for i in range(n) if a[i] == b[i])
            total += n
        out[arm] = {"agreement": agree / total if total else float("nan"), "compared": total}
    return out


def main() -> None:
    data = json.loads((HERE / "results.json").read_text())
    verdicts: dict[str, Any] = {
        "experiment": data["experiment"],
        "bands": data["bands"],
        "environment": data["environment"],
        "reference_arm": REFERENCE,
    }

    for label in ("exp001", "exp002"):
        verdicts[label] = block(data[label]["rows"], COMPARISONS[label])
        verdicts[label]["_config"] = {k: data[label][k] for k in ("arms", "seeds", "budget")}

    ctrl = data["control_masked_steering_POST_HOC"]
    verdicts["control_masked_steering_POST_HOC"] = {}
    for label in ("exp001", "exp002"):
        comps = [c for c in COMPARISONS[label] if c[0] != "E" and c[0] != "D"]
        verdicts["control_masked_steering_POST_HOC"][label] = {
            "verdicts": block(ctrl[label], comps),
            "scanpath_agreement_vs_unmasked": scanpath_agreement(data[label]["rows"], ctrl[label]),
        }

    (HERE / "verdicts.json").write_text(json.dumps(verdicts, indent=2))
    dest = REPO / "results" / "exp005_stratified_reanalysis"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "verdicts.json").write_text(json.dumps(verdicts, indent=2))

    # --- readable summary ----------------------------------------------------
    for label in ("exp001", "exp002"):
        cfg = verdicts[label]["_config"]
        print(
            f"\n=== {label}: arms {cfg['arms']}, {len(cfg['seeds'])} seeds, "
            f"budget {cfg['budget']} ==="
        )
        for key in [f"{x}_vs_{y}" for x, y in COMPARISONS[label]]:
            print(f"\n  {key}")
            for metric in METRICS:
                print(f"    {metric}")
                for band in BANDS:
                    v = verdicts[label][key][band][metric]
                    if v is None:
                        continue
                    mark = "DIST  " if v["distinguishable"] else "indist"
                    print(
                        f"      {band:7s} n={v['n_pixels']:7.0f} "
                        f"diff={v['mean_diff']:+.6f} sd={v['sd_diff']:.6f} "
                        f"floor={v['materiality_floor']:.6f} bar={v['bar']:.6f} "
                        f"({v['x_bar']:5.2f}x, {v['binds']:11s}) {mark} {v['direction']}"
                    )

    print("\n=== POST-HOC control: selection masked to AWAY, scored on AWAY ===")
    for label in ("exp001", "exp002"):
        c = verdicts["control_masked_steering_POST_HOC"][label]
        print(f"\n  {label} scanpath agreement vs unmasked:")
        for arm, a in c["scanpath_agreement_vs_unmasked"].items():
            print(f"    {arm:8s} {a['agreement']:.4f} over {a['compared']} fixations")
        print(f"  {label} termination under masking:")
        for arm, t in c["verdicts"]["_termination"].items():
            print(
                f"    {arm:8s} steps {t['steps_taken_mean']:.1f}, "
                f"{t['terminated_early']} seeds terminated early, "
                f"distinct {t['distinct_fixations_mean']:.1f}"
            )
        for key in c["verdicts"]:
            if key.startswith("_"):
                continue
            for metric in METRICS:
                v = c["verdicts"][key]["AWAY"][metric]
                if v is None:
                    continue
                mark = "DIST  " if v["distinguishable"] else "indist"
                print(
                    f"    {key:18s} {metric:14s} AWAY diff={v['mean_diff']:+.6f} "
                    f"bar={v['bar']:.6f} ({v['x_bar']:5.2f}x) {mark}"
                )

    print(f"\nwrote {HERE / 'verdicts.json'}")


if __name__ == "__main__":
    main()
