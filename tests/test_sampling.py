"""The sample-index to unit-ray boundary (od-001). INFRASTRUCTURE.

The test that matters here is negative: routing the loop through the sampling
model must change **nothing**. An infrastructure iteration's whole gradient is
that the artifact regenerates unchanged, so that is asserted with
``np.array_equal`` and not a tolerance.
"""

from __future__ import annotations

import numpy as np
import pytest

from bio3dvision.figure import panel_arrays
from bio3dvision.fixture import make_synthetic_scene
from bio3dvision.loop import ActiveStereo
from bio3dvision.policy import POLICIES
from bio3dvision.sampling import (
    RECTIFIED_LEFT_CAMERA,
    PinholeSampling,
    SamplingModel,
    route_through_sampling,
)

# B and C evaluate 3314 candidates per step; short budgets for those, longer for
# the cheap arms. The round trip is index-exact, so budget length adds no risk.
ARM_BUDGETS = {"A": 12, "A_prime": 12, "B": 4, "C": 4, "D": 12, "E": 12}


def _model(params) -> PinholeSampling:
    return PinholeSampling.from_params(params)


def drive(arm: str, seed: int, budget: int, routed: bool):
    """Run one arm, optionally routing its choice across the ray boundary."""
    left, right, depth_gt, params = make_synthetic_scene(seed=seed)
    engine = ActiveStereo(left, right, params, matcher="block")
    policy = POLICIES[arm]
    if routed:
        policy = route_through_sampling(policy, _model(params))
    history = []
    for _ in range(budget):
        choice = policy(engine, engine.scanpath)
        if choice is None:
            break
        info = engine.step(fixation=choice)
        m = np.isfinite(depth_gt) & engine.valid
        info["rmse"] = float(np.sqrt(np.mean((engine.mean[m] - depth_gt[m]) ** 2)))
        history.append(info)
    return engine, depth_gt, history


# --- the reproduction requirement -------------------------------------------


@pytest.mark.parametrize("arm", list(ARM_BUDGETS))
def test_routing_through_the_model_is_bit_identical(arm: str) -> None:
    """Every arm, unchanged. np.array_equal, not allclose.

    If this fails, the sampling model has changed the measurement and exp001 and
    exp002 stop being comparable to anything built after it.
    """
    budget = ARM_BUDGETS[arm]
    plain, gt_a, hist_a = drive(arm, 0, budget, routed=False)
    routed, gt_b, hist_b = drive(arm, 0, budget, routed=True)

    np.testing.assert_array_equal(gt_a, gt_b, err_msg="the fixture itself moved")
    assert plain.scanpath == routed.scanpath
    for name in ("mean", "var", "valid", "d_sub", "var_d"):
        np.testing.assert_array_equal(
            getattr(plain, name), getattr(routed, name), err_msg=f"{arm}: {name} diverged"
        )

    pa, pb = panel_arrays(plain, gt_a, hist_a), panel_arrays(routed, gt_b, hist_b)
    for panel in ("posterior_mean", "posterior_std", "absolute_error", "rmse_trajectory"):
        np.testing.assert_array_equal(
            getattr(pa, panel), getattr(pb, panel), err_msg=f"{arm}: panel {panel} diverged"
        )
    assert pa.scanpath == pb.scanpath


def test_the_round_trip_is_exact_on_every_sample() -> None:
    """index -> ray -> index, over all 76 800 indices, exactly.

    This is what makes the reproduction above hold for any policy and any
    budget rather than for the ones that happen to be tested.
    """
    _, _, _, params = make_synthetic_scene(seed=0)
    model = _model(params)
    h, w = model.shape
    rows, cols = np.mgrid[0:h, 0:w]
    idx = np.stack([rows, cols], axis=-1)
    np.testing.assert_array_equal(model.index(model.direction(idx)), idx)


def test_the_round_trip_has_orders_of_margin_before_rounding() -> None:
    """Rounding recovers the index because the float error is 13 orders below 0.5.

    Pinned so that a future change which erodes the margin is visible before it
    starts flipping indices.
    """
    _, _, _, params = make_synthetic_scene(seed=0)
    model = _model(params)
    h, w = model.shape
    rows, cols = np.mgrid[0:h, 0:w]
    d = model.direction(np.stack([rows, cols], axis=-1))
    pr, pc = model.principal_point
    row_f = pr + model.focal_px * d[..., 1] / d[..., 2]
    col_f = pc + model.focal_px * d[..., 0] / d[..., 2]
    assert np.abs(row_f - rows).max() < 1e-9
    assert np.abs(col_f - cols).max() < 1e-9


# --- the interface ----------------------------------------------------------


def test_pinhole_satisfies_the_protocol() -> None:
    _, _, _, params = make_synthetic_scene(seed=0)
    assert isinstance(_model(params), SamplingModel)


def test_directions_are_unit_and_the_frame_is_stated() -> None:
    """+x right, +y down, +z forward, rectified left-camera frame."""
    _, _, _, params = make_synthetic_scene(seed=0)
    model = _model(params)
    assert model.frame == RECTIFIED_LEFT_CAMERA
    h, w = model.shape
    rows, cols = np.mgrid[0:h:16, 0:w:16]
    d = model.direction(np.stack([rows, cols], axis=-1))
    np.testing.assert_allclose(np.linalg.norm(d, axis=-1), 1.0, rtol=0, atol=1e-12)
    assert np.all(d[..., 2] > 0), "every sample looks forward"

    pr, pc = model.principal_point
    # a column right of the principal point looks toward +x; a row below, +y
    centre = model.direction((pr, pc))
    right = model.direction((pr, pc + 40))
    below = model.direction((pr + 40, pc))
    assert right[0] > centre[0] and abs(right[1] - centre[1]) < 1e-12
    assert below[1] > centre[1] and abs(below[0] - centre[0]) < 1e-12


def test_the_optical_axis_maps_to_straight_ahead() -> None:
    _, _, _, params = make_synthetic_scene(seed=0)
    model = _model(params)
    np.testing.assert_allclose(model.direction(model.principal_point), [0.0, 0.0, 1.0], atol=1e-15)


def test_rays_behind_the_sensor_have_no_index() -> None:
    """A caller error, and it raises rather than returning a sentinel index.

    This repository marks invalidity with nan; an integer index has no nan, so
    the only honest options are raise or a separate validity channel, and the
    inverse being undefined is a caller error rather than a data problem.
    """
    _, _, _, params = make_synthetic_scene(seed=0)
    model = _model(params)
    for bad in ([0.0, 0.0, -1.0], [0.0, 0.0, 0.0]):
        with pytest.raises(ValueError, match="behind the sensor"):
            model.index(np.array(bad))
    with pytest.raises(ValueError, match="finite"):
        model.index(np.array([0.0, np.nan, 1.0]))


def test_contains_is_a_membership_question_not_a_bounds_check_forever() -> None:
    """Today it is bounds; on a foveated lattice it stops being one."""
    _, _, _, params = make_synthetic_scene(seed=0)
    model = _model(params)
    h, w = model.shape
    assert bool(model.contains((0, 0)))
    assert bool(model.contains((h - 1, w - 1)))
    assert not bool(model.contains((-1, 0)))
    assert not bool(model.contains((h, 0)))
    assert not bool(model.contains((0, w)))
    got = model.contains(np.array([[0, 0], [h, 0]]))
    np.testing.assert_array_equal(got, [True, False])


def test_shapes_broadcast() -> None:
    """(..., 2) -> (..., 3) and back, for any leading shape."""
    _, _, _, params = make_synthetic_scene(seed=0)
    model = _model(params)
    for shape in [(2,), (3, 4), (2, 3, 5)]:
        idx = np.stack(
            [
                np.random.default_rng(0).integers(0, model.shape[0], shape),
                np.random.default_rng(1).integers(0, model.shape[1], shape),
            ],
            axis=-1,
        )
        d = model.direction(idx)
        assert d.shape == (*shape, 3)
        assert model.index(d).shape == (*shape, 2)
    with pytest.raises(ValueError, match="length 2"):
        model.direction(np.zeros((4, 3)))
    with pytest.raises(ValueError, match="length 3"):
        model.index(np.zeros((4, 2)))


def test_construction_rejects_impossible_models() -> None:
    with pytest.raises(ValueError, match="focal_px"):
        PinholeSampling((10, 10), 0.0)
    with pytest.raises(ValueError, match="focal_px"):
        PinholeSampling((10, 10), float("nan"))
    with pytest.raises(ValueError, match="shape"):
        PinholeSampling((0, 10), 700.0)


def test_routing_preserves_termination() -> None:
    """A policy returning None still terminates; the wrapper must not swallow it."""
    _, _, _, params = make_synthetic_scene(seed=0)
    routed = route_through_sampling(lambda engine, visited: None, _model(params))
    assert routed(object(), []) is None
