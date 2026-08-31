"""The head-frame belief: the fixed-eye control, and the test that outcome 4 fails.

**The control.** With the eyes held fixed, the head-frame belief must produce
results bit-identical to the image-frame belief — ``np.array_equal`` on mean, var
and valid. Without it a reprojection error is invisible: it would surface later as
a slightly worse closed loop, which is indistinguishable from "closing the loop
does not help". That is the exact ambiguity that made exp003 hard to read.

**The trap.** The control is satisfiable by doing nothing. A head frame that is
the image frame by construction passes it and is worthless. So a second class of
test applies a rotation the experiments never apply, and checks the reprojection
against ground truth — that is what separates a representation change from a
rename.
"""

from __future__ import annotations

import numpy as np
import pytest

from bio3dvision.belief import HEAD_FRAME, HeadFrameBelief
from bio3dvision.fixture import make_synthetic_scene
from bio3dvision.loop import ActiveStereo
from bio3dvision.oculomotor import Fixation, StereoRig, eye_rotations
from bio3dvision.policy import POLICIES
from bio3dvision.sampling import PinholeSampling

ARMS = ("A", "A_prime", "D", "E")
STEPS = 8
REFERENCE = Fixation(0.0, 0.0, 0.0)


def _setup(seed: int = 0):
    left, right, gt, params = make_synthetic_scene(seed=seed)
    engine = ActiveStereo(left, right, params, matcher="block")
    sampling = PinholeSampling(
        shape=(int(params["H"]), int(params["W"])), focal_px=float(params["f_px"])
    )
    rig = StereoRig(baseline=float(params["baseline"]))
    return engine, sampling, gt, params, rig


# ---------------------------------------------------------------------------
# The fixed-eye control.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("arm", ARMS)
def test_the_head_frame_belief_is_bit_identical_with_the_eyes_fixed(arm: str) -> None:
    """The control, across arms and seeds. ``array_equal``, never ``allclose``.

    Both beliefs receive the same measurement and the same precision field at
    every step; the only difference is that one fuses in image coordinates and
    the other reprojects into the head frame first. At the reference fixation the
    reprojection is the identity map, so the two must agree exactly.

    A tolerance here would let a real reprojection defect hide, which is the
    failure this whole iteration is arranged to prevent.
    """
    for seed in (0, 3):
        engine, sampling, _gt, _params, rig = _setup(seed)
        belief = HeadFrameBelief.from_sampling(sampling, REFERENCE, rig)
        policy = POLICIES[arm]
        for _ in range(STEPS):
            choice = policy(engine, engine.scanpath)
            if choice is None:
                break
            measurement, precision, _d_fix = engine.measurement(*choice)
            belief.fuse(measurement, precision, REFERENCE, sampling)
            engine.step(fixation=choice)
        assert np.array_equal(engine.mean, belief.mean), f"{arm} seed {seed}: mean differs"
        assert np.array_equal(engine.var, belief.var), f"{arm} seed {seed}: var differs"


def test_the_control_covers_valid_as_well() -> None:
    """``valid`` is a property of the front end and reprojects with everything else."""
    engine, sampling, _gt, _params, rig = _setup()
    belief = HeadFrameBelief.from_sampling(sampling, REFERENCE, rig)
    gathered = belief.gather(engine.valid.astype(np.float32), REFERENCE, sampling, fill=0.0)
    assert np.array_equal(gathered.astype(bool), engine.valid)


def test_reprojection_at_the_reference_fixation_is_the_identity_map() -> None:
    """Structural, not numerical: every cell resolves to the index it came from.

    This is *why* the control is bit-exact, and it is asserted separately so that
    a future change breaking the identity is diagnosed here rather than as an
    unexplained divergence in the control above.
    """
    _engine, sampling, _gt, _params, rig = _setup()
    belief = HeadFrameBelief.from_sampling(sampling, REFERENCE, rig)
    index, visible = belief.reproject(REFERENCE, sampling)
    height, width = sampling.shape
    rows, cols = np.mgrid[0:height, 0:width]
    assert visible.all()
    assert np.array_equal(index[..., 0], rows)
    assert np.array_equal(index[..., 1], cols)


# ---------------------------------------------------------------------------
# Falsifier 4: the tests a do-nothing head frame would fail.
# ---------------------------------------------------------------------------


def test_the_head_frame_is_not_the_image_frame_by_construction() -> None:
    """Under a rotation the cells and the samples genuinely part company.

    **This is the test outcome 4 would fail.** If the head frame were the image
    frame, a rotation would move nothing and the reprojection would be the
    identity at every fixation. It is not: at 8.6 degrees of elevation the
    majority of cells resolve to a different index than they came from.
    """
    _engine, sampling, _gt, _params, rig = _setup()
    belief = HeadFrameBelief.from_sampling(sampling, Fixation(0.0, 0.20, 0.06), rig)
    rotated = Fixation(0.0, 0.35, 0.06)
    at_ref, _ = belief.reproject(belief.origin_fixation, sampling)
    at_rot, _ = belief.reproject(rotated, sampling)
    moved = np.any(at_ref != at_rot, axis=-1)
    assert moved.mean() > 0.5, (
        f"only {moved.mean():.3f} of cells moved under a 8.6 degree rotation; "
        "the head frame is behaving like the image frame"
    )


def test_a_synthetic_rotation_reprojects_a_known_scene_correctly() -> None:
    """Reprojection checked against ground truth, on a rotation no experiment applies.

    Construct a field that is a known function OF THE HEAD-FRAME DIRECTION — here
    the direction's own ``y`` component, which is a property of the cell and not
    of the image — evaluate it in the image frame at a rotated fixation, gather it
    back, and require the head grid to recover the function it started from.

    A do-nothing reprojection fails this: it would return the rotated field
    unshifted, which disagrees with the direction-defined truth everywhere the
    rotation moved a sample.
    """
    _engine, sampling, _gt, params, rig = _setup()
    reference = Fixation(0.0, 0.20, 0.06)
    rotated = Fixation(0.0, 0.35, 0.06)
    belief = HeadFrameBelief.from_sampling(sampling, reference, rig)

    # Truth, defined on head-frame directions: each cell's own y-component.
    truth = belief.directions[..., 1].astype(np.float32)

    # The same function evaluated in the rotated image frame: the image sample's
    # direction carried into the head frame by the ROTATED fixation's rotation.
    height, width = sampling.shape
    rows, cols = np.mgrid[0:height, 0:width]
    idx = np.stack([rows, cols], axis=-1).astype(np.float64)
    rot = np.asarray(eye_rotations(rig, rotated).left)
    field = (sampling.direction(idx) @ rot.T)[..., 1].astype(np.float32)

    recovered = belief.gather(field, rotated, sampling, fill=np.nan)
    seen = np.isfinite(recovered)
    # About half the grid leaves the sensor, and that is arithmetic rather than a
    # defect: the vertical field is 240/700 = 0.34 rad = 19.6 degrees and the
    # rotation is 8.6 degrees, so a large fraction must fall off. 42 000 cells
    # remain, which is what the assertion below rests on.
    assert seen.mean() > 0.5, "too few cells visible for the assertion to mean anything"

    err = np.abs(recovered[seen] - truth[seen])
    # Nearest-neighbour, so the residual is angular quantisation: one cell subtends
    # ~1/f_px radians and the y-component changes by about that much across it.
    cell_rad = 1.0 / float(params["f_px"])
    assert float(err.max()) < 2.0 * cell_rad, (
        f"max reprojection error {float(err.max()):.2e} exceeds two cells "
        f"of quantisation ({2.0 * cell_rad:.2e})"
    )

    # The control that gives the number meaning: NOT reprojecting is much worse.
    naive = np.abs(field[seen] - truth[seen])
    assert float(naive.max()) > 10.0 * float(err.max()), (
        "reprojecting is not measurably better than not reprojecting; the operator is doing nothing"
    )


def test_an_azimuth_saccade_moves_the_mapping_and_preserves_world_direction() -> None:
    """**The test 17a did not have, and the reason this iteration exists.**

    17a had a test that changed azimuth and asserted that NOTHING moved. It
    passed, and it was asserting the defect: the frame was tied to
    ``rectification_rotation``, which zeroes azimuth, so across a 17 degree
    saccade the mapping moved zero cells while the world direction each cell
    actually views moved the full 17 degrees. The same cell then received
    measurements of unrelated directions and fused them.

    Two clauses, and both are needed:

    * the mapping MUST move — a do-nothing reprojection fails this, which is
      exactly what 17a's construction would do;
    * each cell must keep viewing the SAME WORLD DIRECTION — a wrong
      reprojection fails this, and it is checked through ``eye_rotations``
      rather than through the operator under test, because checking an operator
      against itself proves nothing.
    """
    _engine, sampling, _gt, params, rig = _setup()
    anchor = Fixation(0.0, 0.0, 0.06)
    saccade = Fixation(np.radians(17.0), 0.0, 0.06)
    belief = HeadFrameBelief.from_sampling(sampling, anchor, rig)

    at_anchor, visible_anchor = belief.reproject(anchor, sampling)
    at_saccade, visible_saccade = belief.reproject(saccade, sampling)

    # Clause 1: it must move.
    moved = np.any(at_anchor != at_saccade, axis=-1)
    assert moved.all(), f"only {moved.mean():.3f} of cells moved across a 17 deg azimuth saccade"

    # Clause 2: and it must move to the RIGHT place. Computed independently.
    both = visible_anchor & visible_saccade
    assert both.sum() > 10_000, "too few cells visible in both views to mean anything"
    before = belief.world_direction(at_anchor, anchor, sampling)
    after = belief.world_direction(at_saccade, saccade, sampling)
    drift = np.degrees(np.arccos(np.clip((before * after).sum(axis=-1), -1.0, 1.0)))
    # One cell subtends 1/f_px rad = 0.082 deg here, and the gather is
    # nearest-neighbour, so the residual is quantisation and must stay under it.
    cell_deg = float(np.degrees(1.0 / float(params["f_px"])))
    assert float(drift[both].max()) < cell_deg, (
        f"world direction drifts {drift[both].max():.4f} deg, "
        f"more than one cell ({cell_deg:.4f} deg)"
    )


def test_an_elevation_saccade_also_preserves_world_direction() -> None:
    """The axis 17a did exercise, re-checked under the corrected operator.

    17a's elevation test only required that cells MOVE. It never checked that
    they moved to the right place, which is the clause that would have caught the
    azimuth fault had it been applied there.
    """
    _engine, sampling, _gt, params, rig = _setup()
    anchor = Fixation(0.0, 0.10, 0.06)
    saccade = Fixation(0.0, 0.10 + np.radians(8.0), 0.06)
    belief = HeadFrameBelief.from_sampling(sampling, anchor, rig)
    a_i, a_v = belief.reproject(anchor, sampling)
    b_i, b_v = belief.reproject(saccade, sampling)
    assert np.any(a_i != b_i, axis=-1).all()
    both = a_v & b_v
    drift = np.degrees(
        np.arccos(
            np.clip(
                (
                    belief.world_direction(a_i, anchor, sampling)
                    * belief.world_direction(b_i, saccade, sampling)
                ).sum(axis=-1),
                -1.0,
                1.0,
            )
        )
    )
    assert float(drift[both].max()) < float(np.degrees(1.0 / float(params["f_px"])))


def test_vergence_alone_moves_the_mapping() -> None:
    """The third component the rectifier discarded, and the one nothing tested.

    ``rectification_rotation`` zeroes vergence as well as azimuth. A vergence
    change with gaze held fixed rotates each eye — that is what vergence IS — so
    it must reproject. Under 17a's construction it did not.
    """
    _engine, sampling, _gt, _params, rig = _setup()
    anchor = Fixation(0.1, 0.05, 0.03)
    converged = Fixation(0.1, 0.05, 0.16)
    belief = HeadFrameBelief.from_sampling(sampling, anchor, rig)
    a_i, _ = belief.reproject(anchor, sampling)
    b_i, _ = belief.reproject(converged, sampling)
    moved = np.any(a_i != b_i, axis=-1)
    assert moved.mean() > 0.5, f"only {moved.mean():.3f} of cells moved under a vergence change"


def test_a_single_reprojection_cannot_serve_both_eyes() -> None:
    """Measured, and recorded as a property of the representation.

    The belief is anchored to ONE eye because the measurement is a depth field
    attached to that eye's pixels. The two eyes' rotations differ by 1.7 degrees
    at vergence 0.03 and 9.2 degrees at 0.16 — 21 px and 112 px at f = 700 — so a
    right-eye measurement reprojected through the left-eye map would be wrong by
    that much. Nothing consumes a right-eye measurement today; the moment
    something does, this becomes a per-eye belief.
    """
    _engine, _sampling, _gt, _params, rig = _setup()
    for vergence, expected_deg in ((0.03, 1.72), (0.16, 9.17)):
        rot = eye_rotations(rig, Fixation(0.15, 0.10, vergence))
        angle = np.degrees(
            np.arccos(np.clip((np.trace(rot.left.T @ rot.right) - 1.0) / 2.0, -1.0, 1.0))
        )
        assert angle == pytest.approx(expected_deg, abs=0.02)


def test_the_frame_is_named_on_the_type() -> None:
    """``fc-006``: frames are declared where the value is, not in a governance file."""
    _engine, sampling, _gt, _params, rig = _setup()
    belief = HeadFrameBelief.from_sampling(sampling, REFERENCE, rig)
    assert belief.frame == HEAD_FRAME == "cyclopean_head"
    norms = np.linalg.norm(belief.directions, axis=-1)
    assert np.allclose(norms, 1.0, atol=1e-12), "cells must be unit directions"


def test_cells_outside_the_sensor_are_left_untouched() -> None:
    """Zero precision, not a mask: a cell that sees nothing must not move.

    Under a large rotation part of the grid leaves the sensor. Those cells keep
    the prior exactly, which is what makes a partially-visible fuse safe.
    """
    _engine, sampling, _gt, _params, rig = _setup()
    belief = HeadFrameBelief.from_sampling(sampling, Fixation(0.0, 0.0, 0.06), rig)
    before_mean = belief.mean.copy()
    height, width = sampling.shape
    measurement = np.full((height, width), 1.0, np.float32)
    precision = np.full((height, width), 1e3, np.float32)
    far = Fixation(0.0, 0.5, 0.06)
    _index, visible = belief.reproject(far, sampling)
    assert not visible.all(), "this test needs some cells off-sensor to mean anything"
    belief.fuse(measurement, precision, far, sampling)
    assert np.array_equal(belief.mean[~visible], before_mean[~visible])
