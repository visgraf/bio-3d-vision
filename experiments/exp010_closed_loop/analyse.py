"""exp010 — CLOSED against OPEN, on one common cell set, with the cost beside it.

``mean_diff`` and ``bar`` are reported together and never ``x_bar`` alone: exp008
showed a verdict flipping on the denominator while the effect grew.

The excluded sets are reported separately per exp003, because the arms accumulate
differently and a pooled figure that crosses them measures coverage, not accuracy.
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
METRICS = ("median_abs_err", "p90")


def compare(closed: np.ndarray, open_: np.ndarray) -> dict[str, Any]:
    """exp001's two-clause bar. ``d = CLOSED - OPEN``, so positive is CLOSED worse."""
    d = closed - open_
    mean, sd = float(np.mean(d)), float(np.std(d, ddof=1))
    bar = max(sd, MATERIALITY * float(np.mean(open_)))
    return {
        "closed": float(np.mean(closed)),
        "open": float(np.mean(open_)),
        "mean_diff": mean,
        "sd": sd,
        "materiality": MATERIALITY * float(np.mean(open_)),
        "bar": bar,
        "distinguishable": bool(abs(mean) > bar),
        "direction": "CLOSED worse" if mean > 0 else "CLOSED better",
        "x_bar": float(abs(mean) / bar) if bar else float("nan"),
    }


def main() -> None:
    src = REPO / "results" / "exp010_closed_loop" / "results.json"
    if not src.exists():
        src = HERE / "results.json"
    data = json.loads(src.read_text())
    seeds = list(data["seeds"])
    by: dict[int, dict[str, dict]] = collections.defaultdict(dict)
    for r in data["rows"]:
        by[r["seed"]][r["arm"]] = r

    out: dict[str, Any] = {
        "experiment": "exp010_closed_loop",
        "materiality": MATERIALITY,
        "seeds": seeds,
        "budget": data["budget"],
        "left_occluded_fraction": data["left_occluded_fraction"],
        "environment": data["environment"],
        "rendered_with": data.get("rendered_with"),
        "verdict": {},
        "excluded_sets": {},
        "coverage": {},
        "cost": {},
        "vergence": {},
        "completion": {},
    }

    # --- the comparison, on the COMMON set only ------------------------------
    for band in BANDS:
        out["verdict"][band] = {}
        for metric in METRICS:
            c = np.array([by[s]["CLOSED"][f"{band}_common"][metric] for s in seeds], float)
            o = np.array([by[s]["OPEN"][f"{band}_common"][metric] for s in seeds], float)
            out["verdict"][band][metric] = compare(c, o)
            out["verdict"][band][metric]["n"] = int(
                np.mean([by[s]["CLOSED"][f"{band}_common"]["n"] for s in seeds])
            )

    # --- what the common set excludes, per arm, reported separately ----------
    for arm in ("OPEN", "CLOSED"):
        rows = [by[s][arm] for s in seeds]
        out["excluded_sets"][arm] = {
            "ever_measured_fraction": float(np.mean([r["ever_measured_fraction"] for r in rows])),
            "excluded_own_only": float(np.mean([r["excluded_own_only"] for r in rows])),
            "own_set_POOLED_median": float(
                np.mean([r["POOLED_own"]["median_abs_err"] for r in rows])
            ),
            "own_set_POOLED_p90": float(np.mean([r["POOLED_own"]["p90"] for r in rows])),
        }
    out["excluded_sets"]["common_fraction"] = float(
        np.mean([by[s]["OPEN"]["common_fraction"] for s in seeds])
    )

    # --- the grid-loss budget, which only CLOSED pays ------------------------
    for arm in ("OPEN", "CLOSED"):
        rows = [by[s][arm] for s in seeds]
        vis = [h["visible_fraction"] for r in rows for h in r["history"]]
        out["coverage"][arm] = {
            "ever_measured_fraction": float(np.mean([r["ever_measured_fraction"] for r in rows])),
            "survived_whole_run_fraction": float(np.mean([r["survived_fraction"] for r in rows])),
            "mean_visible_per_fixation": float(np.mean(vis)),
            "min_visible_per_fixation": float(np.min(vis)),
        }
        out["cost"][arm] = {
            "renders": float(np.mean([r["renders"] for r in rows])),
            "measurement_seconds": float(np.mean([r["matcher_seconds"] for r in rows])),
            "front_end_seconds": float(np.mean([r["front_end_seconds"] for r in rows])),
            "front_end_calls": float(np.mean([r["front_end_calls"] for r in rows])),
            "render_seconds_at_0p57": float(np.mean([r["renders"] for r in rows])) * 0.57,
        }
        az = [h["azimuth"] for r in rows for h in r["history"]]
        el = [h["elevation_down"] for r in rows for h in r["history"]]
        v = [h["vergence"] for r in rows for h in r["history"]]
        d = [h["D_fix"] for r in rows for h in r["history"]]
        out["vergence"][arm] = {
            "vergence_min": float(np.min(v)),
            "vergence_max": float(np.max(v)),
            "vergence_final_mean": float(np.mean([r["history"][-1]["vergence"] for r in rows])),
            "D_fix_min": float(np.min(d)),
            "D_fix_max": float(np.max(d)),
            "D_fix_at_clip_fraction": float(np.mean([x >= 7.999 or x <= 0.301 for x in d])),
            "abs_azimuth_max": float(np.max(np.abs(az))),
            "abs_elevation_max": float(np.max(np.abs(el))),
        }
        out["completion"][arm] = {
            "steps_completed": float(np.mean([r["steps_completed"] for r in rows])),
            "seeds_reaching_budget": int(sum(r["steps_completed"] == data["budget"] for r in rows)),
            "refusals_total": int(sum(len(r["refusals"]) for r in rows)),
            "stopped_early": [r["stopped_at"] for r in rows if r["stopped_at"]],
        }

    (HERE / "verdicts.json").write_text(json.dumps(out, indent=2))

    # ---- report -------------------------------------------------------------
    print(
        f"exp010 — {data['budget']} fixations, {len(seeds)} seeds, "
        f"{data['left_occluded_fraction'] * 100:.2f}% left-occluded\n"
    )
    print("=== (d) first: did the loop run to completion? ===")
    for arm in ("OPEN", "CLOSED"):
        c = out["completion"][arm]
        print(
            f"  {arm:6s}: {c['seeds_reaching_budget']}/{len(seeds)} seeds reached budget, "
            f"{c['refusals_total']} refusals, stopped early: {len(c['stopped_early'])}"
        )

    print("\n=== the comparison, COMMON cell set only (d = CLOSED - OPEN) ===")
    print(
        f"{'band':>7} {'metric':>15} | {'OPEN':>8} {'CLOSED':>8} {'mean_diff':>10} "
        f"{'sd':>8} {'materiality':>11} {'bar':>8} {'x_bar':>6} | verdict"
    )
    for band in BANDS:
        for metric in METRICS:
            v = out["verdict"][band][metric]
            verdict = v["direction"] if v["distinguishable"] else "indistinguishable"
            print(
                f"{band:>7} {metric:>15} | {v['open']:8.4f} {v['closed']:8.4f} "
                f"{v['mean_diff']:+10.4f} {v['sd']:8.4f} {v['materiality']:11.4f} "
                f"{v['bar']:8.4f} {v['x_bar']:6.2f} | {verdict}"
            )
        print()

    print("=== the excluded sets, reported separately (exp003) ===")
    e = out["excluded_sets"]
    print(f"  common set: {e['common_fraction']:.3f} of the belief")
    for arm in ("OPEN", "CLOSED"):
        a = e[arm]
        print(
            f"  {arm:6s}: ever measured {a['ever_measured_fraction']:.3f}, "
            f"outside the common set {a['excluded_own_only']:.3f} | "
            f"OWN-set POOLED median {a['own_set_POOLED_median']:.4f} "
            f"p90 {a['own_set_POOLED_p90']:.4f}"
        )
    print("  (OWN-set figures cross different cell sets and are NOT comparable to each other)")

    print("\n=== the grid-loss budget ===")
    for arm in ("OPEN", "CLOSED"):
        c = out["coverage"][arm]
        print(
            f"  {arm:6s}: ever measured {c['ever_measured_fraction']:.3f}, "
            f"survived the whole run {c['survived_whole_run_fraction']:.3f}, "
            f"visible per fixation mean {c['mean_visible_per_fixation']:.3f} "
            f"min {c['min_visible_per_fixation']:.3f}"
        )

    print("\n=== cost, and the vergence (fc-010's mechanism, carried unchanged) ===")
    for arm in ("OPEN", "CLOSED"):
        c, v = out["cost"][arm], out["vergence"][arm]
        print(
            f"  {arm:6s}: {c['renders']:5.1f} renders ({c['render_seconds_at_0p57']:6.2f} s), "
            f"front end {c['front_end_seconds']:6.2f} s in {c['front_end_calls']:4.1f} calls, "
            f"measurement {c['measurement_seconds']:5.2f} s\n"
            f"          vergence {v['vergence_min']:.4f}-{v['vergence_max']:.4f} "
            f"(final {v['vergence_final_mean']:.4f}), "
            f"D_fix {v['D_fix_min']:.2f}-{v['D_fix_max']:.2f}, "
            f"clipped {v['D_fix_at_clip_fraction']:.3f}, "
            f"|az| max {v['abs_azimuth_max']:.4f}, |el| max {v['abs_elevation_max']:.4f}"
        )
    print(f"\nwrote {HERE / 'verdicts.json'}")


if __name__ == "__main__":
    main()
