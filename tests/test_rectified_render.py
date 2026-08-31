"""Rectification in the camera, with a principal-point shift. fc-012's falsifiers.

Two falsifiers guard this, and **the second exists because the first cannot catch
the failure that mattered**. ``rectification_rotation`` is the identity at zero
elevation, so B0 — bit-identity at ``Fixation(0, 0, 0)`` — tests the composition
at exactly the fixation where azimuth going inert is undetectable. Composed
without a shift, two fixations differing only in azimuth give bit-identical
cameras and B0 passes anyway.

The shift's units are **pinned by render**, not assumed. Its failure mode is
silent, the same shape as the File Output node that completed and wrote nothing.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from bio3dvision.blender_load import read_exr_image
from bio3dvision.oculomotor import Fixation, StereoRig, rectification_rotation
from bio3dvision.scene_model import (
    CAMERA_FROM_EYE,
    WORLD_FROM_HEAD,
    eye_camera_poses,
    gaze_shift_px,
    rectified_camera_poses,
    scene_from_fixture,
    write_scene,
)

REPO = Path(__file__).resolve().parents[1]
RENDERER = REPO / "src" / "bio3dvision" / "blender_render.py"
H, W, F_PX, BASELINE = 240, 320, 700.0, 0.065
CENTRE_COL = (W - 1) / 2.0
CENTRE_ROW = (H - 1) / 2.0
RIG = StereoRig(baseline=BASELINE)

needs_blender = pytest.mark.skipif(
    shutil.which("blender") is None,
    reason=(
        "no Blender binary on PATH. The geometry is still checked here, but "
        "NOTHING VERIFIES THAT shift_x MEANS WHAT THIS CODE ASSUMES — the one "
        "link in fc-012 that cannot be established without a render."
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
# Geometry. No renderer, so this runs everywhere.
# ---------------------------------------------------------------------------
def test_the_pair_is_rectified_by_construction() -> None:
    """Both eyes share an orientation whose x-axis is exactly the baseline."""
    for fixation in (
        Fixation(0.0, 0.0, 0.06),
        Fixation(0.20, 0.15, 0.06),
        Fixation(-0.224, -0.17, 0.16),
    ):
        poses = rectified_camera_poses(RIG, fixation, F_PX, W)
        left = np.array(poses["left"]["matrix_world"])
        right = np.array(poses["right"]["matrix_world"])
        assert np.array_equal(left[:3, :3], right[:3, :3])
        # x-axis along the baseline is what makes epipolar lines image rows.
        rot = np.asarray(rectification_rotation(fixation))
        assert np.allclose(rot @ np.array([1.0, 0.0, 0.0]), [1.0, 0.0, 0.0])
        # A common shift keeps it rectified; a per-eye shift would not.
        assert poses["left"]["shift_x"] == poses["right"]["shift_x"]
        assert poses["left"]["shift_y"] == poses["right"]["shift_y"] == 0.0


def test_the_row_shift_is_identically_zero() -> None:
    """This rectifier member puts the plane of regard at zero elevation.

    Asserted rather than assumed: a different member would need two numbers per
    fixation, and the code returning one zero is how that would be noticed.
    """
    for el in (0.0, 0.05, 0.10, 0.17, -0.17):
        for vergence in (0.03, 0.06, 0.16):
            row, _col = gaze_shift_px(RIG, Fixation(0.224, el, vergence), F_PX)
            assert abs(row) < 1e-9


def test_the_shift_is_vergence_independent() -> None:
    """It centres the gaze DIRECTION, so vergence cannot enter."""
    cols = {gaze_shift_px(RIG, Fixation(0.224, 0.10, v), F_PX)[1] for v in (0.0, 0.03, 0.06, 0.16)}
    assert len(cols) == 1


def test_azimuth_is_not_inert_which_is_what_B0_cannot_catch() -> None:
    """THE FALSIFIER B0 MISSES. Composed without a shift, this passes anyway.

    ``rectification_rotation`` is azimuth-zeroed by construction, so the camera
    MATRICES are identical at two azimuths — that is not a defect, it is why the
    shift exists. What must differ is the pose as a whole.
    """
    a = rectified_camera_poses(RIG, Fixation(0.00, 0.10, 0.06), F_PX, W)
    b = rectified_camera_poses(RIG, Fixation(0.20, 0.10, 0.06), F_PX, W)
    assert np.array_equal(
        np.array(a["left"]["matrix_world"]), np.array(b["left"]["matrix_world"])
    ), "the matrices SHOULD agree; a rectifier cannot rotate to an eccentric gaze"
    assert a["left"] != b["left"], "the POSE must differ, or azimuth is inert"
    assert abs(a["left"]["shift_x"] - b["left"]["shift_x"]) > 0.1


def test_the_shift_at_the_policy_reach_is_half_a_sensor_width() -> None:
    """bio-063's headline number, pinned where it can fail."""
    poses = rectified_camera_poses(RIG, Fixation(0.2240, 0.0, 0.06), F_PX, W)
    assert poses["left"]["shift_col_px"] == pytest.approx(159.4, abs=0.2)
    assert poses["left"]["shift_x"] == pytest.approx(0.498, abs=0.002)


def test_B0_geometry_the_rectified_path_equals_the_toed_path_at_the_origin() -> None:
    """The precondition for B0's render. At zero vergence and zero elevation the
    two paths must agree AS MATRICES, or bit-identity cannot hold for a reason
    that has nothing to do with the renderer."""
    rect = rectified_camera_poses(RIG, Fixation(0.0, 0.0, 0.0), F_PX, W)
    toed = eye_camera_poses(RIG, Fixation(0.0, 0.0, 0.0))
    for eye in ("left", "right"):
        assert np.array_equal(
            np.array(rect[eye]["matrix_world"]), np.array(toed[eye]["matrix_world"])
        )
    assert rect["left"]["shift_x"] == 0.0


# ---------------------------------------------------------------------------
# The render. This is where shift_x stops being an assumption.
# ---------------------------------------------------------------------------
def _render_marker(tmp: Path, direction, shift_x: float, shift_y: float, distance: float):
    """One emissive marker on a known ray, through RECTIFIED cameras."""
    rot = np.asarray(rectification_rotation(Fixation(0.0, 0.0, 0.06)))
    poses = {}
    for name, sign in (("left", -1.0), ("right", +1.0)):
        matrix = np.eye(4)
        matrix[:3, :3] = WORLD_FROM_HEAD @ rot @ CAMERA_FROM_EYE
        matrix[:3, 3] = WORLD_FROM_HEAD @ np.array([sign * BASELINE / 2, 0.0, 0.0])
        poses[name] = {
            "matrix_world": matrix.tolist(),
            "shift_x": float(shift_x),
            "shift_y": float(shift_y),
        }
    tmp.mkdir(parents=True, exist_ok=True)
    spec = {
        "markers": [(WORLD_FROM_HEAD @ (np.asarray(direction) * distance)).tolist()],
        "marker_radius": 0.004,
        "eye_poses": poses,
        "H": H,
        "W": W,
        "f_px": F_PX,
        "baseline": BASELINE,
    }
    (tmp / "markers.json").write_text(json.dumps(spec))
    subprocess.run(
        [
            str(shutil.which("blender")),
            "--background",
            "--factory-startup",
            "--python",
            str(RENDERER),
            "--",
            "--out",
            str(tmp),
            "--markers",
            str(tmp / "markers.json"),
            "--samples",
            "16",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
    if not (tmp / "left.exr").exists():
        pytest.fail("the marker render failed, which is a result about the renderer")
    img = read_exr_image(tmp / "left.exr")
    mask = img > 0.02
    if not mask.sum():
        return None
    rows, cols = np.nonzero(mask)
    weights = img[mask]
    return (
        float((rows * weights).sum() / weights.sum()),
        float((cols * weights).sum() / weights.sum()),
    )


@needs_exr
@needs_blender
@pytest.mark.parametrize(
    ("az_deg", "distance"), [(0.0, 3.0), (5.0, 3.0), (12.83, 3.0), (10.0, 1.083), (12.83, 6.0)]
)
def test_shift_x_is_pinned_by_render(tmp_path: Path, az_deg: float, distance: float) -> None:
    """``shift_x = f*tan(az)/W`` puts the ray at the sensor centre. **The pin.**

    The prediction carries the LEFT EYE'S PARALLAX, which is not part of the shift
    and is what makes the marker land off centre by ``f*(b/2)/distance``. Leaving
    it out reads as a 7.6 px shift error at 3 m, and it is not one.
    """
    az = np.radians(az_deg)
    direction = np.array([np.sin(az), 0.0, np.cos(az)])
    shift_x = F_PX * np.tan(az) / W
    got = _render_marker(tmp_path, direction, shift_x, 0.0, distance)
    assert got is not None, "the marker left the sensor, so the shift is wrong"
    v = direction * distance - np.array([-BASELINE / 2, 0.0, 0.0])
    predicted = CENTRE_COL + F_PX * v[0] / v[2] - shift_x * W
    assert got[1] == pytest.approx(predicted, abs=0.15)
    assert got[0] == pytest.approx(CENTRE_ROW, abs=0.15)


@needs_exr
@needs_blender
def test_the_shift_unit_is_the_larger_dimension_not_the_smaller(tmp_path: Path) -> None:
    """Discriminates W from H and pins the sign. Both alternatives fail loudly."""
    az = np.radians(10.0)
    direction = np.array([np.sin(az), 0.0, np.cos(az)])
    delta = F_PX * np.tan(az)
    right = _render_marker(tmp_path / "w", direction, delta / W, 0.0, 3.0)
    assert right is not None
    parallax = F_PX * (BASELINE / 2) / 3.0
    assert right[1] == pytest.approx(CENTRE_COL + parallax, abs=0.2)

    wrong_unit = _render_marker(tmp_path / "h", direction, delta / H, 0.0, 3.0)
    assert wrong_unit is not None
    assert abs(wrong_unit[1] - right[1]) > 20.0, "W and H must be distinguishable"

    wrong_sign = _render_marker(tmp_path / "s", direction, -delta / W, 0.0, 3.0)
    assert wrong_sign is None, "the wrong sign must leave the sensor, not land near"


@needs_exr
@needs_blender
def test_B0_the_rectified_path_reproduces_the_recorded_render_bit_identically(
    tmp_path: Path,
) -> None:
    """**B0.** At ``Fixation(0, 0, 0)`` every recorded render must come back exactly.

    Not "close". ``array_equal``. Rectification is the identity at zero elevation
    and the shift is zero at zero azimuth, so the two paths agree AS MATRICES and
    the renderer must therefore be doing the same thing, not something numerically
    near it. If this fails the composition is wrong and nothing after it is
    readable.
    """
    from bio3dvision.blender_load import load_render

    model = scene_from_fixture(seed=0)
    outputs = {}
    for tag, poses in (
        ("baseline", None),
        ("rectified", rectified_camera_poses(RIG, Fixation(0.0, 0.0, 0.0), F_PX, W)),
    ):
        scene = tmp_path / f"scene_{tag}"
        write_scene(model, scene)
        if poses is not None:
            spec = json.loads((scene / "scene.json").read_text())
            spec["eye_poses"] = poses
            (scene / "scene.json").write_text(json.dumps(spec))
        out = tmp_path / tag
        subprocess.run(
            [
                str(shutil.which("blender")),
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
            check=False,
            timeout=900,
        )
        if not (out / "depth_left.exr").exists():
            pytest.fail(f"the {tag} render failed, which is a result about the renderer")
        outputs[tag] = load_render(out)

    for i, what in enumerate(("left", "right", "depth")):
        assert np.array_equal(outputs["baseline"][i], outputs["rectified"][i]), (
            f"{what} differs at Fixation(0, 0, 0); the composition is wrong"
        )
