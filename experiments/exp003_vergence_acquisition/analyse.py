"""Apply exp001's declared bar to exp003, under exp003's coverage rule.

The bar is reused verbatim:

    distinguishable on a metric iff |mean(d_s)| > max( sd(d_s), 0.02 * mean(M_base) )

    python -m experiments.exp003_vergence_acquisition.analyse
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import numpy as np

RESULTS = pathlib.Path("results/exp003_vergence_acquisition/results.json")
PRIMARY = ("median_abs_err", "p90")
SECONDARY = ("rmse",)
RELATIVE_FLOOR = 0.02
ARMS = ("W", "N", "V")


def vals(res: dict[str, Any], arm: str, region: str, metric: str) -> np.ndarray:
    return np.array([row["arms"][arm][region][metric] for row in res["per_seed"]])


def compare(res, base: str, other: str, region: str, metric: str) -> dict[str, Any]:
    ma, mb = vals(res, base, region, metric), vals(res, other, region, metric)
    d = mb - ma
    mean_d, sd_d = float(np.mean(d)), float(np.std(d, ddof=1))
    floor = RELATIVE_FLOOR * float(np.mean(ma))
    bar = max(sd_d, floor)
    return {
        "region": region,
        "metric": metric,
        "baseline_mean": float(np.mean(ma)),
        "other_mean": float(np.mean(mb)),
        "mean_diff": mean_d,
        "sd_diff": sd_d,
        "materiality_bar": floor,
        "bar": bar,
        "fraction_of_bar": abs(mean_d) / bar if bar else float("inf"),
        "distinguishable": abs(mean_d) > bar,
        "direction": "better" if mean_d < 0 else "worse",
    }


def report_pair(res, base: str, other: str, region: str) -> dict[str, Any]:
    print(f"\n--- {other} against {base}, on the {region} (paired, n={len(res['per_seed'])}) ---")
    rows = {}
    for m in PRIMARY + SECONDARY:
        c = compare(res, base, other, region, m)
        rows[m] = c
        tag = "PRIMARY  " if m in PRIMARY else "secondary"
        mark = "DISTINGUISHABLE" if c["distinguishable"] else "indistinguishable"
        print(
            f"  {tag} {m:16s} {base}={c['baseline_mean']:.5f} {other}={c['other_mean']:.5f}  "
            f"diff={c['mean_diff']:+.5f} bar={c['bar']:.5f} ({c['fraction_of_bar']:.2f}x) -> {mark}"
            + (f" [{other} {c['direction']}]" if c["distinguishable"] else "")
        )
    ind = not any(rows[m]["distinguishable"] for m in PRIMARY)
    print(f"  VERDICT: {'INDISTINGUISHABLE' if ind else 'DISTINGUISHABLE'}")
    return {"rows": rows, "indistinguishable_on_primary": ind}


def main() -> None:
    res = json.loads(RESULTS.read_text())
    n = len(res["per_seed"])
    print(
        f"seeds={res['seeds']}\nbudget={res['budget']}  policy={res['policy']}  "
        f"half_width={res['half_width_px']} px"
    )

    print("\n=== THE INTERSECTION — isolates quality (primary) ===")
    print(f"{'arm':4s} {'median|err|':>12s} {'p90':>9s} {'rmse':>9s}")
    for a in ARMS:
        print(
            f"{a:4s} {np.mean(vals(res, a, 'intersection', 'median_abs_err')):12.5f} "
            f"{np.mean(vals(res, a, 'intersection', 'p90')):9.4f} "
            f"{np.mean(vals(res, a, 'intersection', 'rmse')):9.4f}"
        )
    print(f"  intersection size: {np.mean([r['intersection_n'] for r in res['per_seed']]):.0f} px")

    print("\n=== EACH ARM'S EXCLUDED SET — says what coverage was bought ===")
    print(f"{'arm':4s} {'n':>8s} {'median|err|':>12s} {'p90':>9s}")
    for a in ARMS:
        print(
            f"{a:4s} {np.mean(vals(res, a, 'excluded', 'n')):8.0f} "
            f"{np.nanmean(vals(res, a, 'excluded', 'median_abs_err')):12.5f} "
            f"{np.nanmean(vals(res, a, 'excluded', 'p90')):9.4f}"
        )

    print("\n=== POOLED — CONFOUNDED, reported so the record cannot be misread ===")
    print(f"{'arm':4s} {'n':>8s} {'median|err|':>12s} {'p90':>9s}   <- mixes quality with coverage")
    for a in ARMS:
        print(
            f"{a:4s} {np.mean(vals(res, a, 'pooled_CONFOUNDED', 'n')):8.0f} "
            f"{np.mean(vals(res, a, 'pooled_CONFOUNDED', 'median_abs_err')):12.5f} "
            f"{np.mean(vals(res, a, 'pooled_CONFOUNDED', 'p90')):9.4f}"
        )

    print("\n=== COST — reported beside the error, not after it ===")
    cost_hdr = f"{'arm':4s} {'hypotheses':>11s} {'front ends':>11s}"
    print(f"{cost_hdr} {'windows':>8s} {'coverage(union)':>16s}")
    for a in ARMS:
        h = np.mean([r["arms"][a]["hypotheses"] for r in res["per_seed"]])
        w = np.mean([r["arms"][a]["distinct_windows"] for r in res["per_seed"]])
        u = np.mean([r["arms"][a]["valid_union"] for r in res["per_seed"]])
        fe = 1 if a == "W" else (2 if a == "N" else 1 + res["budget"])
        print(f"{a:4s} {h:11.0f} {fe:11d} {w:8.1f} {u:16.0f}")

    verdicts: dict[str, Any] = {}
    print("\n" + "=" * 74)
    print("FALSIFIERS — on the intersection, per the coverage rule")
    print("=" * 74)
    verdicts["V_vs_W_intersection"] = report_pair(res, "W", "V", "intersection")
    verdicts["V_vs_N_intersection"] = report_pair(res, "N", "V", "intersection")
    verdicts["N_vs_W_intersection"] = report_pair(res, "W", "N", "intersection")

    out = pathlib.Path("results/exp003_vergence_acquisition/verdicts.json")
    out.write_text(json.dumps({"n_seeds": n, "verdicts": verdicts}, indent=1))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
