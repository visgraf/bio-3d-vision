"""exp010 — does re-acquiring beat re-weighting? Pre-registered in preregistration.md.

Two arms differing in ONE thing: whether the proposed saccade is executed. Both
propose identically and both render RECT+, because bio-063 measures the rectified
and toed-in paths as different EYE ALIGNMENTS and an unmatched OPEN arm would
confound re-rendering with rectification.

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
from scipy.ndimage import distance_transform_edt, gaussian_filter

from bio3dvision.belief import HeadFrameBelief
from bio3dvision.blender_load import load_render, render_provenance
from bio3dvision.loop import ActiveStereo
from bio3dvision.oculomotor import (
    Estimate,
    Fixation,
    StereoRig,
    TargetRefused,
    rectification_rotation,
    target_to_fixation,
)
from bio3dvision.sampling import PinholeSampling
from bio3dvision.scene_model import (
    gaze_shift_px,
    occlusion_fractions,
    rasterise_depth,
    rectified_camera_poses,
    scene_from_fixture,
    split_cards,
    write_scene,
)

# --- declared in the preregistration -----------------------------------------
K_SPLIT = 4  # 8.84% left-occluded: exp008's sharpest level, measured not assumed
SEEDS = (0, 1, 2, 3, 4, 5, 6, 7)
BUDGET = 40
PRIOR_DEPTH, PRIOR_STD = 3.0, 3.0
AT_MAX_PX, AWAY_MIN_PX = 10.0, 24.0
DISC_STEP_PX = 1.0

REPO = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).parent
RENDERER = REPO / "src" / "bio3dvision" / "blender_render.py"


def rect_orientation(rig: StereoRig, fixation: Fixation, k: float) -> np.ndarray:
    """The camera this loop actually has. Paired with a SHIFTED sampling."""
    return np.asarray(rectification_rotation(fixation))


def sampling_for(fixation: Fixation, rig: StereoRig, params) -> PinholeSampling:
    """The sensor at ``fixation``: rectified orientation, principal point on the gaze."""
    height, width = int(params["H"]), int(params["W"])
    f_px = float(params["f_px"])
    row, col = gaze_shift_px(rig, fixation, f_px)
    return PinholeSampling(
        (height, width), f_px, principal_point=((height - 1) / 2.0 - row, (width - 1) / 2.0 - col)
    )


def anchor_vergence(rig: StereoRig, depth: float) -> float:
    """Vergence that fixates ``depth`` straight ahead. The loop starts at its prior."""
    half_b = rig.baseline / 2.0
    return float(np.arctan(rig.baseline * depth / (depth * depth - half_b * half_b)))


# --- the frame conversion the preregistration requires ------------------------
def planar_to_range(z, rays_head, centre_head):
    """Planar ``z`` in the rectified frame -> RANGE from the cyclopean origin.

    ``z`` is fixation-dependent (``oculomotor.py:460-466``); range from a fixed
    origin is not. Fusing ``z`` across fixations would fuse different quantities,
    which is latent in HeadFrameBelief and could not surface until something moved
    the eye. Returns ``(range, d_range/dz)`` — the Jacobian carries the variance.
    """
    point = centre_head + z[..., None] * rays_head
    rng = np.linalg.norm(point, axis=-1)
    with np.errstate(divide="ignore", invalid="ignore"):
        jac = np.einsum("...i,...i->...", point, rays_head) / rng
    return rng, jac


def range_to_planar(rng: float, ray_head, centre_head) -> float:
    """The inverse, for ONE cell: solve ``|c + z m| = rng`` for the positive root."""
    a = float(ray_head @ ray_head)
    b = 2.0 * float(centre_head @ ray_head)
    c = float(centre_head @ centre_head) - float(rng) * float(rng)
    disc = b * b - 4 * a * c
    if disc < 0.0:
        return float("nan")
    return float((-b + np.sqrt(disc)) / (2 * a))


def unit_z_rays(sampling: PinholeSampling, rotation) -> np.ndarray:
    """Per-pixel rays scaled so their z is 1, in the head frame. Planar-depth rays."""
    height, width = sampling.shape
    rows, cols = np.mgrid[0:height, 0:width]
    index = np.stack([rows, cols], axis=-1).astype(np.float64)
    d = np.asarray(sampling.direction(index))
    return (d / d[..., 2:3]) @ np.asarray(rotation).T


def band_masks(depth_z, params) -> dict[str, np.ndarray]:
    """exp004's bands, in the anchor image where ground truth is expressed."""
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
    return {
        "AT": dist <= AT_MAX_PX,
        "MIDDLE": (dist > AT_MAX_PX) & (dist < AWAY_MIN_PX),
        "AWAY": dist >= AWAY_MIN_PX,
        "POOLED": np.ones_like(dist, bool),
    }


def prepare_scene(work, model, tag):
    """Write the scene ONCE per arm-and-seed. Only ``eye_poses`` changes per render."""
    scene = work / f"scene_{tag}"
    if not (scene / "scene.json").exists():
        write_scene(model, scene)
    return scene


def render(work, tag, scene, poses, binary):
    out = work / tag
    if not (out / "depth_left.exr").exists():
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


def run_arm(
    arm: str,
    model,
    rig,
    anchor,
    work,
    tag,
    binary,
    freeze_pedestal: bool = False,
    replay: list | None = None,
) -> dict[str, Any]:
    """One arm, one seed. ``arm`` is OPEN or CLOSED.

    **Both extra arguments default off and exp010's own behaviour is unchanged.**
    They exist for exp014, which separates the two things that move together when
    the eye moves:

    ``freeze_pedestal`` computes ``d_fix`` once at fixation 0 and holds it, so the
    acuity weight keeps following the gaze while the linearisation stops. The
    pedestal is still computed the ported way — same window, same integrator, same
    clamp — and only then held.

    ``replay`` supplies BOTH the chosen cell and the executed fixation at every
    step, which YOKES an arm to another's trajectory. Replaying the camera path
    alone would not be enough: the fovea is placed on the arm's OWN argmax cell,
    and a frozen pedestal changes the belief and therefore that cell — so the two
    arms would differ in where they looked as well as in how they linearised.
    Replaying the cell too leaves ``d_fix`` as the only difference.

    It is also what lets exp014 reuse exp011's captures rather than rendering new
    ones. What it gives up is the free-running question — how a frozen-pedestal
    loop would choose to look — which is a different experiment.
    """
    scene = prepare_scene(work, model, tag)
    poses = rectified_camera_poses(rig, anchor, float(model.params["f_px"]), int(model.params["W"]))
    left, right, depth, params = render(work, f"{tag}_anchor", scene, poses, binary)
    anchor_sampling = sampling_for(anchor, rig, params)
    belief = HeadFrameBelief.from_sampling(
        anchor_sampling,
        anchor,
        rig,
        prior_depth=PRIOR_DEPTH,
        prior_std=PRIOR_STD,
        orientation=rect_orientation,
    )
    half_b = float(params["baseline"]) / 2.0
    centre_head = np.array([-half_b, 0.0, 0.0])

    ever = np.zeros(belief.shape, dtype=bool)
    survived = np.ones(belief.shape, dtype=bool)
    current = anchor
    t0 = time.time()
    engine = ActiveStereo(left, right, params, prior_depth=PRIOR_DEPTH, prior_std=PRIOR_STD)
    # The FRONT END is where the matcher cost is, and CLOSED pays it again on every
    # saccade. Timing only measurement() would have understated CLOSED by the whole
    # of it and made the cost side of outcome (a) wrong.
    front_end_seconds = time.time() - t0
    front_end_calls = 1
    history: list[dict[str, Any]] = []
    renders = 1
    matcher_seconds = 0.0
    refusals: list[dict[str, Any]] = []
    stopped_at = None
    frozen_pedestal: float | None = None
    # The [d_lo, d_hi] clamp cannot newly bind under freezing — it lives inside
    # vergence, which runs once. Where freezing shows up is the DOWNSTREAM
    # np.clip(Zmeas, 0.3, 10.0): a first-order expansion evaluated far from its
    # expansion point produces absurd depths and that clip is what catches them.
    clip_hits = 0
    clip_total = 0
    trajectory: list[dict[str, Any]] = []
    chosen: list[list[int]] = []

    for step in range(BUDGET):
        sampling = sampling_for(current, rig, params)
        index, visible = belief.reproject(current, sampling)
        survived &= visible
        if not visible.any():
            stopped_at = {"step": step, "why": "the belief left the sensor entirely"}
            break

        # --- choose: argmax posterior variance over cells this eye can see ----
        # Restricted to where information is GETTABLE, exactly as loop.py does:
        # ActiveStereo.valid excludes the border and the disparity-search margin
        # (dmax + win + 1 = 64 columns on the left), and a fovea placed on an
        # invalid pixel measures nothing, leaves the prior untouched, and is
        # therefore still the argmax on the next step. Without this OPEN sits on
        # cell (0, 0) for the whole budget — measured, not supposed.
        gettable = belief.gather(engine.valid.astype(np.float32), current, sampling, 0.0) > 0.0
        selectable = visible & gettable
        if not selectable.any():
            stopped_at = {"step": step, "why": "no visible cell is measurable"}
            break
        if replay is not None:
            cell = tuple(replay[step]["cell"])
        else:
            v = gaussian_filter(np.where(selectable, belief.var, 0.0), 4.0)
            v = np.where(selectable, v, -np.inf)
            cell = np.unravel_index(int(np.argmax(v)), v.shape)
        yf, xf = int(index[cell][0]), int(index[cell][1])
        chosen.append([int(cell[0]), int(cell[1])])

        # --- measure ----------------------------------------------------------
        t0 = time.time()
        z_img, prec_img, d_fix = engine.measurement(yf, xf, d_fix=frozen_pedestal)
        if freeze_pedestal and frozen_pedestal is None:
            # Fixation 0's value, computed exactly as CLOSED computes it, then held.
            frozen_pedestal = float(engine.vergence(yf, xf))
        clipped = int(np.sum((np.asarray(z_img) <= 0.3001) | (np.asarray(z_img) >= 9.9999)))
        clip_hits += clipped
        clip_total += int(np.asarray(z_img).size)
        matcher_seconds += time.time() - t0
        rays = unit_z_rays(sampling, rectification_rotation(current))
        rng_img, jac = planar_to_range(np.asarray(z_img, float), rays, centre_head)
        with np.errstate(divide="ignore", invalid="ignore"):
            prec_rng = np.where(np.abs(jac) > 1e-9, prec_img / (jac * jac), 0.0)
        ok = np.isfinite(rng_img) & np.isfinite(prec_rng)
        belief.fuse(
            np.where(ok, rng_img, 0.0).astype(np.float32),
            np.where(ok, prec_rng, 0.0).astype(np.float32),
            current,
            sampling,
        )
        ever |= visible & (
            belief.gather(np.asarray(prec_rng, np.float32), current, sampling, 0.0) > 0
        )

        # --- propose the next fixation ---------------------------------------
        ray_head = np.asarray(belief.directions[cell], dtype=float)
        rect = np.asarray(rectification_rotation(current))
        in_cam = ray_head @ rect
        z_cell = range_to_planar(
            float(belief.mean[cell]), ray_head / max(in_cam[2], 1e-9), centre_head
        )
        proposal: Any = TargetRefused(frozenset())
        if in_cam[2] > 0.0 and np.isfinite(z_cell) and z_cell > 0.0:
            proposal = target_to_fixation(
                in_cam / np.linalg.norm(in_cam),
                Estimate(value=z_cell, variance=float(belief.var[cell])),
                rig,
                current,
            )
        history.append(
            {
                "step": step,
                "cell": [int(cell[0]), int(cell[1])],
                "pixel": [yf, xf],
                "azimuth": current.azimuth,
                "elevation_down": current.elevation_down,
                "vergence": current.vergence,
                "D_fix": float(d_fix),
                "visible_fraction": float(visible.mean()),
                "refused": isinstance(proposal, TargetRefused),
            }
        )
        if isinstance(proposal, TargetRefused):
            refusals.append({"step": step, "reasons": sorted(r.name for r in proposal.reasons)})
            if arm == "CLOSED":
                stopped_at = {
                    "step": step,
                    "why": "target_to_fixation refused",
                    "reasons": sorted(r.name for r in proposal.reasons),
                }
                break
            continue

        if arm == "CLOSED":
            if replay is not None:
                f = replay[step]["fixation"]
                current = Fixation(f[0], f[1], f[2])
            else:
                current = proposal.fixation
            # Paired AT THE POINT OF ASSIGNMENT, not zipped from two lists
            # afterwards: a refusal `continue`s before this line, so separate
            # lists would silently misalign from that step on and a yoked replay
            # would follow the wrong cell. exp011 recorded no refusals in 192
            # runs, which is exactly why that must not become a latent assumption.
            trajectory.append(
                {
                    "cell": chosen[-1],
                    "fixation": [current.azimuth, current.elevation_down, current.vergence],
                }
            )
            poses = rectified_camera_poses(rig, current, float(params["f_px"]), int(params["W"]))
            left, right, _d, params = render(work, f"{tag}_s{step:03d}", scene, poses, binary)
            renders += 1
            t_fe = time.time()
            engine = ActiveStereo(left, right, params, prior_depth=PRIOR_DEPTH, prior_std=PRIOR_STD)
            front_end_seconds += time.time() - t_fe
            front_end_calls += 1

    return {
        "arm": arm,
        "renders": renders,
        "matcher_seconds": matcher_seconds,
        "front_end_seconds": front_end_seconds,
        "front_end_calls": front_end_calls,
        "frozen_pedestal": frozen_pedestal,
        "trajectory": trajectory,
        "zmeas_clip_fraction": (clip_hits / clip_total) if clip_total else 0.0,
        "history": history,
        "refusals": refusals,
        "stopped_at": stopped_at,
        "steps_completed": len(history),
        "belief_mean": belief.mean,
        "belief_var": belief.var,
        "ever_measured": ever,
        "survived": survived,
        "anchor_depth": depth,
        "params": params,
    }


def main() -> None:
    binary = shutil.which("blender")
    if binary is None:
        raise SystemExit("exp010 renders every fixation; it needs a Blender binary.")
    work = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "results" / "exp010_work"
    work.mkdir(parents=True, exist_ok=True)

    fractions = occlusion_fractions(split_cards(scene_from_fixture(seed=0), K_SPLIT))
    out: dict[str, Any] = {
        "experiment": "exp010_closed_loop",
        "k_split": K_SPLIT,
        "left_occluded_fraction": float(fractions["left_occluded_fraction"]),
        "seeds": list(SEEDS),
        "budget": BUDGET,
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "rows": [],
    }
    print(
        f"k={K_SPLIT}: left occluded {fractions['left_occluded_fraction'] * 100:.2f}%", flush=True
    )

    for seed in SEEDS:
        model = split_cards(scene_from_fixture(seed=seed), K_SPLIT)
        rig = StereoRig(baseline=float(model.params["baseline"]))
        anchor = Fixation(0.0, 0.0, anchor_vergence(rig, PRIOR_DEPTH))
        gt_z = rasterise_depth(model, smooth=False)
        bands = band_masks(gt_z, model.params)

        results = {}
        for arm in ("OPEN", "CLOSED"):
            r = run_arm(arm, model, rig, anchor, work, f"{arm}_s{seed}", binary)
            rays = unit_z_rays(
                sampling_for(anchor, rig, r["params"]), rectification_rotation(anchor)
            )
            half_b = float(r["params"]["baseline"]) / 2.0
            gt_rng, _ = planar_to_range(
                np.asarray(r["anchor_depth"], float), rays, np.array([-half_b, 0.0, 0.0])
            )
            r["gt_range"] = gt_rng
            results[arm] = r

        common = results["OPEN"]["ever_measured"] & results["CLOSED"]["ever_measured"]
        for arm, r in results.items():
            err = np.abs(r["belief_mean"] - r["gt_range"])
            finite = np.isfinite(err) & np.isfinite(r["gt_range"])
            row: dict[str, Any] = {
                "arm": arm,
                "seed": seed,
                "renders": r["renders"],
                "matcher_seconds": r["matcher_seconds"],
                "front_end_seconds": r["front_end_seconds"],
                "front_end_calls": r["front_end_calls"],
                "steps_completed": r["steps_completed"],
                "stopped_at": r["stopped_at"],
                "refusals": r["refusals"],
                "history": r["history"],
                "ever_measured_fraction": float(r["ever_measured"].mean()),
                "survived_fraction": float(r["survived"].mean()),
                "common_fraction": float(common.mean()),
                "excluded_own_only": float((r["ever_measured"] & ~common).mean()),
            }
            for band, mask in bands.items():
                for label, sel in (("common", common), ("own", r["ever_measured"])):
                    m = finite & mask & sel
                    row[f"{band}_{label}"] = {
                        "n": int(m.sum()),
                        "median_abs_err": float(np.median(err[m])) if m.sum() else float("nan"),
                        "p90": float(np.percentile(err[m], 90)) if m.sum() else float("nan"),
                    }
            out["rows"].append(row)
        print(
            f"  seed {seed}: OPEN {results['OPEN']['steps_completed']} steps, "
            f"CLOSED {results['CLOSED']['steps_completed']} steps "
            f"({results['CLOSED']['renders']} renders)",
            flush=True,
        )

    first = sorted(d for d in work.iterdir() if (d / "params.json").exists())[0]
    out["rendered_with"] = render_provenance(first)
    dest = REPO / "results" / "exp010_closed_loop"
    dest.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, indent=2)
    (dest / "results.json").write_text(text)
    (HERE / "results.json").write_text(text)
    print(f"\nwrote {dest / 'results.json'}")


if __name__ == "__main__":
    main()
