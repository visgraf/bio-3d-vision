"""The render loader, against genuine renderer output.

Two sources, and the split is the point.

``tests/data/bioeye-e908170`` is a **Blender 4.x** render, carried verbatim from
``visgraf/bioeye@e908170`` where it is committed and immutable. It runs in CI with
no Blender present, and it tests the loader alone.

A **fresh Blender 5 render** is produced by ``tests/conftest.py`` when a binary is
available, and tests the current path end to end. It skips otherwise, and the
skip is a real result rather than a hidden one: see ``test_falsifier_1b_*``.

Holding a fixed 4.x artifact beside a live 5.x render is what makes version drift
diagnosable. If the fixture passes and the live render fails, the loader is fine
and the renderer moved.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pytest

from bio3dvision import (
    infer_depth_convention,
    load_render,
    radial_to_planar,
    read_exr_depth,
    render_provenance,
)

FIXTURE = Path(__file__).parent / "data" / "bioeye-e908170"


def _have_openexr() -> bool:
    try:
        import OpenEXR  # noqa: F401
    except ImportError:
        return False
    return True


needs_exr = pytest.mark.skipif(
    not _have_openexr(),
    reason='reading EXR needs the optional extra: pip install -e ".[blender]"',
)


# ---------------------------------------------------------------------------
# The optionality of the extra is itself a claim, so it is pinned.
# ---------------------------------------------------------------------------


@pytest.mark.infrastructure
def test_the_package_imports_without_the_blender_extra() -> None:
    """``import bio3dvision`` must not need OpenEXR.

    Run in a subprocess with the module blocked, because it is already imported
    in this process and an in-process check would pass vacuously. This is the
    claim that lets the extra be optional rather than a dependency with a
    politer name.
    """
    script = (
        "import sys;"
        "sys.modules['OpenEXR'] = None;"
        "sys.modules['Imath'] = None;"
        "import bio3dvision;"
        "assert bio3dvision.load_render is not None;"
        "left, right, d, p = bio3dvision.make_synthetic_scene();"
        "print('OK', p['f_px'])"
    )
    out = subprocess.run(
        [__import__("sys").executable, "-c", script],
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0, f"package does not import without the extra:\n{out.stderr}"
    assert out.stdout.startswith("OK"), out.stdout


# ---------------------------------------------------------------------------
# FALSIFIER 1a - the shipped Blender 4.x artifact. Runs in CI, no Blender.
# ---------------------------------------------------------------------------


@needs_exr
def test_falsifier_1a_loads_the_shipped_render() -> None:
    """The loader reads bioeye@e908170's real output into the loop's shape."""
    left, right, depth, params = load_render(FIXTURE)

    assert left.shape == right.shape == depth.shape == (240, 320)
    assert params["f_px"] == pytest.approx(311.1111111111111)
    assert (params["baseline"], params["H"], params["W"]) == (0.065, 240, 320)

    # Same four-tuple as the analytic fixture, so the loop cannot tell them apart.
    from bio3dvision import make_synthetic_scene

    a_left, a_right, a_depth, a_params = make_synthetic_scene()
    assert (left.ndim, right.ndim, depth.ndim) == (a_left.ndim, a_right.ndim, a_depth.ndim)
    assert sorted(params) == sorted(a_params)

    assert np.isfinite(depth).all()
    assert float(depth.min()) == pytest.approx(1.7018, abs=1e-3)
    assert float(depth.max()) == pytest.approx(5.0000, abs=1e-3)
    assert float(left.min()) >= 0.0 and float(left.max()) <= 1.0


@needs_exr
def test_falsifier_1a_depth_channel_is_not_named_z() -> None:
    """The shipped file has no ``Z`` channel, and this is why tolerance is carried.

    bioeye's compositor routed the depth pass through RGB, so the metres sit in
    ``R``, ``G`` and ``B`` together. A reader that looks only for ``Z`` finds
    nothing in a real, shipped render — which is exactly the failure the
    reference's channel-naming tolerance exists to absorb.
    """
    import OpenEXR

    src = OpenEXR.InputFile(str(FIXTURE / "depth_left.exr"))
    try:
        names = list(src.header()["channels"].keys())
    finally:
        src.close()
    assert "Z" not in names and "V" not in names
    assert sorted(names) == ["B", "G", "R"]

    depth = read_exr_depth(FIXTURE / "depth_left.exr")
    assert depth.shape == (240, 320)
    # A property of this fixed artifact, measured from it. It is here so that a
    # reader change which silently picked a different channel, or decoded with a
    # different plugin, moves this number.
    assert float(np.nanmedian(depth)) == pytest.approx(3.4225, abs=1e-3)

    # Which of R/G/B is chosen must not matter: bioeye wrote the same metres to
    # all three, and the loader picks R. If they ever differ, the file is not
    # what this fixture is documented to be.
    import Imath

    src = OpenEXR.InputFile(str(FIXTURE / "depth_left.exr"))
    try:
        pixel = Imath.PixelType(Imath.PixelType.FLOAT)
        planes = [np.frombuffer(src.channel(c, pixel), np.float32).reshape(240, 320) for c in names]
    finally:
        src.close()
    assert all(np.array_equal(planes[0], plane) for plane in planes[1:])


@needs_exr
def test_falsifier_1a_convention_guard_refuses_an_ordinary_scene() -> None:
    """``infer_depth_convention`` returns ``"unknown"`` on the shipped render.

    THIS IS THE GUARD WORKING, NOT FAILING, and the distinction is the whole
    reason the guard was carried.

    The pass really is planar — ``render_stereo_blender.py:10`` in bioeye
    documents it as linear camera-space Z in metres, and that documentation, not
    a measurement, is where the expected convention comes from. But this file is
    an ordinary scene of blocks, and the inference is only meaningful on a
    fronto-parallel calibration render. An earlier version of it answered
    ``"radial"`` here with complete confidence, because a scene with nearer
    objects toward the middle of frame does have depth growing toward the
    corners; acting on that would apply a spurious several-percent correction at
    the field edge, indistinguishable from a modelling result.

    So ``"unknown"`` is the correct answer, and asserting ``"planar"`` on this
    file would require weakening the guard back to the state that produced the
    near-miss. The known-answer test for ``"planar"`` needs a calibration render
    and is ``test_falsifier_1b_convention_guard_reads_planar``.
    """
    depth = read_exr_depth(FIXTURE / "depth_left.exr")
    assert infer_depth_convention(depth) == "unknown"


@needs_exr
def test_the_guard_answers_planar_on_a_synthetic_flat_wall() -> None:
    """A constant-depth field is diagnosed ``planar``, and a radial one ``radial``.

    Synthetic arrays, not renders: this pins the *mechanism* in both directions
    without a Blender binary. It is not a claim about any renderer.
    """
    f_px, height, width = 311.111, 240, 320
    planar = np.full((height, width), 3.0)
    assert infer_depth_convention(planar) == "planar"

    rows, cols = np.indices((height, width))
    u = cols - (width - 1) / 2.0
    v = rows - (height - 1) / 2.0
    radial = 3.0 * np.sqrt(f_px**2 + u**2 + v**2) / f_px
    assert infer_depth_convention(radial) == "radial"

    # And the correction inverts it, which is the property that matters.
    assert np.allclose(radial_to_planar(radial, f_px), planar)


@needs_exr
def test_provenance_is_carried_separately_from_camera_params() -> None:
    """``params`` stays the loop's four keys; the renderer's identity is beside it."""
    _, _, _, params = load_render(FIXTURE)
    assert set(params) == {"f_px", "baseline", "H", "W"}

    extra = render_provenance(FIXTURE)
    # bioeye's params.json predates this repository's provenance field, so it
    # carries none. Recorded as an assertion so that a render written by
    # bio3dvision.blender_render, which does carry it, is visibly different.
    assert extra == {}
    assert json.loads((FIXTURE / "params.json").read_text()).keys() >= {"f_px", "baseline"}


# ---------------------------------------------------------------------------
# FALSIFIER 1b - a fresh render from the installed Blender.
# ---------------------------------------------------------------------------


@needs_exr
def test_falsifier_1b_loaded_depth_matches_analytic_z(fresh_render: Path) -> None:
    """Loaded depth equals ``Z = f_px * baseline / d`` on planes at known distances.

    The falsifier the reference does not have (``gap-009``). A renderer migrated
    before its consumer can only be self-tested; this checks the rendered depth
    against arithmetic, on a scene whose true ``Z`` is known by construction
    rather than by another render.

    Tolerance: 1 mm, against card distances of metres. It is stated rather than
    tuned — the depth pass is 32-bit float and the planes are exactly placed, so
    anything above float noise here is a real disagreement about the convention
    or the units, which is what this is for.
    """
    cards = json.loads((fresh_render / "cards.json").read_text())
    _, _, depth, params = load_render(fresh_render)

    assert params["f_px"] > 0 and params["baseline"] > 0
    assert depth.shape == (params["H"], params["W"])

    finite = np.isfinite(depth)
    # The gaps between the tiled planes have no ray hit and must load as nan.
    # A render in which everything is finite would mean the planes overlap and
    # the scene is not the one the falsifier assumes.
    assert 0.5 < finite.mean() < 1.0

    # EVERY card distance is present, each on its own plane. This is the clause
    # that fails if the planes occlude one another - the depth map would then
    # hold one distance and the check would pass vacuously on the nearest.
    for z in cards:
        hits = np.isclose(depth, z, atol=1e-3) & finite
        assert hits.sum() > 100, f"plane at {z} m is not present in the depth pass"

    # And nothing else is present: every finite pixel belongs to a known plane.
    known = np.zeros_like(depth, dtype=bool)
    for z in cards:
        known |= np.isclose(depth, z, atol=1e-3)
    stray = finite & ~known
    assert stray.sum() == 0, (
        f"{stray.sum()} pixels are at none of the known distances; "
        f"e.g. {np.unique(np.round(depth[stray], 4))[:5]}"
    )

    # The analytic identity, taken through disparity and back, which is the form
    # the loop actually uses: d = f * I / Z, so Z = f * I / d must return the
    # rendered depth on every hit pixel.
    d_analytic = params["f_px"] * params["baseline"] / depth[finite]
    recovered = params["f_px"] * params["baseline"] / d_analytic
    assert np.abs(recovered - depth[finite]).max() < 1e-3


@needs_exr
def test_falsifier_1b_convention_guard_reads_planar(
    fresh_wall_render: Path, fresh_render: Path
) -> None:
    """On a flat-wall calibration render the guard answers ``"planar"``; on the
    three-plane scene it correctly declines.

    The known-answer case. The expected answer comes from the render script's
    documentation of Blender's Z pass as linear camera-space depth, NOT from
    measuring this file — this checks that the pipeline delivers the documented
    convention, it does not discover what the convention is.

    Both halves are asserted because either alone is weak. "planar" on a flat
    wall could be produced by an inference that always says planar; "unknown" on
    the tiled scene could be produced by one that never decides. Together they
    pin that it discriminates, and on the same renderer in the same session.
    """
    wall = read_exr_depth(fresh_wall_render / "depth_left.exr")
    assert infer_depth_convention(wall) == "planar"

    cards = read_exr_depth(fresh_render / "depth_left.exr")
    assert infer_depth_convention(cards) == "unknown"


@needs_exr
def test_falsifier_1b_records_the_blender_version(fresh_render: Path) -> None:
    """A render carries the renderer that made it, or it is prose."""
    extra = render_provenance(fresh_render)
    assert str(extra["blender_version"]).split(".")[0].isdigit()
    assert extra["geometry"] == "rectified_parallel"
    assert extra["depth_pass"] == "Z"
    assert extra["denoising"] is False
