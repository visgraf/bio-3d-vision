"""exp013 — allocation on a sphere. Pre-registered in preregistration.md.

Two arms on ONE shared capture per seed, which fc-013 is what licenses: a
rotation about a fixed optical centre re-indexes a complete sphere and changes
nothing in it, so re-rendering per fixation would return the same data.

    U  uniform weighting over the whole sphere, no gaze
    F  angular foveal weighting about a gaze chosen by argmax variance + IOR

Needs a Blender binary and the ``blender`` extra.
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
from scipy.ndimage import gaussian_filter

from bio3dvision.belief import HeadFrameBelief
from bio3dvision.blender_load import read_exr_depth, read_exr_image, render_provenance
from bio3dvision.matching import front_end_block
from bio3dvision.oculomotor import Fixation, StereoRig
from bio3dvision.policy import FOVEA_SIGMA_RAD, INHIBITION_RADIUS, angular_falloff
from bio3dvision.sampling import EquirectSampling

# --- declared in the preregistration -----------------------------------------
SEEDS = (0, 1, 2, 3, 4, 5, 6, 7)
BUDGET = 40
W_IMG, H_IMG = 2048, 1024  # equirect raster; lattice is (W_IMG, H_IMG)
DISTANCES = [2.0, 3.0, 4.0, 5.0]
BASELINE = 0.065
F_PX_REF = 700.0  # only for converting the two carried px constants
PRIOR_DEPTH, PRIOR_STD = 3.0, 3.0
BELIEF_SHAPE = (512, 256)
WIN = 7

#: **A UNITS CONVERSION, NOT A SWEEP.** 20.0 px at f = 700 is arctan(20/700).
#: met-008 records INHIBITION_RADIUS as carried and never examined; this changes
#: what it is measured in and not what is known about it, exactly as
#: FOVEA_SIGMA_RAD does for met-010.
INHIBITION_RAD = float(np.arctan(INHIBITION_RADIUS / F_PX_REF))

#: local x,y,z -> head. Local +Y is the equirect POLE and must lie on the
#: baseline, or rows stop being epipolar (bio-079). Verified by markers: the
#: transposed, row-reversed raster matches EquirectSampling to 0.56 cells.
POSE = np.array([[0.0, 1.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, -1.0]])

REPO = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).parent
RENDERER = REPO / "src" / "bio3dvision" / "blender_render.py"


def to_lattice(a: np.ndarray) -> np.ndarray:
    """Blender equirect raster -> EquirectSampling layout. An index permutation.

    Transpose, then reverse rows. Both are exact: no interpolation, no
    correlation introduced, none of the variance cost exp009 priced for a warp.
    The row reversal is needed because Blender's longitude and this lattice's phi
    run opposite ways, and no CAMERA ROTATION can fix that — the map that would
    has determinant -1.
    """
    return np.asarray(a).T[::-1]


def distances_for(seed: int) -> list[float]:
    """Per-seed plane distances. **THE SEEDS MUST VARY THE GEOMETRY.**

    The first version varied only the noise texture, so every seed scored the same
    scene and the seed-to-seed sd of the arm difference was EXACTLY 0.0000 in every
    band — which makes exp001's clause 1 vacuous, since it asks whether an effect
    exceeds SCENE-TO-SCENE variation and there was only one scene. Measured, on the
    first run of this experiment.
    """
    rng = np.random.default_rng(1000 + seed)
    return [float(z * rng.uniform(0.75, 1.30)) for z in DISTANCES]


def render(work: pathlib.Path, seed: int, binary: str):
    out = work / f"seed{seed}"
    if not (out / "left.exr").exists():
        out.mkdir(parents=True, exist_ok=True)
        poses = {}
        for name, sign in (("left", -1.0), ("right", +1.0)):
            m = np.eye(4)
            m[:3, :3] = POSE
            m[:3, 3] = np.array([sign * BASELINE / 2.0, 0.0, 0.0])
            poses[name] = {"matrix_world": m.tolist()}
        (out / "poses.json").write_text(json.dumps(poses))
        r = subprocess.run(
            [
                binary,
                "--background",
                "--factory-startup",
                "--python",
                str(RENDERER),
                "--",
                "--out",
                str(out),
                "--sphere-cards",
                *[str(z) for z in distances_for(seed)],
                "--sphere-textured",
                "--sphere-seed",
                str(seed),
                "--pano",
                "--res",
                str(W_IMG),
                str(H_IMG),
                "--samples",
                "1",
                "--poses",
                str(out / "poses.json"),
                "--baseline",
                str(BASELINE),
            ],
            capture_output=True,
            text=True,
            timeout=1800,
        )
        if not (out / "left.exr").exists():
            raise RuntimeError(f"render seed {seed} failed\n{r.stderr[-2000:]}")
    return to_lattice(read_exr_image(out / "left.exr")), to_lattice(
        read_exr_image(out / "right.exr")
    )


def ground_truth_analytic(
    model: EquirectSampling, centre: np.ndarray, distances: list[float]
) -> np.ndarray:
    """Analytic RANGE to the tiled planes. **SUPERSEDED — kept for the record.**

    It agrees with Blender's depth pass to 2 MICROMETRES when the render and the
    formula are given the same distances, so it is correct.

    **IT IS SUPERSEDED BECAUSE IT WAS ONCE COMPARED AGAINST A RENDER OF A
    DIFFERENT SCENE, AND THE DISAGREEMENT LOOKED LIKE A BUG IN THE FORMULA.** A
    failed edit left the renderer on the unperturbed distances while this ran on
    the per-seed ones; the median disagreement was 0.146 m and the maximum 1.39 m,
    and the first explanation written down — an edge-attribution error from the
    0.97 shrink — was wrong. What found it was checking the DEPTH PASS RANGE per
    seed and seeing all eight identical.

    The experiment now takes ground truth from the depth pass, which bio-077
    established as radial to 73 micrometres. That is one fewer thing that has to
    agree with the renderer by construction rather than by measurement.
    """
    height, width = model.shape
    rows, cols = np.mgrid[0:height, 0:width]
    dirs = model.direction(np.stack([rows, cols], -1).astype(np.float64))
    span = 2.0 * np.pi / len(distances)
    best = np.full(model.shape, np.inf)
    for i, z in enumerate(sorted(distances)):
        lam = -np.pi + span * (i + 0.5)
        # THE NORMAL IS ALREADY IN THE HEAD FRAME. The scene is built in Blender
        # WORLD coordinates and the eye centres are placed at (+/-b/2, 0, 0) in
        # those same coordinates, so world IS the head frame here. POSE maps
        # CAMERA-LOCAL to world and has no business acting on a world vector;
        # applying it put the ground truth in a frame nothing else used and
        # produced a median error of 1.96 m on a 2-5 m scene. Measured, on the
        # first run of this function.
        normal = np.array([np.sin(lam), 0.0, -np.cos(lam)])
        along = dirs @ normal
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (z - centre @ normal) / along
        point = centre + t[..., None] * dirs
        ex = np.array([np.cos(lam), 0.0, np.sin(lam)])
        ey = np.array([0.0, 1.0, 0.0])
        half_w = z * np.tan((span - 2 * span * 0.05) / 2)
        half_h = z * np.tan(np.radians(58.0))
        hit = (
            (along > 1e-6)
            & (t > 0)
            & (np.abs((point - z * normal) @ ex) < half_w * 0.97)
            & (np.abs((point - z * normal) @ ey) < half_h * 0.97)
        )
        best = np.where(hit & (t < best), t, best)
    return np.where(np.isfinite(best), best, np.nan)


def spherical_front_end(
    left: np.ndarray, right: np.ndarray, model: EquirectSampling, near_m: float
):
    """Match along rows and turn ANGULAR disparity into RANGE by the sine rule.

    **Columns are reversed before matching and the result reversed back.** In this
    lattice theta_R > theta_L, so the right eye's sample sits at a LARGER column
    and ``d = x_L - x_R`` is NEGATIVE — which ``matching.cost_volume`` cannot
    search at all (bio-057). Reversing the column axis makes it positive. Like the
    transpose, it is an index permutation and costs nothing.
    """
    height, width = model.shape
    pitch = np.pi / width
    # FROM THIS SEED'S OWN NEAREST PLANE, not from a global bound. A search range
    # wider than the scene needs costs accuracy: widening it from 16 to 18 columns
    # tripled the front end's median error, from 0.0695 m to 0.2299 m on the same
    # geometry, because every extra candidate is another chance at a false match.
    # Measured, and the reason the bound is tight rather than safe.
    d_max_rad = np.arctan2(BASELINE, near_m * 0.95)
    dmax = int(np.ceil(d_max_rad / pitch)) + 2
    t0 = time.time()
    d_sub, var_d, valid = front_end_block(left[:, ::-1], right[:, ::-1], 0, dmax, WIN)
    seconds = time.time() - t0
    d_sub, var_d, valid = d_sub[:, ::-1], var_d[:, ::-1], valid[:, ::-1]

    cols = np.arange(width)[None, :]
    theta_l = pitch * (cols + 0.5) * np.ones((height, 1))
    d_rad = np.maximum(d_sub.astype(np.float64), 1e-9) * pitch
    theta_r = theta_l + d_rad
    with np.errstate(divide="ignore", invalid="ignore"):
        rng = BASELINE * np.sin(theta_r) / np.sin(d_rad)
        # dr/dd = -b sin(theta_L)/sin^2(d). THE PINHOLE JACOBIAN IS CONSTANT PER
        # FIXATION; this one is theta-dependent, and var_r ~ 1/sin^2(theta) is
        # what makes the epipoles the least certain directions on the sphere.
        jac = BASELINE * np.sin(theta_l) / np.sin(d_rad) ** 2
    var_r = (jac * pitch) ** 2 * np.maximum(var_d.astype(np.float64), 1e-9)
    ok = valid & np.isfinite(rng) & (rng > 0.2) & (rng < 40.0) & np.isfinite(var_r)
    return rng, var_r, ok, seconds, dmax


def run_arm(arm: str, rng_img, var_img, ok_img, model, belief_model, gt):
    belief = HeadFrameBelief.from_sampling(
        belief_model,
        Fixation(0.0, 0.0, 0.06),
        StereoRig(baseline=BASELINE),
        prior_depth=PRIOR_DEPTH,
        prior_std=PRIOR_STD,
    )
    dirs = belief.directions
    index = np.asarray(model.index(dirs))
    gathered_r = rng_img[index[..., 0], index[..., 1]]
    gathered_v = var_img[index[..., 0], index[..., 1]]
    gathered_ok = ok_img[index[..., 0], index[..., 1]]
    base_prec = np.where(gathered_ok, 1.0 / np.maximum(gathered_v, 1e-9), 0.0)

    history: list[dict[str, Any]] = []
    visited: list[np.ndarray] = []
    # The MECHANISM, measured rather than asserted: how much of the sphere does
    # each arm actually put weight on? A foveal weight models an ACUITY GRADIENT,
    # and a uniform capture has none.
    total_weight = np.zeros(belief.shape, dtype=np.float64)
    for step in range(BUDGET):
        if arm == "U":
            weight = np.ones(belief.shape, dtype=np.float64)
            gaze = None
        else:
            score = gaussian_filter(np.where(gathered_ok, belief.var, 0.0), 2.0)
            for g in visited:
                score = np.where(
                    angular_falloff(dirs, g, INHIBITION_RAD) > np.exp(-0.5), -np.inf, score
                )
            score = np.where(gathered_ok, score, -np.inf)
            if not np.isfinite(score).any():
                break
            cell = np.unravel_index(int(np.argmax(score)), score.shape)
            gaze = dirs[cell]
            visited.append(gaze)
            weight = angular_falloff(dirs, gaze, FOVEA_SIGMA_RAD)
        prec = base_prec * weight
        prior_prec = 1.0 / np.maximum(belief.var, 1e-6)
        post = prior_prec + prec
        belief.mean = ((prior_prec * belief.mean + prec * np.nan_to_num(gathered_r)) / post).astype(
            np.float32
        )
        belief.var = (1.0 / post).astype(np.float32)
        total_weight = total_weight + weight
        history.append({"step": step, "gaze": None if gaze is None else [float(x) for x in gaze]})
    return belief, history, dirs, gathered_ok, total_weight


def main() -> None:
    binary = shutil.which("blender")
    if binary is None:
        raise SystemExit("exp013 renders a spherical pair; it needs a Blender binary.")
    work = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "results" / "exp013_work"
    work.mkdir(parents=True, exist_ok=True)
    model = EquirectSampling((W_IMG, H_IMG))
    belief_model = EquirectSampling(BELIEF_SHAPE)
    _ = np.array([-BASELINE / 2.0, 0.0, 0.0])  # left-eye centre; kept for ground_truth_analytic
    brows, bcols = np.mgrid[0 : BELIEF_SHAPE[0], 0 : BELIEF_SHAPE[1]]
    belief_dirs = belief_model.direction(np.stack([brows, bcols], -1).astype(np.float64))

    out: dict[str, Any] = {
        "experiment": "exp013_spherical_allocation",
        "seeds": list(SEEDS),
        "budget": BUDGET,
        "raster": [W_IMG, H_IMG],
        "lattice": list(model.shape),
        "belief_lattice": list(BELIEF_SHAPE),
        "distances_m": DISTANCES,
        "fovea_sigma_rad": FOVEA_SIGMA_RAD,
        "inhibition_rad": INHIBITION_RAD,
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "rows": [],
    }
    for seed in SEEDS:
        out.setdefault("distances", {})[str(seed)] = distances_for(seed)
        left, right = render(work, seed, binary)
        # GROUND TRUTH IS THE DEPTH PASS, not the analytic formula above. bio-077
        # established it as radial to 73 micrometres; the formula was exact on the
        # geometry it was written against and wrong by 1.39 m on the one it was
        # used for.
        gt_full = to_lattice(read_exr_depth(work / f"seed{seed}" / "depth_left.exr"))
        _bidx = np.asarray(model.index(belief_dirs))
        gt_belief = gt_full[_bidx[..., 0], _bidx[..., 1]]
        out.setdefault("solid_angle_with_geometry", []).append(float(np.isfinite(gt_belief).mean()))
        rng_img, var_img, ok_img, seconds, dmax = spherical_front_end(
            left, right, model, min(distances_for(seed))
        )
        m = ok_img & np.isfinite(gt_full)
        out.setdefault("front_end", []).append(
            {
                "seed": seed,
                "seconds": seconds,
                "dmax_cols": dmax,
                "valid_fraction": float(ok_img.mean()),
                "scored_fraction": float(m.mean()),
                "median_abs_err_m": float(np.median(np.abs(rng_img[m] - gt_full[m]))),
            }
        )
        for arm in ("U", "F"):
            belief, history, dirs, gok, tw = run_arm(
                arm, rng_img, var_img, ok_img, model, belief_model, gt_belief
            )
            err = np.abs(belief.mean - gt_belief)
            scored = gok & np.isfinite(gt_belief) & np.isfinite(err)
            theta = np.arccos(np.clip(dirs @ np.array([1.0, 0.0, 0.0]), -1, 1))
            bands = {
                "EQUATOR": np.abs(theta - np.pi / 2) < np.radians(30.0),
                "MID": (np.abs(theta - np.pi / 2) >= np.radians(30.0))
                & (np.abs(theta - np.pi / 2) < np.radians(60.0)),
                "POLE": np.abs(theta - np.pi / 2) >= np.radians(60.0),
                "ALL": np.ones_like(theta, bool),
            }
            theta_all = np.arccos(np.clip(dirs @ np.array([1.0, 0.0, 0.0]), -1, 1))
            sa = np.sin(theta_all)  # solid-angle weight of each equirect cell
            row: dict[str, Any] = {
                "arm": arm,
                "seed": seed,
                "steps": len(history),
                # Fraction of the sphere's SOLID ANGLE receiving more than 1% of the
                # peak weight, summed over the run. For U this is 1.0 by definition.
                "weighted_solid_angle_fraction": float(
                    (sa * (tw > 0.01 * max(tw.max(), 1e-12))).sum() / sa.sum()
                ),
            }
            if arm == "F":
                g = np.array([h["gaze"] for h in history if h["gaze"]])
                gt_theta = np.degrees(np.arccos(np.clip(g @ np.array([1.0, 0.0, 0.0]), -1, 1)))
                row["gaze_theta_deg"] = [float(x) for x in gt_theta]
            for band, mask in bands.items():
                sel = scored & mask
                row[band] = {
                    "n": int(sel.sum()),
                    "median_abs_err": float(np.median(err[sel])) if sel.sum() else float("nan"),
                    "p90": float(np.percentile(err[sel], 90)) if sel.sum() else float("nan"),
                }
            out["rows"].append(row)
        print(f"  seed {seed}: front end {seconds:.1f}s, valid {ok_img.mean():.3f}", flush=True)

    first = sorted(d for d in work.iterdir() if (d / "params.json").exists())[0]
    out["rendered_with"] = render_provenance(first)
    dest = REPO / "results" / "exp013_spherical_allocation"
    dest.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, indent=2)
    (dest / "results.json").write_text(text)
    (HERE / "results.json").write_text(text)
    print(f"\nwrote {dest / 'results.json'}")


if __name__ == "__main__":
    main()
