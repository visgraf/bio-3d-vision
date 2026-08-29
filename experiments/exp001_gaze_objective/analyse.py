"""Apply the pre-registered verdict rule to exp001's results.

Nothing here chooses a threshold. The rule is declared in preregistration.md:

    C is distinguishable from A' on a metric iff
        |mean(d_s)| > max( sd(d_s), 0.02 * mean(M(A', s)) )
    with d_s the per-seed paired difference at the final step.
    The arms are indistinguishable iff neither primary metric is distinguishable.

    python -m experiments.exp001_gaze_objective.analyse
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import numpy as np

RESULTS = pathlib.Path("results/exp001_gaze_objective/results.json")
PRIMARY = ("median_abs_err", "p90")
SECONDARY = ("rmse",)
RELATIVE_FLOOR = 0.02


def finals(res: dict[str, Any], arm: str, metric: str) -> np.ndarray:
    return np.array([r["final"][metric] for r in res["arms"][arm]])


def compare(res: dict[str, Any], a: str, b: str, metric: str) -> dict[str, Any]:
    """Paired comparison of arm ``b`` against baseline arm ``a`` on ``metric``."""
    ma, mb = finals(res, a, metric), finals(res, b, metric)
    d = mb - ma
    mean_d = float(np.mean(d))
    sd_d = float(np.std(d, ddof=1))
    floor = RELATIVE_FLOOR * float(np.mean(ma))
    bar = max(sd_d, floor)
    return {
        "metric": metric,
        "baseline_mean": float(np.mean(ma)),
        "other_mean": float(np.mean(mb)),
        "mean_diff": mean_d,
        "sd_diff": sd_d,
        "spread_bar": sd_d,
        "materiality_bar": floor,
        "bar": bar,
        "distinguishable": abs(mean_d) > bar,
        "direction": "better" if mean_d < 0 else "worse",
        "binding_clause": "spread" if sd_d >= floor else "materiality",
        "per_seed_diff": [float(x) for x in d],
    }


def main() -> None:
    res = json.loads(RESULTS.read_text())
    print(f"seeds={res['seeds']}  budget={res['budget']}  stride={res['stride']}")
    print(f"stride check: {json.dumps(res['stride_check'])}\n")

    print("=== per-arm final metrics (mean over 8 seeds) ===")
    hdr = (
        f"{'arm':9s} {'median|err|':>12s} {'p90':>9s} {'rmse':>9s} {'distinct':>9s} {'wasted':>8s}"
    )
    print(hdr)
    for arm in res["arms"]:
        runs = res["arms"][arm]
        print(
            f"{arm:9s} {np.mean(finals(res, arm, 'median_abs_err')):12.5f} "
            f"{np.mean(finals(res, arm, 'p90')):9.4f} "
            f"{np.mean(finals(res, arm, 'rmse')):9.4f} "
            f"{np.mean([r['distinct_fixations'] for r in runs]):9.2f} "
            f"{np.mean([r['wasted_budget_fraction'] for r in runs]):8.3f}"
        )

    verdicts: dict[str, Any] = {}
    for label, (base, other) in {
        "A_prime_vs_C": ("A_prime", "C"),
        "C_vs_B": ("C", "B"),
        "A_vs_A_prime": ("A", "A_prime"),
        "A_vs_C": ("A", "C"),
    }.items():
        print(f"\n=== {other} against {base} (paired, n=8) ===")
        rows = {}
        for m in PRIMARY + SECONDARY:
            c = compare(res, base, other, m)
            rows[m] = c
            tag = "PRIMARY  " if m in PRIMARY else "secondary"
            mark = "DISTINGUISHABLE" if c["distinguishable"] else "indistinguishable"
            print(
                f"  {tag} {m:16s} {base}={c['baseline_mean']:.5f} {other}={c['other_mean']:.5f}  "
                f"diff={c['mean_diff']:+.5f}  bar={c['bar']:.5f} "
                f"(spread {c['sd_diff']:.5f}, floor {c['materiality_bar']:.5f})  -> {mark}"
                + (f" [{c['direction']}]" if c["distinguishable"] else "")
            )
        indistinguishable = not any(rows[m]["distinguishable"] for m in PRIMARY)
        verdicts[label] = {"rows": rows, "indistinguishable_on_primary": indistinguishable}
        word = "INDISTINGUISHABLE" if indistinguishable else "DISTINGUISHABLE"
        print(f"  VERDICT on primary metrics: {word}")

    print("\n=== A vs C argmax agreement (same state, same candidate grid) ===")
    ag = res["agreement"]
    rates = [a["argmax_agreement_rate"] for a in ag]
    rhos = [a["spearman_mean"] for a in ag]
    print(f"  argmax agreement rate : mean {np.mean(rates):.4f}  per-seed {rates}")
    print(
        f"  Spearman over grid    : mean {np.mean(rhos):+.4f}  range "
        f"[{min(rhos):+.3f}, {max(rhos):+.3f}]"
    )

    print("\n=== B vs C argmax agreement (same state, same candidate grid) ===")
    bc = res.get("agreement_bc", [])
    if bc:
        r2 = [a["argmax_agreement_rate"] for a in bc]
        d2 = [a["median_argmax_distance_px"] for a in bc]
        s2 = [a["spearman_mean"] for a in bc]
        print(f"  argmax agreement rate : mean {np.mean(r2):.4f}  per-seed {r2}")
        print(
            f"  median argmax distance: mean {np.mean(d2):.1f} px  "
            f"(fovea sigma is 34 px, so {np.mean(d2) / 34.0:.1f} sigma apart)"
        )
        print(f"  Spearman over grid    : mean {np.mean(s2):+.4f}")

    out = pathlib.Path("results/exp001_gaze_objective/verdicts.json")
    out.write_text(
        json.dumps(
            {
                "verdicts": verdicts,
                "argmax_agreement_mean": float(np.mean(rates)),
                "spearman_mean": float(np.mean(rhos)),
            },
            indent=1,
        )
    )
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
