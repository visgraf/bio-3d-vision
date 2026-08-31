"""L1 — oculomotor geometry: gaze becomes SO(3) here and nowhere else.

Migrated from ``visgraf/active-stereo@3f7a263``'s ``geometry/oculomotor.py``, with
one structural change: **the stereo rig no longer carries a sensor.**

The reference's ``StereoRig`` declared ``baseline``, ``focal_px`` and
``principal_point`` in one frozen type, with ``focal_px`` required and no default
(``types.py:31-34``). Every rig construction therefore carried an intrinsic —
including in the 32 tests whose assertions are pure SO(3) and whose code paths
never read ``focal_px`` at all. ``eye_rotations``, ``fixation_distance``,
``fixation_point`` and ``rectification_rotation`` read ``baseline`` and never
``focal_px``. **The coupling was in the type, not in the mathematics.**

Here :class:`StereoRig` is baseline and capture vergence. The sensor is the
:class:`~bio3dvision.sampling.SamplingModel` that ``fc-009`` built — and this
module is its first consumer, which is what makes ``fc-009``'s deferred
falsifier-2 verdict answerable at last.

Frames and units
----------------
**Cyclopean head frame**: origin between the eyes, +X right, +Y down, +Z forward,
right-handed. Angles in radians, distances in metres. Gaze angles compose in
**Helmholtz order**: elevation about the interaural X axis first, azimuth within
the elevated plane. The consequence is what makes the geometry below closed-form —
the plane of regard contains the baseline for every azimuth, so elevation does not
enter the chord construction.

**Domain**: ``fixation.azimuth`` must lie in ``(-pi/2, pi/2)``. Beyond it the chord
construction lands on the minor arc of the Vieth-Müller circle, where the
inscribed angle is ``pi - vergence`` and the returned geometry is silently wrong.
The functions raise instead.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]

__all__ = [
    "K_LISTING_DEFAULT",
    "Estimate",
    "EyeRotations",
    "Fixation",
    "FixationProposal",
    "RefusalReason",
    "StereoRig",
    "TargetRefused",
    "eye_rotations",
    "fixation_distance",
    "fixation_point",
    "is_forward_gaze",
    "rectification_rotation",
    "require_forward_azimuth",
    "target_to_fixation",
]

_Z = np.array([0.0, 0.0, 1.0])

#: Temporal tilt of each eye's Listing plane per radian of vergence.
#:
#: **0.25, and NOT 0.5.** ``k = 1/2`` is the plane-of-regard alignment optimum —
#: the value at which vertical disparity in the plane of regard vanishes exactly —
#: and it is not the default. The two numbers sit one line apart in the reference
#: and the optimum is the more memorable of them, so the distinction is stated here
#: and pinned by ``tests/test_oculomotor.py::test_the_default_k_is_a_quarter_not_a_half``.
#:
#: **The correction travels with the parameter.** ADR-0014 introduced ``k`` and
#: predicted the alignment null at 0.25, instructing that a minimum found elsewhere
#: be read as a sign or axis error in :func:`eye_rotations`. ADR-0016 corrected
#: that: the null is at 1/2, exactly, and the reason is that at ``k = 1/2`` the
#: tilted-Listing composition IS the Helmholtz rotation of the eye's own gaze, so
#: the plane of regard images on the horizontal meridian of both retinas. A
#: corrected rationale detached from its correction gets re-broken, which is why
#: both halves are recorded at the parameter rather than in a document.
K_LISTING_DEFAULT = 0.25


@dataclass(frozen=True)
class StereoRig:
    """Stereo geometry: where the eyes are, and how converged the capture was.

    **Carries no sensor**, and that absence is the point of this migration. Focal
    length and principal point live in the sampling model; see the module
    docstring for what the coupling cost.

    Attributes
    ----------
    baseline : float
        Interocular separation, metres. Positive.
    vergence : float
        Capture convergence of a static stimulus, radians. Zero means parallel.
        **Never read by the oculomotor functions here** — the fixation state
        carries the vergence they use. It exists so a static stimulus can say
        what it was captured at.
    """

    baseline: float
    vergence: float = 0.0

    def __post_init__(self) -> None:
        # Finiteness is checked explicitly: `baseline <= 0` is False for NaN, so
        # the sign check alone would silently admit a NaN rig.
        for name in ("baseline", "vergence"):
            value = getattr(self, name)
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite, got {value}")
        if self.baseline <= 0:
            raise ValueError(f"baseline must be positive, got {self.baseline}")
        if self.vergence < 0:
            raise ValueError(f"vergence must be non-negative, got {self.vergence}")


@dataclass(frozen=True)
class Fixation:
    """Binocular oculomotor state: where the eyes point, as gaze plus vergence.

    Attributes
    ----------
    azimuth : float
        Radians, cyclopean head frame. Positive toward +X (rightward).
    elevation_down : float
        Radians, positive **downward** (+Y), matching row growth in image
        coordinates. The sign is in the name deliberately: "elevation" alone is a
        sign-error trap and this field must not be shortened.
    vergence : float
        Total vergence angle at the fixation point, radians. Zero is legal and
        means parallel gaze, fixation at infinity.

    **Why not two per-eye rotations.** This is Hering's decomposition into version
    (conjugate) and vergence (disjunctive), which is the control-regime closure
    expressed in the type: saccades act on version, vergence is feedback-controlled
    and acts on the third component. Per-eye rotations would destroy that split.

    **Why torsion is not a field.** It is *determined*, not free — computed from
    gaze and vergence by the binocular Listing law in :func:`eye_rotations`. Its
    absence is a decision, not an omission. ``k`` is a property of the plant, not
    of a fixation state, and never becomes a field here either.
    """

    azimuth: float
    elevation_down: float
    vergence: float

    def __post_init__(self) -> None:
        for name in ("azimuth", "elevation_down", "vergence"):
            value = getattr(self, name)
            if not np.isfinite(value):
                raise ValueError(f"{name} must be finite, got {value}")
        if self.vergence < 0:
            raise ValueError(f"vergence must be non-negative, got {self.vergence}")


@dataclass(frozen=True)
class EyeRotations:
    """Head-frame orientations of the two eyes under a fixation.

    ``(3, 3)`` rotation matrices, dimensionless, cyclopean head frame. ``R`` maps
    the reference (straight-ahead) eye frame into the fixated one, so the eye's
    optical axis in the head frame is ``R @ [0, 0, 1]``. Camera extrinsics
    (head -> eye) use ``R.T``.

    A named pair rather than a tuple: an ``R_right, R_left = ...`` unpack swap is
    silent at the call site, and the sagittal-mirror test cannot see a swap that
    happens outside this module.
    """

    left: FloatArray
    right: FloatArray


@dataclass(frozen=True)
class Estimate:
    """A scalar belief about depth: a value and its variance, both metres-based.

    **Scalar, where the reference took a field.** The reference's
    ``target_to_fixation`` took the whole ``(H, W)`` depth field and indexed it
    internally, because ``StereoRig`` carried no image dimensions and that was
    "the only thing that makes the bounds check possible at all". With a direction
    at the boundary there is no pixel to bounds-check — the sampling model owns
    ``shape`` and ``contains`` — so the field-shaped argument loses its reason to
    exist and the type narrows to what the geometry actually reads.
    """

    value: float
    variance: float


class RefusalReason(Enum):
    """Why a target could not become a fixation.

    A set of kinds rather than a bare ``None``: a caller counting bad targets
    needs to know which kind, and refusals can co-occur.
    """

    DEPTH_UNAVAILABLE = "depth_unavailable"
    DEPTH_NONPOSITIVE = "depth_nonpositive"
    TOO_NEAR = "too_near"
    BACKWARD_GAZE = "backward_gaze"


@dataclass(frozen=True)
class FixationProposal:
    """A proposed oculomotor state and the variance of its vergence component."""

    fixation: Fixation
    vergence_variance: float


@dataclass(frozen=True)
class TargetRefused:
    """A target that cannot become a fixation, with every reason that applied."""

    reasons: frozenset[RefusalReason] = field(default_factory=frozenset)


def require_forward_azimuth(fixation: Fixation) -> None:
    """Raise unless ``fixation.azimuth`` lies in ``(-pi/2, pi/2)``.

    Public because the domain is a property of the Vieth-Müller chord
    construction, not of any one function that uses it; a second copy of this rule
    and its message elsewhere is the thing to avoid.
    """
    if not abs(fixation.azimuth) < np.pi / 2.0:
        raise ValueError(
            f"azimuth must lie in (-pi/2, pi/2), got {fixation.azimuth}: the fixation "
            "point must be forward of the interaural axis (beyond it the Vieth-Muller "
            "chord subtends pi - vergence instead of vergence)"
        )


def _cyclopean_direction(fixation: Fixation) -> FloatArray:
    """Unit gaze direction of the cyclopean eye, head frame, Helmholtz order."""
    az, el = fixation.azimuth, fixation.elevation_down
    return np.array([np.sin(az), np.cos(az) * np.sin(el), np.cos(az) * np.cos(el)])


def _shortest_arc(p: FloatArray, g: FloatArray) -> FloatArray:
    """Rotation taking unit ``p`` to unit ``g`` about the axis ``p x g``.

    Trig-free exact Rodrigues form ``R = I + [v]x + [v]x^2 / (1 + c)`` with
    ``v = p x g`` and ``c = p . g``: no ``acos``-near-1 precision loss, and
    ``g == p`` yields exactly the identity with no branch. The axis is undefined at
    ``c = -1``, so that neighbourhood raises.
    """
    v = np.cross(p, g)
    c = float(p @ g)
    if 1.0 + c < 1e-9:
        raise ValueError("gaze direction is antiparallel to the primary direction")
    mat = np.array([[0.0, -v[2], v[1]], [v[2], 0.0, -v[0]], [-v[1], v[0], 0.0]])
    return np.asarray(np.eye(3) + mat + (mat @ mat) / (1.0 + c))


def fixation_distance(rig: StereoRig, fixation: Fixation) -> float:
    """Distance from the cyclopean origin to the fixation point, **metres**.

    Exact, via the Vieth-Müller chord in the plane of regard. Under Helmholtz
    composition that plane contains the baseline for every azimuth, **so elevation
    does not enter**: with ``h = (b/2)/tan(mu)`` the circle centre's height and
    ``az`` the azimuth,

        ``D = h cos(az) + sqrt(h^2 cos^2(az) + (b/2)^2)``

    Returns ``inf`` at zero vergence. At azimuth 0 this reduces exactly to
    ``b / (2 tan(mu/2))``.
    """
    require_forward_azimuth(fixation)
    mu = fixation.vergence
    if mu <= 0.0:
        return float("inf")
    half_b = rig.baseline / 2.0
    h = half_b / np.tan(mu)
    ca = np.cos(fixation.azimuth)
    return float(h * ca + np.sqrt(h * h * ca * ca + half_b * half_b))


def fixation_point(rig: StereoRig, fixation: Fixation) -> FloatArray:
    """Fixation point, ``(3,)`` **metres**, cyclopean head frame (+Z forward).

    Raises at zero vergence: the point is at infinity and an inf-valued vector is
    a NaN trap under any subsequent arithmetic. Callers needing the parallel-gaze
    limit should work with the gaze direction, as :func:`eye_rotations` does.
    """
    require_forward_azimuth(fixation)
    if fixation.vergence <= 0.0:
        raise ValueError("fixation point is at infinity at zero vergence")
    return fixation_distance(rig, fixation) * _cyclopean_direction(fixation)


def eye_rotations(rig: StereoRig, fixation: Fixation, k: float = K_LISTING_DEFAULT) -> EyeRotations:
    """Per-eye orientations under the binocular Listing law with tilt ``k``.

    Torsion is determined, not free. Each eye's primary direction ``p_e`` is
    straight ahead tilted **temporally** (away from the nose: -X left, +X right) by
    ``k * vergence`` — the only place ``k`` enters. The orientation is the
    shortest-arc displacement from the primary orientation:

        ``R_e = A(p_e -> g_e) @ A(z -> p_e)``       # maps z -> p_e -> g_e

    **The composition order is the part that was wrong on first derivation.** The
    second factor is the primary orientation, a pure temporal yaw with no torsional
    component since ``p_e`` lies in the horizontal plane. Omitting it mis-points
    the optical axis by about ``k * vergence``, which
    ``test_gaze_lines_intersect_the_fixation_point`` pins and
    ``test_the_second_factor_is_load_bearing`` guards against being dropped.

    The displacement axis ``p_e x g_e`` is perpendicular to ``p_e`` by
    construction, so it lies in the tilted Listing plane; for an axis ``n``
    perpendicular to ``p`` taking ``p`` to ``g``, ``g . n = 0`` forces
    ``n || p x g``, so the shortest arc is the *unique* Listing-compatible
    displacement. ``k = 0`` gives ``p_e = z``, the second factor collapses to the
    identity, and strict Listing holds with no branch.

    Parameters
    ----------
    rig : StereoRig
        Supplies the **baseline only**. ``rig.vergence`` is never read here; the
        fixation carries the vergence this uses.
    k : float
        Dimensionless. Default :data:`K_LISTING_DEFAULT` = 0.25. Deliberately not
        range-restricted: a sweep must be free to explore, and ``k = 1/2`` is a
        result rather than a bound.
    """
    if not np.isfinite(k):
        raise ValueError(f"k must be finite, got {k}")
    require_forward_azimuth(fixation)
    mu = fixation.vergence
    s, c = np.sin(k * mu), np.cos(k * mu)
    p_left = np.array([-s, 0.0, c])
    p_right = np.array([s, 0.0, c])
    if mu <= 0.0:
        g_left = g_right = _cyclopean_direction(fixation)
    else:
        point = fixation_point(rig, fixation)
        half_b = rig.baseline / 2.0
        g_left = point - np.array([-half_b, 0.0, 0.0])
        g_left = g_left / np.linalg.norm(g_left)
        g_right = point - np.array([half_b, 0.0, 0.0])
        g_right = g_right / np.linalg.norm(g_right)
    return EyeRotations(
        left=_shortest_arc(p_left, g_left) @ _shortest_arc(_Z, p_left),
        right=_shortest_arc(p_right, g_right) @ _shortest_arc(_Z, p_right),
    )


def rectification_rotation(fixation: Fixation) -> FloatArray:
    """Rotation **from the rectified frame into the head frame**, shared by both eyes.

    The Helmholtz version rotation with **azimuth zeroed**. Dimensionless,
    ``(3, 3)``.

    **Direction: rect -> head**, the same convention as :class:`EyeRotations`, so
    consumers project with ``R.T``. Stated with the matrix rather than apart from
    it: the matrix is unambiguous and a direction sentence is the only part that
    can be wrong. At ``elevation_down == 0`` this is the identity, so applying it,
    omitting it and transposing it are bit-identical there — every assertion about
    it must use a non-zero elevation.

    **Azimuth-independent by construction**, not by assertion: under Helmholtz
    composition the plane of regard is the elevated plane for every azimuth, so
    zeroing azimuth loses nothing. Independent of vergence and of the rig, and
    ``k`` is not an input at all.

    **The member choice is the part that can be wrong.** Rectification is
    determined only up to a rotation about the baseline; every member rectifies
    equally well and they differ only in where the fixation point lands. This one
    is chosen because it puts **the plane of regard at zero elevation in the
    rectified frame** — the reference stated that as "on the principal row", which
    needs a principal point to say; in directions it needs nothing.
    """
    el = fixation.elevation_down
    c, s = np.cos(el), np.sin(el)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, s], [0.0, -s, c]])


def is_forward_gaze(fixation: Fixation) -> bool:
    """Whether the cyclopean gaze points forward of the interaural plane.

    ``True`` iff ``cos(azimuth) * cos(elevation_down) > 0``.

    **Additive, not a tightening of anything.** ``Fixation`` validates finiteness
    and ``vergence >= 0`` only, so ``Fixation(0.1, 2.0, 0.064)`` — elevation past
    ``pi/2``, a point *behind* the head — is constructible, and
    :func:`fixation_distance`, :func:`fixation_point` and :func:`eye_rotations` all
    accept it and return well-formed geometry that points backward.
    :func:`require_forward_azimuth` cannot catch it: it is a statement about
    azimuth, and elevation is the free direction. The domains coincide; the
    failures do not.

    **This is the geometry test, not the angle test.** ``abs(el) < pi/2`` agrees
    with it everywhere except on *wrapped* elevations, where they disagree
    outright: at ``el = 7.0`` — which wraps to 0.7168, plainly forward — the angle
    test says backward. Do not "simplify" this to a comparison on the angle.

    A **predicate, not a raiser**, because its first caller
    (:func:`target_to_fixation`) must *refuse* rather than raise: a bad target must
    not kill the active loop.
    """
    return bool(_cyclopean_direction(fixation)[2] > 0.0)


def target_to_fixation(
    direction: FloatArray,
    depth: Estimate,
    rig: StereoRig,
    current: Fixation,
) -> FixationProposal | TargetRefused:
    """Turn a **unit direction** into an oculomotor state. The one boundary.

    The only place a sensor sample becomes a rotation.

    **The reference took a pixel and un-projected it here**, using
    ``rig.focal_px`` and ``rig.principal_point``. That un-projection has moved out
    to the :class:`~bio3dvision.sampling.SamplingModel`, which is what
    ``PinholeSampling.direction`` already computes and what ``fc-009`` built. This
    function is its first real consumer.

    Parameters
    ----------
    direction : (3,) unit vector in the **rectified left-camera frame**
        +x right along increasing column, +y down along increasing row, +z forward
        along the optical axis. Must be unit and forward-pointing; both are caller
        errors and raise, because producing a well-formed ray is the sensor's job.
    depth : Estimate
        **Planar depth**: ``z`` in the rectified left-camera frame, metres, with
        its variance. Not a range along the ray — see below.
    rig : StereoRig
        Baseline only.
    current : Fixation
        The state the target was *observed* under. Supplies the rectification
        rotation, so it is load-bearing, not context.

    Returns
    -------
    FixationProposal | TargetRefused
        Narrow before use. Data-quality problems — an unusable depth, a point too
        near, a backward gaze — are **refused, not raised**: a raise kills the
        active loop on one bad estimate, and a caller must be able to *count* bad
        targets rather than crash on them.

    Notes
    -----
    **Planar, not radial, and this is the trap the ray form introduces.** The
    reference multiplied depth by a ray whose ``z`` component was 1, so depth was
    ``z`` in the rectified frame. A **unit** direction is not that ray: scaling a
    unit direction by depth would make depth a *range*. The two differ by
    ``1/cos(angle)`` off-axis — small, smooth, largest at the field edge, and
    therefore shaped exactly like a modelling result rather than a units error.
    This is the same confusion ``infer_depth_convention`` guards in the render
    path, arriving by a different door. The division by ``direction[2]`` below is
    what keeps depth planar, and ``test_depth_is_planar_not_radial`` pins it.

    **Un-projection is about the LEFT optical centre**, ``(-b/2, 0, 0)``, not the
    cyclopean origin — disparity is left-image convention. At the image centre with
    a 0.064 m baseline and ``z = 1.5`` the two differ by 0.0213 rad, which is not a
    rounding-level distinction.

    **Depth frame.** ``depth`` is ``z`` in the rectified left-camera frame, which
    is what the scaling layer returns. It is *fixation-dependent*: the same world
    point has a different bare ``z`` at different fixations, so ground-truth
    comparison needs a stated frame once elevation is non-zero.
    """
    direction = np.asarray(direction, dtype=float)
    if direction.shape != (3,):
        raise ValueError(f"direction must be a (3,) vector, got shape {direction.shape}")
    norm = float(np.linalg.norm(direction))
    if not np.isfinite(norm) or abs(norm - 1.0) > 1e-9:
        raise ValueError(f"direction must be a unit vector, got norm {norm}")
    if direction[2] <= 0.0:
        raise ValueError(f"direction must be forward in the rectified frame (+z), got {direction}")

    value, variance = float(depth.value), float(depth.variance)
    if not (np.isfinite(value) and np.isfinite(variance)):
        return TargetRefused(frozenset({RefusalReason.DEPTH_UNAVAILABLE}))
    if value <= 0.0:
        return TargetRefused(frozenset({RefusalReason.DEPTH_NONPOSITIVE}))

    half_b = rig.baseline / 2.0
    centre_left = np.array([-half_b, 0.0, 0.0])
    # Unit-z ray in the rectified frame, then rotated into the head frame. The
    # division is what makes `value` a PLANAR depth; see the note above.
    ray = rectification_rotation(current) @ (direction / direction[2])
    point = centre_left + value * ray
    distance = float(np.linalg.norm(point))
    sin_az = point[0] / distance
    azimuth = float(np.arcsin(np.clip(sin_az, -1.0, 1.0)))
    elevation = float(np.arctan2(point[1], point[2]))

    # Independent conditions: neither ranks the other, so both are reported.
    # Elevation needs no depth at all, so a backward target is refused even under
    # a perfect depth estimate.
    reasons: set[RefusalReason] = set()
    if not is_forward_gaze(Fixation(azimuth, elevation, 0.0)):
        reasons.add(RefusalReason.BACKWARD_GAZE)
    # Must precede Fixation construction: below b/2 the arctan below takes the far
    # branch and returns a negative angle, which Fixation rejects with a
    # ValueError — a raise escaping where a refusal is required.
    if distance <= half_b:
        reasons.add(RefusalReason.TOO_NEAR)
    if reasons:
        return TargetRefused(frozenset(reasons))

    cos_az = np.cos(azimuth)
    numer = rig.baseline * distance * cos_az
    denom = distance * distance - half_b * half_b
    vergence = float(np.arctan(numer / denom))

    # First-order propagation. Depth enters through BOTH the distance and the
    # azimuth — the left-centre offset makes azimuth depth-dependent — so the
    # chain rule has two branches and dropping either is a silent factor error.
    #   dD/dz  = (P . m) / D
    #   daz/dz = (m_x D - P_x dD/dz) / (D^2 sqrt(1 - sin_az^2))
    #   dmu/dz = (M dN/dz - N dM/dz) / (M^2 + N^2),  N = b D cos(az), M = D^2 - (b/2)^2
    d_distance = float(point @ ray) / distance
    d_azimuth = (ray[0] * distance - point[0] * d_distance) / (
        distance * distance * np.sqrt(1.0 - sin_az * sin_az)
    )
    d_numer = rig.baseline * (cos_az * d_distance - distance * np.sin(azimuth) * d_azimuth)
    d_denom = 2.0 * distance * d_distance
    jac = (denom * d_numer - numer * d_denom) / (denom * denom + numer * numer)

    return FixationProposal(
        fixation=Fixation(azimuth, elevation, vergence),
        vergence_variance=float(jac * jac * variance),
    )
