"""exp008 — effect size per level, and the shape of the trend across levels.

Every comparison is computed WITHIN its level. Only the resulting effect sizes are
compared across levels, and the x-axis is the measured ``left_occluded_fraction``,
not ``k``.

``mean_diff`` and ``bar`` are reported separately at every level, because both
move across the sweep and a ratio alone cannot say which did.
"""

from __future__ import annotations

import itertools
import json
import pathlib
from typing import Any

import numpy as np

HERE = pathlib.Path(__file__).parent
REPO = HERE.resolve().parents[1]
MATERIALITY = 0.02
METRICS = ("median_abs_err", "p90")
BANDS = ("AT", "MIDDLE", "AWAY", "POOLED")
COMPARISONS = [("E", "A_prime"), ("D", "E")]


def compare(rows: list[dict], k: int, x: str, y: str, band: str, metric: str) -> dict[str, Any]:
    """exp001's two-clause bar, within one level and one band."""
    ax = {r["seed"]: r for r in rows if r["k"] == k and r["arm"] == x}
    ay = {r["seed"]: r for r in rows if r["k"] == k and r["arm"] == y}
    seeds = sorted(set(ax) & set(ay))
    a = np.array([ax[s]["final"][band][metric] for s in seeds], dtype=float)
    b = np.array([ay[s]["final"][band][metric] for s in seeds], dtype=float)
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
        "n_pixels": float(np.mean([ay[s]["final"][band]["n"] for s in seeds])),
        # A view of the effect that the bar cannot inflate or deflate. x_bar is a
        # ratio of a difference to a spread, and BOTH move across this sweep; this
        # is the ratio of the arm means themselves, which moves only if the arms do.
        "arm_mean_ratio": float(np.mean(a) / np.mean(b)) if np.mean(b) > 0 else float("nan"),
    }


def trend(xs: list[float], ys: list[float]) -> dict[str, Any]:
    """The shape of a four-point series, and an honest statement of its limits.

    Monotonicity is a definite property of four points and is reported as one.
    The fit is reported because the specification asked for a slope, and it is
    reported with the warning that four points cannot distinguish linear from
    saturating.
    """
    inc = all(b > a for a, b in itertools.pairwise(ys))
    dec = all(b < a for a, b in itertools.pairwise(ys))
    shape = "monotone_increase" if inc else ("monotone_decrease" if dec else "non_monotone")
    peak = int(np.argmax(ys))
    lin = np.polyfit(xs, ys, 1)
    lin_pred = np.polyval(lin, xs)
    ss = float(np.sum((np.array(ys) - np.mean(ys)) ** 2))
    r2_lin = 1.0 - float(np.sum((ys - lin_pred) ** 2)) / ss if ss > 0 else float("nan")
    log = np.polyfit(np.log(xs), np.log(ys), 1) if min(ys) > 0 else [float("nan")] * 2
    return {
        "shape": shape,
        "values": ys,
        "max_over_min": float(max(ys) / min(ys)) if min(ys) > 0 else float("inf"),
        "peak_at_index": peak,
        "peak_at_fraction": xs[peak],
        "linear_slope_per_unit_fraction": float(lin[0]),
        "linear_r2": r2_lin,
        "log_log_exponent": float(log[0]),
        "caveat": "four points; linear and saturating are not distinguishable here",
    }


def main() -> None:
    data = json.loads((HERE / "results.json").read_text())
    rows, geom, levels = data["rows"], data["geometry"], data["levels_k"]
    fracs = [geom[f"k{k}"]["left_occluded_fraction"] for k in levels]

    v: dict[str, Any] = {
        "experiment": data["experiment"],
        "levels_k": levels,
        "x_axis": "left_occluded_fraction",
        "achieved": {
            f"k{k}": {
                "left_occluded_fraction": geom[f"k{k}"]["left_occluded_fraction"],
                "right_unmatched_fraction": geom[f"k{k}"]["right_unmatched_fraction"],
                "border_fraction": geom[f"k{k}"]["border_fraction"],
                "card_area_fraction": geom[f"k{k}"]["card_area_fraction"],
                "band_composition": geom[f"k{k}"]["band_composition"],
            }
            for k in levels
        },
        "rendered_with": data["rendered_with"],
        "environment": data["environment"],
        "per_level": {},
        "trend": {},
    }

    for x, y in COMPARISONS:
        key = f"{x}_vs_{y}"
        v["per_level"][key] = {
            f"k{k}": {band: {m: compare(rows, k, x, y, band, m) for m in METRICS} for band in BANDS}
            for k in levels
        }
        v["trend"][key] = {
            m: trend(fracs, [v["per_level"][key][f"k{k}"]["POOLED"][m]["x_bar"] for k in levels])
            for m in METRICS
        }
        v["trend"][key]["raw_mean_diff"] = {
            m: [v["per_level"][key][f"k{k}"]["POOLED"][m]["mean_diff"] for k in levels]
            for m in METRICS
        }
        v["trend"][key]["bar"] = {
            m: [v["per_level"][key][f"k{k}"]["POOLED"][m]["bar"] for k in levels] for m in METRICS
        }
        v["trend"][key]["arm_mean_ratio"] = {
            m: trend(
                fracs,
                [v["per_level"][key][f"k{k}"]["POOLED"][m]["arm_mean_ratio"] for k in levels],
            )
            for m in METRICS
        }
        # Saturation check: if every arm converges on one value the comparison has
        # stopped being askable, whatever the bar says.
        v["trend"][key]["arm_spread_p90"] = [
            float(
                max(v["per_level"][key][f"k{k}"]["POOLED"]["p90"][f"{n}_mean"] for n in (x, y))
                - min(v["per_level"][key][f"k{k}"]["POOLED"]["p90"][f"{n}_mean"] for n in (x, y))
            )
            for k in levels
        ]

    (HERE / "verdicts.json").write_text(json.dumps(v, indent=2))
    dest = REPO / "results" / "exp008_occlusion_sweep"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "verdicts.json").write_text(json.dumps(v, indent=2))

    # --- report --------------------------------------------------------------
    print("=== achieved geometry per level ===")
    print(f"{'k':>3} {'left occl':>10} {'right':>8} {'border':>8} {'card area':>10} {'AT band':>9}")
    for k in levels:
        a = v["achieved"][f"k{k}"]
        print(
            f"{k:>3} {a['left_occluded_fraction'] * 100:>9.2f}% "
            f"{a['right_unmatched_fraction'] * 100:>7.2f}% {a['border_fraction'] * 100:>7.2f}% "
            f"{a['card_area_fraction'] * 100:>9.1f}% {a['band_composition']['AT']:>9}"
        )

    for x, y in COMPARISONS:
        key = f"{x}_vs_{y}"
        print(f"\n=== {key} — POOLED, per level ===")
        for m in METRICS:
            print(f"  {m}")
            for k in levels:
                c = v["per_level"][key][f"k{k}"]["POOLED"][m]
                f = v["achieved"][f"k{k}"]["left_occluded_fraction"]
                print(
                    f"    k={k} occl={f * 100:5.2f}%  diff={c['mean_diff']:+.6f} "
                    f"bar={c['bar']:.6f} ({c['binds']:11s}) -> {c['x_bar']:7.2f}x "
                    f"{'DIST' if c['distinguishable'] else 'ind '} {c['direction']}"
                )
            ratios = [v["per_level"][key][f"k{k}"]["POOLED"][m]["arm_mean_ratio"] for k in levels]
            print(
                "      arm-mean ratio: "
                + "  ".join(f"{r:.2f}" for r in ratios)
                + f"   ({v['trend'][key]['arm_mean_ratio'][m]['shape']})"
            )
            t = v["trend"][key][m]
            print(
                f"    TREND: {t['shape']}, max/min {t['max_over_min']:.2f}, "
                f"slope {t['linear_slope_per_unit_fraction']:+.2f}/unit-fraction, "
                f"r2 {t['linear_r2']:.3f}, log-log exponent {t['log_log_exponent']:+.2f}"
            )

    print("\n=== band series (x_bar) — composition changes with occlusion ===")
    for x, y in COMPARISONS:
        key = f"{x}_vs_{y}"
        for m in METRICS:
            print(f"  {key} {m}")
            for k in levels:
                cells = " ".join(
                    f"{b} {v['per_level'][key][f'k{k}'][b][m]['x_bar']:7.2f}x" for b in BANDS
                )
                print(f"    k={k}: {cells}")
    print(f"\nwrote {HERE / 'verdicts.json'}")


if __name__ == "__main__":
    main()
