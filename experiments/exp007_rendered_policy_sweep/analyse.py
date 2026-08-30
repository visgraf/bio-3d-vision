"""exp007 — apply exp001's bar, then classify each comparison into (a)/(b)/(c)/(d).

The classification is the point. A rendered verdict is only interesting relative
to what the fixture said, and the fixture said two different things depending on
which pixels were scored. The four outcomes are enumerated in the
pre-registration; this file decides which one occurred and reports it.
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

# (x, y, which foreclosure it bears on)
COMPARISONS = [
    ("E", "A_prime", "fc-008"),
    ("D", "E", "fc-008"),
    ("A", "A_prime", "fc-007 supporting"),
    ("V", "W", "fc-010, fc-011"),
]


def index(rows: list[dict]) -> dict[tuple[str, str], dict[int, dict]]:
    out: dict[tuple[str, str], dict[int, dict]] = {}
    for r in rows:
        out.setdefault((r["source"], r["arm"]), {})[r["seed"]] = r
    return out


def compare(
    idx: dict, source: str, x: str, y: str, band: str, metric: str, key: str = "final"
) -> dict[str, Any] | None:
    """exp001's two-clause bar, within one band, on one source."""
    ax, ay = idx.get((source, x)), idx.get((source, y))
    if not ax or not ay:
        return None
    seeds = sorted(set(ax) & set(ay))
    a = np.array([ax[s][key][band][metric] for s in seeds], dtype=float)
    b = np.array([ay[s][key][band][metric] for s in seeds], dtype=float)
    if not (np.isfinite(a).all() and np.isfinite(b).all()):
        return None
    d = a - b
    mean_d, spread = float(np.mean(d)), float(np.std(d, ddof=1))
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
        "n_pixels": float(np.mean([ay[s][key][band]["n"] for s in seeds])),
    }


def classify(rendered: dict, fx_pooled: dict, fx_away: dict) -> dict[str, Any]:
    """Which of the four pre-registered outcomes occurred.

    Precedence: (d) first, then (a)/(b) — which may both hold, and that is
    informative — then (c). A direction flip between two indistinguishable
    verdicts is noise, not (d).
    """
    if rendered is None or fx_pooled is None or fx_away is None:
        return {"outcome": "unavailable"}

    def same(u: dict, v: dict) -> bool:
        return u["distinguishable"] == v["distinguishable"] and (
            not u["distinguishable"] or u["direction"] == v["direction"]
        )

    reversed_vs_pooled = (
        rendered["distinguishable"]
        and fx_pooled["distinguishable"]
        and rendered["direction"] != fx_pooled["direction"]
    )
    a, b = same(rendered, fx_pooled), same(rendered, fx_away)

    if reversed_vs_pooled:
        outcome = "d"
    elif a and b:
        outcome = "a=b"
    elif a:
        outcome = "a"
    elif b:
        outcome = "b"
    else:
        outcome = "c"
    return {
        "outcome": outcome,
        "rendered": {
            k: rendered[k]
            for k in ("x_bar", "distinguishable", "direction", "mean_diff", "bar", "binds")
        },
        "fixture_pooled": {k: fx_pooled[k] for k in ("x_bar", "distinguishable", "direction")},
        "fixture_away": {k: fx_away[k] for k in ("x_bar", "distinguishable", "direction")},
        "reversed_vs_fixture_pooled": bool(reversed_vs_pooled),
    }


def main() -> None:
    data = json.loads((HERE / "results.json").read_text())
    idx = index(data["rows"])

    v: dict[str, Any] = {
        "experiment": data["experiment"],
        "seeds": data["seeds"],
        "budget": data["budget"],
        "bands": data["bands"],
        "lateral_overlap": data["lateral_overlap"],
        "rendered_with": data["rendered_with"],
        "environment": data["environment"],
        "comparisons": {},
        "classification": {},
        "coverage": {},
    }

    idx40 = index(data["rows_budget40"])
    # E-vs-A' and D-vs-E are decided at exp002's budget of 40; A-vs-A' and V-vs-W
    # at exp001's and exp003's 18. See BUDGET_LATTICE in run.py.
    AT_40 = {"E_vs_A_prime", "D_vs_E"}

    for x, y, bears_on in COMPARISONS:
        key = f"{x}_vs_{y}"
        use, budget = (idx40, data["budget_lattice"]) if key in AT_40 else (idx, data["budget"])
        v["comparisons"][key] = {"bears_on": bears_on, "budget": budget}
        for source in ("F", "R"):
            v["comparisons"][key][source] = {
                band: {m: compare(use, source, x, y, band, m) for m in METRICS} for band in BANDS
            }
        v["classification"][key] = {
            "bears_on": bears_on,
            "budget": budget,
            **{
                m: classify(
                    v["comparisons"][key]["R"]["POOLED"][m],
                    v["comparisons"][key]["F"]["POOLED"][m],
                    v["comparisons"][key]["F"]["AWAY"][m],
                )
                for m in METRICS
            },
        }

    # The 18-step lattice figures, kept and labelled: budget-starved, not fc-008.
    v["lattice_at_budget18_STARVED"] = {
        f"{x}_vs_{y}": {
            source: {m: compare(idx, source, x, y, "POOLED", m) for m in METRICS}
            for source in ("F", "R")
        }
        for x, y, _ in COMPARISONS
        if f"{x}_vs_{y}" in AT_40
    }

    # V/W coverage, per exp003's rule
    for source in ("F", "R"):
        vv = idx.get((source, "V"), {})
        ww = idx.get((source, "W"), {})
        seeds = sorted(set(vv) & set(ww))
        v["coverage"][source] = {
            "V_valid": float(np.mean([vv[s]["valid"] for s in seeds])),
            "W_valid": float(np.mean([ww[s]["valid"] for s in seeds])),
            "V_hypotheses": float(np.mean([vv[s]["hypotheses"] for s in seeds])),
            "W_hypotheses": float(np.mean([ww[s]["hypotheses"] for s in seeds])),
            "V_exclusive_median": float(
                np.mean([vv[s]["exclusive"]["median_abs_err"] for s in seeds])
            ),
            "V_exclusive_n": float(np.mean([vv[s]["exclusive"]["n"] for s in seeds])),
            "W_exclusive_median": float(
                np.mean([ww[s]["exclusive"]["median_abs_err"] for s in seeds])
            ),
            "W_exclusive_n": float(np.mean([ww[s]["exclusive"]["n"] for s in seeds])),
            "V_vs_W_own_mask_CONFOUNDED": {
                m: compare(idx, source, "V", "W", "POOLED", m, key="final_own_mask_CONFOUNDED")
                for m in METRICS
            },
        }

    (HERE / "verdicts.json").write_text(json.dumps(v, indent=2))
    dest = REPO / "results" / "exp007_rendered_policy_sweep"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "verdicts.json").write_text(json.dumps(v, indent=2))

    # --- report --------------------------------------------------------------
    ov = data["lateral_overlap"]
    print(
        f"lateral overlap: {ov['right_fraction'] * 100:.2f}% of right-image pixels "
        f"unmatched, runs to {ov['max_run_px']} px; "
        f"{ov['left_fraction'] * 100:.2f}% of left pixels occluded\n"
    )

    print("=== CLASSIFICATION: which of the four outcomes occurred ===")
    for key, c in v["classification"].items():
        print(f"\n  {key}   (bears on {c['bears_on']}, budget {c['budget']})")
        for m in METRICS:
            k = c[m]
            if k["outcome"] == "unavailable":
                continue
            r, fp, fa = k["rendered"], k["fixture_pooled"], k["fixture_away"]
            flag = "  <<< DIRECTION REVERSAL" if k["reversed_vs_fixture_pooled"] else ""
            print(f"    {m:14s} OUTCOME ({k['outcome']}){flag}")
            print(
                f"      rendered      {r['x_bar']:6.2f}x "
                f"{'DIST' if r['distinguishable'] else 'ind '} {r['direction']:10s} "
                f"diff={r['mean_diff']:+.6f} bar={r['bar']:.6f} ({r['binds']})"
            )
            print(
                f"      fixture POOLED{fp['x_bar']:6.2f}x "
                f"{'DIST' if fp['distinguishable'] else 'ind '} {fp['direction']}"
            )
            print(
                f"      fixture AWAY  {fa['x_bar']:6.2f}x "
                f"{'DIST' if fa['distinguishable'] else 'ind '} {fa['direction']}"
            )

    print("\n=== BAND GRADIENT on each source (median) ===")
    for key in v["comparisons"]:
        print(f"  {key}")
        for source in ("F", "R"):
            xs = []
            for band in ("AT", "MIDDLE", "AWAY", "POOLED"):
                c = v["comparisons"][key][source][band]["median_abs_err"]
                xs.append(f"{band} {c['x_bar']:6.2f}x" if c else f"{band}    n/a")
            print(f"    {source}: " + "  ".join(xs))

    print("\n=== V/W coverage (exp003's rule) ===")
    for source in ("F", "R"):
        c = v["coverage"][source]
        print(
            f"  {source}: V valid {c['V_valid']:.0f} W valid {c['W_valid']:.0f}  "
            f"hypotheses V {c['V_hypotheses']:.0f} W {c['W_hypotheses']:.0f}"
        )
        print(
            f"     V-exclusive n={c['V_exclusive_n']:.0f} median {c['V_exclusive_median']:.4f}   "
            f"W-exclusive n={c['W_exclusive_n']:.0f} median {c['W_exclusive_median']:.4f}"
        )

    print(f"\nwrote {HERE / 'verdicts.json'}")


if __name__ == "__main__":
    main()
