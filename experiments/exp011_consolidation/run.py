"""exp011 — exp010 at 24 seeds and four occlusion levels. Pre-registered.

**The runner is exp010's, imported rather than copied.** The specification says
no new code and no new design, and importing is the literal form of that: the
arms, the policy, the fusion, the bar and the budget are the same objects, and
the only things that differ are the seed count and the stimulus level. A copy
would have been a second thing to keep in step.

One statistic is added, and it is declared in the preregistration rather than
chosen after the tables: the error over ALL cells with unmeasured ones left at
the prior, which is the yardstick question 3's judgement is made on.

Needs a Blender binary and the ``blender`` extra.
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

# --- declared in the preregistration -----------------------------------------
LEVELS = (1, 2, 4, 8)  # exp008's four, at 0.0197 / 0.0426 / 0.0884 / 0.1716
SEEDS = tuple(range(24))  # three times exp010's eight
BANDS = ("AT", "MIDDLE", "AWAY", "POOLED")

REPO = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).parent


def main() -> None:
    binary = shutil.which("blender")
    if binary is None:
        raise SystemExit("exp011 renders every fixation; it needs a Blender binary.")
    work = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "results" / "exp011_work"
    work.mkdir(parents=True, exist_ok=True)

    out: dict[str, Any] = {
        "experiment": "exp011_consolidation",
        "levels_k": list(LEVELS),
        "seeds": list(SEEDS),
        "budget": BUDGET,
        "prior_depth": PRIOR,
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "left_occluded_fraction": {},
        "rows": [],
    }
    for k in LEVELS:
        frac = occlusion_fractions(split_cards(scene_from_fixture(seed=0), k))
        out["left_occluded_fraction"][str(k)] = float(frac["left_occluded_fraction"])
        print(f"k={k}: left occluded {frac['left_occluded_fraction'] * 100:.2f}%", flush=True)

    for k in LEVELS:
        for seed in SEEDS:
            model = split_cards(scene_from_fixture(seed=seed), k)
            rig = StereoRig(baseline=float(model.params["baseline"]))
            anchor = Fixation(0.0, 0.0, anchor_vergence(rig, PRIOR))
            bands = band_masks(rasterise_depth(model, smooth=False), model.params)

            results = {}
            for arm in ("OPEN", "CLOSED"):
                r = run_arm(arm, model, rig, anchor, work, f"k{k}_{arm}_s{seed}", binary)
                rays = unit_z_rays(
                    sampling_for(anchor, rig, r["params"]), rectification_rotation(anchor)
                )
                half_b = float(r["params"]["baseline"]) / 2.0
                r["gt_range"], _ = planar_to_range(
                    np.asarray(r["anchor_depth"], float), rays, np.array([-half_b, 0.0, 0.0])
                )
                results[arm] = r

            common = results["OPEN"]["ever_measured"] & results["CLOSED"]["ever_measured"]
            for arm, r in results.items():
                err = np.abs(r["belief_mean"] - r["gt_range"])
                finite = np.isfinite(err) & np.isfinite(r["gt_range"])
                row: dict[str, Any] = {
                    "k": k,
                    "arm": arm,
                    "seed": seed,
                    "renders": r["renders"],
                    "front_end_seconds": r["front_end_seconds"],
                    "matcher_seconds": r["matcher_seconds"],
                    "steps_completed": r["steps_completed"],
                    "stopped_at": r["stopped_at"],
                    "refusals": len(r["refusals"]),
                    "ever_measured_fraction": float(r["ever_measured"].mean()),
                    "survived_fraction": float(r["survived"].mean()),
                    "common_fraction": float(common.mean()),
                    "excluded_own_only": float((r["ever_measured"] & ~common).mean()),
                    "vergence_min": float(min(h["vergence"] for h in r["history"])),
                    "vergence_max": float(max(h["vergence"] for h in r["history"])),
                    "mean_visible_per_fixation": float(
                        np.mean([h["visible_fraction"] for h in r["history"]])
                    ),
                }
                # THREE SELECTIONS, and they answer different questions.
                #   common — the arms' shared cells; the only comparable accuracy.
                #   own    — each arm's own measured cells; NOT comparable across arms.
                #   all    — every cell, unmeasured ones left at the prior. The
                #            yardstick question 3's judgement is made on, declared
                #            in the preregistration before these tables existed.
                #   closed_only — the cells OPEN never reached, reported beside the
                #            headline rather than in an excluded-sets block.
                selections = {
                    "common": common,
                    "own": r["ever_measured"],
                    "all": np.ones_like(common),
                    "closed_only": results["CLOSED"]["ever_measured"] & ~common,
                }
                for band, mask in bands.items():
                    for label, sel in selections.items():
                        m = finite & mask & sel
                        row[f"{band}_{label}"] = {
                            "n": int(m.sum()),
                            "mean_abs_err": float(np.mean(err[m])) if m.sum() else float("nan"),
                            "median_abs_err": float(np.median(err[m])) if m.sum() else float("nan"),
                            "p90": float(np.percentile(err[m], 90)) if m.sum() else float("nan"),
                        }
                out["rows"].append(row)
            print(
                f"  k={k} seed {seed}: OPEN ever {results['OPEN']['ever_measured'].mean():.3f}, "
                f"CLOSED ever {results['CLOSED']['ever_measured'].mean():.3f}",
                flush=True,
            )

    first = sorted(d for d in work.iterdir() if (d / "params.json").exists())[0]
    out["rendered_with"] = render_provenance(first)
    dest = REPO / "results" / "exp011_consolidation"
    dest.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, indent=2)
    (dest / "results.json").write_text(text)
    (HERE / "results.json").write_text(text)
    print(f"\nwrote {dest / 'results.json'}")


if __name__ == "__main__":
    main()
