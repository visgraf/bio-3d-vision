"""exp009 — the cost of the epipolar violation, and whether d_v is recoverable.

Pre-registered in ``preregistration.md``, committed before this file existed.

Two arms at each fixation: RECT renders a rectified pair and searches 1-D;
TOED renders the toed-in pair the oculomotor geometry gives and searches 2-D.
They are compared in a **common frame** — range from the cyclopean origin as a
function of head-frame direction — because their Z passes are in different camera
frames and a comparison of two depth maps in two frames is not a measurement.

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
from scipy.ndimage import distance_transform_edt, uniform_filter

from bio3dvision.blender_load import load_render, render_provenance
from bio3dvision.matching import decode_disparity, front_end_block
from bio3dvision.oculomotor import Fixation, StereoRig, eye_rotations, rectification_rotation
from bio3dvision.sampling import PinholeSampling
from bio3dvision.scene_model import (
    WORLD_FROM_HEAD,
    eye_camera_poses,
    scene_from_fixture,
    write_scene,
)

# --- declared in the preregistration -----------------------------------------
FIXATIONS = [
    (0.00, 0.00),
    (0.08, 0.05),
    (0.15, 0.10),  # the 17c-plausible amplitude
    (0.20, 0.15),
    (0.30, 0.20),  # stress: beyond the policy's reach
]
VERGENCE = 0.06
SEEDS = (0, 1, 2, 3)
DV_BAND = 4  # from the 2.41 px predicted maximum, rounded up with a 1 px margin
WIN = 7
AT_MAX_PX, AWAY_MIN_PX = 10.0, 24.0
DISC_STEP_PX = 1.0

REPO = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).parent
RENDERER = REPO / "src" / "bio3dvision" / "blender_render.py"


def rect_poses(rig: StereoRig, fixation: Fixation) -> dict[str, dict[str, Any]]:
    """Both eyes at the SAME rectifying orientation. A valid rectified pair.

    ``rectification_rotation``'s x-axis is exactly ``[1, 0, 0]``, the baseline, so
    the pair is rectified by construction. Its forward axis is necessarily at
    azimuth zero — see the preregistration: that is a property of every rectifier,
    not of this member.
    """
    rot = rectification_rotation(fixation)
    half_b = float(rig.baseline) / 2.0
    poses: dict[str, dict[str, Any]] = {}
    for name, sign in (("left", -1.0), ("right", +1.0)):
        basis = WORLD_FROM_HEAD @ rot @ np.diag([1.0, -1.0, -1.0])
        centre = WORLD_FROM_HEAD @ np.array([sign * half_b, 0.0, 0.0])
        matrix = np.eye(4)
        matrix[:3, :3] = basis
        matrix[:3, 3] = centre
        poses[name] = {
            "matrix_world": matrix.tolist(),
            "head_rotation": np.asarray(rot).tolist(),
            "centre_world": centre.tolist(),
        }
    return poses


SCENE_NEAR_M, SCENE_FAR_M = 2.4, 4.5  # the fixture's own depth bounds


def disparity_range(rot_l, rot_r, rig: StereoRig, params, margin: int = 6):
    """Search bounds from the two orientations and the KNOWN scene depth bounds.

    Derived rather than picked, as the preregistration requires of the vertical
    band, and applied to **both** arms so they differ in the search and in nothing
    else. A converged pair's disparities are SIGNED — zero at the fixation
    distance and negative beyond it — so a range assumed positive is wrong for
    TOED; deriving it for RECT too keeps the two symmetric.
    """
    f_px = float(params["f_px"])
    rot_l, rot_r = np.asarray(rot_l), np.asarray(rot_r)
    half_b = float(rig.baseline) / 2.0
    rng = np.random.default_rng(0)
    n = 4000
    zs = rng.uniform(SCENE_NEAR_M, SCENE_FAR_M, n)
    height, width = int(params["H"]), int(params["W"])
    xs = (rng.uniform(0, width, n) - (width - 1) / 2.0) / f_px * zs
    ys = (rng.uniform(0, height, n) - (height - 1) / 2.0) / f_px * zs
    pts = np.stack([xs, ys, zs], -1) @ rot_l.T + np.array([-half_b, 0.0, 0.0])
    vl = (pts - np.array([-half_b, 0.0, 0.0])) @ rot_l
    vr = (pts - np.array([half_b, 0.0, 0.0])) @ rot_r
    ok = (vl[:, 2] > 0) & (vr[:, 2] > 0)
    dh = f_px * vl[ok, 0] / vl[ok, 2] - f_px * vr[ok, 0] / vr[ok, 2]
    return int(np.floor(dh.min())) - margin, int(np.ceil(dh.max())) + margin


def cost_volume_2d(left, right, ds, dv_band: int = DV_BAND, win: int = WIN):
    """SSD cost over ``(d_v, d_h)``, reduced to a profile over ``d_h``.

    ``d_v > 0`` shifts the right image DOWN, matching the sign convention of the
    horizontal shift, which moves it right. The aggregation is the same ``win``
    box, so the only difference from ``matching.cost_volume`` is the extra axis —
    which is what makes the arms comparable.

    The returned profile is ``min`` over ``d_v`` at each ``d_h``: a genuine cost
    curve, so ``decode_disparity``'s parabola and the ratio test see the same
    shape of input they see in the 1-D arm. An earlier version stored the cost
    only where it improved on the running best, which left ``inf`` at every other
    ``d_h`` and silently corrupted both.
    """
    height, width = left.shape
    dvs = np.arange(-dv_band, dv_band + 1)
    ds = np.asarray(ds)
    profile = np.full((height, width, len(ds)), np.inf, np.float32)
    best = np.full((height, width), np.inf, np.float32)
    best_v = np.zeros((height, width), np.int32)
    for dv in dvs:
        shifted_v = np.empty_like(right)
        if dv > 0:
            shifted_v[:dv] = right[:1]
            shifted_v[dv:] = right[: height - dv]
        elif dv < 0:
            shifted_v[dv:] = right[-1:]
            shifted_v[:dv] = right[-dv:]
        else:
            shifted_v[:] = right
        for k, d in enumerate(ds):
            # SIGNED horizontal shift. matching.cost_volume cannot do this — it
            # copies the right image unshifted for d <= 0 — which is a latent
            # assumption that the rig is PARALLEL, not merely rectified. A
            # converged pair puts the whole scene at negative disparity whenever
            # it lies beyond the fixation distance, which it does here.
            d = int(d)
            rs = np.empty_like(shifted_v)
            if d > 0:
                rs[:, :d] = shifted_v[:, :1]
                rs[:, d:] = shifted_v[:, : width - d]
            elif d < 0:
                rs[:, d:] = shifted_v[:, -1:]
                rs[:, :d] = shifted_v[:, -d:]
            else:
                rs[:] = shifted_v
            c = uniform_filter((left - rs) ** 2, size=(win, win)).astype(np.float32)
            np.minimum(profile[..., k], c, out=profile[..., k])
            better = c < best
            best = np.where(better, c, best)
            best_v = np.where(better, dv, best_v)
    return profile, ds, best_v


def lr_consistency_2d(
    d_left, dv_left, left, right, ds, dv_band: int = DV_BAND, win: int = WIN, tol: float = 1.0
):
    """Left-right consistency for a 2-D search, referenced from the RIGHT image.

    Two apparatus faults were found here and both are recorded because both
    produced plausible-looking numbers:

    1. ``matching.lr_consistency`` mirrors the pair and calls ``cost_volume``,
       which copies the right image unshifted for every ``d <= 0``. On a
       converged pair every disparity is negative, so all its cost slices are
       identical and the argmin is whichever index comes first. TOED's valid
       fraction was 0.009.
    2. Correcting the right image by the left-referenced ``dv`` field indexes
       that field at right-pixel columns, which are ~25 px away. TOED's valid
       fraction was 0.131 against RECT's 0.932 at the fixation where the
       vertical disparity the arms differ over is smallest.

    The fix is to run the right-referenced pass as its own 2-D search, exactly
    mirroring the forward one: ``cost_R(y, x, dv, d) = SSD(right(y, x),
    left(y + dv, x + d))``. It costs a second full search, which is part of what
    2-D matching actually costs and is reported as such.
    """
    cost_r, ds_r, _ = cost_volume_2d(right, left, -np.asarray(ds)[::-1], dv_band=dv_band, win=win)
    d_right = (-np.asarray(ds_r)[np.argmin(cost_r, axis=2)]).astype(np.float32)
    height, width = left.shape
    rows, cols = np.mgrid[0:height, 0:width]
    yr = np.clip(rows - np.round(dv_left).astype(int), 0, height - 1)
    xr = np.clip(cols - np.round(d_left).astype(int), 0, width - 1)
    agree = np.abs(d_left - d_right[yr, xr]) <= tol
    return agree


def front_end_block_2d(left, right, ds, dv_band: int = DV_BAND, win: int = WIN):
    """The 2-D counterpart of ``front_end_block``, with the SAME validity rules.

    Ratio test and left-right consistency exactly as the 1-D front end applies
    them, so the arms differ in the search and in nothing else.
    """
    cost, ds, dv_est = cost_volume_2d(left, right, ds, dv_band=dv_band, win=win)
    d_sub, var_d = decode_disparity(cost, ds)
    srt = np.sort(cost, axis=2)
    with np.errstate(invalid="ignore"):
        distinct = (srt[:, :, 1] - srt[:, :, 0]) / (srt[:, :, 1] + 1e-6)
    agree = lr_consistency_2d(d_sub, dv_est, left, right, ds, dv_band=dv_band, win=win)
    valid = (distinct > 0.10) & agree
    return d_sub.astype(np.float32), var_d.astype(np.float32), valid, dv_est


def triangulate_depth(d_h, d_v, params, rig: StereoRig, fixation: Fixation, arm: str):
    """Planar depth in the LEFT camera frame, by triangulating the two rays.

    **Not ``f*b/d``.** That relation holds only for a PARALLEL pair, where zero
    disparity means infinity. For a converged pair zero disparity is the fixation
    distance and disparity is signed, so the closed form is simply wrong — which
    is the same class of latent assumption as the epipolar one.

    Triangulation is correct for both arms and reduces exactly to ``f*b/d`` on a
    parallel rectified pair, so both arms take one code path and no asymmetry is
    introduced by the fix.

    The match convention follows the cost volume: ``d_h = x_L - x_R`` and
    ``d_v = y_L - y_R``.
    """
    f_px = float(params["f_px"])
    height, width = int(params["H"]), int(params["W"])
    half_b = float(rig.baseline) / 2.0
    if arm == "RECT":
        rot_l = rot_r = np.asarray(rectification_rotation(fixation))
    else:
        rots = eye_rotations(rig, fixation)
        rot_l, rot_r = np.asarray(rots.left), np.asarray(rots.right)
    c_l = np.array([-half_b, 0.0, 0.0])
    c_r = np.array([half_b, 0.0, 0.0])

    rows, cols = np.mgrid[0:height, 0:width]

    def ray(r, c, rot):
        v = np.stack(
            [(c - (width - 1) / 2.0) / f_px, (r - (height - 1) / 2.0) / f_px, np.ones_like(c)],
            axis=-1,
        )
        v = v / np.linalg.norm(v, axis=-1, keepdims=True)
        return v @ rot.T

    dl = ray(rows.astype(float), cols.astype(float), rot_l)
    dr = ray(rows - d_v, cols - d_h, rot_r)

    # Closest approach of the two rays; the midpoint is the reconstructed point.
    w0 = c_l - c_r
    a = np.einsum("...i,...i->...", dl, dl)
    b = np.einsum("...i,...i->...", dl, dr)
    c = np.einsum("...i,...i->...", dr, dr)
    d = np.einsum("...i,...i->...", dl, w0)
    e = np.einsum("...i,...i->...", dr, w0)
    denom = a * c - b * b
    with np.errstate(divide="ignore", invalid="ignore"):
        s = (b * e - c * d) / denom
        t = (a * e - b * d) / denom
    p_l = c_l + s[..., None] * dl
    p_r = c_r + t[..., None] * dr
    mid = 0.5 * (p_l + p_r)
    z = ((mid - c_l) @ rot_l)[..., 2]
    bad = ~np.isfinite(z) | (np.abs(denom) < 1e-12) | (s <= 0) | (t <= 0)
    return np.where(bad, np.nan, z)


def head_points(depth_z, params, rotation, centre_head):
    """Per-pixel 3-D points in the head frame, from a planar depth in a camera frame."""
    height, width = depth_z.shape
    f_px = float(params["f_px"])
    rows, cols = np.mgrid[0:height, 0:width]
    ray = np.stack(
        [(cols - (width - 1) / 2.0) / f_px, (rows - (height - 1) / 2.0) / f_px, np.ones_like(rows)],
        axis=-1,
    )
    local = depth_z[..., None] * ray
    return local @ np.asarray(rotation).T + centre_head


def band_masks(depth_z, params) -> dict[str, np.ndarray]:
    """Discontinuity bands in the LEFT IMAGE OF THIS ARM, from its own Z pass.

    Not from the fixture's canonical raster. The two arms look in different
    directions, so a mask built in a third frame indexes the wrong pixels — at
    az 0.30 it would be a largely unrelated region. exp004's thresholds are kept;
    only the frame the distance is measured in is corrected.

    ``f*b/z`` is used as the disparity scale for the 1 px step threshold. It is
    exact for RECT and an approximation for TOED, where the true relation is
    signed; the threshold selects a *depth step*, and the two agree on which
    steps exceed it at these depths.
    """
    d_gt = float(params["f_px"]) * float(params["baseline"]) / depth_z
    edge = np.zeros(d_gt.shape, dtype=bool)
    with np.errstate(invalid="ignore"):
        dx = np.abs(np.diff(d_gt, axis=1)) > DISC_STEP_PX
        dy = np.abs(np.diff(d_gt, axis=0)) > DISC_STEP_PX
    edge[:, :-1] |= dx
    edge[:, 1:] |= dx
    edge[:-1, :] |= dy
    edge[1:, :] |= dy
    edge |= ~np.isfinite(d_gt)
    dist = np.asarray(distance_transform_edt(~edge), dtype=float)
    return {"AT": dist <= AT_MAX_PX, "AWAY": dist >= AWAY_MIN_PX, "ALL": np.ones_like(dist, bool)}


def common_lattice(params) -> PinholeSampling:
    """The shared direction lattice: head-anchored, sensor resolution, DOUBLE field.

    The preregistration's common frame is range from the cyclopean origin as a
    function of head-frame direction. That needs one lattice both arms index
    into. A sensor-sized grid would not do: at az 0.30 the gaze is 17.2 deg off
    axis and the scene leaves a +/-12.88 deg field entirely, so the intersection
    would be empty for the very case the stress fixation exists to probe.

    Doubling the grid at the same focal length keeps the cell size equal to a
    sensor pixel on axis and widens the field to +/-24.5 deg, which covers every
    fixation here. Anchored to the head frame itself (+x right, +y down,
    +z forward), so it does not move with gaze.
    """
    h, w = int(params["H"]), int(params["W"])
    return PinholeSampling((2 * h, 2 * w), float(params["f_px"]))


def lattice_cells(points, lattice: PinholeSampling):
    """Head-frame points -> ``(index, inside)`` on the common lattice."""
    with np.errstate(invalid="ignore", divide="ignore"):
        d = points / np.linalg.norm(points, axis=-1, keepdims=True)
    forward = np.all(np.isfinite(d), axis=-1) & (d[..., 2] > 0.0)
    index = np.zeros(points.shape[:-1] + (2,), dtype=np.int_)
    index[forward] = lattice.index(d[forward])
    inside = np.zeros(points.shape[:-1], dtype=bool)
    inside[forward] = np.asarray(lattice.contains(index[forward]))
    return index, inside


def render(work, tag, model, fixation, poses, binary):
    out = work / tag
    if not (out / "depth_left.exr").exists():
        scene = work / f"scene_{tag}"
        write_scene(model, scene, fixation=fixation)
        spec = json.loads((scene / "scene.json").read_text())
        spec["eye_poses"] = poses
        (scene / "scene.json").write_text(json.dumps(spec))
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
                "--scene",
                str(scene),
                "--samples",
                "1",
            ],
            capture_output=True,
            text=True,
            timeout=900,
        )
        if not (out / "depth_left.exr").exists():
            raise RuntimeError(f"render {tag} failed\n{r.stderr[-2000:]}")
    return load_render(out)


def main() -> None:
    binary = shutil.which("blender")
    if binary is None:
        raise SystemExit("exp009 renders both arms; it needs a Blender binary.")
    work = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "results" / "exp009_work"
    work.mkdir(parents=True, exist_ok=True)

    out: dict[str, Any] = {
        "experiment": "exp009_epipolar_cost",
        "fixations": FIXATIONS,
        "vergence": VERGENCE,
        "seeds": list(SEEDS),
        "dv_band": DV_BAND,
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "rows": [],
        "timing": {},
    }

    for az, el in FIXATIONS:
        fx = Fixation(az, el, VERGENCE)
        for seed in SEEDS:
            model = scene_from_fixture(seed=seed)
            rig = StereoRig(baseline=float(model.params["baseline"]))
            tag = f"az{az:.2f}_el{el:.2f}_s{seed}"
            rots = eye_rotations(rig, fx)
            rect = rectification_rotation(fx)
            arms = {
                "RECT": (rect_poses(rig, fx), rect, rect),
                "TOED": (eye_camera_poses(rig, fx), rots.left, rots.right),
            }
            half_b = float(model.params["baseline"]) / 2.0
            centre_head = np.array([-half_b, 0.0, 0.0])

            # --- pass 1: render and match each arm -------------------------
            per_arm: dict[str, dict[str, Any]] = {}
            for arm, (poses, rot_l, rot_r) in arms.items():
                left, right, depth, params = render(work, f"{arm}_{tag}", model, fx, poses, binary)
                lo, hi = disparity_range(rot_l, rot_r, rig, params)
                t0 = time.time()
                if arm == "RECT":
                    d_sub, var_d, valid = front_end_block(left, right, lo, hi, WIN)
                    dv_est = np.zeros_like(d_sub)
                else:
                    d_sub, var_d, valid, dv_est = front_end_block_2d(
                        left, right, np.arange(lo, hi + 1)
                    )
                elapsed = time.time() - t0
                out["timing"].setdefault(arm, []).append(elapsed)

                z_est = triangulate_depth(d_sub, dv_est, params, rig, fx, arm)
                p_est = head_points(z_est, params, rot_l, centre_head)
                p_true = head_points(depth, params, rot_l, centre_head)
                per_arm[arm] = {
                    "params": params,
                    "depth": depth,
                    "dv_est": dv_est,
                    "valid": valid,
                    "elapsed": elapsed,
                    "range": (lo, hi),
                    "rng_est": np.linalg.norm(p_est, axis=-1),
                    "rng_true": np.linalg.norm(p_true, axis=-1),
                    "p_true": p_true,
                }

            # --- the intersection of directions BOTH arms actually see ------
            lattice = common_lattice(per_arm["RECT"]["params"])
            covered = {}
            for arm, a in per_arm.items():
                index, inside = lattice_cells(a["p_true"], lattice)
                a["index"], a["inside"] = index, inside
                seen = np.zeros(lattice.shape, dtype=bool)
                seen[index[inside][:, 0], index[inside][:, 1]] = True
                covered[arm] = seen
            both = covered["RECT"] & covered["TOED"]

            # --- pass 2: score, restricted to the common directions ---------
            for arm, a in per_arm.items():
                params, index, inside = a["params"], a["index"], a["inside"]
                in_common = np.zeros(inside.shape, dtype=bool)
                in_common[inside] = both[index[inside][:, 0], index[inside][:, 1]]
                bands = band_masks(a["depth"], params)
                ok = a["valid"] & in_common & np.isfinite(a["rng_est"]) & np.isfinite(a["rng_true"])
                row: dict[str, Any] = {
                    "arm": arm,
                    "az": az,
                    "el": el,
                    "seed": seed,
                    "matcher_seconds": a["elapsed"],
                    "disparity_range": list(a["range"]),
                    "valid_fraction": float(a["valid"].mean()),
                    "common_fraction": float(in_common.mean()),
                    "scored_fraction": float(ok.mean()),
                }
                for band, mask in bands.items():
                    m = ok & mask
                    err = np.abs(a["rng_est"][m] - a["rng_true"][m])
                    row[band] = {
                        "n": int(m.sum()),
                        "median": float(np.median(err)) if m.sum() else float("nan"),
                        "p90": float(np.percentile(err, 90)) if m.sum() else float("nan"),
                    }
                if arm == "TOED":
                    f_px = float(params["f_px"])
                    hb = float(params["baseline"]) / 2.0
                    pts = a["p_true"]
                    vl = (pts - np.array([-hb, 0.0, 0.0])) @ np.asarray(rots.left)
                    vr = (pts - np.array([hb, 0.0, 0.0])) @ np.asarray(rots.right)
                    with np.errstate(divide="ignore", invalid="ignore"):
                        dv_pred = f_px * (vl[..., 1] / vl[..., 2] - vr[..., 1] / vr[..., 2])
                    finite = np.isfinite(dv_pred)
                    row["dv_pred_max"] = float(np.max(np.abs(dv_pred[finite])))
                    row["dv_pred_rms"] = float(np.sqrt(np.mean(dv_pred[finite] ** 2)))
                    row["dv"] = {}
                    for band, mask in bands.items():
                        m = ok & mask & np.isfinite(dv_pred)
                        if m.sum() > 50:
                            x, y = a["dv_est"][m].astype(float), dv_pred[m]
                            # est_sd is recorded because a CONSTANT estimate makes
                            # the correlation undefined while leaving the residual
                            # small and flattering. Without it that case reads as a
                            # success.
                            row["dv"][band] = {
                                "n": int(m.sum()),
                                "corr": float(np.corrcoef(x, y)[0, 1]),
                                "est_sd": float(np.std(x)),
                                "pred_sd": float(np.std(y)),
                                "residual_rms": float(np.sqrt(np.mean((x - y) ** 2))),
                                "pred_rms": float(np.sqrt(np.mean(y**2))),
                                "est_rms": float(np.sqrt(np.mean(x**2))),
                                "mean_offset": float(np.mean(x - y)),
                            }
                out["rows"].append(row)
        print(f"  az={az:.2f} el={el:.2f} done", flush=True)

    first = sorted(d for d in work.iterdir() if (d / "params.json").exists())[0]
    out["rendered_with"] = render_provenance(first)
    dest = REPO / "results" / "exp009_epipolar_cost"
    dest.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, indent=2)
    (dest / "results.json").write_text(text)
    (HERE / "results.json").write_text(text)
    print(f"\nwrote {dest / 'results.json'}")


if __name__ == "__main__":
    main()
