"""exp007 — six arms on the fixture and on a render of the same geometry.

Pre-registered in ``preregistration.md``, committed before this file existed.

Needs a Blender binary and the ``blender`` extra. The renders are the scene model
of exp004, re-rendered here so the run is self-contained; being deterministic,
they are the same stimulus exp004 measured.
"""

from __future__ import annotations

import json
import pathlib
import platform
import shutil
import subprocess
import sys
import time
from typing import Any

import numpy as np
from scipy.ndimage import distance_transform_edt

from bio3dvision.acquisition import PANUM_HALF_WIDTH_PX, Window, reacquire, window_around
from bio3dvision.blender_load import load_render, render_provenance
from bio3dvision.figure import save_result_fig
from bio3dvision.fixture import make_synthetic_scene
from bio3dvision.loop import ActiveStereo
from bio3dvision.policy import POLICIES
from bio3dvision.scene_model import rasterise_depth, scene_from_fixture, write_scene

# --- inherited from exp004, unchanged ----------------------------------------
DISCONTINUITY_STEP_PX = 1.0
AT_MAX_PX = 10.0
AWAY_MIN_PX = 24.0

# --- declared in the preregistration -----------------------------------------
SEEDS = tuple(range(8))
BUDGET = 18  # exp001's and exp003's alike

# THE LATTICE ARMS NEED THEIR OWN BUDGET, and this is a deviation from the
# specification, taken because following it literally defeats its own purpose.
#
# The specification says 18 steps for A/A'/D/E. But D and E are LATTICE SCANS
# whose pitch exp002 derived from the inhibition radius for a 40-fixation budget,
# and the lattice has 70 sites. At 18 steps E has visited 26% of it and reads a
# median of 0.0447 against A''s 0.0117 -- a four-fold gap that is about budget,
# not about variance versus the mask. At 40 steps E reads 0.0105 against A''s
# 0.0103, which IS exp002's finding and is what fc-008 rests on.
#
# So E-vs-A' and D-vs-E are run at 40 as well, matching exp002 exactly, and the
# 40-step figures are the ones that bear on fc-008. The 18-step figures are kept
# and reported, labelled as the budget-starved measurement they are.
BUDGET_LATTICE = 40
LATTICE_ARMS = ("A_prime", "D", "E")
POLICY_ARMS = ("A", "A_prime", "D", "E")
WINDOW_ARMS = ("W", "V")  # exp003's, both driven by A'
WINDOW_POLICY = "A_prime"

REPO = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).parent
RENDERER = REPO / "src" / "bio3dvision" / "blender_render.py"


def band_masks() -> dict[str, np.ndarray]:
    """AT / MIDDLE / AWAY / POOLED from the scene model's step-edge geometry.

    Identical across seeds: the fixture varies texture with the seed, not
    geometry. Identical across sources: both sources ARE that geometry, which is
    what makes a band comparison between them meaningful at all.
    """
    model = scene_from_fixture(seed=0)
    params = model.params
    d_gt = float(params["f_px"]) * float(params["baseline"]) / rasterise_depth(model, smooth=False)
    edge = np.zeros(d_gt.shape, dtype=bool)
    dx = np.abs(np.diff(d_gt, axis=1)) > DISCONTINUITY_STEP_PX
    dy = np.abs(np.diff(d_gt, axis=0)) > DISCONTINUITY_STEP_PX
    edge[:, :-1] |= dx
    edge[:, 1:] |= dx
    edge[:-1, :] |= dy
    edge[1:, :] |= dy
    dist = np.asarray(distance_transform_edt(~edge), dtype=float)
    return {
        "AT": dist <= AT_MAX_PX,
        "MIDDLE": (dist > AT_MAX_PX) & (dist < AWAY_MIN_PX),
        "AWAY": dist >= AWAY_MIN_PX,
        "POOLED": np.ones_like(dist, dtype=bool),
    }


def lateral_overlap() -> dict[str, float]:
    """How much genuine half-occlusion the fixture's geometry actually produces.

    THE STRENGTH OF EVERY CLAIM HERE DEPENDS ON THIS NUMBER, which is why it is
    measured rather than asserted. The rendered scene copies the FIXTURE'S
    geometry, so its occlusions are incidental to that geometry rather than
    designed. If the overlap is small, the rendered stimulus is only marginally
    less degenerate than the fixture and every verdict below is correspondingly
    weaker.

    Reports both directions: right-image pixels no left pixel maps to (the
    half-occluded strips), and left-image pixels whose correspondent is hidden.
    """
    model = scene_from_fixture(seed=0)
    params = model.params
    depth = rasterise_depth(model, smooth=False)
    d_gt = float(params["f_px"]) * float(params["baseline"]) / depth
    height, width = depth.shape
    cols = np.arange(width)[None, :].repeat(height, 0)
    target = np.rint(cols - d_gt).astype(int)

    unmatched_right = 0
    occluded_left = 0
    runs: list[int] = []
    for y in range(height):
        order = np.argsort(-depth[y])  # far to near; nearer wins
        xs = target[y, order]
        inside = (xs >= 0) & (xs < width)
        seen = np.zeros(width, dtype=bool)
        owner = np.full(width, -1)
        for idx, col in zip(order[inside], xs[inside], strict=True):
            if owner[col] == -1 or depth[y, idx] < depth[y, owner[col]]:
                owner[col] = idx
            seen[col] = True
        unmatched_right += int((~seen).sum())
        # A left pixel is occluded if some nearer left pixel claims its target.
        for idx, col in zip(order[inside], xs[inside], strict=True):
            if owner[col] != idx:
                occluded_left += 1
        run = 0
        for flag in ~seen:
            run = run + 1 if flag else 0
            if run:
                runs.append(run)
    return {
        "right_pixels_unmatched": unmatched_right,
        "right_fraction": unmatched_right / depth.size,
        "left_pixels_occluded": occluded_left,
        "left_fraction": occluded_left / depth.size,
        "max_run_px": max(runs) if runs else 0,
    }


def render_seed(seed: int, work: pathlib.Path, binary: str) -> pathlib.Path:
    out_dir = work / f"render_{seed}"
    if (out_dir / "depth_left.exr").exists():
        return out_dir
    scene_dir = work / f"scene_{seed}"
    write_scene(scene_from_fixture(seed=seed), scene_dir)
    result = subprocess.run(
        [
            binary,
            "--background",
            "--factory-startup",
            "--python",
            str(RENDERER),
            "--",
            "--out",
            str(out_dir),
            "--scene",
            str(scene_dir),
            "--samples",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
    if result.returncode != 0 or not (out_dir / "depth_left.exr").exists():
        raise RuntimeError(f"render failed for seed {seed}\n{result.stderr[-2000:]}")
    return out_dir


def source_arrays(source: str, seed: int, work: pathlib.Path, binary: str) -> tuple:
    if source == "F":
        return make_synthetic_scene(seed=seed)
    left, right, depth, params = load_render(render_seed(seed, work, binary))
    return left, right, depth, params


def metrics_by_band(
    engine: ActiveStereo,
    depth_gt: np.ndarray,
    bands: dict[str, np.ndarray],
    restrict: np.ndarray | None = None,
) -> dict[str, dict[str, float]]:
    """Error statistics per band. ``restrict`` applies the coverage rule."""
    known = np.isfinite(depth_gt) & engine.valid
    if restrict is not None:
        known = known & restrict
    out: dict[str, dict[str, float]] = {}
    for name, band in bands.items():
        m = known & band
        if m.sum() == 0:
            out[name] = {
                "n": 0,
                "median_abs_err": float("nan"),
                "p90": float("nan"),
                "rmse": float("nan"),
            }
            continue
        err = np.abs(engine.mean[m] - depth_gt[m]).astype(np.float64)
        out[name] = {
            "n": int(m.sum()),
            "median_abs_err": float(np.median(err)),
            "p90": float(np.percentile(err, 90)),
            "rmse": float(np.sqrt(np.mean(err**2))),
        }
    return out


def run_policy_arm(arm: str, left, right, params, depth_gt, budget: int = BUDGET) -> ActiveStereo:
    engine = ActiveStereo(left, right, params, matcher="block")
    policy = POLICIES[arm]
    for _ in range(budget):
        choice = policy(engine, engine.scanpath)
        if choice is None:
            break
        engine.step(fixation=choice)
    return engine


def run_window_arm(arm: str, left, right, params, depth_gt) -> tuple[ActiveStereo, dict]:
    """exp003's W and V, reproduced exactly: the arms vary the window, not the policy."""
    engine = ActiveStereo(left, right, params, matcher="block")
    policy = POLICIES[WINDOW_POLICY]
    hypotheses = Window(0, 56).hypotheses
    d_fixes: list[float] = []
    windows: list[list[int]] = []
    for _step in range(BUDGET):
        choice = policy(engine, engine.scanpath)
        if choice is None:
            break
        d_fix = engine.vergence(*choice)  # never from ground truth
        d_fixes.append(float(d_fix))
        if arm == "V":
            w = window_around(d_fix, PANUM_HALF_WIDTH_PX)
            hypotheses += reacquire(engine, left, right, w)
            windows.append([w.dmin, w.dmax])
        else:
            windows.append([0, 56])
        engine.step(fixation=choice)
    return engine, {
        "hypotheses": int(hypotheses),
        "d_fix": d_fixes,
        "distinct_windows": len({tuple(w) for w in windows}),
    }


def main() -> None:
    binary = shutil.which("blender")
    if binary is None:
        raise SystemExit(
            "exp007 needs a Blender binary: its whole point is to run the "
            "comparisons on a RENDERED stimulus. Refusing to run the fixture half "
            "and report it as the experiment."
        )
    work = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "results" / "exp007_work"
    work.mkdir(parents=True, exist_ok=True)

    bands = band_masks()
    out: dict[str, Any] = {
        "experiment": "exp007_rendered_policy_sweep",
        "seeds": list(SEEDS),
        "budget": BUDGET,
        "policy_arms": list(POLICY_ARMS),
        "window_arms": list(WINDOW_ARMS),
        "window_policy": WINDOW_POLICY,
        "bands": {
            "at_max_px": AT_MAX_PX,
            "away_min_px": AWAY_MIN_PX,
            "discontinuity_step_px": DISCONTINUITY_STEP_PX,
            "inherited_from": "exp004, unchanged",
        },
        "lateral_overlap": lateral_overlap(),
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "rows": [],
        "rows_budget40": [],
        "budget_lattice": BUDGET_LATTICE,
        "lattice_arms": list(LATTICE_ARMS),
    }
    print("lateral overlap of the geometry:", out["lateral_overlap"])

    for source in ("F", "R"):
        t0 = time.time()
        for seed in SEEDS:
            left, right, depth_gt, params = source_arrays(source, seed, work, binary)
            engines: dict[str, ActiveStereo] = {}
            extra: dict[str, dict] = {}
            for arm in POLICY_ARMS:
                engines[arm] = run_policy_arm(arm, left, right, params, depth_gt)
            # The lattice arms again at exp002's budget; see BUDGET_LATTICE.
            for arm in LATTICE_ARMS:
                eng40 = run_policy_arm(arm, left, right, params, depth_gt, BUDGET_LATTICE)
                out["rows_budget40"].append(
                    {
                        "source": source,
                        "arm": arm,
                        "seed": seed,
                        "valid": int(eng40.valid.sum()),
                        "distinct_fixations": len(set(eng40.scanpath)),
                        "final": metrics_by_band(eng40, depth_gt, bands),
                    }
                )
            for arm in WINDOW_ARMS:
                engines[arm], extra[arm] = run_window_arm(arm, left, right, params, depth_gt)

            # exp003's coverage rule. A/A'/D/E share a mask; V rewrites its own.
            vw_intersection = engines["V"].valid & engines["W"].valid
            for arm, engine in engines.items():
                restrict = vw_intersection if arm in WINDOW_ARMS else None
                row: dict[str, Any] = {
                    "source": source,
                    "arm": arm,
                    "seed": seed,
                    "valid": int(engine.valid.sum()),
                    "scanpath": [list(map(int, p)) for p in engine.scanpath],
                    "distinct_fixations": len(set(engine.scanpath)),
                    "final": metrics_by_band(engine, depth_gt, bands, restrict),
                }
                if arm in WINDOW_ARMS:
                    row["final_own_mask_CONFOUNDED"] = metrics_by_band(engine, depth_gt, bands)
                    row["exclusive"] = metrics_by_band(
                        engine,
                        depth_gt,
                        {"POOLED": np.ones_like(vw_intersection)},
                        restrict=engine.valid & ~vw_intersection,
                    )["POOLED"]
                    row.update(extra[arm])
                out["rows"].append(row)

            if seed == 0:
                figs = REPO / "results" / "exp007_rendered_policy_sweep"
                for arm, engine in engines.items():
                    d = figs / f"{source}_{arm}_seed0"
                    d.mkdir(parents=True, exist_ok=True)
                    hist = [
                        {
                            "rmse": float(
                                np.sqrt(
                                    np.mean(
                                        (
                                            engine.mean[np.isfinite(depth_gt) & engine.valid]
                                            - depth_gt[np.isfinite(depth_gt) & engine.valid]
                                        )
                                        ** 2
                                    )
                                )
                            )
                        }
                    ]
                    save_result_fig(engine, depth_gt, hist * BUDGET, out=str(d))
        print(f"  source {source}: {len(SEEDS)} seeds x 6 arms in {time.time() - t0:.1f}s")

    out["rendered_with"] = render_provenance(work / "render_0")
    dest = REPO / "results" / "exp007_rendered_policy_sweep"
    dest.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, indent=2)
    (dest / "results.json").write_text(text)
    (HERE / "results.json").write_text(text)
    print(f"\nwrote {dest / 'results.json'}")


if __name__ == "__main__":
    main()
