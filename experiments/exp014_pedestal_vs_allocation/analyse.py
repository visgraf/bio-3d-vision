"""exp014 — how much of CLOSED's accuracy gain survives freezing the pedestal.

All three criteria per exp012 — the sd bar, the sign test with its p, and the
materiality floor — with which one binds named in every cell.
"""

from __future__ import annotations

import collections
import json
import math
import pathlib
from typing import Any

import numpy as np

HERE = pathlib.Path(__file__).parent
REPO = HERE.resolve().parents[1]
MATERIALITY = 0.02
BANDS = ("AT", "MIDDLE", "AWAY", "POOLED")


def sign_test(diff: np.ndarray) -> tuple[int, int, float]:
    nz = diff[diff != 0]
    n = int(nz.size)
    k = int(np.sum(nz < 0))
    if n == 0:
        return 0, 0, float("nan")
    lo = min(k, n - k)
    return k, n, float(min(1.0, 2 * sum(math.comb(n, i) for i in range(lo + 1)) / 2**n))


def compare(x: np.ndarray, y: np.ndarray) -> dict[str, Any]:
    """exp001's bar on ``x - y``, plus the sign test. Negative means x better."""
    d = x - y
    mean, sd = float(np.mean(d)), float(np.std(d, ddof=1))
    floor = MATERIALITY * float(np.mean(y))
    bar = max(sd, floor)
    k, n, p = sign_test(d)
    return {
        "x": float(np.mean(x)),
        "y": float(np.mean(y)),
        "mean_diff": mean,
        "sd": sd,
        "materiality": floor,
        "bar": bar,
        "binds": "sd" if sd >= floor else "materiality",
        "distinguishable": bool(abs(mean) > bar),
        "x_bar": float(abs(mean) / bar) if bar else float("nan"),
        "seeds_favouring_x": k,
        "seeds": n,
        "sign_p": p,
    }


def main() -> None:
    src = REPO / "results" / "exp014_pedestal_vs_allocation" / "results.json"
    if not src.exists():
        src = HERE / "results.json"
    data = json.loads(src.read_text())
    levels, seeds = data["levels_k"], data["seeds"]
    by: dict[tuple, dict[str, dict]] = collections.defaultdict(dict)
    for r in data["rows"]:
        by[(r["k"], r["seed"])][r["arm"]] = r
    frac = {int(k): v for k, v in data["left_occluded_fraction"].items()}

    out: dict[str, Any] = {
        "experiment": "exp014_pedestal_vs_allocation",
        "levels_k": levels,
        "n_seeds": len(seeds),
        "budget": data["budget"],
        "environment": data["environment"],
        "coverage_check": {},
        "decomposition": {},
        "comparisons": {},
        "retention": {},
        "clips": {},
    }

    # --- the pre-registered coverage check ----------------------------------
    checks = data["coverage_check"]
    out["coverage_check"] = {
        "runs": len(checks),
        "ever_measured_identical": int(sum(c["identical"] for c in checks)),
        "common_equals_common_all": int(sum(c["common_equals_common_all"] for c in checks)),
        "max_abs_ever_difference": float(
            max(abs(c["closed_ever"] - c["frozen_ever"]) for c in checks)
        ),
    }

    # OPEN's error on the CLOSED-only cells is the coverage term's reference, and
    # exp014 does not record it: OPEN's own_only set is EMPTY by construction,
    # since common IS OPEN's set. It is taken from exp011, which is legitimate
    # because exp014's OPEN arm reproduces exp011's BIT-IDENTICALLY — max |diff|
    # 0.000e+00 on ever_measured, common_fraction and every band median across all
    # 96 (level, seed) pairs, checked before this line was written.
    e11 = json.loads((REPO / "experiments" / "exp011_consolidation" / "results.json").read_text())
    ref: dict[tuple, float] = {}
    for r in e11["rows"]:
        if r["arm"] == "OPEN":
            ref[(r["k"], r["seed"])] = r["POOLED_closed_only"]["mean_abs_err"]

    for k in levels:
        share_common = float(np.mean([by[(k, s)]["OPEN"]["common_fraction"] for s in seeds]))
        share_own = float(np.mean([by[(k, s)]["CLOSED"]["own_only_fraction"] for s in seeds]))
        cell: dict[str, Any] = {
            "left_occluded_fraction": frac[k],
            "share_common": share_common,
            "share_own_only": share_own,
        }
        for arm in ("CLOSED", "FROZEN"):
            acc = (
                float(
                    np.mean(
                        [
                            by[(k, s)]["OPEN"]["POOLED_common"]["mean_abs_err"]
                            - by[(k, s)][arm]["POOLED_common"]["mean_abs_err"]
                            for s in seeds
                        ]
                    )
                )
                * share_common
            )
            cov = (
                float(
                    np.mean(
                        [
                            ref[(k, s)] - by[(k, s)][arm]["POOLED_own_only"]["mean_abs_err"]
                            for s in seeds
                        ]
                    )
                )
                * share_own
            )
            cell[arm] = {"accuracy_term_m": acc, "coverage_term_m": cov}
        # A RATIO OF TERMS WITH OPPOSITE SIGNS IS NOT A "FRACTION RETAINED", so
        # the sign is reported alongside and the per-band table below is the one to
        # read. A negative accuracy term means the arm is WORSE than OPEN.
        cell["retention"] = (
            cell["FROZEN"]["accuracy_term_m"] / cell["CLOSED"]["accuracy_term_m"]
            if cell["CLOSED"]["accuracy_term_m"]
            else float("nan")
        )
        cell["frozen_accuracy_sign"] = (
            "worse than OPEN" if cell["FROZEN"]["accuracy_term_m"] < 0 else "better"
        )
        out["decomposition"][f"k{k}"] = cell

        out["comparisons"][f"k{k}"] = {}
        for band in BANDS:
            out["comparisons"][f"k{k}"][band] = {}
            for label, (a, b) in (
                ("CLOSED_vs_OPEN", ("CLOSED", "OPEN")),
                ("FROZEN_vs_OPEN", ("FROZEN", "OPEN")),
                ("FROZEN_vs_CLOSED", ("FROZEN", "CLOSED")),
            ):
                xa = np.array(
                    [by[(k, s)][a][f"{band}_common"]["median_abs_err"] for s in seeds], float
                )
                yb = np.array(
                    [by[(k, s)][b][f"{band}_common"]["median_abs_err"] for s in seeds], float
                )
                out["comparisons"][f"k{k}"][band][label] = compare(xa, yb)

        # Retention per band, on the common-set median: how much of CLOSED's gain
        # over OPEN survives. Negative means FROZEN is worse than OPEN.
        out["retention"][f"k{k}"] = {}
        for band in BANDS:
            o = np.array([by[(k, s)]["OPEN"][f"{band}_common"]["median_abs_err"] for s in seeds])
            c = np.array([by[(k, s)]["CLOSED"][f"{band}_common"]["median_abs_err"] for s in seeds])
            f = np.array([by[(k, s)]["FROZEN"][f"{band}_common"]["median_abs_err"] for s in seeds])
            gap = float(np.mean(o - c))
            out["retention"][f"k{k}"][band] = {
                "closed_gain_m": gap,
                "frozen_gain_m": float(np.mean(o - f)),
                "retained_fraction": float(np.mean(o - f) / gap) if gap else float("nan"),
            }

        out["clips"][f"k{k}"] = {
            arm: float(np.mean([by[(k, s)][arm]["zmeas_clip_fraction"] for s in seeds]))
            for arm in ("OPEN", "CLOSED", "FROZEN")
        }

    (HERE / "verdicts.json").write_text(json.dumps(out, indent=2))

    c = out["coverage_check"]
    print("=== the pre-registered coverage check ===")
    print(
        f"  ever_measured identical for CLOSED and FROZEN in "
        f"{c['ever_measured_identical']}/{c['runs']} runs; "
        f"common == common_all in {c['common_equals_common_all']}/{c['runs']}; "
        f"max |difference| {c['max_abs_ever_difference']:.2e}"
    )

    print("\n=== the decomposition, per level (exp011's terms) ===")
    print(
        f"{'level':>6} {'occl':>7} | {'CLOSED acc':>11} {'FROZEN acc':>11} {'retained':>9} | "
        f"{'CLOSED cov':>11} {'FROZEN cov':>11}"
    )
    for k in levels:
        d = out["decomposition"][f"k{k}"]
        print(
            f"{'k' + str(k):>6} {d['left_occluded_fraction']:7.4f} | "
            f"{d['CLOSED']['accuracy_term_m']:11.5f} {d['FROZEN']['accuracy_term_m']:11.5f} "
            f"{d['retention']:9.2f} | {d['CLOSED']['coverage_term_m']:11.5f} "
            f"{d['FROZEN']['coverage_term_m']:11.5f}"
        )

    print("\n=== the three comparisons, common-set median, all three criteria ===")
    for k in levels:
        print(f"  k{k} (occlusion {frac[k]:.4f})")
        print(
            f"    {'band':>7} {'comparison':>18} | {'mean_diff':>10} {'sd':>9} {'floor':>9} "
            f"{'bar':>9} {'binds':>12} {'x_bar':>6} {'sign':>7} {'p':>9} | verdict"
        )
        for band in BANDS:
            for label in ("CLOSED_vs_OPEN", "FROZEN_vs_OPEN", "FROZEN_vs_CLOSED"):
                v = out["comparisons"][f"k{k}"][band][label]
                verdict = (
                    ("better" if v["mean_diff"] < 0 else "worse")
                    if v["distinguishable"]
                    else "indistinguishable"
                )
                print(
                    f"    {band:>7} {label:>18} | {v['mean_diff']:+10.5f} {v['sd']:9.5f} "
                    f"{v['materiality']:9.5f} {v['bar']:9.5f} {v['binds']:>12} "
                    f"{v['x_bar']:6.2f} {v['seeds_favouring_x']:3d}/{v['seeds']:<3d} "
                    f"{v['sign_p']:9.2e} | {verdict}"
                )
        print()

    print("=== retention of CLOSED's gain over OPEN, per band ===")
    print(f"{'level':>6} " + " ".join(f"{b:>10}" for b in BANDS))
    for k in levels:
        row = " ".join(f"{out['retention'][f'k{k}'][b]['retained_fraction']:10.2f}" for b in BANDS)
        print(f"{'k' + str(k):>6} {row}")

    print("\n=== Zmeas clip fraction (where freezing shows up) ===")
    print(f"{'level':>6} {'OPEN':>9} {'CLOSED':>9} {'FROZEN':>9}")
    for k in levels:
        cl = out["clips"][f"k{k}"]
        print(f"{'k' + str(k):>6} {cl['OPEN']:9.4f} {cl['CLOSED']:9.4f} {cl['FROZEN']:9.4f}")
    print(f"\nwrote {HERE / 'verdicts.json'}")


if __name__ == "__main__":
    main()
