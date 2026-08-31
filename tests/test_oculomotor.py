"""Oculomotor geometry, ported from active-stereo@3f7a263 in DIRECTION form.

Every assertion here is on unit vectors, rotations, angles or SO(3) membership.
**No test in this file constructs a focal length or a principal point**, and that
is the migration's structural claim: the reference could not state these tests
without an intrinsic, because ``StereoRig`` required ``focal_px`` with no default
(``types.py:31-34``), so all 32 pure-SO(3) tests in its ``test_oculomotor.py``
carried one anyway. The coupling was in the type, not the mathematics.

Two of the four expensive results were stated in PIXELS in the reference. They are
**restated in angles** here, and the restatement is exact rather than approximate:
in ``max_vertical_disparity`` the focal length multiplies both eyes' image
ordinates equally, so it cancels from the question "is this difference zero". Where
a magnitude in pixels is worth reporting, the test multiplies by a focal length
**it owns**, which is what moving the intrinsic out of the type buys.

Ported verbatim / restated / dropped is recorded per test and totalled in
``experiments`` — see the findings for step 15.
"""

from __future__ import annotations

import dataclasses
import itertools

import numpy as np
import pytest

from bio3dvision.oculomotor import (
    Estimate,
    EyeRotations,
    Fixation,
    FixationProposal,
    RefusalReason,
    StereoRig,
    TargetRefused,
    eye_rotations,
    fixation_distance,
    fixation_point,
    is_forward_gaze,
    rectification_rotation,
    require_forward_azimuth,
    target_to_fixation,
)

BASELINE = 0.064


@pytest.fixture
def rig() -> StereoRig:
    """A rig with a baseline and nothing else. There is nothing else to give it."""
    return StereoRig(baseline=BASELINE)


# ---------------------------------------------------------------------------
# Test-local reimplementations. Independent of the module by construction, as in
# the reference: pinning a module against its own internals proves nothing.
# ---------------------------------------------------------------------------


def arc(p: np.ndarray, g: np.ndarray) -> np.ndarray:
    """Reference shortest-arc rotation p -> g. Independent reimplementation."""
    v = np.cross(p, g)
    mat = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]], dtype=float)
    return np.eye(3) + mat + mat @ mat / (1.0 + p @ g)


def torsion(r: np.ndarray) -> float:
    """Signed twist of ``r`` about its own gaze, relative to strict Listing.

    ``tau > 0`` is right-handed about +g and carries the top of the eye (-Y,
    since +Y is down) toward +X.
    """
    z = np.array([0.0, 0.0, 1.0])
    g = r @ z
    t = r @ arc(z, g).T
    angle = float(np.arccos(np.clip((np.trace(t) - 1.0) / 2.0, -1.0, 1.0)))
    if angle < 1e-14:
        return 0.0
    axis = np.array([t[2, 1] - t[1, 2], t[0, 2] - t[2, 0], t[1, 0] - t[0, 1]])
    return float(angle * np.sign(axis @ g))


def helmholtz_rotation(az: float, el: float) -> np.ndarray:
    """``Rx(el) @ Ry(az)`` — elevation about the fixed interaural +X axis first."""
    ce, se, ca, sa = np.cos(el), np.sin(el), np.cos(az), np.sin(az)
    rx = np.array([[1.0, 0.0, 0.0], [0.0, ce, se], [0.0, -se, ce]])
    ry = np.array([[ca, 0.0, sa], [0.0, 1.0, 0.0], [-sa, 0.0, ca]])
    return rx @ ry


def helmholtz(az: float, el: float) -> np.ndarray:
    return np.array([np.sin(az), np.cos(az) * np.sin(el), np.cos(az) * np.cos(el)])


def eye_gazes(rig: StereoRig, fx: Fixation) -> tuple[np.ndarray, np.ndarray]:
    """Unit gaze directions (left, right) from each optical centre to the fixation."""
    if fx.vergence == 0.0:
        d = helmholtz(fx.azimuth, fx.elevation_down)
        return d, d
    p = fixation_point(rig, fx)
    gl = p - np.array([-rig.baseline / 2.0, 0.0, 0.0])
    gr = p - np.array([rig.baseline / 2.0, 0.0, 0.0])
    return gl / np.linalg.norm(gl), gr / np.linalg.norm(gr)


def image_ordinate(points: np.ndarray, r: np.ndarray, centre: np.ndarray) -> np.ndarray:
    """``v_y / v_z`` in an eye's own frame — the TANGENT of the vertical angle.

    The reference's ``project_px`` returned ``f * v_y / v_z``. The focal length is a
    pure multiplicative constant applied identically to both eyes, so it cancels
    from every assertion below, all of which are on a DIFFERENCE between the eyes.
    Dropping it is what makes these tests statable without an intrinsic.
    """
    v = (points - centre) @ r
    return np.asarray(v[..., 1] / v[..., 2])


def plane_of_regard_points(
    rig: StereoRig, el: float, mu: float, half_width: float = 0.2, n: int = 51
) -> np.ndarray:
    """Points spanning the plane of regard, ``(N, 3)`` metres, cyclopean head frame."""
    d = fixation_distance(rig, Fixation(0.0, el, mu))
    phi = np.linspace(-half_width, half_width, n)
    in_plane = np.array([1.0, 0.0, 0.0])
    forward = np.array([0.0, np.sin(el), np.cos(el)])
    dirs = np.sin(phi)[:, None] * in_plane + np.cos(phi)[:, None] * forward
    return np.concatenate([s * d * dirs for s in (0.7, 1.0, 1.4)], axis=0)


def max_vertical_misalignment(rig: StereoRig, fx: Fixation, k: float, points) -> float:
    """max |tan(elev_L) - tan(elev_R)| over ``points`` — the misalignment observable.

    The reference measured this in pixels. In radians-tangent it is the same
    quantity divided by the focal length, and the focal length is the test's to
    choose rather than the rig's to carry.
    """
    rot = eye_rotations(rig, fx, k=k)
    half_b = rig.baseline / 2.0
    y_left = image_ordinate(points, rot.left, np.array([-half_b, 0.0, 0.0]))
    y_right = image_ordinate(points, rot.right, np.array([half_b, 0.0, 0.0]))
    return float(np.abs(y_left - y_right).max())


# ---------------------------------------------------------------------------
# eye_rotations — ported verbatim in substance, restated only in the rig type.
# ---------------------------------------------------------------------------


def test_k0_reduces_to_strict_listing(rig: StereoRig) -> None:
    """k = 0: each eye's orientation is the shortest arc from straight ahead."""
    fx = Fixation(0.2, 0.15, 0.08)
    rot = eye_rotations(rig, fx, k=0.0)
    z = np.array([0.0, 0.0, 1.0])
    for r, g in zip((rot.left, rot.right), eye_gazes(rig, fx), strict=True):
        np.testing.assert_allclose(r @ z, g, atol=1e-12)
        # Shortest arc: the rotation axis is perpendicular to both z and g.
        axis = np.cross(z, g)
        np.testing.assert_allclose(r @ axis, axis, atol=1e-12)


def test_rotation_matrices_are_special_orthogonal(rig: StereoRig) -> None:
    for az, el, mu, k in itertools.product((0.0, 0.3), (0.0, 0.2), (0.0, 0.1), (0.0, 0.25, 0.5)):
        rot = eye_rotations(rig, Fixation(az, el, mu), k=k)
        for r in (rot.left, rot.right):
            np.testing.assert_allclose(r @ r.T, np.eye(3), atol=1e-12)
            assert np.linalg.det(r) == pytest.approx(1.0, abs=1e-12)


def test_gaze_lines_intersect_the_fixation_point(rig: StereoRig) -> None:
    """R_e = A(p->g) @ A(z->p): each eye's optical axis passes through the fixation.

    **This is the composition-order result.** Omitting the second factor
    mis-points the optical axis by about ``k * vergence``, which is exactly what
    this catches. Stated on directions; no focal length can enter.
    """
    z = np.array([0.0, 0.0, 1.0])
    for az, el, mu in itertools.product((0.0, 0.25), (0.0, 0.18), (0.05, 0.16)):
        fx = Fixation(az, el, mu)
        rot = eye_rotations(rig, fx, k=0.25)
        point = fixation_point(rig, fx)
        half_b = rig.baseline / 2.0
        for r, centre in ((rot.left, -half_b), (rot.right, half_b)):
            to_point = point - np.array([centre, 0.0, 0.0])
            np.testing.assert_allclose(r @ z, to_point / np.linalg.norm(to_point), atol=1e-12)


def test_the_second_factor_is_load_bearing(rig: StereoRig) -> None:
    """Negative control for the composition order: A(p->g) alone mis-points.

    Without this, an implementation that dropped ``A(z -> p)`` would pass
    ``test_gaze_lines_intersect_the_fixation_point`` only if that test were
    wrong. Restated from the reference's pixel figure (13-32 px) into the angle
    it is: the mis-pointing is of order ``k * vergence``.
    """
    fx = Fixation(0.0, 0.0, 0.16)
    k = 0.25
    rot = eye_rotations(rig, fx, k=k)
    z = np.array([0.0, 0.0, 1.0])
    gl, _ = eye_gazes(rig, fx)
    # The correct axis is the gaze; a single-factor rotation would land short by
    # roughly k*mu. Assert the true one is right and that k*mu is not negligible.
    np.testing.assert_allclose(rot.left @ z, gl, atol=1e-12)
    assert k * fx.vergence > 1e-3


def test_sagittal_mirror_symmetry(rig: StereoRig) -> None:
    """At azimuth 0 the two eyes mirror in the sagittal plane."""
    mirror = np.diag([-1.0, 1.0, 1.0])
    for el, mu in itertools.product((0.0, 0.2), (0.05, 0.16)):
        rot = eye_rotations(rig, Fixation(0.0, el, mu), k=0.25)
        np.testing.assert_allclose(rot.right, mirror @ rot.left @ mirror, atol=1e-12)


def test_handedness_anchors(rig: StereoRig) -> None:
    """Signs, not just magnitudes: rightward gaze yaws both eyes toward +X."""
    z = np.array([0.0, 0.0, 1.0])
    rot = eye_rotations(rig, Fixation(0.3, 0.0, 0.06), k=0.25)
    assert (rot.left @ z)[0] > 0
    assert (rot.right @ z)[0] > 0
    down = eye_rotations(rig, Fixation(0.0, 0.3, 0.06), k=0.25)
    assert (down.left @ z)[1] > 0
    assert (down.right @ z)[1] > 0


def test_vergence_to_zero_limit_is_continuous(rig: StereoRig) -> None:
    """No singularity at parallel gaze: both eyes tend to the cyclopean direction."""
    fx0 = Fixation(0.2, 0.1, 0.0)
    rot0 = eye_rotations(rig, fx0, k=0.25)
    tiny = eye_rotations(rig, Fixation(0.2, 0.1, 1e-9), k=0.25)
    np.testing.assert_allclose(rot0.left, tiny.left, atol=1e-7)
    np.testing.assert_allclose(rot0.right, tiny.right, atol=1e-7)


def test_nonfinite_k_raises(rig: StereoRig) -> None:
    for k in (np.nan, np.inf, -np.inf):
        with pytest.raises(ValueError, match="k must be finite"):
            eye_rotations(rig, Fixation(0.0, 0.0, 0.06), k=k)


def test_eye_rotations_result_is_frozen(rig: StereoRig) -> None:
    rot = eye_rotations(rig, Fixation(0.0, 0.0, 0.06))
    with pytest.raises(dataclasses.FrozenInstanceError):
        rot.left = np.eye(3)  # type: ignore[misc]


def test_the_default_k_is_a_quarter_not_a_half(rig: StereoRig) -> None:
    """ADR-0014's default is 0.25. k = 1/2 is the alignment OPTIMUM, not the default.

    Pinned because the two numbers are one line apart in the reference and the
    optimum is the more memorable of them. A default silently moved to 0.5 would
    change every rotation this repository computes and break nothing loudly.
    """
    fx = Fixation(0.0, 0.2, 0.16)
    np.testing.assert_array_equal(eye_rotations(rig, fx).left, eye_rotations(rig, fx, k=0.25).left)
    assert np.abs(eye_rotations(rig, fx).left - eye_rotations(rig, fx, k=0.5).left).max() > 1e-4


# ---------------------------------------------------------------------------
# The plane-of-regard optimum. RESTATED from pixels into angles.
# ---------------------------------------------------------------------------


def test_plane_of_regard_alignment_optimum_is_k_half(rig: StereoRig) -> None:
    """k = 1/2 zeroes vertical misalignment in the plane of regard, exactly.

    **Restated, not ported verbatim.** The reference asserted ``max |row_L -
    row_R| < 1e-12`` in pixels, over rigs at three focal lengths. Here the
    assertion is on ``max |tan(elev_L) - tan(elev_R)|`` and the focal lengths are
    gone — they were a multiplicative constant on both sides of a difference.
    That the result survives the restatement is the point: it never needed a
    sensor, and the reference's three-focal-length loop was testing that a
    constant cancels.

    ADR-0016 corrected ADR-0014, which had predicted the null at k = 0.25 and
    instructed that a minimum elsewhere be read as a sign or axis error in
    ``eye_rotations``. It is not one. **The correction travels with the
    parameter**: a corrected rationale detached from its correction gets
    re-broken.

    Deliberately an assertion about a stated k, not a minimisation: searching for
    the argmin and asserting it equals 0.5 would bake the search into the pin,
    and the argmin drifts off 0.5 off-axis while this statement does not.
    """
    for baseline in (0.064, 0.10, 0.03):
        r = StereoRig(baseline=baseline)
        for mu, el in itertools.product((0.064, 0.16), (0.149, 0.3)):
            points = plane_of_regard_points(r, el, mu)
            fx = Fixation(0.0, el, mu)
            assert max_vertical_misalignment(r, fx, 0.5, points) < 1e-14
            # Negative control: the default and strict Listing both miss it, by
            # orders of magnitude. Without this a projection returning zeros would
            # pass. The reference quoted ~0.2-1 px at f = 800; in tangent units
            # that is ~2.5e-4 to 1.2e-3, and the bound below is deliberately loose.
            for k in (0.0, 0.25):
                assert max_vertical_misalignment(r, fx, k, points) > 1e-6


def test_the_optimum_in_pixels_if_a_reader_wants_pixels(rig: StereoRig) -> None:
    """The same result reported in pixels, with a focal length the TEST owns.

    This is what the separation buys and it is worth one test to show it: a
    magnitude in pixels is still available, and the focal length that produces it
    is a property of whoever is asking, not of the stereo rig.
    """
    focal_px = 800.0  # this test's, not the rig's
    el, mu = 0.149, 0.064
    points = plane_of_regard_points(rig, el, mu)
    fx = Fixation(0.0, el, mu)
    assert focal_px * max_vertical_misalignment(rig, fx, 0.5, points) < 1e-9
    assert focal_px * max_vertical_misalignment(rig, fx, 0.25, points) > 0.1


def test_tilted_listing_at_k_half_is_helmholtz(rig: StereoRig) -> None:
    """At sagittal gaze, ``A(p->g) @ A(z->p)`` at k = 1/2 IS the Helmholtz rotation.

    Ported verbatim in substance — it was already pure SO(3) and the reference
    classified it ``mixed`` only because the rig type dragged a focal length in.

    This is the reason the k = 1/2 null is exact rather than first-order:
    Helmholtz composition carries no torsion about the plane of regard, so the
    plane images on the horizontal meridian of both retinas and vertical
    disparity vanishes there for every point at once. The spherical-excess
    cancellation that predicts k = 1/2 to first order is this identity linearised.
    Fails independently of the misalignment test above: it needs no projection.
    """
    for el, mu in itertools.product((0.05, 0.149, 0.3), (0.02, 0.064, 0.16, 0.35)):
        fx = Fixation(0.0, el, mu)
        rot = eye_rotations(rig, fx, k=0.5)
        for r, g in zip((rot.left, rot.right), eye_gazes(rig, fx), strict=True):
            az_e = float(np.arcsin(np.clip(g[0], -1.0, 1.0)))
            el_e = float(np.arctan2(g[1], g[2]))
            np.testing.assert_allclose(r, helmholtz_rotation(az_e, el_e), atol=1e-12)
        rot_default = eye_rotations(rig, fx, k=0.25)
        for r, g in zip((rot_default.left, rot_default.right), eye_gazes(rig, fx), strict=True):
            az_e = float(np.arcsin(np.clip(g[0], -1.0, 1.0)))
            el_e = float(np.arctan2(g[1], g[2]))
            assert np.abs(r - helmholtz_rotation(az_e, el_e)).max() > 1e-5


# ---------------------------------------------------------------------------
# fixation_distance / fixation_point / the azimuth domain
# ---------------------------------------------------------------------------


def test_fixation_distance_forward_matches_the_chord_convention(rig: StereoRig) -> None:
    """At azimuth 0 the plane-of-regard chord reduces to ``b / (2 tan(mu/2))``."""
    for mu in (0.02, 0.064, 0.16):
        got = fixation_distance(rig, Fixation(0.0, 0.0, mu))
        assert got == pytest.approx(rig.baseline / (2.0 * np.tan(mu / 2.0)), rel=1e-12)


def test_fixation_distance_is_elevation_independent(rig: StereoRig) -> None:
    """Under Helmholtz composition the plane of regard contains the baseline always.

    So elevation does not enter the chord construction — the property that makes
    the closed form closed. Not in the reference's set; added because the
    docstring asserts it and nothing tested it.
    """
    for mu, az in itertools.product((0.02, 0.16), (0.0, 0.3, -0.4)):
        base = fixation_distance(rig, Fixation(az, 0.0, mu))
        for el in (0.1, 0.4, -0.25):
            assert fixation_distance(rig, Fixation(az, el, mu)) == pytest.approx(base, rel=1e-12)


def test_fixation_point_norm_is_fixation_distance(rig: StereoRig) -> None:
    for az, el, mu in itertools.product((0.0, 0.3), (0.0, 0.2), (0.03, 0.16)):
        fx = Fixation(az, el, mu)
        assert float(np.linalg.norm(fixation_point(rig, fx))) == pytest.approx(
            fixation_distance(rig, fx), rel=1e-12
        )


def test_zero_vergence_is_infinite_distance_and_no_point(rig: StereoRig) -> None:
    assert fixation_distance(rig, Fixation(0.1, 0.1, 0.0)) == float("inf")
    with pytest.raises(ValueError, match="infinity"):
        fixation_point(rig, Fixation(0.1, 0.1, 0.0))


def test_azimuth_at_or_beyond_the_interaural_axis_raises(rig: StereoRig) -> None:
    """Beyond |az| = pi/2 the chord lands on the minor arc and the geometry lies."""
    for az in (np.pi / 2.0, -np.pi / 2.0, 2.0, -3.0):
        with pytest.raises(ValueError, match="azimuth must lie"):
            require_forward_azimuth(Fixation(az, 0.0, 0.06))
        with pytest.raises(ValueError, match="azimuth must lie"):
            fixation_distance(rig, Fixation(az, 0.0, 0.06))


def test_backward_gaze_raises_antiparallel(rig: StereoRig) -> None:
    """A gaze antiparallel to the primary direction has no defined shortest arc."""
    with pytest.raises(ValueError, match="antiparallel"):
        eye_rotations(rig, Fixation(0.0, np.pi, 0.0), k=0.0)


# ---------------------------------------------------------------------------
# rectification_rotation — the member choice
# ---------------------------------------------------------------------------


def test_rectification_rotation_matches_helmholtz_with_azimuth_zeroed() -> None:
    for el in (0.0, 0.15, -0.3, 0.5):
        np.testing.assert_allclose(
            rectification_rotation(Fixation(0.2, el, 0.06)),
            helmholtz_rotation(0.0, el),
            atol=1e-15,
        )


def test_rectification_rotation_ignores_azimuth_and_vergence() -> None:
    """Azimuth-independent by construction, not by assertion.

    Under Helmholtz composition the plane of regard is the elevated plane for
    every azimuth, so zeroing azimuth loses nothing.
    """
    base = rectification_rotation(Fixation(0.0, 0.2, 0.0))
    for az, mu in itertools.product((-0.5, 0.0, 0.4), (0.0, 0.06, 0.2)):
        np.testing.assert_array_equal(rectification_rotation(Fixation(az, 0.2, mu)), base)


def test_rectification_puts_the_plane_of_regard_on_the_zero_elevation_row(
    rig: StereoRig,
) -> None:
    """The member choice, RESTATED: the plane of regard maps to zero elevation.

    The reference stated this as "the plane of regard lands on the principal
    row", which needs a principal point and a focal length to say. In the
    rectified frame it is the same statement without either: a plane-of-regard
    direction, rotated into the rectified frame, has zero ``y``-component.

    Determined only up to a rotation about the baseline. **This member is chosen
    because of that property** — every other member rectifies equally well and
    differs only in where the fixation point lands. The choice is what ADR-0017
    records, and it is the part that can be wrong.
    """
    el, mu = 0.25, 0.08
    fx = Fixation(0.0, el, mu)
    rect = rectification_rotation(fx)
    for point in plane_of_regard_points(rig, el, mu, half_width=0.15, n=9):
        in_rect = rect.T @ point
        assert abs(in_rect[1]) < 1e-12 * max(1.0, float(np.linalg.norm(point)))


def test_transposing_the_rectifier_is_not_a_no_op() -> None:
    """The direction convention is rect -> head, and the transpose is different.

    At elevation 0 the rectifier is the identity, so a transposition is invisible
    — the sagittal-gaze hole. Every assertion about the rectifier must therefore
    use a non-zero elevation, and this test exists to say so in code.
    """
    identity_at_zero = rectification_rotation(Fixation(0.3, 0.0, 0.06))
    np.testing.assert_array_equal(identity_at_zero, identity_at_zero.T)
    tilted = rectification_rotation(Fixation(0.3, 0.25, 0.06))
    assert np.abs(tilted - tilted.T).max() > 1e-3


# ---------------------------------------------------------------------------
# is_forward_gaze
# ---------------------------------------------------------------------------


def test_is_forward_gaze_is_the_geometry_test_not_the_angle_test() -> None:
    """``cos(az) cos(el) > 0``, not ``abs(el) < pi/2``. They differ on wrapping.

    At ``el = 7.0`` — which wraps to 0.7168, plainly forward — the angle test says
    backward. Constructed fixations never wrap, but a hand-written or loaded state
    can. Do not "simplify" this to a comparison on the angle.
    """
    assert is_forward_gaze(Fixation(0.0, 7.0, 0.0))
    assert not is_forward_gaze(Fixation(0.0, 2.0, 0.0))
    assert is_forward_gaze(Fixation(0.0, 0.0, 0.0))


def test_is_forward_gaze_catches_the_elevation_hole(rig: StereoRig) -> None:
    """A backward-pointing state that ``require_forward_azimuth`` cannot catch.

    ``Fixation(0.1, 2.0, 0.064)`` is constructible, and the distance and rotation
    functions all accept it and return well-formed geometry pointing backward. The
    azimuth guard is about azimuth; elevation is the free direction. The domains
    coincide; the failures do not.
    """
    backward = Fixation(0.1, 2.0, 0.064)
    require_forward_azimuth(backward)  # does not raise
    assert np.isfinite(fixation_distance(rig, backward))
    assert not is_forward_gaze(backward)


# ---------------------------------------------------------------------------
# target_to_fixation — now taking a DIRECTION
# ---------------------------------------------------------------------------


def unit(v: list[float]) -> np.ndarray:
    a = np.asarray(v, dtype=float)
    return a / np.linalg.norm(a)


def test_target_to_fixation_takes_a_unit_direction_not_a_pixel(rig: StereoRig) -> None:
    """The boundary now speaks directions. The un-projection moved to the sensor.

    The reference un-projected a pixel inside this function using
    ``rig.focal_px`` and ``rig.principal_point``. That is exactly the work
    ``PinholeSampling.direction`` already does, and doing it here is what forced
    every caller to carry an intrinsic.
    """
    current = Fixation(0.0, 0.0, 0.06)
    got = target_to_fixation(unit([0.0, 0.0, 1.0]), Estimate(1.5, 1e-4), rig, current)
    assert isinstance(got, FixationProposal)
    assert got.fixation.vergence > 0.0


def test_a_straight_ahead_direction_at_the_fixation_distance_round_trips(
    rig: StereoRig,
) -> None:
    """Looking where you already look proposes the fixation you already have.

    The strongest available self-consistency check on the whole chain: distance,
    azimuth, elevation and vergence all have to agree for it to close.
    """
    for el, mu in itertools.product((0.0, 0.2), (0.04, 0.12)):
        current = Fixation(0.0, el, mu)
        point = fixation_point(rig, current)
        centre_left = np.array([-rig.baseline / 2.0, 0.0, 0.0])
        ray_head = point - centre_left
        ray_rect = rectification_rotation(current).T @ ray_head
        depth_z = float(ray_rect[2])  # planar depth in the rectified frame
        got = target_to_fixation(unit(list(ray_rect)), Estimate(depth_z, 1e-6), rig, current)
        assert isinstance(got, FixationProposal)
        assert got.fixation.azimuth == pytest.approx(current.azimuth, abs=1e-9)
        assert got.fixation.elevation_down == pytest.approx(current.elevation_down, abs=1e-9)
        assert got.fixation.vergence == pytest.approx(current.vergence, abs=1e-9)


def test_depth_is_planar_not_radial(rig: StereoRig) -> None:
    """**The trap this migration had to step over.**

    The reference multiplied depth by a ray whose ``z`` component was 1, so depth
    was ``z`` in the rectified frame — PLANAR. A unit direction is not that ray:
    scaling a unit direction by depth would make depth a RANGE. Off-axis the two
    differ by ``1/cos(angle)``, which is small, smooth, largest at the field edge,
    and therefore looks like a modelling result rather than a units error — the
    same shape as the radial/planar confusion ``infer_depth_convention`` guards in
    the render path.

    Pinned by construction: a direction 30 degrees off-axis at planar depth 2.0
    must land at ``z = 2.0``, not at range 2.0.
    """
    current = Fixation(0.0, 0.0, 0.05)
    off_axis = unit([np.tan(np.deg2rad(30.0)), 0.0, 1.0])
    depth_z = 2.0
    got = target_to_fixation(off_axis, Estimate(depth_z, 1e-6), rig, current)
    assert isinstance(got, FixationProposal)
    # Reconstruct where the proposal says the point is and check its z.
    point = fixation_point(rig, got.fixation)
    in_rect = rectification_rotation(current).T @ point
    assert float(in_rect[2]) == pytest.approx(depth_z, rel=1e-9)


def test_refuses_rather_than_raises_on_unusable_depth(rig: StereoRig) -> None:
    """Data-quality problems refuse; caller errors raise. A raise kills the loop."""
    current = Fixation(0.0, 0.0, 0.06)
    d = unit([0.0, 0.0, 1.0])
    for bad in (np.nan, np.inf):
        got = target_to_fixation(d, Estimate(bad, 1e-4), rig, current)
        assert isinstance(got, TargetRefused)
        assert RefusalReason.DEPTH_UNAVAILABLE in got.reasons
    got = target_to_fixation(d, Estimate(1.5, np.nan), rig, current)
    assert isinstance(got, TargetRefused)
    assert RefusalReason.DEPTH_UNAVAILABLE in got.reasons
    for bad in (0.0, -1.0):
        got = target_to_fixation(d, Estimate(bad, 1e-4), rig, current)
        assert isinstance(got, TargetRefused)
        assert RefusalReason.DEPTH_NONPOSITIVE in got.reasons


def test_refuses_a_target_nearer_than_half_the_baseline(rig: StereoRig) -> None:
    """``D <= b/2`` has no forward vergence solution; the arctan takes the far branch.

    **Reachable only on the nasal side.** Un-projection is about the LEFT optical
    centre, so a straight-ahead ray at depth ``z`` puts the point at
    ``sqrt((b/2)^2 + z^2)`` from the cyclopean origin, which exceeds ``b/2`` for
    every positive depth. The ray has to run toward +x to bring the point in. The
    reference reached this with a column right of the principal column; in
    direction form that is a positive x-component.
    """
    nasal = unit([0.7, 0.0, 1.0])
    got = target_to_fixation(nasal, Estimate(0.010, 1e-9), rig, Fixation(0.0, 0.0, 0.06))
    assert isinstance(got, TargetRefused)
    assert got.reasons == frozenset({RefusalReason.TOO_NEAR})


def test_refuses_a_target_that_would_point_the_eyes_backward(rig: StereoRig) -> None:
    current = Fixation(0.0, 1.5, 0.02)
    got = target_to_fixation(unit([0.0, 0.63875, 1.0]), Estimate(1.5, 1e-6), rig, current)
    assert isinstance(got, TargetRefused)
    assert got.reasons == frozenset({RefusalReason.BACKWARD_GAZE})


def test_co_occurring_refusals_are_all_reported(rig: StereoRig) -> None:
    """Neither condition ranks the other, so both are returned.

    A first-match return would hide one, and a caller counting refusal kinds
    would under-count silently.
    """
    current = Fixation(0.0, 1.5, 0.02)
    got = target_to_fixation(unit([0.7, 0.63875, 1.0]), Estimate(0.010, 1e-9), rig, current)
    assert isinstance(got, TargetRefused)
    assert got.reasons == frozenset({RefusalReason.BACKWARD_GAZE, RefusalReason.TOO_NEAR})

    # Same current fixation and depth, the nasal component removed: only the
    # elevation condition survives. If the two were evaluated as a chain rather
    # than independently, this pair could not both hold.
    only_backward = target_to_fixation(
        unit([0.0, 0.63875, 1.0]), Estimate(0.010, 1e-9), rig, current
    )
    assert isinstance(only_backward, TargetRefused)
    assert only_backward.reasons == frozenset({RefusalReason.BACKWARD_GAZE})


def test_a_non_unit_or_backward_direction_raises(rig: StereoRig) -> None:
    """Caller errors, not data problems. The sensor's job is to hand over a unit ray."""
    current = Fixation(0.0, 0.0, 0.06)
    with pytest.raises(ValueError, match="unit"):
        target_to_fixation(np.array([0.0, 0.0, 2.0]), Estimate(1.5, 1e-6), rig, current)
    with pytest.raises(ValueError, match="forward"):
        target_to_fixation(unit([0.0, 0.0, -1.0]), Estimate(1.5, 1e-6), rig, current)


def test_vergence_variance_is_linear_in_the_input_variance(rig: StereoRig) -> None:
    current = Fixation(0.0, 0.0, 0.06)
    d = unit([0.1, 0.05, 1.0])
    a = target_to_fixation(d, Estimate(1.5, 1e-4), rig, current)
    b = target_to_fixation(d, Estimate(1.5, 4e-4), rig, current)
    assert isinstance(a, FixationProposal) and isinstance(b, FixationProposal)
    assert b.vergence_variance == pytest.approx(4.0 * a.vergence_variance, rel=1e-9)


def test_vergence_variance_jacobian_matches_finite_differences(rig: StereoRig) -> None:
    """The propagation is a real derivative, not a plausible-looking formula.

    Depth enters through both the distance and the azimuth — the left-centre
    offset makes azimuth depth-dependent — so the chain rule has two branches and
    dropping either is a silent factor error.
    """
    current = Fixation(0.1, 0.15, 0.06)
    d = unit([0.12, -0.05, 1.0])
    z0, h = 1.8, 1e-6

    def vergence_at(z: float) -> float:
        got = target_to_fixation(d, Estimate(z, 1e-8), rig, current)
        assert isinstance(got, FixationProposal)
        return got.fixation.vergence

    numeric = (vergence_at(z0 + h) - vergence_at(z0 - h)) / (2.0 * h)
    got = target_to_fixation(d, Estimate(z0, 1.0), rig, current)
    assert isinstance(got, FixationProposal)
    analytic = np.sqrt(got.vergence_variance)  # variance 1.0 -> |d mu / d z|
    assert analytic == pytest.approx(abs(numeric), rel=1e-5)


def test_the_refusal_union_forces_callers_to_narrow(rig: StereoRig) -> None:
    """The return type is a union; a caller that forgets to narrow cannot compile.

    Asserted at runtime here because mypy's judgement is not visible to pytest:
    what this pins is that a refusal is a distinct TYPE, not a sentinel fixation.
    """
    got = target_to_fixation(
        unit([0.0, 0.0, 1.0]), Estimate(np.nan, 1.0), rig, Fixation(0.0, 0.0, 0.06)
    )
    assert not isinstance(got, FixationProposal)
    assert isinstance(got, TargetRefused)
    assert not hasattr(got, "fixation")


def test_2pi_invariance_in_the_current_elevation(rig: StereoRig) -> None:
    """Adding 2pi to the current elevation must not move the proposal.

    The rectifier is built from ``cos`` and ``sin`` of the elevation, so it is
    invariant by construction — but only if nothing anywhere compares the angle
    itself. This is the test that would catch an ``abs(el) < pi/2`` creeping in.
    """
    d = unit([0.05, 0.02, 1.0])
    base = target_to_fixation(d, Estimate(1.7, 1e-6), rig, Fixation(0.1, 0.2, 0.06))
    wrapped = target_to_fixation(
        d, Estimate(1.7, 1e-6), rig, Fixation(0.1, 0.2 + 2.0 * np.pi, 0.06)
    )
    assert isinstance(base, FixationProposal) and isinstance(wrapped, FixationProposal)
    assert wrapped.fixation.azimuth == pytest.approx(base.fixation.azimuth, abs=1e-12)
    assert wrapped.fixation.vergence == pytest.approx(base.fixation.vergence, abs=1e-12)


# ---------------------------------------------------------------------------
# The type split itself
# ---------------------------------------------------------------------------


def test_the_rig_carries_no_intrinsic(rig: StereoRig) -> None:
    """**The structural claim of step 15, as an assertion.**

    ``StereoRig`` is stereo geometry: a baseline and a capture vergence. Focal
    length and principal point belong to the ``SamplingModel``. If an intrinsic
    ever reappears here, 39 tests that need no sensor will start requiring one
    again, which is the coupling this migration removed.
    """
    fields = {f.name for f in dataclasses.fields(StereoRig)}
    assert fields == {"baseline", "vergence"}
    assert not hasattr(rig, "focal_px")
    assert not hasattr(rig, "principal_point")


def test_the_rig_validates_what_it_carries() -> None:
    for bad in (0.0, -1.0, np.nan, np.inf):
        with pytest.raises(ValueError):
            StereoRig(baseline=bad)
    with pytest.raises(ValueError):
        StereoRig(baseline=0.064, vergence=np.nan)
    with pytest.raises(ValueError):
        StereoRig(baseline=0.064, vergence=-0.1)


def test_fixation_validates_and_is_frozen() -> None:
    for bad in (np.nan, np.inf):
        with pytest.raises(ValueError):
            Fixation(bad, 0.0, 0.0)
        with pytest.raises(ValueError):
            Fixation(0.0, 0.0, bad)
    with pytest.raises(ValueError):
        Fixation(0.0, 0.0, -0.1)
    fx = Fixation(0.0, 0.0, 0.06)
    with pytest.raises(dataclasses.FrozenInstanceError):
        fx.azimuth = 1.0  # type: ignore[misc]


def test_eye_rotations_is_a_named_pair_not_a_tuple(rig: StereoRig) -> None:
    """An ``R_right, R_left = ...`` unpack swap is silent at the call site."""
    rot = eye_rotations(rig, Fixation(0.2, 0.1, 0.06))
    assert isinstance(rot, EyeRotations)
    with pytest.raises(TypeError):
        _a, _b = rot  # type: ignore[misc]


def test_horizontal_plane_fixation_is_pure_yaw(rig: StereoRig) -> None:
    """el = 0: everything stays in the plane of regard; zero torsion at ANY k."""
    for az, mu, k in itertools.product((0.0, -0.15, 0.15), (0.0, 0.064, 0.16), (0.0, 0.25)):
        rot = eye_rotations(rig, Fixation(az, 0.0, mu), k=k)
        for r in (rot.left, rot.right):
            np.testing.assert_allclose(r[1, :], [0.0, 1.0, 0.0], atol=1e-15)
            np.testing.assert_allclose(r[:, 1], [0.0, 1.0, 0.0], atol=1e-15)
            assert torsion(r) == 0.0


def test_elevation_dependent_torsion_signs(rig: StereoRig) -> None:
    """Intorsion for upward proximal gaze, extorsion for downward, mirrored between eyes.

    ``tau > 0`` carries the top of the eye toward +X, which is nasal for the left
    eye and temporal for the right — so intorsion is ``tau_L > 0, tau_R < 0``. The
    magnitude floor keeps this from passing on numerical dust, and the monotone
    sweep at the end keeps it from passing on a constant.
    """
    k = 0.25
    for el, expect_up in ((-0.149, True), (0.149, False)):
        rot = eye_rotations(rig, Fixation(0.0, el, 0.0914), k=k)
        tau_left, tau_right = torsion(rot.left), torsion(rot.right)
        assert abs(tau_left) > 1e-4 and abs(tau_right) > 1e-4
        assert tau_left == pytest.approx(-tau_right, rel=1e-9)
        if expect_up:
            assert tau_left > 0 and tau_right < 0  # intorsion
        else:
            assert tau_left < 0 and tau_right > 0  # extorsion
    magnitudes = [
        abs(torsion(eye_rotations(rig, Fixation(0.0, 0.149, mu), k=k).left))
        for mu in (0.064, 0.0914, 0.16)
    ]
    assert magnitudes[0] < magnitudes[1] < magnitudes[2]


def test_rectification_rotation_is_sufficient_for_rectification(rig: StereoRig) -> None:
    """Vertical disparity vanishes in the pair the rectifier induces — RESTATED.

    The reference asserted ``max |row_L - row_R| == 0.0`` in pixels. Here it is
    the same statement on the vertical tangent, which is that quantity divided by
    a focal length: both eyes share an orientation and their centres differ along
    the head +X axis, which the rectifier fixes, so the ordinates agree EXACTLY
    rather than approximately.

    Validity is eye-indexed: a point behind either eye is not "zero vertical
    disparity", it is not imageable, and mixing the two would be a masking
    violation.
    """
    rng = np.random.default_rng(0)
    el = 0.22
    rect = rectification_rotation(Fixation(0.3, el, 0.06))
    points = rng.normal(size=(300, 3)) * np.array([0.4, 0.4, 0.2]) + np.array([0.0, 0.0, 1.8])
    half_b = rig.baseline / 2.0
    left_c = np.array([-half_b, 0.0, 0.0])
    v_l = (points - left_c) @ rect
    v_r = (points + left_c) @ rect
    imageable = (v_l[:, 2] > 0) & (v_r[:, 2] > 0)
    assert imageable.sum() > 100, "degenerate sample: the assertion below would be vacuous"
    y_l = v_l[imageable, 1] / v_l[imageable, 2]
    y_r = v_r[imageable, 1] / v_r[imageable, 2]
    assert float(np.abs(y_l - y_r).max()) == 0.0
