"""Gaze-contingent rendering: the basis change, and the four geometric falsifiers.

The basis change is the trap and it is tested WITHOUT a renderer, because
``blender_render`` may import nothing but the standard library and ``bpy`` and so
cannot compute it. The conversion lives in ``scene_model.eye_camera_poses``, which
is why it can be checked here at all.

The geometric falsifiers need a real Blender and skip without one, with a reason
naming what goes unverified. **None of them is a visual check**: each measures
where a known point lands, because "it looks right" is exactly the evidence a
wrong basis change survives.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from bio3dvision.oculomotor import Fixation, StereoRig, eye_rotations
from bio3dvision.scene_model import (
    CAMERA_FROM_EYE,
    WORLD_FROM_HEAD,
    eye_camera_poses,
)

REPO = Path(__file__).resolve().parents[1]
RENDERER = REPO / "src" / "bio3dvision" / "blender_render.py"
H, W, F_PX, BASELINE = 240, 320, 700.0, 0.065
PRINCIPAL = ((H - 1) / 2.0, (W - 1) / 2.0)
RIG = StereoRig(baseline=BASELINE)

needs_blender = pytest.mark.skipif(
    shutil.which("blender") is None,
    reason=(
        "no Blender binary on PATH. The basis change is still checked here, but "
        "nothing verifies that a RENDER puts the fixation point at the principal "
        "point or that torsion reaches the camera — falsifiers 1, 2 and 3."
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
# The basis change. No renderer, so this runs everywhere.
# ---------------------------------------------------------------------------


def test_the_two_basis_changes_are_stated_separately() -> None:
    """They are numerically equal and they are different statements.

    One carries the head frame into the world; the other carries the eye frame
    into Blender's camera-local frame. Collapsing them into one constant because
    they happen to be the same matrix is how a basis change stops being checkable.
    """
    assert np.array_equal(WORLD_FROM_HEAD, np.diag([1.0, -1.0, -1.0]))
    assert np.array_equal(CAMERA_FROM_EYE, np.diag([1.0, -1.0, -1.0]))


@pytest.mark.parametrize(
    "fixation",
    [
        Fixation(0.0, 0.0, 0.0),
        Fixation(0.25, 0.18, 0.16),
        Fixation(-0.3, -0.22, 0.09),
    ],
)
@pytest.mark.parametrize("k", [0.0, 0.25, 0.5])
def test_the_camera_looks_down_its_own_minus_z_along_the_optical_axis(
    fixation: Fixation, k: float
) -> None:
    """``M @ [0,0,-1]`` must equal the optical axis in world coordinates.

    Blender looks down local -Z; the geometry looks along +Z. This is the identity
    the whole conversion exists to satisfy, and a sign error anywhere in it fails
    here rather than in a render that merely looks odd.
    """
    poses = eye_camera_poses(RIG, fixation, k=k)
    rotations = eye_rotations(RIG, fixation, k=k)
    for name, rot in (("left", rotations.left), ("right", rotations.right)):
        matrix = np.array(poses[name]["matrix_world"])
        view = matrix[:3, :3] @ np.array([0.0, 0.0, -1.0])
        optical_axis_world = WORLD_FROM_HEAD @ (rot @ np.array([0.0, 0.0, 1.0]))
        np.testing.assert_allclose(view, optical_axis_world, atol=1e-15)


@pytest.mark.parametrize("k", [0.0, 0.25, 0.5])
def test_the_camera_up_vector_is_the_eye_down_vector_flipped(k: float) -> None:
    """The remaining degree of freedom, which the optical axis alone cannot pin.

    Two orientations can share an optical axis and differ by a roll about it —
    which is exactly torsion. Checking only the axis would let a torsion error
    through, so the up vector is checked too.
    """
    fixation = Fixation(0.25, 0.18, 0.16)
    poses = eye_camera_poses(RIG, fixation, k=k)
    rotations = eye_rotations(RIG, fixation, k=k)
    for name, rot in (("left", rotations.left), ("right", rotations.right)):
        matrix = np.array(poses[name]["matrix_world"])
        up = matrix[:3, :3] @ np.array([0.0, 1.0, 0.0])
        eye_down_world = WORLD_FROM_HEAD @ (rot @ np.array([0.0, 1.0, 0.0]))
        np.testing.assert_allclose(up, -eye_down_world, atol=1e-15)


def test_matrices_are_rigid() -> None:
    for k in (0.0, 0.5):
        poses = eye_camera_poses(RIG, Fixation(0.25, 0.18, 0.16), k=k)
        for name in ("left", "right"):
            basis = np.array(poses[name]["matrix_world"])[:3, :3]
            np.testing.assert_allclose(basis @ basis.T, np.eye(3), atol=1e-14)
            assert np.linalg.det(basis) == pytest.approx(1.0, abs=1e-14)


def test_parallel_gaze_reproduces_the_rectified_parallel_placement() -> None:
    """At ``Fixation(0, 0, 0)`` the poses are the identity, offset along X.

    This is why falsifier 4 can be bit-exact: the gaze-contingent path and the
    rectified-parallel path agree *as matrices* at the fixation the old geometry
    was correct for, so the renderer is doing the same thing rather than something
    numerically close.
    """
    poses = eye_camera_poses(RIG, Fixation(0.0, 0.0, 0.0))
    for name, sign in (("left", -1.0), ("right", +1.0)):
        matrix = np.array(poses[name]["matrix_world"])
        np.testing.assert_array_equal(matrix[:3, :3], np.eye(3))
        np.testing.assert_allclose(matrix[:3, 3], [sign * BASELINE / 2.0, 0.0, 0.0], atol=1e-18)


def test_torsion_reaches_the_matrices() -> None:
    """``k`` must change the pose, or nothing downstream can be testing torsion.

    The pre-render half of falsifier 3: if the matrices were identical, no render
    could distinguish them and falsifier 2 would pass for the wrong reason.
    """
    fixation = Fixation(0.25, 0.18, 0.16)
    half = np.array(eye_camera_poses(RIG, fixation, k=0.5)["left"]["matrix_world"])
    zero = np.array(eye_camera_poses(RIG, fixation, k=0.0)["left"]["matrix_world"])
    angle = np.degrees(
        np.arccos(np.clip((np.trace(half[:3, :3].T @ zero[:3, :3]) - 1.0) / 2.0, -1.0, 1.0))
    )
    assert angle > 0.1, f"k barely moves the camera: {angle:.4f} deg"


def test_blenders_native_toe_in_is_not_used() -> None:
    """A yaw-only, zero-torsion mode is right only for symmetric horizontal gaze.

    Asserted as an absence: the renderer must not set a convergence mode anywhere,
    because doing so would silently override the matrices computed here.
    """
    source = (REPO / "src" / "bio3dvision" / "blender_render.py").read_text()
    for forbidden in ("convergence_mode", "convergence_distance", "stereo_convergence"):
        assert forbidden not in source, f"{forbidden} appears in the renderer"


# ---------------------------------------------------------------------------
# The geometric falsifiers. Real Blender, measured, never visual.
# ---------------------------------------------------------------------------


def _render_markers(tmp: Path, markers_head, fixation: Fixation, k: float, radius: float):
    from bio3dvision.blender_load import read_exr_image

    spec = {
        "markers": [(WORLD_FROM_HEAD @ np.asarray(m)).tolist() for m in markers_head],
        "marker_radius": radius,
        "eye_poses": eye_camera_poses(RIG, fixation, k=k),
        "H": H,
        "W": W,
        "f_px": F_PX,
        "baseline": BASELINE,
    }
    tmp.mkdir(parents=True, exist_ok=True)
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
    return read_exr_image(tmp / "left.exr"), read_exr_image(tmp / "right.exr")


def _centroid(img, threshold: float = 0.02):
    mask = img > threshold
    if mask.sum() == 0:
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
    "fixation",
    [Fixation(0.0, 0.0, 0.09), Fixation(0.25, 0.18, 0.09), Fixation(-0.3, -0.22, 0.12)],
)
def test_falsifier_1_the_fixation_point_images_at_the_principal_point(
    tmp_path: Path, fixation: Fixation
) -> None:
    """**That is what fixation MEANS.** A marker at the fixation point, both eyes.

    A wrong sign, a wrong basis or a dropped composition factor all fail this, and
    none of them is visible in a render that merely looks plausible. Tolerance is
    0.2 px, which is loose against the measured 0.007-0.033 px and tight against
    any of those errors, which move the image by pixels or tens of pixels.
    """
    from bio3dvision.oculomotor import fixation_point

    point = fixation_point(RIG, fixation)
    left, right = _render_markers(tmp_path, [point], fixation, 0.5, 0.004)
    for name, img in (("left", left), ("right", right)):
        centre = _centroid(img)
        assert centre is not None, f"{name}: the fixation marker is not visible at all"
        error = float(np.hypot(centre[0] - PRINCIPAL[0], centre[1] - PRINCIPAL[1]))
        assert error < 0.2, f"{name} eye: fixation point lands {error:.3f} px off centre"


@needs_exr
@needs_blender
def test_falsifier_2_and_3_torsion_at_an_eccentric_fixation(tmp_path: Path) -> None:
    """Vertical disparity vanishes in the plane of regard at k = 1/2, and not at k = 0.

    **Eccentric by requirement: az != 0 AND el != 0.** A symmetric horizontal
    fixation cannot distinguish correct torsion from none — the rectifier is the
    identity at zero elevation, so applying it, omitting it and transposing it are
    bit-identical there. The predecessor hit that hole three times.

    The observable is the one ``oculomotor.py`` pins analytically: ``row_L -
    row_R`` over points of the plane of regard, not the absolute row. And the
    render is checked against that analytic prediction rather than against a
    threshold, which is what makes this a geometric verdict rather than a visual
    one.

    Falsifier 3 is the same measurement at k = 0: if the two agreed, torsion would
    not be reaching the camera and the k = 1/2 result would mean nothing.
    """
    from bio3dvision.oculomotor import fixation_distance

    fixation = Fixation(0.25, 0.18, 0.16)
    distance = fixation_distance(RIG, fixation)
    elevation = fixation.elevation_down
    angles = fixation.azimuth + np.linspace(-0.12, 0.12, 5)
    points = [
        (
            np.sin(a) * np.array([1.0, 0.0, 0.0])
            + np.cos(a) * np.array([0.0, np.sin(elevation), np.cos(elevation)])
        )
        * distance
        for a in angles
    ]

    def analytic(k: float) -> float:
        rot = eye_rotations(RIG, fixation, k=k)
        half_b = BASELINE / 2.0

        def ordinate(r, centre):
            v = (np.asarray(points) - centre) @ r
            return v[..., 1] / v[..., 2]

        return float(
            F_PX
            * np.abs(
                ordinate(rot.left, np.array([-half_b, 0.0, 0.0]))
                - ordinate(rot.right, np.array([half_b, 0.0, 0.0]))
            ).max()
        )

    measured = {}
    for k in (0.5, 0.0):
        disparities = []
        for i, point in enumerate(points):
            left, right = _render_markers(tmp_path / f"k{k}_{i}", [point], fixation, k, 0.0006)
            a, b = _centroid(left), _centroid(right)
            assert a is not None and b is not None, f"marker {i} not visible at k={k}"
            disparities.append(a[0] - b[0])
        measured[k] = float(np.abs(disparities).max())
        # The render must reproduce what the geometry predicts, not merely look
        # plausible. 0.1 px covers sub-pixel centroid noise on a ~2 px marker.
        assert abs(measured[k] - analytic(k)) < 0.1, (
            f"k={k}: rendered {measured[k]:.4f} px vs analytic {analytic(k):.4f} px"
        )

    # Falsifier 2: the null at k = 1/2.
    assert measured[0.5] < 0.1, f"vertical disparity at k=1/2 is {measured[0.5]:.4f} px"
    # Falsifier 3: and it is a property of k = 1/2 alone. A magnitude, not just a
    # difference — the alternative is measured beside the result.
    assert measured[0.0] > 10.0 * measured[0.5], (
        f"k=0 gives {measured[0.0]:.4f} px against k=1/2's {measured[0.5]:.4f} px; "
        "torsion is not reaching the camera"
    )


@needs_exr
@needs_blender
def test_falsifier_4_the_rectified_parallel_render_is_unchanged(tmp_path: Path) -> None:
    """At parallel gaze the new path must reproduce the old render bit-identically.

    Nine experiments' numbers depend on those renders. ``array_equal``, not
    ``allclose``: a tolerance here would let a real change in the camera placement
    hide as rounding.
    """
    from bio3dvision.blender_load import load_render
    from bio3dvision.scene_model import scene_from_fixture, write_scene

    scene = tmp_path / "scene"
    old_out, new_out = tmp_path / "old", tmp_path / "new"
    model = scene_from_fixture(seed=0)

    write_scene(model, scene)  # no fixation -> rectified-parallel path
    _run_scene(scene, old_out)
    write_scene(model, scene, fixation=Fixation(0.0, 0.0, 0.0))  # gaze-contingent
    _run_scene(scene, new_out)

    old, new = load_render(old_out), load_render(new_out)
    for name, a, b in zip(("left", "right", "depth"), old[:3], new[:3], strict=True):
        assert np.array_equal(a, b), f"{name} differs between the two camera paths"
    assert old[3] == new[3]


def _run_scene(scene: Path, out: Path) -> None:
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
        pytest.fail(f"render into {out} failed")
