"""exp014 — exp011's design with a third arm. Pre-registered in preregistration.md.

    OPEN            one capture, pedestal recomputed per fixation
    CLOSED          a capture per fixation, pedestal recomputed per fixation
    CLOSED-FROZEN   CLOSED's captures and CLOSED's trajectory, pedestal held

**No new renders.** exp011's 4.0 GB of captures are reused by giving the frozen
arm CLOSED's own render tag, and its trajectory by replaying CLOSED's cells and
fixations. That yoke is what makes ``d_fix`` the only difference.

Needs a Blender binary only because the render helper checks for one; every
capture it asks for is already on disk.
"""

from __future__ import annotations

import json
import pathlib
import platform
import shutil
import sys
from typing import Any

import numpy as np

from bio3dvision.blender_load import render_provenance
from bio3dvision.oculomotor import Fixation, StereoRig, rectification_rotation
from bio3dvision.scene_model import (
    occlusion_fractions,
    rasterise_depth,
    scene_from_fixture,
    split_cards,
)
from experiments.exp010_closed_loop.run import (
    BUDGET,
    anchor_vergence,
    band_masks,
    planar_to_range,
    run_arm,
    sampling_for,
    unit_z_rays,
)
from experiments.exp010_closed_loop.run import PRIOR_DEPTH as PRIOR

LEVELS = (1, 2, 4, 8)
SEEDS = tuple(range(24))
BANDS = ("AT", "MIDDLE", "AWAY", "POOLED")
ARMS = ("OPEN", "CLOSED", "FROZEN")

REPO = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).parent


def main() -> None:
    binary = shutil.which("blender")
    if binary is None:
        raise SystemExit("exp014 reuses exp011's captures but the helper needs a binary.")
    work = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "results" / "exp011_work"
    if not work.exists():
        raise SystemExit(f"{work} does not exist; exp014 makes no new renders.")

    out: dict[str, Any] = {
        "experiment": "exp014_pedestal_vs_allocation",
        "levels_k": list(LEVELS),
        "seeds": list(SEEDS),
        "budget": BUDGET,
        "arms": list(ARMS),
        "reused_captures_from": str(work),
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "left_occluded_fraction": {},
        "rows": [],
        "coverage_check": [],
    }
    for k in LEVELS:
        frac = occlusion_fractions(split_cards(scene_from_fixture(seed=0), k))
        out["left_occluded_fraction"][str(k)] = float(frac["left_occluded_fraction"])

    for k in LEVELS:
        for seed in SEEDS:
            model = split_cards(scene_from_fixture(seed=seed), k)
            rig = StereoRig(baseline=float(model.params["baseline"]))
            anchor = Fixation(0.0, 0.0, anchor_vergence(rig, PRIOR))
            bands = band_masks(rasterise_depth(model, smooth=False), model.params)

            results: dict[str, Any] = {}
            # OPEN and CLOSED under exp011's own tags, so every capture is cached.
            results["OPEN"] = run_arm(
                "OPEN", model, rig, anchor, work, f"k{k}_OPEN_s{seed}", binary
            )
            results["CLOSED"] = run_arm(
                "CLOSED", model, rig, anchor, work, f"k{k}_CLOSED_s{seed}", binary
            )
            # YOKED: CLOSED's tag (so the captures are the same files) and CLOSED's
            # trajectory (so the cell and the fixation are the same at every step).
            results["FROZEN"] = run_arm(
                "CLOSED",
                model,
                rig,
                anchor,
                work,
                f"k{k}_CLOSED_s{seed}",
                binary,
                freeze_pedestal=True,
                replay=results["CLOSED"]["trajectory"],
            )

            for r in results.values():
                rays = unit_z_rays(
                    sampling_for(anchor, rig, r["params"]), rectification_rotation(anchor)
                )
                half_b = float(r["params"]["baseline"]) / 2.0
                r["gt_range"], _ = planar_to_range(
                    np.asarray(r["anchor_depth"], float), rays, np.array([-half_b, 0.0, 0.0])
                )

            common = results["OPEN"]["ever_measured"] & results["CLOSED"]["ever_measured"]
            common_all = common & results["FROZEN"]["ever_measured"]
            # THE PRE-REGISTERED CHECK. Freezing the pedestal changes nothing about
            # which cells are visible — unless something else is coupled to d_fix.
            # meas_prec contains 1/var_Z which contains sig_model, so it is possible.
            out["coverage_check"].append(
                {
                    "k": k,
                    "seed": seed,
                    "closed_ever": float(results["CLOSED"]["ever_measured"].mean()),
                    "frozen_ever": float(results["FROZEN"]["ever_measured"].mean()),
                    "identical": bool(
                        np.array_equal(
                            results["CLOSED"]["ever_measured"], results["FROZEN"]["ever_measured"]
                        )
                    ),
                    "common_equals_common_all": bool(np.array_equal(common, common_all)),
                }
            )

            for arm, r in results.items():
                err = np.abs(r["belief_mean"] - r["gt_range"])
                finite = np.isfinite(err) & np.isfinite(r["gt_range"])
                own_only = r["ever_measured"] & ~common
                row: dict[str, Any] = {
                    "k": k,
                    "arm": arm,
                    "seed": seed,
                    "renders": r["renders"],
                    "steps_completed": r["steps_completed"],
                    "refusals": len(r["refusals"]),
                    "frozen_pedestal": r["frozen_pedestal"],
                    "zmeas_clip_fraction": r["zmeas_clip_fraction"],
                    "ever_measured_fraction": float(r["ever_measured"].mean()),
                    "common_fraction": float(common.mean()),
                    "own_only_fraction": float(own_only.mean()),
                }
                for band, mask in bands.items():
                    for label, sel in (
                        ("common", common),
                        ("all", np.ones_like(common)),
                        ("own_only", own_only),
                    ):
                        m = finite & mask & sel
                        row[f"{band}_{label}"] = {
                            "n": int(m.sum()),
                            "mean_abs_err": float(np.mean(err[m])) if m.sum() else float("nan"),
                            "median_abs_err": float(np.median(err[m])) if m.sum() else float("nan"),
                            "p90": float(np.percentile(err[m], 90)) if m.sum() else float("nan"),
                        }
                out["rows"].append(row)
            print(
                f"  k={k} seed {seed}: pedestal {results['FROZEN']['frozen_pedestal']:.3f} px, "
                f"clip C {results['CLOSED']['zmeas_clip_fraction']:.4f} "
                f"F {results['FROZEN']['zmeas_clip_fraction']:.4f}",
                flush=True,
            )

    first = sorted(d for d in work.iterdir() if (d / "params.json").exists())[0]
    out["rendered_with"] = render_provenance(first)
    dest = REPO / "results" / "exp014_pedestal_vs_allocation"
    dest.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, indent=2)
    (dest / "results.json").write_text(text)
    (HERE / "results.json").write_text(text)
    print(f"\nwrote {dest / 'results.json'}")


if __name__ == "__main__":
    main()
