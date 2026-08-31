"""The sample-index to unit-ray boundary (od-001). INFRASTRUCTURE.

No science. This commit adds no measurement and changes none: configured for
uniform sampling on the existing pinhole grid it is the identity, and the test
that matters asserts exactly that (``tests/test_sampling.py``).

What od-001 decided
-------------------
The boundary from the active-sampling layer into geometry passes **a unit ray in
a stated frame**, not a pixel index. The predecessor consumed pinhole intrinsics
*inside* its geometry layer — ``geometry/oculomotor.py:391-392`` at
``visgraf/active-stereo@3f7a263`` un-projected a pixel inline using
``rig.focal_px`` and ``rig.principal_point``. Under the ray commitment that
un-projection moves out into a sampling model, which is this file. Neither
reference repository contains one: ``projection.py`` there runs world -> pixel
only, and the inverse existed nowhere as a named thing.

The frame, stated here and not in governance
--------------------------------------------
Directions are unit vectors in the **rectified left-camera frame**:

    +x  right, along increasing column
    +y  down,  along increasing row      (matches row-major image order)
    +z  forward, along the optical axis
    right-handed; origin at the left camera's optical centre.

Stated at the function that returns the value, per ``fc-006``. The predecessor's
CLAUDE.md carried a false frame invariant at governance level for eleven days
precisely because a sentence in a governance file has nothing to fail against.
Every public function below restates the frame in its own docstring; that
repetition is deliberate.

What the interface has to admit, and does
-----------------------------------------
Two cases are coming and neither is built here:

* a **non-uniform lattice** (foveated sampling), and
* a **non-planar projection** (spherical sampling).

They fit without a signature change because nothing below assumes either.
``direction`` is an arbitrary map from index to unit vector — a foveated lattice
simply computes a different one. ``index`` returns the *nearest* sample, which is
well defined for any lattice. ``contains`` exists because on a non-uniform
lattice "is this index sampled?" stops being a bounds check. No parameter for
eccentricity, no parameter for a sphere: those arrive with the implementations
that need them, which is what "design so they fit, implement what is exercised"
means.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int_]
BoolArray = NDArray[np.bool_]

#: The one frame this module speaks. A string rather than a bare convention so
#: that a second frame, if one ever arrives, cannot be introduced silently.
RECTIFIED_LEFT_CAMERA = "rectified_left_camera"


@runtime_checkable
class SamplingModel(Protocol):
    """Maps sample indices to unit directions, and back where the inverse exists.

    Implementations state their frame. Indices are ``(row, col)`` in row-major
    image order; directions are unit 3-vectors in ``frame``.
    """

    @property
    def shape(self) -> tuple[int, int]:
        """``(H, W)`` of the index space."""
        ...

    @property
    def frame(self) -> str:
        """The frame ``direction`` returns vectors in."""
        ...

    def direction(self, index: Any) -> FloatArray:
        """``(..., 2)`` indices -> ``(..., 3)`` unit directions in ``frame``."""
        ...

    def index(self, direction: Any) -> IntArray:
        """``(..., 3)`` directions in ``frame`` -> ``(..., 2)`` nearest indices."""
        ...

    def contains(self, index: Any) -> BoolArray:
        """Whether each ``(..., 2)`` index is one this model actually samples."""
        ...


class PinholeSampling:
    """Uniform pinhole sampling on a fixed-resolution grid. The only model here.

    Sample ``(row, col)`` looks along the ray through the image plane at that
    pixel, normalised:

        v = [ (col - c_col) / f,  (row - c_row) / f,  1 ]
        d = v / |v|

    in the **rectified left-camera frame**: +x right along increasing column, +y
    down along increasing row, +z forward along the optical axis, right-handed.

    Parameters
    ----------
    shape : (H, W) of the index space.
    focal_px : focal length in pixels.
    principal_point : (row, col) of the optical axis, defaulting to the geometric
        centre ``((H-1)/2, (W-1)/2)``.

    **The principal point is this model's declaration, not the fixture's.**
    ``CameraParams`` carries ``f_px``, ``baseline``, ``H`` and ``W`` and no
    principal point, because the ported loop never projects a 3-D point and so
    never needed one. Nothing measured in this repository constrains it, and
    nothing downstream currently reads the absolute orientation of the returned
    rays — only that index -> ray -> index is the identity, which holds for any
    principal point. Recorded so that a later component which *does* depend on
    the absolute orientation knows this value was chosen here and not measured.
    """

    def __init__(
        self,
        shape: tuple[int, int],
        focal_px: float,
        principal_point: tuple[float, float] | None = None,
    ) -> None:
        h, w = int(shape[0]), int(shape[1])
        if h <= 0 or w <= 0:
            raise ValueError(f"shape must be positive, got {shape}")
        if not np.isfinite(focal_px) or focal_px <= 0:
            raise ValueError(f"focal_px must be finite and positive, got {focal_px}")
        self._shape = (h, w)
        self._focal_px = float(focal_px)
        self._principal_point = (
            ((h - 1) / 2.0, (w - 1) / 2.0)
            if principal_point is None
            else (float(principal_point[0]), float(principal_point[1]))
        )

    @classmethod
    def from_params(cls, params: Any, shape: tuple[int, int] | None = None) -> PinholeSampling:
        """Build from a :class:`~bio3dvision.fixture.CameraParams`-shaped mapping."""
        h, w = (int(params["H"]), int(params["W"])) if shape is None else shape
        return cls((h, w), float(params["f_px"]))

    @property
    def shape(self) -> tuple[int, int]:
        return self._shape

    @property
    def frame(self) -> str:
        return RECTIFIED_LEFT_CAMERA

    @property
    def focal_px(self) -> float:
        return self._focal_px

    @property
    def principal_point(self) -> tuple[float, float]:
        return self._principal_point

    def direction(self, index: Any) -> FloatArray:
        """``(..., 2)`` ``(row, col)`` -> ``(..., 3)`` unit rays, rectified left-camera frame.

        +x right, +y down, +z forward. Accepts a bare ``(row, col)`` pair.
        """
        idx = np.asarray(index, dtype=np.float64)
        if idx.shape[-1] != 2:
            raise ValueError(f"index must have a trailing axis of length 2, got {idx.shape}")
        row, col = idx[..., 0], idx[..., 1]
        pr, pc = self._principal_point
        v = np.stack(
            [
                (col - pc) / self._focal_px,
                (row - pr) / self._focal_px,
                np.ones_like(row),
            ],
            axis=-1,
        )
        norm: FloatArray = np.linalg.norm(v, axis=-1, keepdims=True)
        out: FloatArray = v / norm
        return out

    def index(self, direction: Any) -> IntArray:
        """``(..., 3)`` unit rays -> ``(..., 2)`` nearest ``(row, col)`` indices.

        The inverse exists only for rays in front of the sensor. A ray with
        ``d_z <= 0`` points behind the image plane and has no sample; that is a
        caller error and raises, rather than returning a sentinel index — this
        repository represents invalidity with ``nan``, and an index has no ``nan``.

        Returns the **nearest** index, which is what makes this well defined for a
        lattice that is not uniform. On the uniform lattice the arithmetic is
        exact to floating point and rounding recovers the originating index
        exactly; ``tests/test_sampling.py`` asserts that over all 76 800 of them.
        """
        d = np.asarray(direction, dtype=np.float64)
        if d.shape[-1] != 3:
            raise ValueError(f"direction must have a trailing axis of length 3, got {d.shape}")
        z = d[..., 2]
        if not np.all(np.isfinite(d)):
            raise ValueError("direction must be finite")
        if np.any(z <= 0.0):
            raise ValueError(
                "direction has no sample index: rays with d_z <= 0 point behind the "
                "sensor, and the pinhole inverse is undefined there"
            )
        pr, pc = self._principal_point
        row = pr + self._focal_px * d[..., 1] / z
        col = pc + self._focal_px * d[..., 0] / z
        out: IntArray = np.stack([np.rint(row), np.rint(col)], axis=-1).astype(np.int_)
        return out

    def contains(self, index: Any) -> BoolArray:
        """Whether each index is sampled. Here: whether it is in bounds.

        A bounds check *today*, and a real question on a non-uniform lattice —
        which is why it is on the interface rather than left to callers.
        """
        idx = np.asarray(index)
        if idx.shape[-1] != 2:
            raise ValueError(f"index must have a trailing axis of length 2, got {idx.shape}")
        h, w = self._shape
        row, col = idx[..., 0], idx[..., 1]
        ok: BoolArray = (row >= 0) & (row < h) & (col >= 0) & (col < w)
        return ok


class EquirectSampling:
    """Equirectangular sampling on a sphere, with the pole ALONG THE BASELINE.

    **The frame is unchanged.** Directions come back in
    :data:`RECTIFIED_LEFT_CAMERA` — +x right along the baseline, +y down, +z
    forward — exactly as :class:`PinholeSampling` returns them. Only the
    index-to-direction MAP differs, which is the whole of what a projection is.
    That is why this needed no change to the Protocol; see the step 18a findings.

    **Rows are epipolar, and that is the reason for this parameterisation.**
    With the baseline along +x the two epipoles sit at ``+/-x``, so every epipolar
    great circle passes through them, and the family of such circles is exactly
    the set of MERIDIANS about +x. Indexing rows by the meridian ``phi`` and
    columns by the colatitude ``theta`` from +x therefore puts corresponding
    points on the same row, and ``matching.cost_volume``'s horizontal shift is
    a shift along ``theta``.

        row ``r`` -> ``phi   = 2*pi*(r + 0.5)/H - pi``   (about +x)
        col ``c`` -> ``theta = pi*(c + 0.5)/W``          (from +x)
        ``d = (cos(theta), sin(theta)*cos(phi), sin(theta)*sin(phi))``

    **The disparity is an ANGLE and the depth relation is not ``f*b/z``.** For a
    point seen at ``theta_L`` and ``theta_R`` from the two centres, with
    ``d = theta_R - theta_L``:

        ``r_L = b * sin(theta_R) / sin(d)``     and     ``r_R = b * sin(theta_L) / sin(d)``

    which is the sine rule on the triangle (left centre, right centre, point).
    It depends on ``theta`` — the angle from the baseline — and the pinhole
    relation has no analogue of that: at a range of 3 m the disparity is 5.8x
    larger at ``theta = 90 deg`` than at ``theta = 10 deg``. Substituting into
    ``f*b/z`` is wrong, not approximate. Measured in the step 18a findings and
    checked against a render to 1e-14 relative.

    **There is no "behind the sensor".** ``PinholeSampling.index`` raises for rays
    with ``d_z <= 0`` because the pinhole inverse is undefined there; a sphere
    samples every direction, so this ``index`` raises for no direction at all.
    Callers that guard on ``in_eye[..., 2] > 0`` are carrying a pinhole assumption.

    **The lattice is non-uniform in solid angle and COMPLETE in membership.** Rows
    near the pole subtend far less solid angle than rows near the equator, so this
    is a genuinely non-uniform lattice — but every in-bounds index is sampled, so
    :meth:`contains` remains a bounds check. fc-009 provided ``contains`` for
    lattices where membership is *not* a bounds check; this projection does not
    exercise that half of the provision, and saying so is more useful than
    claiming it does.
    """

    def __init__(self, shape: tuple[int, int], pole: Any = (1.0, 0.0, 0.0)) -> None:
        h, w = int(shape[0]), int(shape[1])
        if h <= 0 or w <= 0:
            raise ValueError(f"shape must be positive, got {shape}")
        axis = np.asarray(pole, dtype=np.float64)
        if axis.shape != (3,):
            raise ValueError(f"pole must be a (3,) vector, got shape {axis.shape}")
        norm = float(np.linalg.norm(axis))
        if not np.isfinite(norm) or norm == 0.0:
            raise ValueError(f"pole must be a non-zero finite vector, got {pole!r}")
        axis = axis / norm
        # A right-handed triad (pole, e1, e2). The seed is whichever axis the pole
        # is least aligned with, so the cross product is never near-degenerate.
        seed = np.eye(3)[int(np.argmin(np.abs(axis)))]
        e1 = np.cross(axis, seed)
        e1 = e1 / np.linalg.norm(e1)
        e2 = np.cross(axis, e1)
        self._shape = (h, w)
        self._pole = axis
        self._e1 = e1
        self._e2 = e2

    @property
    def shape(self) -> tuple[int, int]:
        return self._shape

    @property
    def frame(self) -> str:
        return RECTIFIED_LEFT_CAMERA

    @property
    def pole(self) -> FloatArray:
        """The axis rows are meridians about. The baseline, by default."""
        out: FloatArray = self._pole.copy()
        return out

    def direction(self, index: Any) -> FloatArray:
        """``(..., 2)`` ``(row, col)`` -> ``(..., 3)`` unit rays, same frame as pinhole."""
        idx = np.asarray(index, dtype=np.float64)
        if idx.shape[-1] != 2:
            raise ValueError(f"index must have a trailing axis of length 2, got {idx.shape}")
        h, w = self._shape
        phi = 2.0 * np.pi * (idx[..., 0] + 0.5) / h - np.pi
        theta = np.pi * (idx[..., 1] + 0.5) / w
        st = np.sin(theta)
        out: FloatArray = (
            np.cos(theta)[..., None] * self._pole
            + (st * np.cos(phi))[..., None] * self._e1
            + (st * np.sin(phi))[..., None] * self._e2
        )
        return out

    def index(self, direction: Any) -> IntArray:
        """``(..., 3)`` unit rays -> ``(..., 2)`` nearest ``(row, col)``.

        **Raises for no direction.** Unlike the pinhole inverse there is no
        half-space this map is undefined on, and rows wrap in ``phi``.
        """
        d = np.asarray(direction, dtype=np.float64)
        if d.shape[-1] != 3:
            raise ValueError(f"direction must have a trailing axis of length 3, got {d.shape}")
        if not np.all(np.isfinite(d)):
            raise ValueError("direction must be finite")
        h, w = self._shape
        theta = np.arccos(np.clip(d @ self._pole, -1.0, 1.0))
        phi = np.arctan2(d @ self._e2, d @ self._e1)
        row = h * (phi + np.pi) / (2.0 * np.pi) - 0.5
        col = w * theta / np.pi - 0.5
        # Rows wrap: phi is periodic, so a row rounding to h belongs at 0.
        rows = np.mod(np.rint(row), h)
        cols = np.clip(np.rint(col), 0, w - 1)
        out: IntArray = np.stack([rows, cols], axis=-1).astype(np.int_)
        return out

    def contains(self, index: Any) -> BoolArray:
        """Whether each index is sampled. Here: a bounds check, as for the pinhole.

        Rows are periodic in ``phi``, so an out-of-range row is a caller error
        rather than an unsampled direction; it is reported as not contained, which
        is what every caller in this repository already does with the answer.
        """
        idx = np.asarray(index)
        if idx.shape[-1] != 2:
            raise ValueError(f"index must have a trailing axis of length 2, got {idx.shape}")
        h, w = self._shape
        row, col = idx[..., 0], idx[..., 1]
        ok: BoolArray = (row >= 0) & (row < h) & (col >= 0) & (col < w)
        return ok


def route_as_direction(policy: Any, model: SamplingModel) -> Any:
    """Wrap a policy so it returns a **unit ray**, and no index, to its caller.

    The difference from :func:`route_through_sampling` is the whole of step 15's
    falsifier 1: that adapter converts index -> ray -> index and hands back a
    pixel, so no ray ever leaves it. This one stops at the ray.

    ``ActiveStereo.step(direction=..., sampling=...)`` consumes it. **The index
    does not drop out of the system** — it reappears inside ``step``, because the
    foveal weight and the vergence window are defined on the pixel lattice. What
    this removes is the index from the POLICY path; what it cannot remove is the
    sensor at the point of use.

    Recorded that way because ``route_through_sampling``'s docstring predicted
    otherwise: "when a geometry layer exists, the ray goes straight into it and
    ``model.index`` drops out of this path". The geometry layer now exists, the
    ray does go into it, and the prediction is half right.
    """

    def routed(engine: Any, visited: list[tuple[int, int]]) -> FloatArray | None:
        chosen = policy(engine, visited)
        if chosen is None:
            return None
        return model.direction(np.asarray(chosen, dtype=np.float64))

    return routed


def route_through_sampling(policy: Any, model: SamplingModel) -> Any:
    """Wrap a policy so its choice crosses the L6->L1 boundary AS A DIRECTION.

    This is what "the sampling model sits in front of ``ActiveStereo``, not
    inside it" means concretely. The policy picks a sample index; the index
    becomes a unit ray, which is the boundary od-001 specifies; the ray is then
    turned back into an index **only because ``ActiveStereo`` still consumes a
    pixel**. That second hop is the temporary half: when a geometry layer exists,
    the ray goes straight into it and ``model.index`` drops out of this path.

    ``ActiveStereo`` is not modified — the whole point of falsifier 2 — and on
    the uniform pinhole lattice the round trip is exactly the identity, so every
    arm reproduces bit-for-bit.
    """

    def routed(engine: Any, visited: list[tuple[int, int]]) -> tuple[int, int] | None:
        chosen = policy(engine, visited)
        if chosen is None:
            return None
        ray = model.direction(np.asarray(chosen, dtype=np.float64))
        back = model.index(ray)
        return (int(back[0]), int(back[1]))

    return routed
