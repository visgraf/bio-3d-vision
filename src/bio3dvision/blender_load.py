"""Read a Blender render into the shape the loop consumes. **This half is tested.**

The render/load boundary is drawn along testability, and this is the side CI can
reach. Its counterpart, :mod:`bio3dvision.blender_render`, runs inside Blender's
own Python and no test in this repository executes a line of it — ``gap-009``
records that the same was true of the whole Blender surface in the reference.
The line is drawn here so that the untestable part is as small as it can be:
Blender writes its native formats and nothing else, and every conversion,
convention and unit question happens in this module, under test.

:func:`load_render` returns ``(left, right, depth_gt, params)`` — the same
four-tuple as :func:`bio3dvision.make_synthetic_scene`, with ``params`` the same
:class:`~bio3dvision.fixture.CameraParams`. That is the point of it: the loop
takes a rendered scene or an analytic one without knowing which.

Reading EXR needs the optional ``blender`` extra (``pip install -e ".[blender]"``).
It is imported inside the function that needs it, so this module — and the whole
package — imports cleanly without it.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np

from bio3dvision.fixture import CameraParams, FloatArray

__all__ = [
    "infer_depth_convention",
    "load_render",
    "radial_to_planar",
    "read_exr_depth",
    "read_exr_image",
    "render_provenance",
]

# Blender writes non-hits as a very large sentinel rather than as nan.
_NON_HIT = 1e6


def _read_exr_plane(path: str | Path) -> FloatArray:
    """One channel of a single-layer float EXR, decoded and nothing more.

    Channel preference is ``Z``, then ``V``, then a lone channel, then ``R`` —
    see :func:`read_exr_depth` for why that tolerance is load-bearing rather than
    defensive.
    """
    import Imath
    import OpenEXR

    path = Path(path)
    src = OpenEXR.InputFile(str(path))
    try:
        header = src.header()
        window = header["dataWindow"]
        width = window.max.x - window.min.x + 1
        height = window.max.y - window.min.y + 1
        names = list(header["channels"].keys())

        channel = _depth_channel(names)
        if channel is None:
            raise KeyError(
                f"no readable channel in {path.name}. Channels present: {names}. "
                "For a depth pass, enable the Z pass before rendering "
                "(view_layer.use_pass_z)."
            )
        raw = src.channel(channel, Imath.PixelType(Imath.PixelType.FLOAT))
    finally:
        src.close()
    return np.frombuffer(raw, dtype=np.float32).reshape(height, width).astype(float)


def read_exr_depth(path: str | Path) -> FloatArray:
    """Depth from a single-layer EXR, in **metres**, non-hits as ``nan``.

    Returns an ``(H, W)`` array of distances in the sense the render wrote them:
    Blender's Z pass is distance along the camera's view axis (planar), but that
    is a property of the render, not of this function — see
    :func:`infer_depth_convention` before assuming it, and
    :func:`radial_to_planar` if the answer is radial.

    **Channel naming is not stable and this is where that is absorbed.** The
    depth channel has been named ``Z`` and ``V`` across Blender versions, and
    where a render routes the pass through an RGB path there is no ``Z`` at all —
    the metres land in ``R``, ``G`` and ``B`` together. The fixture in
    ``tests/data/bioeye-e908170`` is exactly that case, so a reader that looks
    only for ``Z`` finds nothing in a real, shipped render. Preference order is
    ``Z``, then ``V``, then a single channel if that is all there is, then ``R``.

    Multi-part EXR is **not** handled, deliberately. The reference's reader walks
    every part of the file because its renders are multi-layer; the renderer in
    :mod:`bio3dvision.blender_render` writes one pass per file, and the shipped
    fixture is single-part. Carrying the part-walking would be carrying machinery
    for a layout this repository does not produce. If a live render ever needs
    it, the ``KeyError`` below names the parts it actually found.
    """
    depth = _read_exr_plane(path)
    depth = np.array(depth, copy=True)
    depth[~np.isfinite(depth) | (depth > _NON_HIT) | (depth <= 0)] = np.nan
    return depth


def read_exr_image(path: str | Path) -> FloatArray:
    """A rendered beauty pass from a single-layer float EXR, **no sentinel applied**.

    Same decoding as :func:`read_exr_depth` and deliberately NOT the same
    post-processing. The depth reader maps non-positive values to ``nan``, because
    a depth of zero is Blender's way of saying the ray hit nothing. Zero is a
    perfectly good *intensity*, and running an image through the depth reader
    turns every black pixel into ``nan`` — which is how this function came to
    exist rather than being anticipated.
    """
    return _read_exr_plane(path)


def _depth_channel(names: list[str]) -> str | None:
    """The channel holding depth, or ``None``. See :func:`read_exr_depth`."""
    for wanted in ("Z", "V"):
        for name in names:
            if name.rsplit(".", 1)[-1].upper() == wanted:
                return name
    if len(names) == 1:
        return names[0]
    for name in names:
        if name.rsplit(".", 1)[-1].upper() == "R":
            return name
    return None


def radial_to_planar(depth: FloatArray, f_px: float) -> FloatArray:
    """Convert ray distance to distance along the optical axis, in metres.

    ``Z = r * f / sqrt(f^2 + u^2 + v^2)`` for a pixel offset ``(u, v)`` from the
    principal point, taken as the geometric centre ``((W-1)/2, (H-1)/2)``.

    The correction is negligible at the centre of frame and reaches several
    percent at the corners of a wide field. That is the whole reason the
    convention has to be established rather than assumed: applying this when it
    was not needed, or skipping it when it was, produces an error that is small,
    smooth, and largest at the field edge — which is the shape of a plausible
    finding rather than the shape of a bug.
    """
    height, width = depth.shape
    rows, cols = np.indices((height, width))
    u = cols - (width - 1) / 2.0
    v = rows - (height - 1) / 2.0
    return np.asarray(depth * f_px / np.sqrt(f_px**2 + u**2 + v**2), dtype=float)


def infer_depth_convention(depth: FloatArray, tolerance: float = 1e-3) -> str:
    """Diagnose a **fronto-parallel calibration render**: planar, radial, unknown.

    Returns ``"planar"`` if depth is constant across the field, ``"radial"`` if it
    grows with image radius alone, and ``"unknown"`` otherwise. Run it once per
    Blender version on a flat-wall render and record the answer with the render;
    do not carry the answer between versions.

    **Only meaningful on a fronto-parallel calibration render, and the guard
    below is the reason this function is worth carrying at all.** Handed an
    ordinary scene, an earlier version of this inference answered ``"radial"``
    with complete confidence, for the wrong reason: any scene with nearer objects
    toward the middle of frame has depth "growing toward the corners". Acting on
    that answer applies a spurious radial correction of several percent at the
    field edge — smooth, plausible, largest at the periphery, and easy to mistake
    for a modelling result rather than for the artefact it is.

    The guard: a flat wall is **radially symmetric** about the principal point
    under either convention, so depth must vary *with* image radius and not
    *around* it. Sixteen annuli are measured; when the median within-annulus
    spread is an appreciable fraction of the total spread, the input is not a
    calibration render and the answer is ``"unknown"``.

    A consequence worth stating, because it looks like a failure and is not:
    ``"unknown"`` is the correct answer for an ordinary rendered scene, including
    the shipped fixture in ``tests/data/bioeye-e908170`` whose pass is known from
    its render script to be planar. This function does not report what the
    convention *is*; it reports what a calibration render *shows*, and refuses
    otherwise. Weakening it to answer on ordinary scenes would restore exactly
    the near-miss it exists to prevent.
    """
    finite = np.isfinite(depth)
    if not finite.any():
        return "unknown"
    centre = float(np.nanmedian(depth[depth.shape[0] // 2, :]))
    if not centre > 0:
        return "unknown"

    values = depth[finite]
    total = float(np.max(values) - np.min(values))
    if total / centre < tolerance:
        return "planar"

    height, width = depth.shape
    rows, cols = np.indices((height, width))
    radius = np.hypot(cols - (width - 1) / 2.0, rows - (height - 1) / 2.0)
    edges = np.linspace(0.0, float(radius.max()), 17)
    within = [
        float(np.ptp(depth[sel]))
        for lo, hi in itertools.pairwise(edges)
        if (sel := finite & (radius >= lo) & (radius < hi)).sum() >= 8
    ]
    if not within or float(np.median(within)) > 0.25 * total:
        return "unknown"

    corner = float(np.nanmean([depth[0, 0], depth[0, -1], depth[-1, 0], depth[-1, -1]]))
    return "radial" if corner > centre else "unknown"


def render_provenance(directory: str | Path) -> dict[str, object]:
    """Everything in ``params.json`` that is not a camera parameter.

    Kept out of :func:`load_render`'s return so that a rendered scene and an
    analytic one are the same four-tuple. The Blender version lives here: a depth
    map without the renderer that produced it is prose, for the same reason a
    measurement without its commit is.
    """
    with open(Path(directory) / "params.json") as handle:
        raw = json.load(handle)
    return {k: v for k, v in raw.items() if k not in ("f_px", "baseline", "H", "W")}


def load_render(
    directory: str | Path,
    depth_is_radial: bool = False,
) -> tuple[FloatArray, FloatArray, FloatArray, CameraParams]:
    """Load a render directory into ``(left, right, depth_gt, params)``.

    The same four-tuple :func:`bio3dvision.make_synthetic_scene` returns, so the
    loop consumes either source without knowing which. ``left`` and ``right`` are
    float in ``[0, 1]``; ``depth_gt`` is **metres**, planar (distance along the
    left camera's optical axis), with non-hits as ``nan``; ``params`` carries
    ``f_px`` in pixels and ``baseline`` in metres, so that ``d = f_px * baseline
    / Z`` holds for the returned depth.

    Expects the contract :mod:`bio3dvision.blender_render` writes, which is
    bioeye's: ``left.png``, ``right.png``, ``depth_left.exr``, ``params.json``.

    ``depth_is_radial`` is an explicit flag and is **not** inferred, because
    inferring it from an ordinary scene is the failure
    :func:`infer_depth_convention` documents. Establish it once per Blender
    version on a calibration render and pass the answer in.

    Raises rather than substituting a default if the depth pass is missing: a
    stimulus without ground truth is not a stimulus.
    """
    directory = Path(directory)

    with open(directory / "params.json") as handle:
        raw = json.load(handle)

    # Float EXR in preference to PNG. The PNG is 8-bit and carries the display
    # transform; where a comparison needs a rendered pixel to EQUAL a modelled
    # value, neither is survivable. The PNGs stay because they are what a person
    # opens, and older renders that have only PNGs still load.
    if (directory / "left.exr").exists():
        left = read_exr_image(directory / "left.exr")
        right = read_exr_image(directory / "right.exr")
    else:
        left = _read_gray(directory / "left.png")
        right = _read_gray(directory / "right.png")

    depth_path = directory / "depth_left.exr"
    if not depth_path.exists():
        raise FileNotFoundError(
            f"missing depth pass: {depth_path}. A render without ground truth "
            "cannot be used as a stimulus; re-render with the Z pass enabled."
        )
    depth = read_exr_depth(depth_path)

    if depth_is_radial:
        depth = radial_to_planar(depth, float(raw["f_px"]))

    if depth.shape != left.shape:
        raise ValueError(
            f"depth pass is {depth.shape} but the left image is {left.shape}. "
            "These must agree; a mismatch means the passes came from different "
            "renders or the EXR was decoded with the wrong plugin."
        )

    params: CameraParams = {
        "f_px": float(raw["f_px"]),
        "baseline": float(raw["baseline"]),
        "H": int(raw.get("H", left.shape[0])),
        "W": int(raw.get("W", left.shape[1])),
    }
    return left, right, depth, params


def _read_gray(path: Path) -> FloatArray:
    """A PNG as float grayscale in ``[0, 1]``.

    Read through matplotlib, which is already a dependency, rather than adding an
    image library for one call. matplotlib returns PNG as float in ``[0, 1]``
    already; the division the reference does is not repeated here because it
    would be a second normalisation.
    """
    import matplotlib.image as mpimg

    if not path.exists():
        raise FileNotFoundError(f"missing image: {path}")
    img = np.asarray(mpimg.imread(path), dtype=float)
    if img.ndim == 3:
        img = img[..., :3].mean(axis=-1)
    return np.asarray(img, dtype=float)
