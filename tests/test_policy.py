"""The gaze policies, and the two equivalences the experiment rests on.

If policy A does not reproduce the ported selection, arm A is not the baseline.
If Delta does not match the ported update, B and C are optimising something the
loop does not actually do. Both are pinned here rather than argued in a docstring.
"""

from __future__ import annotations

import numpy as np
import pytest

from bio3dvision.fixture import make_synthetic_scene
from bio3dvision.loop import ActiveStereo
from bio3dvision.policy import (
    CANDIDATE_STRIDE,
    INHIBITION_RADIUS,
    candidate_grid,
    delta_single,
    delta_total,
    expected_reduction_field,
    measurement_precision,
    policy_a,
    policy_a_prime,
)


@pytest.fixture(scope="module")
def engine():
    left, right, gt, params = make_synthetic_scene(seed=0)
    e = ActiveStereo(left, right, params, matcher="block")
    e.run(3, depth_gt=gt)
    return e


def test_policy_a_reproduces_the_ported_selection() -> None:
    """Arm A must be the baseline, not a lookalike.

    Run the ported loop and the same loop driven by policy_a through explicit
    fixations; the scanpaths and posteriors must be identical.
    """
    left, right, gt, params = make_synthetic_scene(seed=0)
    ported = ActiveStereo(left, right, params, matcher="block")
    ported.run(12, depth_gt=gt)

    driven = ActiveStereo(left, right, params, matcher="block")
    for _ in range(12):
        driven.step(fixation=policy_a(driven, driven.scanpath))

    assert driven.scanpath == ported.scanpath
    np.testing.assert_array_equal(driven.mean, ported.mean)
    np.testing.assert_array_equal(driven.var, ported.var)


def test_delta_matches_the_ported_update(engine) -> None:
    """Delta_q(c) is the variance the ported update actually removes.

    Two claims, checked separately because they hold to different precisions.

    1. ALGEBRAICALLY the identity is exact: v - v/(1+vp) == v - 1/(1/v + p).
       Checked in float64, where it holds to 2e-15.
    2. AGAINST step()'s realised float32 arithmetic it holds only to float32
       cancellation. step() forms the new variance as 1/(1/v + p) and the
       observable reduction is a subtraction of two numbers near the prior
       variance 9.0, where one ulp is 9.5e-7. Agreement to ~2 ulp is the most
       that can be asked, and asking for more would be pinning float32 noise.

    The max(v, 1e-6) guard in step() is the one admitted divergence; it cannot
    bind here, asserted rather than assumed.
    """
    y, x = 120, 180
    assert engine.var.min() > 1e-6, "the max(v,1e-6) guard would bind; the claim needs restating"

    predicted = expected_reduction_field(engine, y, x)

    # 1. the algebra, in float64
    v64 = np.asarray(engine.var, dtype=np.float64)
    p64 = measurement_precision(engine, y, x).astype(np.float64)
    closed_form = v64 - 1.0 / (1.0 / np.maximum(v64, 1e-6) + p64)
    np.testing.assert_allclose(predicted, closed_form, rtol=1e-12, atol=1e-14)

    # 2. against what step() actually does, in float32
    before = engine.var.copy()
    engine.step(fixation=(y, x))
    actual = before - engine.var
    np.testing.assert_allclose(predicted, actual, rtol=1e-3, atol=2e-6)


def test_float32_cancellation_does_not_decide_the_argmax() -> None:
    """The float64 choice is hygiene, and this checks it is not load-bearing.

    If float32 noise ever exceeded the best-to-second-best margin, C's selection
    would be arithmetic rather than objective. Builds its own engine: the shared
    fixture is stepped by other tests in this module, and a margin measured at an
    unknown state pins nothing.
    """
    left, right, gt, params = make_synthetic_scene(seed=0)
    e = ActiveStereo(left, right, params, matcher="block")
    e.run(3, depth_gt=gt)

    grid = candidate_grid(e, CANDIDATE_STRIDE)
    f64 = np.array([delta_total(e, y, x) for y, x in grid])
    f32 = np.array(
        [
            float(
                np.sum(e.var - e.var / (np.float32(1.0) + e.var * measurement_precision(e, y, x)))
            )
            for y, x in grid
        ]
    )
    ranked = np.sort(f64)[::-1]
    margin = ranked[0] - ranked[1]
    noise = float(np.abs(f32 - f64).max())
    assert noise < margin / 100.0, (
        f"float32 noise {noise:.3e} is not safely below the winning margin {margin:.3e}"
    )
    assert grid[int(np.argmax(f32))] == grid[int(np.argmax(f64))]


def test_measurement_precision_is_the_ported_meas_prec(engine) -> None:
    """p_q(c) is step()'s meas_prec, recomputed the same way."""
    y, x = 100, 150
    p = measurement_precision(engine, y, x)
    assert p.shape == engine.var.shape
    assert np.all(p >= 0.0)
    assert np.all(p[~engine.valid] == 0.0), "invalid pixels receive no precision"
    # The fovea weight peaks at the fixation, so precision should too, among
    # pixels of comparable var_Z. Check the fixation is in the top decile.
    assert p[y, x] > np.percentile(p[engine.valid], 90)


def test_delta_total_is_not_delta_single(engine) -> None:
    """The two objectives are genuinely different quantities.

    If they agreed, falsifier 2 would be untestable and the field integral would
    be pointless.
    """
    y, x = 120, 180
    assert delta_total(engine, y, x) > delta_single(engine, y, x) * 10


def test_halving_the_stride_gives_a_superset(engine) -> None:
    """The declared stride check is only meaningful if the grids nest."""
    coarse = set(candidate_grid(engine, CANDIDATE_STRIDE))
    fine = set(candidate_grid(engine, CANDIDATE_STRIDE // 2))
    assert coarse <= fine
    assert len(fine) > 3 * len(coarse)


def test_inhibition_of_return_excludes_visited_neighbourhoods(engine) -> None:
    """A' must not select within the predecessor's 20.0 px radius of a visit."""
    first = policy_a_prime(engine, [])
    assert first is not None
    second = policy_a_prime(engine, [first])
    assert second is not None
    assert np.hypot(second[0] - first[0], second[1] - first[1]) > INHIBITION_RADIUS


def test_inhibition_returns_none_when_nothing_remains(engine) -> None:
    """Terminate rather than spin — the predecessor's contract."""
    ys, xs = np.where(engine.valid)
    everywhere = [(int(r), int(c)) for r, c in zip(ys[::7], xs[::7], strict=True)]
    assert policy_a_prime(engine, everywhere) is None


def test_policies_do_not_mutate_the_engine(engine) -> None:
    """A policy chooses; only step() updates. Otherwise arms are not comparable."""
    before_mean = engine.mean.copy()
    before_var = engine.var.copy()
    for pol in (policy_a, policy_a_prime):
        pol(engine, [(50, 100)])
    np.testing.assert_array_equal(engine.mean, before_mean)
    np.testing.assert_array_equal(engine.var, before_var)


def test_precomputed_scores_change_nothing() -> None:
    """Passing the grid integrals in must not change what C selects."""
    from bio3dvision.policy import policy_c

    left, right, gt, params = make_synthetic_scene(seed=0)
    e = ActiveStereo(left, right, params, matcher="block")
    e.run(2, depth_gt=gt)
    grid = candidate_grid(e, CANDIDATE_STRIDE)
    scores = np.array([delta_total(e, y, x) for y, x in grid])
    assert policy_c(e, [], scores=scores) == policy_c(e, [])
