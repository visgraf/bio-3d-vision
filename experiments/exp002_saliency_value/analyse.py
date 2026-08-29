"""Apply exp001's declared bar to exp002, and re-check exp001's C_vs_B.

The bar is reused verbatim, not redeclared:

    distinguishable on a metric iff
        |mean(d_s)| > max( sd(d_s), 0.02 * mean(M_baseline) )

    python -m experiments.exp002_saliency_value.analyse
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import numpy as np

EXP002 = pathlib.Path("results/exp002_saliency_value/results.json")
EXP001 = pathlib.Path("experiments/exp001_gaze_objective/results.json")
PRIMARY = ("median_abs_err", "p90")
SECONDARY = ("rmse",)
RELATIVE_FLOOR = 0.02  # exp001's materiality floor, reused


def at(res: dict[str, Any], arm: str, metric: str, step: int | None = None) -> np.ndarray:
    """Metric per seed, at ``step`` (1-indexed) or at the final fixation."""
    out = []
    for r in res["arms"][arm]:
        t = r["trajectory"]
        out.append(t[-1][metric] if step is None else t[step - 1][metric])
    return np.array(out)


def compare(res, base: str, other: str, metric: str, step: int | None = None) -> dict[str, Any]:
    ma, mb = at(res, base, metric, step), at(res, other, metric, step)
    d = mb - ma
    mean_d, sd_d = float(np.mean(d)), float(np.std(d, ddof=1))
    floor = RELATIVE_FLOOR * float(np.mean(ma))
    bar = max(sd_d, floor)
    return {
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


def convergence_index(res, base: str, other: str, budget: int) -> dict[str, Any]:
    """Smallest k such that the pair is indistinguishable at every step >= k."""
    out: dict[str, Any] = {}
    for m in PRIMARY:
        flags = [
            compare(res, base, other, m, step=k)["distinguishable"] for k in range(1, budget + 1)
        ]
        k = None
        for i in range(len(flags)):
            if not any(flags[i:]):
                k = i + 1
                break
        out[m] = k
    both = None
    for i in range(budget):
        if all(
            not compare(res, base, other, m, step=k)["distinguishable"]
            for m in PRIMARY
            for k in range(i + 1, budget + 1)
        ):
            both = i + 1
            break
    out["both_primary"] = both
    return out


def report_pair(res, base: str, other: str, step: int | None, label: str) -> dict[str, Any]:
    where = "final" if step is None else f"step {step}"
    print(f"\n=== {other} against {base} ({where}, paired, n={len(res['seeds'])}) ===")
    rows = {}
    for m in PRIMARY + SECONDARY:
        c = compare(res, base, other, m, step)
        rows[m] = c
        tag = "PRIMARY  " if m in PRIMARY else "secondary"
        mark = "DISTINGUISHABLE" if c["distinguishable"] else "indistinguishable"
        print(
            f"  {tag} {m:16s} {base}={c['baseline_mean']:.5f} {other}={c['other_mean']:.5f}  "
            f"diff={c['mean_diff']:+.5f} bar={c['bar']:.5f} ({c['fraction_of_bar']:.2f}x) -> {mark}"
            + (f" [{c['direction']}]" if c["distinguishable"] else "")
        )
    ind = not any(rows[m]["distinguishable"] for m in PRIMARY)
    print(f"  VERDICT: {'INDISTINGUISHABLE' if ind else 'DISTINGUISHABLE'}")
    return {"label": label, "rows": rows, "indistinguishable_on_primary": ind}


def main() -> None:
    res = json.loads(EXP002.read_text())
    budget = res["budget"]
    print(f"seeds={res['seeds']}\nbudget={budget}  raster_pitch={res['raster_pitch']:.3f}")

    print("\n=== per-arm final metrics (mean over 16 seeds, step 40) ===")
    hdr = f"{'arm':9s} {'median|err|':>12s} {'p90':>9s} {'rmse':>9s}"
    print(f"{hdr} {'distinct':>9s} {'onInvalid':>10s}")
    for arm in res["arms"]:
        runs = res["arms"][arm]
        print(
            f"{arm:9s} {np.mean(at(res, arm, 'median_abs_err')):12.5f} "
            f"{np.mean(at(res, arm, 'p90')):9.4f} {np.mean(at(res, arm, 'rmse')):9.4f} "
            f"{np.mean([r['distinct_fixations'] for r in runs]):9.2f} "
            f"{np.mean([r['fixations_on_invalid'] for r in runs]):10.2f}"
        )

    verdicts = {}
    for label, base, other in (
        ("E_vs_A_prime", "A_prime", "E"),
        ("E_vs_C", "C", "E"),
        ("D_vs_E", "E", "D"),
        ("A_prime_vs_C", "A_prime", "C"),
    ):
        verdicts[label] = report_pair(res, base, other, None, label)
        ci = convergence_index(res, base, other, budget)
        print(f"  convergence index (indistinguishable from here on): {ci}")
        verdicts[label]["convergence_index"] = ci

    print("\n" + "=" * 72)
    print("exp001 re-check: C_vs_B at step 18, now with 16 seeds")
    print("=" * 72)
    verdicts["C_vs_B_recheck"] = report_pair(res, "C", "B", 18, "C_vs_B_recheck")

    # harness check: seeds 0-7 at step 18 must reproduce exp001
    if EXP001.exists():
        e1 = json.loads(EXP001.read_text())
        print("\n=== harness check: seeds 0-7 at step 18 against exp001 ===")
        ok = True
        for arm in ("A", "A_prime", "B", "C"):
            a = [r["final"]["median_abs_err"] for r in e1["arms"][arm]]
            b = [r["at_exp001_endpoint"]["median_abs_err"] for r in res["arms"][arm][:8]]
            same = np.allclose(a, b, rtol=0, atol=1e-12)
            ok &= same
            delta = float(np.max(np.abs(np.array(a) - np.array(b))))
            word = "IDENTICAL" if same else "DIFFERS"
            print(f"  {arm:8s} exp001 vs exp002 seeds 0-7: {word}  max|d|={delta:.3e}")
        print(f"  harness reproduces exp001: {ok}")
        verdicts["harness_reproduces_exp001"] = bool(ok)

    out = pathlib.Path("results/exp002_saliency_value/verdicts.json")
    out.write_text(json.dumps(verdicts, indent=1))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
