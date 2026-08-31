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
from bio3dvision.oculomotor import Fixation, rectification_rotation
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
    return engine, sampling, gt, params


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
        engine, sampling, _gt, _params = _setup(seed)
        belief = HeadFrameBelief.from_sampling(sampling, REFERENCE)
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
    engine, sampling, _gt, _params = _setup()
    belief = HeadFrameBelief.from_sampling(sampling, REFERENCE)
    gathered = belief.gather(engine.valid.astype(np.float32), REFERENCE, sampling, fill=0.0)
    assert np.array_equal(gathered.astype(bool), engine.valid)


def test_reprojection_at_the_reference_fixation_is_the_identity_map() -> None:
    """Structural, not numerical: every cell resolves to the index it came from.

    This is *why* the control is bit-exact, and it is asserted separately so that
    a future change breaking the identity is diagnosed here rather than as an
    unexplained divergence in the control above.
    """
    _engine, sampling, _gt, _params = _setup()
    belief = HeadFrameBelief.from_sampling(sampling, REFERENCE)
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
    _engine, sampling, _gt, _params = _setup()
    belief = HeadFrameBelief.from_sampling(sampling, Fixation(0.0, 0.20, 0.06))
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
    _engine, sampling, _gt, params = _setup()
    reference = Fixation(0.0, 0.20, 0.06)
    rotated = Fixation(0.0, 0.35, 0.06)
    belief = HeadFrameBelief.from_sampling(sampling, reference)

    # Truth, defined on head-frame directions: each cell's own y-component.
    truth = belief.directions[..., 1].astype(np.float32)

    # The same function evaluated in the rotated image frame: the image sample's
    # direction carried into the head frame by the ROTATED fixation's rotation.
    height, width = sampling.shape
    rows, cols = np.mgrid[0:height, 0:width]
    idx = np.stack([rows, cols], axis=-1).astype(np.float64)
    field = (sampling.direction(idx) @ rectification_rotation(rotated).T)[..., 1].astype(np.float32)

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


def test_azimuth_alone_reprojects_nothing() -> None:
    """A measured property of this operator, and a real limitation.

    ``rectification_rotation`` zeroes azimuth by construction — the plane of
    regard is the elevated plane for every azimuth — so the rectified frame does
    not rotate with azimuth. Tying the head grid to the rectified frame therefore
    means a purely azimuthal gaze change reprojects **nothing**.

    Asserted rather than left implicit: a reader who assumed a head-frame belief
    remaps under every saccade would be wrong about this one, and 17b will have to
    decide whether the grid should track gaze rather than the rectifier.
    """
    _engine, sampling, _gt, _params = _setup()
    belief = HeadFrameBelief.from_sampling(sampling, Fixation(0.0, 0.20, 0.06))
    same_elevation = Fixation(0.7, 0.20, 0.06)
    a, _ = belief.reproject(belief.origin_fixation, sampling)
    b, _ = belief.reproject(same_elevation, sampling)
    assert np.array_equal(a, b)


def test_the_frame_is_named_on_the_type() -> None:
    """``fc-006``: frames are declared where the value is, not in a governance file."""
    _engine, sampling, _gt, _params = _setup()
    belief = HeadFrameBelief.from_sampling(sampling, REFERENCE)
    assert belief.frame == HEAD_FRAME == "cyclopean_head"
    norms = np.linalg.norm(belief.directions, axis=-1)
    assert np.allclose(norms, 1.0, atol=1e-12), "cells must be unit directions"


def test_cells_outside_the_sensor_are_left_untouched() -> None:
    """Zero precision, not a mask: a cell that sees nothing must not move.

    Under a large rotation part of the grid leaves the sensor. Those cells keep
    the prior exactly, which is what makes a partially-visible fuse safe.
    """
    _engine, sampling, _gt, _params = _setup()
    belief = HeadFrameBelief.from_sampling(sampling, Fixation(0.0, 0.0, 0.06))
    before_mean = belief.mean.copy()
    height, width = sampling.shape
    measurement = np.full((height, width), 1.0, np.float32)
    precision = np.full((height, width), 1e3, np.float32)
    far = Fixation(0.0, 0.5, 0.06)
    _index, visible = belief.reproject(far, sampling)
    assert not visible.all(), "this test needs some cells off-sensor to mean anything"
    belief.fuse(measurement, precision, far, sampling)
    assert np.array_equal(belief.mean[~visible], before_mean[~visible])
