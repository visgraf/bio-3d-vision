"""exp011 — the three questions, each with its own table and its own verdict.

`mean_diff` and `bar` are reported SEPARATELY at every level, never `x_bar`
alone: exp008 showed a verdict flipping on the denominator while the effect grew,
and exp010 showed the same shape within its bands.

Arms are compared WITHIN a level. Effect sizes are compared across levels. No
cell set crosses a level, because coverage moves violently between them.
"""

from __future__ import annotations

import collections
import json
import pathlib
from typing import Any

import numpy as np

HERE = pathlib.Path(__file__).parent
REPO = HERE.resolve().parents[1]
MATERIALITY = 0.02
BANDS = ("AT", "MIDDLE", "AWAY", "POOLED")
EXP010 = {  # measured at cdd5a85, 8 seeds, k=4. Restated for question 1.
    "AT": {"mean_diff": -0.01396, "sd": 0.01459, "x_bar": 0.96},
    "MIDDLE": {"mean_diff": -0.00996, "sd": 0.00383, "x_bar": 2.60},
    "AWAY": {"mean_diff": -0.00458, "sd": 0.00108, "x_bar": 4.26},
    "POOLED": {"mean_diff": -0.01122, "sd": 0.00816, "x_bar": 1.37},
}


def compare(closed: np.ndarray, open_: np.ndarray) -> dict[str, Any]:
    """exp001's two-clause bar. ``d = CLOSED - OPEN``; negative is CLOSED better.

    ``bar`` is ``np.std(d, ddof=1)`` — a SAMPLE STANDARD DEVIATION, not a standard
    error. It has no ``1/sqrt(n)``, so ``x_bar`` is an effect size and the bar is a
    threshold at ``d = 1``. Adding seeds refines the estimate; it does not shrink
    the bar. Verified in exp001, exp005, exp007 and exp008.
    """
    d = closed - open_
    mean, sd = float(np.mean(d)), float(np.std(d, ddof=1))
    floor = MATERIALITY * float(np.mean(open_))
    bar = max(sd, floor)
    return {
        "n_seeds": int(len(d)),
        "open": float(np.mean(open_)),
        "closed": float(np.mean(closed)),
        "mean_diff": mean,
        "sd": sd,
        "materiality": floor,
        "bar": bar,
        "binds": "sd" if sd >= floor else "materiality",
        "distinguishable": bool(abs(mean) > bar),
        "direction": "CLOSED worse" if mean > 0 else "CLOSED better",
        "x_bar": float(abs(mean) / bar) if bar else float("nan"),
        "seeds_favouring_closed": int(np.sum(d < 0)),
    }


def main() -> None:
    src = REPO / "results" / "exp011_consolidation" / "results.json"
    if not src.exists():
        src = HERE / "results.json"
    data = json.loads(src.read_text())
    levels = data["levels_k"]
    seeds = data["seeds"]
    by: dict[tuple, dict[str, dict]] = collections.defaultdict(dict)
    for r in data["rows"]:
        by[(r["k"], r["seed"])][r["arm"]] = r
    frac = {int(k): v for k, v in data["left_occluded_fraction"].items()}

    out: dict[str, Any] = {
        "experiment": "exp011_consolidation",
        "materiality": MATERIALITY,
        "levels_k": levels,
        "left_occluded_fraction": frac,
        "n_seeds": len(seeds),
        "budget": data["budget"],
        "environment": data["environment"],
        "rendered_with": data.get("rendered_with"),
        "q1_seeds": {},
        "q2_scaling": {},
        "q3_coverage": {},
        "cost": {},
        "completion": {},
    }

    # --- Q1: does the AT effect survive 24 seeds? (at k=4, exp010's level) ----
    for band in BANDS:
        c = np.array([by[(4, s)]["CLOSED"][f"{band}_common"]["median_abs_err"] for s in seeds])
        o = np.array([by[(4, s)]["OPEN"][f"{band}_common"]["median_abs_err"] for s in seeds])
        got = compare(c, o)
        was = EXP010[band]
        got["exp010_n8"] = was
        got["sd_ratio_24_over_8"] = got["sd"] / was["sd"]
        got["effect_ratio_24_over_8"] = got["mean_diff"] / was["mean_diff"]
        # What a sqrt(n) bar WOULD have given, so the reader can see the gap.
        got["x_bar_if_bar_were_standard_error"] = float(
            abs(got["mean_diff"]) / (got["sd"] / np.sqrt(len(seeds)))
        )
        out["q1_seeds"][band] = got

    # --- Q2: does the gain scale with occlusion? -----------------------------
    for band in BANDS:
        out["q2_scaling"][band] = {}
        for k in levels:
            c = np.array([by[(k, s)]["CLOSED"][f"{band}_common"]["median_abs_err"] for s in seeds])
            o = np.array([by[(k, s)]["OPEN"][f"{band}_common"]["median_abs_err"] for s in seeds])
            out["q2_scaling"][band][f"k{k}"] = compare(c, o)

    # --- Q3: coverage, on the declared all-cells yardstick -------------------
    for k in levels:
        cell: dict[str, Any] = {"left_occluded_fraction": frac[k]}
        for arm in ("OPEN", "CLOSED"):
            rows = [by[(k, s)][arm] for s in seeds]
            cell[arm] = {
                "ever_measured_fraction": float(
                    np.mean([r["ever_measured_fraction"] for r in rows])
                ),
                "all_cells_mean_abs_err": float(
                    np.mean([r["POOLED_all"]["mean_abs_err"] for r in rows])
                ),
                "common_median": float(
                    np.mean([r["POOLED_common"]["median_abs_err"] for r in rows])
                ),
                "closed_only_mean_abs_err": float(
                    np.mean([r["POOLED_closed_only"]["mean_abs_err"] for r in rows])
                ),
                "closed_only_n": float(np.mean([r["POOLED_closed_only"]["n"] for r in rows])),
            }
        # The two gains on ONE yardstick, declared before the tables existed.
        allc = np.array([by[(k, s)]["CLOSED"]["POOLED_all"]["mean_abs_err"] for s in seeds])
        allo = np.array([by[(k, s)]["OPEN"]["POOLED_all"]["mean_abs_err"] for s in seeds])
        cell["all_cells_verdict"] = compare(allc, allo)
        commonc = np.array([by[(k, s)]["CLOSED"]["POOLED_common"]["mean_abs_err"] for s in seeds])
        commono = np.array([by[(k, s)]["OPEN"]["POOLED_common"]["mean_abs_err"] for s in seeds])
        # Accuracy term: the shared-cell gain, weighted by the share of cells it acts on.
        share_common = float(np.mean([by[(k, s)]["OPEN"]["common_fraction"] for s in seeds]))
        share_closed_only = float(
            np.mean([by[(k, s)]["CLOSED"]["excluded_own_only"] for s in seeds])
        )
        acc_gain = float(np.mean(commono - commonc)) * share_common
        cov_gain = (
            float(
                np.mean(
                    [
                        by[(k, s)]["OPEN"]["POOLED_closed_only"]["mean_abs_err"]
                        - by[(k, s)]["CLOSED"]["POOLED_closed_only"]["mean_abs_err"]
                        for s in seeds
                    ]
                )
            )
            * share_closed_only
        )
        cell["decomposition"] = {
            "accuracy_term_m": acc_gain,
            "coverage_term_m": cov_gain,
            "share_common": share_common,
            "share_closed_only": share_closed_only,
            "coverage_over_accuracy": cov_gain / acc_gain if acc_gain else float("inf"),
            "total_all_cells_gain_m": float(np.mean(allo - allc)),
        }
        out["q3_coverage"][f"k{k}"] = cell

    for arm in ("OPEN", "CLOSED"):
        rows = [by[(k, s)][arm] for k in levels for s in seeds]
        out["cost"][arm] = {
            "renders": float(np.mean([r["renders"] for r in rows])),
            "render_seconds_at_0p58": float(np.mean([r["renders"] for r in rows])) * 0.58,
            "front_end_seconds": float(np.mean([r["front_end_seconds"] for r in rows])),
        }
        out["completion"][arm] = {
            "runs_reaching_budget": int(sum(r["steps_completed"] == data["budget"] for r in rows)),
            "runs": len(rows),
            "refusals_total": int(sum(r["refusals"] for r in rows)),
            "stopped_early": [r["stopped_at"] for r in rows if r["stopped_at"]],
            "vergence_min": float(np.min([r["vergence_min"] for r in rows])),
            "vergence_max": float(np.max([r["vergence_max"] for r in rows])),
        }

    (HERE / "verdicts.json").write_text(json.dumps(out, indent=2))

    # ---- report -------------------------------------------------------------
    n = out["n_seeds"]
    print(f"exp011 — {n} seeds, budget {out['budget']}, levels {levels}\n")

    print("=== Q1: does the AT effect survive more seeds? (k=4, exp010's level) ===")
    print(
        f"{'band':>7} | {'eff@8':>9} {'eff@24':>9} {'ratio':>6} | {'sd@8':>9} {'sd@24':>9} "
        f"{'ratio':>6} | {'x_bar@8':>8} {'x_bar@24':>9} | verdict"
    )
    for band in BANDS:
        v = out["q1_seeds"][band]
        w = v["exp010_n8"]
        verdict = v["direction"] if v["distinguishable"] else "indistinguishable"
        print(
            f"{band:>7} | {w['mean_diff']:+9.5f} {v['mean_diff']:+9.5f} "
            f"{v['effect_ratio_24_over_8']:6.2f} | {w['sd']:9.5f} {v['sd']:9.5f} "
            f"{v['sd_ratio_24_over_8']:6.2f} | {w['x_bar']:8.2f} {v['x_bar']:9.2f} | {verdict}"
        )
    se = ", ".join(
        f"{b} {out['q1_seeds'][b]['x_bar_if_bar_were_standard_error']:.2f}" for b in BANDS
    )
    print(f"\n  If the bar were a STANDARD ERROR (sd/sqrt(n)), x_bar at {n} seeds would be: {se}")
    print("  It is not. The bar is np.std(d, ddof=1) and has no 1/sqrt(n).")

    print("\n=== Q2: does the gain scale with occlusion? (common set, within level) ===")
    for band in BANDS:
        print(f"  {band}")
        print(
            f"    {'level':>6} {'occl':>7} | {'OPEN':>8} {'CLOSED':>8} {'mean_diff':>10} "
            f"{'sd':>9} {'floor':>9} {'bar':>9} {'binds':>12} {'x_bar':>6} | verdict"
        )
        for k in levels:
            v = out["q2_scaling"][band][f"k{k}"]
            verdict = v["direction"] if v["distinguishable"] else "indistinguishable"
            print(
                f"    {'k' + str(k):>6} {frac[k]:7.4f} | {v['open']:8.4f} {v['closed']:8.4f} "
                f"{v['mean_diff']:+10.5f} {v['sd']:9.5f} {v['materiality']:9.5f} "
                f"{v['bar']:9.5f} {v['binds']:>12} {v['x_bar']:6.2f} | {verdict}"
            )
        print()

    print("=== Q3: coverage, beside the headline — and the declared yardstick ===")
    print(
        f"{'level':>6} {'occl':>7} | {'ever OPEN':>9} {'ever CLOSED':>11} | "
        f"{'ALL-cells OPEN':>14} {'ALL-cells CLOSED':>16} {'x_bar':>6} | "
        f"{'acc term':>9} {'cov term':>9} {'cov/acc':>8}"
    )
    for k in levels:
        c = out["q3_coverage"][f"k{k}"]
        d = c["decomposition"]
        print(
            f"{'k' + str(k):>6} {c['left_occluded_fraction']:7.4f} | "
            f"{c['OPEN']['ever_measured_fraction']:9.4f} "
            f"{c['CLOSED']['ever_measured_fraction']:11.4f} | "
            f"{c['OPEN']['all_cells_mean_abs_err']:14.4f} "
            f"{c['CLOSED']['all_cells_mean_abs_err']:16.4f} "
            f"{c['all_cells_verdict']['x_bar']:6.2f} | "
            f"{d['accuracy_term_m']:9.5f} {d['coverage_term_m']:9.5f} "
            f"{d['coverage_over_accuracy']:8.1f}x"
        )
    print("\n  On the cells OPEN never reached (CLOSED-only), mean abs error:")
    for k in levels:
        c = out["q3_coverage"][f"k{k}"]
        print(
            f"    k{k}: OPEN {c['OPEN']['closed_only_mean_abs_err']:.4f} m (at the prior), "
            f"CLOSED {c['CLOSED']['closed_only_mean_abs_err']:.4f} m, "
            f"n={c['CLOSED']['closed_only_n']:.0f} cells"
        )

    print("\n=== completion and cost ===")
    for arm in ("OPEN", "CLOSED"):
        c, k_ = out["cost"][arm], out["completion"][arm]
        print(
            f"  {arm:6s}: {k_['runs_reaching_budget']}/{k_['runs']} runs reached budget, "
            f"{k_['refusals_total']} refusals | {c['renders']:.0f} renders "
            f"({c['render_seconds_at_0p58']:.2f} s), front end {c['front_end_seconds']:.2f} s | "
            f"vergence {k_['vergence_min']:.4f}-{k_['vergence_max']:.4f}"
        )
    print(f"\nwrote {HERE / 'verdicts.json'}")


if __name__ == "__main__":
    main()
