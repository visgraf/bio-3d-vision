"""The analytic fixture's geometry, as a scene a renderer can build. **Tested.**

This is a MODEL, not a render script. It says what the scene *is* — surfaces at
depths, with lateral extent and a texture — in the terms
:func:`~bio3dvision.fixture.make_synthetic_scene` already uses, and nothing else.
Turning it into Blender objects happens in :mod:`bio3dvision.blender_render`,
which runs inside Blender and is untestable; deciding what the scene contains
happens here, where it can be checked.

The check that matters is :func:`rasterise_depth`. The model is not asserted to
match the fixture — it is *tested* to, by rasterising these surfaces, smoothing
the result the way the fixture does, and comparing against the fixture's own
``depth_gt`` array. If someone changes either side, that test fails.

Parameterisation, and why it stops here
---------------------------------------
A :class:`Surface` has a depth and a rectangle. That is all the analytic fixture
has, so that is all this has. The temptation is to add a rotation, a curvature, a
material, a light — each individually reasonable, and together the 42% that
``fc-002`` records. None is added, because nothing in this iteration exercises
one.

The claim being made is that this parameterisation is *sufficient*: work needing
true half-occlusions extends it by MOVING surfaces so they laterally overlap, and
work needing a contrast axis extends it by changing the TEXTURE. Neither needs a
new field. If a later step finds it does, that is a real result about this model
and should be recorded as one rather than quietly patched.

Two deliberate departures from physics
--------------------------------------
Both are here to remove a confound, and both would have to go before anything
about appearance could be measured on a scene built from this model.

**The material is an emitter.** The fixture has no lighting model at all — its
texture *is* its image, ``left = tex``. A rendered pixel must therefore equal the
texture value, which means no shading, no shadows, no interreflection. This is
unphysical on purpose: a physically-lit render would differ from the fixture in
radiometry *and* in geometry at once, and a divergence could not be attributed to
either. To make it physical: replace the emission shader with a diffuse BSDF, add
a light, and accept that the rendered image is then no longer comparable to the
fixture's pixel-for-pixel — a different experiment, needing its own control.

**The texture is the fixture's own array**, not a procedural Blender texture.
Same reason: different noise statistics would confound a wrong render path with a
different stimulus, and the two are not separable after the fact.

Frames and units
----------------
Depths are **metres**, planar, along the **left camera's** optical axis — the
same convention ``depth_gt`` uses, and the reason the left camera rather than the
rig centre is the origin of the geometry below. Rectangles are **pixel indices in
the left image**, half-open ``[start, stop)``, matching NumPy slicing. Texture is
float in ``[0, 1]``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import gaussian_filter

from bio3dvision.fixture import CameraParams, FloatArray, make_synthetic_scene
from bio3dvision.oculomotor import K_LISTING_DEFAULT, Fixation, StereoRig, eye_rotations

__all__ = [
    "CAMERA_FROM_EYE",
    "FIXTURE_SMOOTHING_SIGMA",
    "WORLD_FROM_HEAD",
    "eye_camera_poses",
    "SceneModel",
    "Surface",
    "rasterise_depth",
    "occlusion_fractions",
    "scene_from_fixture",
    "split_cards",
    "write_scene",
]

# The fixture smooths its depth map by this much before returning it. The model
# carries the number because the comparison needs it, and does NOT render it:
# flat planes have step edges. See SceneModel.smoothing_sigma.
FIXTURE_SMOOTHING_SIGMA = 0.6


@dataclass(frozen=True)
class Surface:
    """One fronto-parallel surface: a depth and the rectangle it occupies.

    ``depth_m`` is metres along the left camera's optical axis. ``rows`` and
    ``cols`` are half-open pixel ranges in the left image, so a surface covers
    ``[rows[0]:rows[1], cols[0]:cols[1]]`` exactly as NumPy would slice it.

    Order matters: surfaces are painted in sequence, so a later surface occludes
    an earlier one where they overlap. That is the only relationship between
    surfaces this model expresses, and it is enough to place one in front of
    another — which is what a half-occlusion is made of.
    """

    depth_m: float
    rows: tuple[int, int]
    cols: tuple[int, int]

    def __post_init__(self) -> None:
        if not self.depth_m > 0:
            raise ValueError(f"depth must be positive, got {self.depth_m}")
        for name, (lo, hi) in (("rows", self.rows), ("cols", self.cols)):
            if not 0 <= lo < hi:
                raise ValueError(f"{name} must be a half-open ascending range, got {(lo, hi)}")


@dataclass(frozen=True)
class SceneModel:
    """Surfaces, the camera that sees them, and the texture painted on them."""

    surfaces: tuple[Surface, ...]
    params: CameraParams
    texture: FloatArray
    smoothing_sigma: float = FIXTURE_SMOOTHING_SIGMA

    @property
    def shape(self) -> tuple[int, int]:
        return int(self.params["H"]), int(self.params["W"])

    @property
    def left_camera_x(self) -> float:
        """Where the left camera sits, in metres, on the rig's baseline.

        The rig is centred on the origin, so the left eye is at ``-baseline/2``.
        This is not a detail: ``depth_gt`` and the surface rectangles are both
        expressed in the LEFT camera's frame, so a surface's world position must
        be computed from the left eye's position and not from the rig centre. Get
        this wrong and every surface is laterally displaced by half a baseline —
        32.5 mm, about 7 px at the fixture's focal length, which is large enough
        to wreck the comparison and small enough to look like a subtle bug.
        """
        return -float(self.params["baseline"]) / 2.0

    def extent_world(self, surface: Surface) -> tuple[float, float, float, float]:
        """``(x_min, x_max, y_min, y_max)`` in metres for one surface, at its depth.

        Back-projects the surface's pixel rectangle through the left camera. A
        pixel ``c`` covers ``[c - 0.5, c + 0.5]``, so a rectangle spanning columns
        ``[c0, c1)`` has its edges at ``c0 - 0.5`` and ``c1 - 0.5``. Rows are
        flipped: image rows increase downward and world ``y`` increases upward.

        **A surface that reaches the edge of the left image is extended past it**,
        by one baseline plus a pixel. This is a rule about what the model means,
        not a tuning parameter: a surface running to the edge of the frame is one
        the frame cuts off, not one that stops there, and THE RIGHT CAMERA LOOKS
        FURTHER. Sitting a baseline to the side, it sees a strip beyond the left
        frustum — 10.1 px wide at the background's depth here.
        Without the extension that strip lands on no surface at all and renders
        as empty, while the fixture fills it by reflecting texture. Measured
        before the extension was added: it accounted for essentially all of the
        right-image disagreement away from depth discontinuities, which is the
        one place falsifier 1 requires the two sources to agree. It would have
        been read as a broken render path.
        The extension is invisible to the left camera by construction, since it
        lies outside its frustum, and a test asserts the left image is unchanged
        by it.
        """
        height, width = self.shape
        f_px = float(self.params["f_px"])
        cx, cy = (width - 1) / 2.0, (height - 1) / 2.0
        z = surface.depth_m
        c0, c1 = surface.cols
        r0, r1 = surface.rows
        x_min = self.left_camera_x + (c0 - 0.5 - cx) * z / f_px
        x_max = self.left_camera_x + (c1 - 0.5 - cx) * z / f_px
        y_max = -(r0 - 0.5 - cy) * z / f_px
        y_min = -(r1 - 0.5 - cy) * z / f_px

        margin = float(self.params["baseline"]) + z / f_px
        if c0 <= 0:
            x_min -= margin
        if c1 >= width:
            x_max += margin
        if r0 <= 0:
            y_max += margin
        if r1 >= height:
            y_min -= margin
        return x_min, x_max, y_min, y_max

    def uv_window(self, surface: Surface) -> tuple[float, float, float, float]:
        """``(u_min, u_max, v_min, v_max)`` selecting this surface's slice of the texture.

        One texture image is shared by every surface and each takes the window of
        it that its own rectangle covers, so the left camera reconstructs the
        texture exactly. Blender's ``v`` runs bottom-up, hence the flip.
        """
        height, width = self.shape
        f_px = float(self.params["f_px"])
        z = surface.depth_m
        c0, c1 = surface.cols
        r0, r1 = surface.rows
        u_min, u_max = c0 / width, c1 / width
        v_min, v_max = 1.0 - r1 / height, 1.0 - r0 / height

        # The edge extension above widened the plane in world units; the UV
        # window has to widen with it by the same fraction, or the texture is
        # stretched and the left image no longer matches. Expressed in pixels
        # first, because that is the unit the window is defined in.
        margin_px = (float(self.params["baseline"]) + z / f_px) * f_px / z
        if c0 <= 0:
            u_min -= margin_px / width
        if c1 >= width:
            u_max += margin_px / width
        if r0 <= 0:
            v_max += margin_px / height
        if r1 >= height:
            v_min -= margin_px / height
        return u_min, u_max, v_min, v_max


#: **head frame -> Blender world frame.** Head is +X right, +Y DOWN, +Z FORWARD.
#: The world these scenes are built in is +X right, +Y UP, and the camera looks
#: down -Z, so forward is -Z. Both axes that disagree flip, and this is the
#: matrix that flips them.
WORLD_FROM_HEAD: FloatArray = np.diag([1.0, -1.0, -1.0])

#: **eye frame -> Blender camera-local frame.** The geometry's eye frame has the
#: optical axis along +Z with +Y down, matching the image. Blender's camera looks
#: down its local **-Z** with local **+Y up**. Numerically the same flip as
#: :data:`WORLD_FROM_HEAD`, and written separately because it is a different
#: statement: one is about the scene, the other about the camera. Collapsing them
#: into one constant is how a basis change becomes uncheckable.
CAMERA_FROM_EYE: FloatArray = np.diag([1.0, -1.0, -1.0])


def eye_camera_poses(
    rig: StereoRig, fixation: Fixation, k: float = K_LISTING_DEFAULT
) -> dict[str, dict[str, Any]]:
    """Blender world matrices for the two eyes at ``fixation``. **Tested, no bpy.**

    Returns ``{"left": {...}, "right": {...}}``, each with a ``matrix_world`` as a
    4x4 row-major nested list and the pieces it was built from, so a reader can
    check the construction rather than trust it.

    **THE BASIS CHANGE IS THE TRAP AND IT LIVES HERE, NOT IN BLENDER.**
    ``blender_render`` may import nothing but the standard library and ``bpy``, so
    it cannot compute this; it applies a matrix it is handed. That constraint is
    load-bearing rather than inconvenient — the conversion is the part most likely
    to be wrong, and putting it here makes it testable without a renderer.

    The construction, written out because inferring it from a render that "looks
    right" is exactly how a rotated eye passes for a different scene:

        ``M = WORLD_FROM_HEAD @ R @ CAMERA_FROM_EYE``

    Read right to left: take the camera's local axes into the eye frame, apply the
    eye's head-frame orientation ``R``, then carry the result into the world. The
    optical axis check is ``M @ [0, 0, -1] == WORLD_FROM_HEAD @ (R @ [0, 0, 1])``
    — Blender looks down local -Z, the geometry looks along +Z.

    **Not Blender's native toe-in**, which is yaw-only and zero-torsion and is
    therefore right only for a symmetric horizontal fixation. Each camera's world
    matrix is set explicitly from the rotation the geometry gives, torsion
    included.

    Optical centres are ``(-b/2, 0, 0)`` and ``(+b/2, 0, 0)`` in the head frame;
    ``x`` is the one axis the basis change leaves alone, so they are the same
    numbers in the world frame.
    """
    rotations = eye_rotations(rig, fixation, k=k)
    half_b = float(rig.baseline) / 2.0
    poses: dict[str, dict[str, Any]] = {}
    for name, rot, sign in (
        ("left", rotations.left, -1.0),
        ("right", rotations.right, +1.0),
    ):
        basis = WORLD_FROM_HEAD @ rot @ CAMERA_FROM_EYE
        centre_head = np.array([sign * half_b, 0.0, 0.0])
        centre_world = WORLD_FROM_HEAD @ centre_head
        matrix = np.eye(4)
        matrix[:3, :3] = basis
        matrix[:3, 3] = centre_world
        poses[name] = {
            "matrix_world": matrix.tolist(),
            "head_rotation": np.asarray(rot).tolist(),
            "centre_world": centre_world.tolist(),
        }
    return poses


def scene_from_fixture(seed: int = 0, H: int = 240, W: int = 320) -> SceneModel:
    """The scene the analytic fixture describes, as a model.

    The surface rectangles are **declared here and tested against the fixture**
    rather than read out of it — ``make_synthetic_scene`` builds its depth map
    with literal slice assignments and exposes no structure to read. Declaring
    them duplicates four numbers; :func:`rasterise_depth` is what stops the
    duplicate from drifting, by reproducing the fixture's own ``depth_gt``.

    Surfaces are ordered far to near, which is also the order the fixture assigns
    them, so painting them in sequence gives the same visibility.
    """
    left, _right, _depth, params = make_synthetic_scene(H=H, W=W, seed=seed)
    if (H, W) != (240, 320):
        raise ValueError(
            f"the fixture's surface rectangles are literals at 240x320; got {(H, W)}. "
            "Rendering another size needs the rectangles scaled, which is a decision, "
            "not a default."
        )
    surfaces = (
        Surface(depth_m=4.5, rows=(0, H), cols=(0, W)),  # background
        Surface(depth_m=3.6, rows=(30, 100), cols=(205, 290)),
        Surface(depth_m=3.0, rows=(40, 170), cols=(40, 170)),
        Surface(depth_m=2.4, rows=(120, 220), cols=(160, 290)),
    )
    return SceneModel(surfaces=surfaces, params=params, texture=np.asarray(left, dtype=np.float64))


def split_cards(model: SceneModel, k: int) -> SceneModel:
    """Cut every non-background surface into ``k`` vertical strips. Returns a new model.

    A transformation on a scene rather than a new scene family: depths, texture,
    camera and materials are untouched, and only the lateral extent of the
    existing surfaces changes. The first surface is treated as background and left
    alone — it is the one that covers the frame.

    **This is a lever on OCCLUSION, and occlusion is what comes out, not what goes
    in.** Occluded area is the sum over vertical depth edges of (edge height ×
    disparity step), so cutting a card into strips multiplies its edges and raises
    occlusion. How much is a measured outcome of the geometry: ``k`` of 1, 2, 4, 8
    yields 1.97%, 4.26%, 8.84% and 17.16% of left pixels occluded on the fixture's
    geometry, and ``k = 10`` yields LESS than ``k = 8`` because strips narrow past
    the 8.85 px disparity step and the geometry degenerates. Do not read ``k`` as a
    quantity of occlusion.

    Each card becomes ``k`` strips with ``k - 1`` gaps of equal width, inside the
    card's original columns. Total card area therefore falls as ``k`` rises — from
    46.0% of the frame at ``k = 1`` to 24.6% at ``k = 8`` — which is a covariate of
    any sweep over ``k`` and cannot be separated from it within one frame. Holding
    area fixed would need the strips spread wider than the original extent, which
    does not fit.
    """
    if k < 1:
        raise ValueError(f"k must be at least 1, got {k}")
    if k == 1:
        return model

    background, *cards = model.surfaces
    strips: list[Surface] = []
    for card in cards:
        c0, c1 = card.cols
        width = (c1 - c0) / (2 * k - 1)  # k strips and k-1 gaps, all equal
        for i in range(k):
            lo = int(round(c0 + 2 * i * width))
            hi = int(round(c0 + (2 * i + 1) * width))
            if hi > lo:
                strips.append(Surface(depth_m=card.depth_m, rows=card.rows, cols=(lo, hi)))
    return SceneModel(
        surfaces=(background, *strips),
        params=model.params,
        texture=model.texture,
        smoothing_sigma=model.smoothing_sigma,
    )


def occlusion_fractions(model: SceneModel) -> dict[str, float]:
    """How much of the frame is geometrically unmeasurable, both ways round.

    ``left_occluded_fraction`` is the one to use as a measure of OCCLUSION: a left
    pixel whose correspondent is hidden by a nearer surface. ``right_unmatched_
    fraction`` counts right-image pixels no left pixel maps to, and it includes a
    contribution that is not occlusion at all.

    **The two differ by a constant 3.12% on this camera, whatever the geometry** —
    measured across card heights from 15% to 100% and split counts from 1 to 8.
    That constant is the FRAME BORDER: the right camera sits a baseline to the
    side, so a strip of left pixels maps outside the right image entirely. exp007
    reported 5.09% "lateral overlap" for the fixture's geometry, of which 3.12%
    is border and 1.97% is occlusion.

    Computed from the model's step-edge depth, so it is a property of the geometry
    and needs no render.
    """
    depth = rasterise_depth(model, smooth=False)
    f_px = float(model.params["f_px"])
    baseline = float(model.params["baseline"])
    d_gt = f_px * baseline / depth
    height, width = depth.shape
    cols = np.arange(width)[None, :].repeat(height, 0)
    target = np.rint(cols - d_gt).astype(int)

    unmatched_right = 0
    occluded_left = 0
    longest_run = 0
    for y in range(height):
        order = np.argsort(-depth[y])  # far to near, so nearer surfaces win
        xs = target[y, order]
        inside = (xs >= 0) & (xs < width)
        seen = np.zeros(width, dtype=bool)
        owner = np.full(width, -1)
        for idx, col in zip(order[inside], xs[inside], strict=True):
            if owner[col] == -1 or depth[y, idx] < depth[y, owner[col]]:
                owner[col] = idx
            seen[col] = True
        unmatched_right += int((~seen).sum())
        occluded_left += int(
            sum(1 for idx, col in zip(order[inside], xs[inside], strict=True) if owner[col] != idx)
        )
        run = 0
        for flag in ~seen:
            run = run + 1 if flag else 0
            longest_run = max(longest_run, run)

    size = depth.size
    return {
        "right_unmatched": unmatched_right,
        "right_unmatched_fraction": unmatched_right / size,
        "left_occluded": occluded_left,
        "left_occluded_fraction": occluded_left / size,
        "border_fraction": (unmatched_right - occluded_left) / size,
        "longest_run_px": longest_run,
        "card_area_fraction": float((depth < depth.max() - 1e-6).mean()),
    }


def rasterise_depth(model: SceneModel, smooth: bool = True) -> FloatArray:
    """The model's depth map, as the fixture would have produced it.

    Painted far-to-near in ``surfaces`` order, then smoothed by
    ``smoothing_sigma``. With ``smooth=True`` this must equal the fixture's
    ``depth_gt`` exactly, and a test asserts it; with ``smooth=False`` it is the
    step-edged depth map the RENDERER will actually produce, because flat planes
    have no soft edges.

    That difference is real and is confined to a band a few pixels wide at each
    depth discontinuity. It is declared rather than corrected: smoothing the
    rendered depth to match would mean modelling the fixture's blur in Blender,
    which is machinery in service of a comparison rather than of a scene.
    """
    height, width = model.shape
    depth = np.zeros((height, width), dtype=np.float64)
    for surface in model.surfaces:
        r0, r1 = surface.rows
        c0, c1 = surface.cols
        depth[r0:r1, c0:c1] = surface.depth_m
    if depth.min() <= 0:
        raise ValueError("the surfaces do not cover the frame; every pixel needs a depth")
    if smooth:
        depth = gaussian_filter(depth, model.smoothing_sigma)
    return np.asarray(depth, dtype=np.float32)


def write_scene(
    model: SceneModel,
    directory: str | Path,
    fixation: Fixation | None = None,
    k: float = K_LISTING_DEFAULT,
) -> Path:
    """Write the model where Blender can read it: ``scene.json`` and ``texture.exr``.

    Blender runs in its own process and its own interpreter, so the model crosses
    that boundary as files. The texture goes out as **32-bit float EXR**, not
    PNG: 8-bit would quantise it to 256 levels, and the point of using the
    fixture's own array is that the rendered image can equal it rather than
    approximate it.

    Needs the optional ``blender`` extra for the EXR write.
    """
    import Imath
    import OpenEXR

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)

    height, width = model.shape
    texture = np.asarray(model.texture, dtype=np.float32)
    if texture.shape != (height, width):
        raise ValueError(f"texture is {texture.shape} but the camera says {(height, width)}")

    header = OpenEXR.Header(width, height)
    channel = Imath.Channel(Imath.PixelType(Imath.PixelType.FLOAT))
    header["channels"] = {"Y": channel}
    out = OpenEXR.OutputFile(str(directory / "texture.exr"), header)
    try:
        out.writePixels({"Y": texture.tobytes()})
    finally:
        out.close()

    spec = {
        "params": dict(model.params),
        "smoothing_sigma": model.smoothing_sigma,
        "left_camera_x": model.left_camera_x,
        "texture": "texture.exr",
        # Present only when a fixation was asked for. Absent means the renderer
        # uses its rectified-parallel path, unchanged, which is what keeps every
        # render before this step reproducible.
        "eye_poses": (
            None
            if fixation is None
            else eye_camera_poses(
                StereoRig(baseline=float(model.params["baseline"])), fixation, k=k
            )
        ),
        "fixation": (
            None
            if fixation is None
            else {
                "azimuth": fixation.azimuth,
                "elevation_down": fixation.elevation_down,
                "vergence": fixation.vergence,
                "k": k,
            }
        ),
        "surfaces": [
            {
                "depth_m": s.depth_m,
                "rows": list(s.rows),
                "cols": list(s.cols),
                "extent_world": list(model.extent_world(s)),
                "uv_window": list(model.uv_window(s)),
            }
            for s in model.surfaces
        ],
    }
    path = directory / "scene.json"
    path.write_text(json.dumps(spec, indent=2))
    return path
