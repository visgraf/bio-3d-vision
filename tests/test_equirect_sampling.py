"""Step 18a: equirectangular capture, spherical sampling, and what the belief assumes.

**Which of these ran against a real Blender is marked.** Everything in the first
three sections is pure geometry and runs everywhere; the render section skips
without a Blender binary, naming what goes unverified.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from bio3dvision.belief import HeadFrameBelief
from bio3dvision.oculomotor import Fixation, StereoRig, eye_rotations
from bio3dvision.sampling import (
    RECTIFIED_LEFT_CAMERA,
    EquirectSampling,
    PinholeSampling,
    SamplingModel,
)

REPO = Path(__file__).resolve().parents[1]
RENDERER = REPO / "src" / "bio3dvision" / "blender_render.py"
BASELINE = 0.065
RIG = StereoRig(baseline=BASELINE)
ANCHOR = Fixation(0.0, 0.0, 0.06)

needs_blender = pytest.mark.skipif(
    shutil.which("blender") is None,
    reason=(
        "no Blender binary on PATH. The sampling model, the disparity relation and "
        "the belief are still checked here, but NOTHING VERIFIES THAT CYCLES' "
        "PANORAMIC Z PASS IS RADIAL — falsifier 1, the one everything downstream "
        "rests on."
    ),
)


def _have_openexr() -> bool:
    try:
        import OpenEXR  # noqa: F401
    except ImportError:
        return False
    return True


needs_exr = pytest.mark.skipif(not _have_openexr(), reason='needs the "blender" extra')


# ---------------------------------------------------------------------------
# UNKNOWN 3 — the interface. fc-009 asserted this; here it is by construction.
# ---------------------------------------------------------------------------
def test_equirect_satisfies_the_protocol_with_no_signature_change() -> None:
    """fc-009's claim, which has been an assertion since iteration 6."""
    model = EquirectSampling((64, 32))
    assert isinstance(model, SamplingModel)
    for member in ("shape", "frame", "direction", "index", "contains"):
        assert hasattr(model, member), member


def test_the_frame_is_the_same_one_the_pinhole_returns() -> None:
    """Only the index-to-direction MAP changes; the 3-D frame does not.

    This is what lets the belief consume it unchanged, and it is the substance of
    "a non-planar projection without a signature change".
    """
    assert EquirectSampling((8, 4)).frame == RECTIFIED_LEFT_CAMERA
    assert EquirectSampling((8, 4)).frame == PinholeSampling((8, 4), 700.0).frame


@pytest.mark.parametrize("shape", [(64, 32), (256, 128), (512, 256)])
def test_the_round_trip_is_exact_on_every_sample(shape: tuple[int, int]) -> None:
    """``index(direction(i)) == i`` over the WHOLE lattice, poles included.

    The pole was the expected failure — a column at ``theta = 0`` would collapse
    every row onto one direction. It does not arise: the half-pixel offset keeps
    ``theta`` in ``[pi/2W, pi - pi/2W]``, so no column sits at a pole. Checked at
    three resolutions here and to 8192x4096 (33.5M indices) in the findings.
    """
    model = EquirectSampling(shape)
    height, width = shape
    rows, cols = np.mgrid[0:height, 0:width]
    index = np.stack([rows, cols], axis=-1)
    directions = model.direction(index.astype(np.float64))
    assert np.abs(np.linalg.norm(directions, axis=-1) - 1.0).max() < 1e-12
    assert np.array_equal(model.index(directions), index)


def test_index_accepts_directions_the_pinhole_inverse_refuses() -> None:
    """A sphere has no 'behind the sensor', and the pinhole does."""
    backward = np.array([0.0, 0.0, -1.0])
    EquirectSampling((8, 4)).index(backward)  # must not raise
    with pytest.raises(ValueError, match="d_z <= 0"):
        PinholeSampling((8, 4), 700.0).index(backward)


def test_the_lattice_is_non_uniform_but_membership_is_a_bounds_check() -> None:
    """Both halves matter, and only one of them exercises fc-009's provision."""
    model = EquirectSampling((256, 128))
    height, width = model.shape
    theta = np.pi * (np.arange(width) + 0.5) / width
    omega = (2 * np.pi / height) * (np.pi / width) * np.sin(theta)
    assert omega.max() / omega.min() > 50.0, "equirect must be non-uniform in solid angle"
    assert omega.sum() * height == pytest.approx(4 * np.pi, rel=1e-4)
    # ... and yet every in-bounds index is sampled, so `contains` is still bounds.
    assert bool(model.contains(np.array([0, 0])))
    assert bool(model.contains(np.array([height - 1, width - 1])))
    assert not bool(model.contains(np.array([height, 0])))


# ---------------------------------------------------------------------------
# UNKNOWN 2 — rows are epipolar, and the depth relation is NOT f*b/z.
# ---------------------------------------------------------------------------
def test_rows_are_epipolar_when_the_pole_is_the_baseline() -> None:
    """Corresponding points share a row, exactly, for every point in space."""
    model = EquirectSampling((256, 128))
    assert np.allclose(model.pole, [1.0, 0.0, 0.0])
    rng = np.random.default_rng(0)
    points = rng.uniform(-4.0, 4.0, (4000, 3))
    points = points[np.linalg.norm(points, axis=1) > 0.5]
    left = model.index(_unit(points - np.array([-BASELINE / 2, 0.0, 0.0])))
    right = model.index(_unit(points - np.array([BASELINE / 2, 0.0, 0.0])))
    # The epipolar coordinate is phi about the baseline, computed from each eye
    # SEPARATELY — computing it once and comparing it with itself would assert
    # nothing. Rows may still differ by a rounding step; the angle must not.
    v_l = points - np.array([-BASELINE / 2, 0.0, 0.0])
    v_r = points - np.array([BASELINE / 2, 0.0, 0.0])
    phi_l = np.arctan2(v_l[:, 2], v_l[:, 1])
    phi_r = np.arctan2(v_r[:, 2], v_r[:, 1])
    assert np.abs(phi_l - phi_r).max() == 0.0, "phi about the baseline must be identical"
    assert (left[:, 0] == right[:, 0]).mean() > 0.999


def _unit(v: np.ndarray) -> np.ndarray:
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def test_the_disparity_to_depth_relation_is_the_sine_rule_not_f_b_over_z() -> None:
    """``r_L = b sin(theta_R) / sin(theta_R - theta_L)``, and it depends on theta."""
    rng = np.random.default_rng(1)
    points = rng.uniform(-4.0, 4.0, (20000, 3))
    points = points[np.linalg.norm(points, axis=1) > 0.5]
    c_l, c_r = np.array([-BASELINE / 2, 0.0, 0.0]), np.array([BASELINE / 2, 0.0, 0.0])
    v_l, v_r = points - c_l, points - c_r
    r_l = np.linalg.norm(v_l, axis=1)
    theta_l = np.arccos(np.clip(v_l[:, 0] / r_l, -1.0, 1.0))
    theta_r = np.arccos(np.clip(v_r[:, 0] / np.linalg.norm(v_r, axis=1), -1.0, 1.0))
    disparity = theta_r - theta_l
    assert disparity.min() > 0.0, "angular disparity is strictly positive for a parallel pair"
    predicted = BASELINE * np.sin(theta_r) / np.sin(disparity)
    assert np.abs(predicted / r_l - 1.0).max() < 1e-8

    # And it is not the pinhole relation with a substitution: at equal range the
    # disparity depends on the angle from the baseline.
    near_pole = np.arctan2(
        BASELINE * np.sin(np.radians(10.0)), 3.0 + BASELINE * np.cos(np.radians(10.0))
    )
    equator = np.arctan2(
        BASELINE * np.sin(np.radians(90.0)), 3.0 + BASELINE * np.cos(np.radians(90.0))
    )
    assert equator / near_pole > 5.0


# ---------------------------------------------------------------------------
# FALSIFIER 4 — the belief. It works, and it carries a pinhole assumption.
# ---------------------------------------------------------------------------
def test_the_belief_builds_on_spherical_sampling_and_cells_move() -> None:
    model = EquirectSampling((240, 120))
    belief = HeadFrameBelief.from_sampling(model, ANCHOR, RIG)
    base_index, base_visible = belief.reproject(ANCHOR, model)
    for fixation in (
        Fixation(np.radians(10.0), 0.0, 0.06),
        Fixation(0.0, np.radians(10.0), 0.06),
        Fixation(0.0, 0.0, 0.16),
    ):
        index, visible = belief.reproject(fixation, model)
        both = base_visible & visible
        moved = (index != base_index).any(axis=-1) & both
        assert moved.sum() / both.sum() > 0.95, fixation


def test_the_world_direction_drift_is_quantisation_and_scales_with_the_cell() -> None:
    """17a-fix's invariance, on a lattice where it can only hold to a cell.

    Nearest-neighbour reprojection cannot preserve a direction exactly on a finite
    lattice. What it must do is preserve it TO THE CELL, and halving the pitch must
    halve the drift — otherwise the residual is a frame error wearing quantisation
    as a disguise.
    """
    fixation = Fixation(np.radians(10.0), 0.0, 0.06)
    ratios = []
    for height, width in ((120, 60), (240, 120), (480, 240)):
        model = EquirectSampling((height, width))
        belief = HeadFrameBelief.from_sampling(model, ANCHOR, RIG)
        i0, v0 = belief.reproject(ANCHOR, model)
        i1, v1 = belief.reproject(fixation, model)
        both = v0 & v1
        w0 = belief.world_direction(i0, ANCHOR, model)
        w1 = belief.world_direction(i1, fixation, model)
        drift = np.degrees(np.arccos(np.clip(np.einsum("...i,...i->...", w0, w1), -1.0, 1.0)))
        ratios.append(float(drift[both].max()) / (180.0 / width))
    assert max(ratios) - min(ratios) < 0.1, f"drift/pitch must be flat, got {ratios}"
    assert max(ratios) < 1.0


def test_the_sphere_loses_no_grid_but_reproject_discards_half_of_it() -> None:
    """**The finding of falsifier 4.** The loss is the belief's, not the sphere's.

    ``contains`` reports every cell present at every amplitude — a sphere sees
    every direction, which is what 18b's hypothesis rests on. ``reproject`` then
    ANDs in ``in_eye[..., 2] > 0.0``, a pinhole guard, and discards the back
    hemisphere at every amplitude. The constant 0.5 is the signature: the pinhole
    grid loss GROWS with amplitude (0.041 at 1 deg to 0.584 at 15, bio-055),
    because what it loses is the field edge; this loses a fixed half-sphere.
    """
    model = EquirectSampling((240, 120))
    belief = HeadFrameBelief.from_sampling(model, ANCHOR, RIG)
    for degrees in (1.0, 5.0, 10.0, 30.0, 60.0):
        for fixation in (
            Fixation(np.radians(degrees), 0.0, 0.06),
            Fixation(0.0, np.radians(degrees), 0.06),
        ):
            rotation = np.asarray(eye_rotations(RIG, fixation).left)
            in_eye = belief.directions @ rotation
            index = np.asarray(model.index(in_eye))
            assert np.asarray(model.contains(index)).all(), "a sphere loses no grid"
            _reprojected, visible = belief.reproject(fixation, model)
            assert float(visible.mean()) == pytest.approx(0.5, abs=0.01)


# ---------------------------------------------------------------------------
# UNKNOWN 1 — the render. Everything above is unreadable if this fails.
# ---------------------------------------------------------------------------
@needs_exr
@needs_blender
def test_the_equirect_depth_pass_is_radial_on_tiled_planes(tmp_path: Path) -> None:
    """**Falsifier 1.** Three planes in three longitude bands, checked analytically.

    Tiled and not stacked, for the reason ``build_calibration_scene`` records: a
    shell at each distance would leave one distance in the pass and a three-way
    check would silently be a one-way one.
    """
    from bio3dvision.blender_load import read_exr_depth

    width, height = 512, 256
    distances = [2.0, 3.5, 5.0]
    subprocess.run(
        [
            str(shutil.which("blender")),
            "--background",
            "--factory-startup",
            "--python",
            str(RENDERER),
            "--",
            "--out",
            str(tmp_path),
            "--sphere-cards",
            *[str(z) for z in distances],
            "--pano",
            "--res",
            str(width),
            str(height),
            "--samples",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
    if not (tmp_path / "depth_left.exr").exists():
        pytest.fail("the equirect render failed, which is a result about the renderer")
    depth = read_exr_depth(tmp_path / "depth_left.exr")
    assert depth.shape == (height, width)

    rows, cols = np.mgrid[0:height, 0:width]
    lon = 2 * np.pi * (cols + 0.5) / width - np.pi
    lat = np.pi / 2 - np.pi * (rows + 0.5) / height
    dirs = np.stack([np.cos(lat) * np.sin(lon), np.sin(lat), -np.cos(lat) * np.cos(lon)], axis=-1)
    centre = np.array([-BASELINE / 2, 0.0, 0.0])
    span = 2 * np.pi / len(distances)
    radial_err, planar_err, total = [], [], 0
    for i, z in enumerate(sorted(distances)):
        lam = -np.pi + span * (i + 0.5)
        normal = np.array([np.sin(lam), 0.0, -np.cos(lam)])
        along = dirs @ normal
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (z - centre @ normal) / along
        point = centre + t[..., None] * dirs
        ex, ey = np.array([np.cos(lam), 0.0, np.sin(lam)]), np.array([0.0, 1.0, 0.0])
        half_w = z * np.tan((span - 2 * span * 0.10) / 2)
        half_h = z * np.tan(np.radians(35.0))
        hit = (
            np.isfinite(depth)
            & (along > 1e-6)
            & (t > 0)
            & (np.abs((point - z * normal) @ ex) < half_w * 0.95)
            & (np.abs((point - z * normal) @ ey) < half_h * 0.95)
        )
        assert hit.sum() > 5000, f"plane at {z} m is barely visible: {hit.sum()} px"
        total += int(hit.sum())
        radial_err.append(np.abs(depth[hit] - t[hit]))
        planar_err.append(np.abs(depth[hit] - (z - centre @ normal)))
    radial = np.concatenate(radial_err)
    planar = np.concatenate(planar_err)
    assert total > 30000
    assert radial.max() < 1e-3, f"depth is not radial: max error {radial.max()} m"
    assert planar.max() > 1.0, "the two conventions must be distinguishable on this scene"
