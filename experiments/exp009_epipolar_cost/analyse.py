"""exp009 — effect size per fixation, and whether ``d_v`` tracks its prediction.

Two things are kept apart throughout, because pooling them would have produced
the wrong reading of this experiment:

- **Errors** are compared only over directions BOTH arms see. The rectified pair
  points at azimuth zero whatever the gaze, so at eccentric fixations the two arms
  image largely different regions; an unrestricted comparison measures scene
  content.
- **Valid fraction over the whole image is confounded** by the fixture's finite
  extent — as gaze moves off axis both arms look past the cards at empty space,
  and RECT looks less far past them than TOED does. The unconfounded quantity is
  validity CONDITIONAL on a direction both arms see, reported beside it.
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
BANDS = ("ALL", "AT", "AWAY")
METRICS = ("median", "p90")
# Inherited, exp004: a band is AT a discontinuity within 10 px, AWAY beyond 24 px.


def bar_compare(a: np.ndarray, b: np.ndarray) -> dict[str, Any]:
    """exp001's two-clause bar. ``a`` is TOED, ``b`` is RECT; ``d = a - b``."""
    d = a - b
    mean, sd = float(np.mean(d)), float(np.std(d, ddof=1))
    bar = max(sd, MATERIALITY * float(np.mean(b)))
    return {
        "toed": float(np.mean(a)),
        "rect": float(np.mean(b)),
        "mean_diff": mean,
        "sd": sd,
        "materiality": MATERIALITY * float(np.mean(b)),
        "bar": bar,
        "distinguishable": bool(abs(mean) > bar),
        "direction": "TOED worse" if mean > 0 else "TOED better",
        "ratio": float(np.mean(a) / np.mean(b)) if np.mean(b) else float("nan"),
    }


def main() -> None:
    src = REPO / "results" / "exp009_epipolar_cost" / "results.json"
    if not src.exists():
        src = HERE / "results.json"
    data = json.loads(src.read_text())
    seeds = list(data["seeds"])
    by: dict[tuple, dict[str, dict]] = collections.defaultdict(dict)
    for r in data["rows"]:
        by[(r["az"], r["el"], r["seed"])][r["arm"]] = r
    fixations = [tuple(f) for f in data["fixations"]]

    out: dict[str, Any] = {
        "experiment": "exp009_epipolar_cost",
        "materiality": MATERIALITY,
        "seeds": seeds,
        "environment": data["environment"],
        "rendered_with": data.get("rendered_with"),
        "per_fixation": {},
        "timing": {},
    }

    for az, el in fixations:
        key = f"az{az:.2f}_el{el:.2f}"
        cell: dict[str, Any] = {"azimuth": az, "elevation_down": el, "bands": {}}
        for band in BANDS:
            cell["bands"][band] = {}
            for metric in METRICS:
                a = np.array([by[(az, el, s)]["TOED"][band][metric] for s in seeds], float)
                b = np.array([by[(az, el, s)]["RECT"][band][metric] for s in seeds], float)
                cell["bands"][band][metric] = bar_compare(a, b)
        for arm in ("RECT", "TOED"):
            rows = [by[(az, el, s)][arm] for s in seeds]
            cond = [
                r["scored_fraction"] / r["common_fraction"] for r in rows if r["common_fraction"]
            ]
            cell[arm] = {
                "valid_fraction": float(np.mean([r["valid_fraction"] for r in rows])),
                "common_fraction": float(np.mean([r["common_fraction"] for r in rows])),
                "conditional_valid": float(np.mean(cond)),
                "disparity_range": rows[0]["disparity_range"],
                "matcher_seconds": float(np.mean([r["matcher_seconds"] for r in rows])),
            }
        toed = [by[(az, el, s)]["TOED"] for s in seeds]
        cell["dv_pred_max"] = float(np.mean([r["dv_pred_max"] for r in toed]))
        cell["dv_pred_rms"] = float(np.mean([r["dv_pred_rms"] for r in toed]))
        cell["dv"] = {}
        for band in BANDS:
            vals = [r["dv"][band] for r in toed if band in r.get("dv", {})]
            if not vals:
                cell["dv"][band] = {"n_seeds": 0, "note": "no seed had n > 50"}
                continue

            def mean_of(k: str, vals: list = vals) -> float:
                return float(np.mean([v[k] for v in vals]))

            finite = [v for v in vals if np.isfinite(v["corr"])]
            entry: dict[str, Any] = {
                "n_seeds": len(vals),
                "n": mean_of("n"),
                "residual_rms": mean_of("residual_rms"),
                "pred_rms": mean_of("pred_rms"),
                "est_rms": mean_of("est_rms"),
                "est_sd": mean_of("est_sd"),
                "pred_sd": mean_of("pred_sd"),
                "mean_offset": mean_of("mean_offset"),
                "signal_to_residual": mean_of("pred_rms") / mean_of("residual_rms"),
            }
            if len(finite) == len(vals):
                entry["corr"] = float(np.mean([v["corr"] for v in finite]))
                entry["corr_sd"] = (
                    float(np.std([v["corr"] for v in finite], ddof=1)) if len(finite) > 1 else 0.0
                )
            else:
                # Undefined, not missing. The estimate has no variance over these
                # pixels, so it carries no information about the prediction and the
                # small residual below is an artefact of that, not a success.
                entry["corr"] = None
                entry["corr_sd"] = None
                entry["note"] = (
                    f"correlation undefined in {len(vals) - len(finite)}/{len(vals)} seeds: "
                    f"the estimate is constant (sd {mean_of('est_sd'):.4f}) over these pixels"
                )
            cell["dv"][band] = entry
        out["per_fixation"][key] = cell

    for arm, ts in data["timing"].items():
        out["timing"][arm] = {"mean_seconds": float(np.mean(ts)), "n": len(ts)}
    out["timing"]["ratio_toed_over_rect"] = (
        out["timing"]["TOED"]["mean_seconds"] / out["timing"]["RECT"]["mean_seconds"]
    )

    (HERE / "verdicts.json").write_text(json.dumps(out, indent=2))

    # ---- report ------------------------------------------------------------
    print("=== Measurement 1: range error (m) on COMMON directions, 4 seeds ===")
    print(
        f"{'fixation':>12} {'band':>5} | {'RECT':>8} {'TOED':>8} {'diff':>9} "
        f"{'bar':>8} {'ratio':>6} {'verdict':>13}"
    )
    for key, c in out["per_fixation"].items():
        for band in BANDS:
            v = c["bands"][band]["median"]
            verdict = v["direction"] if v["distinguishable"] else "indistinct"
            print(
                f"{key:>12} {band:>5} | {v['rect']:8.4f} {v['toed']:8.4f} {v['mean_diff']:+9.4f} "
                f"{v['bar']:8.4f} {v['ratio']:6.2f} {verdict:>13}"
            )
        print()

    print("=== coverage and validity ===")
    print(
        f"{'fixation':>12} | {'RECT valid':>10} {'TOED valid':>10} | {'common':>7} | "
        f"{'RECT cond':>9} {'TOED cond':>9} | {'RECT ds':>10} {'TOED ds':>10}"
    )
    for key, c in out["per_fixation"].items():
        print(
            f"{key:>12} | {c['RECT']['valid_fraction']:10.3f} "
            f"{c['TOED']['valid_fraction']:10.3f} | "
            f"{c['RECT']['common_fraction']:7.3f} | {c['RECT']['conditional_valid']:9.3f} "
            f"{c['TOED']['conditional_valid']:9.3f} | {str(c['RECT']['disparity_range']):>10} "
            f"{str(c['TOED']['disparity_range']):>10}"
        )

    print("\n=== Measurement 2: is d_v signal or noise? ===")
    print(
        f"{'fixation':>12} {'band':>5} | {'n':>7} {'corr':>7} {'sd':>6} {'resid':>7} "
        f"{'pred_rms':>8} {'S/R':>5} {'offset':>7} | {'pred_max':>8}"
    )
    for key, c in out["per_fixation"].items():
        for band in ("AT", "AWAY", "ALL"):
            v = c["dv"][band]
            if v.get("n_seeds") == 0:
                print(f"{key:>12} {band:>5} |   {v['note']}")
                continue
            corr = f"{v['corr']:+7.3f}" if v["corr"] is not None else "  UNDEF"
            sd = f"{v['corr_sd']:6.3f}" if v["corr_sd"] is not None else "     -"
            print(
                f"{key:>12} {band:>5} | {v['n']:7.0f} {corr:>7} {sd:>6} "
                f"{v['residual_rms']:7.3f} {v['pred_rms']:8.3f} {v['signal_to_residual']:5.2f} "
                f"{v['mean_offset']:+7.3f} | {c['dv_pred_max']:8.2f}"
            )
            if "note" in v:
                print(f"{'':>12} {'':>5} |   {v['note']}")
        print()

    t = out["timing"]
    print(
        f"=== matcher wall-clock ===\n  RECT {t['RECT']['mean_seconds']:.3f} s   "
        f"TOED {t['TOED']['mean_seconds']:.3f} s   ratio {t['ratio_toed_over_rect']:.1f}x"
    )
    print(f"\nwrote {HERE / 'verdicts.json'}")


if __name__ == "__main__":
    main()
