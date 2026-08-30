"""The scene model, and its fidelity to the fixture it is a model OF.

The load-bearing test is :func:`test_the_model_reproduces_the_fixture_depth_map`.
Everything else in this file guards a property that, if it broke, would make the
exp004 comparison mean something other than it claims.

Tests needing a real Blender are marked and skip without one, as in
``test_blender_load.py``; the skip names what goes unverified.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pytest

from bio3dvision.fixture import make_synthetic_scene
from bio3dvision.scene_model import (
    SceneModel,
    Surface,
    rasterise_depth,
    scene_from_fixture,
    write_scene,
)

REPO = Path(__file__).resolve().parents[1]
RENDERER = REPO / "src" / "bio3dvision" / "blender_render.py"


def _have_openexr() -> bool:
    try:
        import OpenEXR  # noqa: F401
    except ImportError:
        return False
    return True


needs_exr = pytest.mark.skipif(
    not _have_openexr(),
    reason='writing the scene texture needs the optional extra: pip install -e ".[blender]"',
)
needs_blender = pytest.mark.skipif(
    shutil.which("blender") is None,
    reason=(
        "no Blender binary on PATH. The scene model's geometry is still checked "
        "against the fixture, but nothing checks that a RENDER of it reproduces "
        "the fixture's left image, which is what makes exp004's comparison sound."
    ),
)


# ---------------------------------------------------------------------------
# The model against the fixture. No Blender, no EXR — runs everywhere.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed", [0, 3, 7])
def test_the_model_reproduces_the_fixture_depth_map(seed: int) -> None:
    """Rasterised and smoothed, the model's surfaces ARE the fixture's depth map.

    This is why the model is a model and not a second scene that resembles one.
    The surface rectangles are declared in ``scene_from_fixture`` because
    ``make_synthetic_scene`` builds its depth with literal slice assignments and
    exposes no structure to read; this test is what stops the two from drifting.
    Exact equality, not a tolerance: both sides run the same smoothing on the same
    array, so anything but bit-equality means a real disagreement.
    """
    _left, _right, depth_gt, _params = make_synthetic_scene(seed=seed)
    assert np.array_equal(rasterise_depth(scene_from_fixture(seed=seed)), depth_gt)


def test_the_model_texture_is_the_fixture_left_image() -> None:
    """The texture is the fixture's own array, not a lookalike.

    Removing the noise-statistics confound depends entirely on this, so it is
    pinned rather than trusted: a procedural texture with the same spectrum would
    pass every other test in this file and quietly make exp004 a comparison of two
    different stimuli.
    """
    left, _right, _depth, _params = make_synthetic_scene(seed=0)
    assert np.array_equal(scene_from_fixture(seed=0).texture, left.astype(np.float64))


def test_unsmoothed_depth_has_exactly_the_four_declared_surfaces() -> None:
    """The step-edge depth map holds the four surface depths and nothing between.

    exp004's discontinuity set is computed from this array, so a stray value would
    move the strata the whole experiment is stratified by.
    """
    depth = rasterise_depth(scene_from_fixture(seed=0), smooth=False)
    # float32, so the declared metres round-trip as 2.4000000953... - compared
    # elementwise rather than as literals for that reason.
    assert np.allclose(sorted(np.unique(depth).tolist()), [2.4, 3.0, 3.6, 4.5], atol=1e-6)


def test_the_surfaces_laterally_overlap_so_occlusion_is_possible() -> None:
    """A nearer surface must hide part of a farther one, or there is no occlusion.

    Falsifier 2 of exp004 turns on this. If it failed, a null at depth
    discontinuities would mean "this scene has no half-occlusions" rather than
    anything about the fixture, and the two readings are not distinguishable after
    the fact — so the geometry is asserted in advance.
    """
    model = scene_from_fixture(seed=0)
    params = model.params
    depth = rasterise_depth(model, smooth=False)
    d_gt = params["f_px"] * params["baseline"] / depth

    height, width = depth.shape
    cols = np.arange(width)[None, :].repeat(height, 0)
    target = np.rint(cols - d_gt).astype(int)

    occluded = 0
    for y in range(height):
        order = np.argsort(-depth[y])  # far to near, nearer wins
        xs = target[y, order]
        inside = (xs >= 0) & (xs < width)
        seen = np.zeros(width, dtype=bool)
        seen[xs[inside]] = True
        occluded += int((~seen).sum())

    # 5.09% at seed 0, measured. The bound is loose on purpose: the claim is that
    # real half-occlusions EXIST and are not a rounding artefact, not that they
    # occupy a particular fraction.
    assert occluded > 0.01 * depth.size


def test_surface_rejects_a_degenerate_rectangle() -> None:
    with pytest.raises(ValueError, match="half-open ascending"):
        Surface(depth_m=1.0, rows=(10, 10), cols=(0, 5))
    with pytest.raises(ValueError, match="depth must be positive"):
        Surface(depth_m=0.0, rows=(0, 5), cols=(0, 5))


def test_edge_surfaces_are_extended_and_interior_ones_are_not() -> None:
    """The frustum extension applies at the frame edge and nowhere else.

    Extending an interior surface would change the occlusion geometry, which is
    the one thing this comparison is about.
    """
    model = scene_from_fixture(seed=0)
    background, _far_card, mid_card, _near_card = model.surfaces

    height, width = model.shape
    f_px, z = model.params["f_px"], mid_card.depth_m
    cx = (width - 1) / 2.0
    x_min, x_max, _, _ = model.extent_world(mid_card)
    expected_min = model.left_camera_x + (mid_card.cols[0] - 0.5 - cx) * z / f_px
    expected_max = model.left_camera_x + (mid_card.cols[1] - 0.5 - cx) * z / f_px
    assert x_min == pytest.approx(expected_min)
    assert x_max == pytest.approx(expected_max)

    # The background touches all four edges, so it is extended on all four.
    bx_min, bx_max, by_min, by_max = model.extent_world(background)
    bare_min = model.left_camera_x + (0 - 0.5 - cx) * background.depth_m / f_px
    assert bx_min < bare_min
    assert bx_max - bx_min > by_max - by_min  # still landscape, not distorted


def test_the_extension_covers_the_second_viewpoint() -> None:
    """The extension must exceed one baseline's worth of disparity, or it is useless.

    Its whole job is to reach past the left frustum far enough that the RIGHT
    camera still lands on the surface. Measured before it existed: without it, the
    uncovered strip accounted for essentially all of the right-image disagreement
    away from discontinuities.
    """
    model = scene_from_fixture(seed=0)
    background = model.surfaces[0]
    z = background.depth_m
    f_px = model.params["f_px"]
    x_min, x_max, _, _ = model.extent_world(background)
    width = model.shape[1]
    cx = (width - 1) / 2.0
    bare_max = model.left_camera_x + (width - 0.5 - cx) * z / f_px
    disparity_m = model.params["baseline"]
    assert x_max - bare_max > disparity_m
    assert x_min < model.left_camera_x + (-0.5 - cx) * z / f_px - disparity_m


# ---------------------------------------------------------------------------
# The model through a real renderer.
# ---------------------------------------------------------------------------


@needs_exr
def test_write_scene_round_trips(tmp_path: Path) -> None:
    model = scene_from_fixture(seed=0)
    path = write_scene(model, tmp_path)
    spec = json.loads(path.read_text())
    assert (tmp_path / "texture.exr").exists()
    assert len(spec["surfaces"]) == len(model.surfaces)
    assert spec["params"]["f_px"] == pytest.approx(700.0)
    assert spec["left_camera_x"] == pytest.approx(-0.0325)

    from bio3dvision.blender_load import read_exr_image

    assert np.allclose(read_exr_image(tmp_path / "texture.exr"), model.texture, atol=1e-6)


@needs_exr
@needs_blender
def test_a_render_of_the_model_reproduces_the_fixture_left_image(tmp_path: Path) -> None:
    """The load-bearing render check, and the reason the whole comparison is sound.

    If the LEFT images agree, the geometry, the camera, the texture mapping and the
    emission material are all right, because a single error in any of them shifts
    or reshades the image. That leaves the RIGHT image free to differ — which is
    the thing exp004 measures, and would be uninterpretable without this.

    Tolerance 1e-3 against a [0, 1] image. The residual is ~2.5e-4 and comes from
    Blender's bilinear texture filter, which does not land exactly on texel
    centres; ``Linear`` is used rather than ``Closest`` because the fixture builds
    its right image with ``order=1`` bilinear interpolation and matching the two
    resamplers removes a confound 100x larger than this residual.
    """
    from bio3dvision.blender_load import load_render

    scene_dir = tmp_path / "scene"
    out_dir = tmp_path / "render"
    write_scene(scene_from_fixture(seed=0), scene_dir)
    result = subprocess.run(
        [
            str(shutil.which("blender")),
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
    if result.returncode != 0 or not (out_dir / "left.exr").exists():
        pytest.fail(
            "the scene-model render failed, which is a result about the renderer "
            f"and not a reason to skip.\nexit={result.returncode}\n"
            f"{result.stdout[-2000:]}\n{result.stderr[-2000:]}"
        )

    left, _right, depth, params = load_render(out_dir)
    fixture_left, _fr, _fgt, fixture_params = make_synthetic_scene(seed=0)

    assert params["f_px"] == pytest.approx(fixture_params["f_px"])
    assert params["baseline"] == pytest.approx(fixture_params["baseline"])
    assert np.abs(left - fixture_left).max() < 1e-3

    # And the rendered depth is the model's step-edge map exactly - no tolerance,
    # because the planes sit at exactly representable distances.
    step = rasterise_depth(scene_from_fixture(seed=0), smooth=False)
    assert np.abs(depth[np.isfinite(depth)] - step[np.isfinite(depth)]).max() == 0.0


@needs_exr
@needs_blender
def test_a_render_of_the_model_has_a_genuinely_different_right_image(tmp_path: Path) -> None:
    """The right image must NOT reproduce the fixture's, or there is nothing to compare.

    The fixture warps its left image; the render photographs a second viewpoint.
    They agree away from depth discontinuities and must differ at them. This is the
    weak, always-true form of exp004's falsifier 2 — enough to catch a render that
    accidentally reproduced the warp, not enough to be a finding.
    """
    from bio3dvision.blender_load import load_render

    scene_dir = tmp_path / "scene"
    out_dir = tmp_path / "render"
    write_scene(scene_from_fixture(seed=0), scene_dir)
    subprocess.run(
        [
            str(shutil.which("blender")),
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
    _left, right, _depth, _params = load_render(out_dir)
    _fl, fixture_right, _gt, _p = make_synthetic_scene(seed=0)
    assert np.abs(right - fixture_right).max() > 0.1


def test_scene_model_rejects_a_frame_it_does_not_cover() -> None:
    """Every pixel needs a depth; a model that leaves a hole is not a scene."""
    left, _r, _d, params = make_synthetic_scene(seed=0)
    holed = SceneModel(
        surfaces=(Surface(depth_m=3.0, rows=(0, 10), cols=(0, 10)),),
        params=params,
        texture=np.asarray(left, dtype=np.float64),
    )
    with pytest.raises(ValueError, match="every pixel needs a depth"):
        rasterise_depth(holed)
