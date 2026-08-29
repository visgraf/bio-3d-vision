"""Re-acquisition, and the duplication it is built on.

``reacquire`` reproduces four lines of ``ActiveStereo.__init__`` that are not
factored out into a callable. That duplication is a deliberate cost — the
alternative was editing ``ActiveStereo`` — and this file is what keeps it from
drifting silently.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from bio3dvision.acquisition import (
    DEFAULT_WIN,
    INVALID_VARIANCE_SENTINEL,
    PANUM_HALF_WIDTH_PX,
    Window,
    reacquire,
    window_around,
)
from bio3dvision.fixture import make_synthetic_scene, true_disparity
from bio3dvision.loop import ActiveStereo


@pytest.fixture(scope="module")
def scene():
    return make_synthetic_scene(seed=0)


def test_reacquire_reproduces_construction(scene) -> None:
    """THE DUPLICATION GUARD.

    reacquire on the construction window must reproduce __init__ exactly — the
    front end, the border mask, the valid mask, and the 1e3 sentinel. If
    __init__'s acquisition ever changes and reacquire does not, this fails
    instead of the two silently diverging.
    """
    left, right, _, params = scene
    engine = ActiveStereo(left, right, params, matcher="block")
    d0, v0, m0 = engine.d_sub.copy(), engine.var_d.copy(), engine.valid.copy()

    dmax = int(params["f_px"] * params["baseline"] / 0.8)
    k = reacquire(engine, left, right, Window(0, dmax), DEFAULT_WIN)

    np.testing.assert_array_equal(engine.d_sub, d0)
    np.testing.assert_array_equal(engine.var_d, v0)
    np.testing.assert_array_equal(engine.valid, m0)
    assert k == dmax + 1


def test_reacquire_carries_the_sentinel_unchanged(scene) -> None:
    """Defect 1 of the port is carried, not fixed, and that is deliberate."""
    left, right, _, params = scene
    engine = ActiveStereo(left, right, params, matcher="block")
    reacquire(engine, left, right, window_around(14.0))
    assert np.all(engine.var_d[~engine.valid] == INVALID_VARIANCE_SENTINEL)


def test_reacquire_changes_the_measurement_not_the_belief(scene) -> None:
    """Acquisition changes what is measured; the posterior is left alone."""
    left, right, depth_gt, params = scene
    engine = ActiveStereo(left, right, params, matcher="block")
    engine.step(fixation=(120, 180))
    mean0, var0 = engine.mean.copy(), engine.var.copy()

    reacquire(engine, left, right, window_around(14.0))

    np.testing.assert_array_equal(engine.mean, mean0)
    np.testing.assert_array_equal(engine.var, var0)
    del depth_gt


def test_a_narrow_window_can_lose_validity_as_well_as_gain_coverage(scene) -> None:
    """Narrowing is not free coverage, which is why the coverage rule exists.

    The border constraint moves left as dmax falls, making more columns
    reachable — but matches whose true disparity lies outside the window fail the
    ratio and consistency tests, so validity can fall on net.
    """
    left, right, _, params = scene
    wide = ActiveStereo(left, right, params, matcher="block")
    narrow = ActiveStereo(left, right, params, matcher="block")
    reacquire(narrow, left, right, window_around(14.0))
    assert narrow.valid.sum() < wide.valid.sum()


def test_window_around_holds_its_width_and_clamps(scene) -> None:
    for d in (10.0, 14.4, 18.8, 30.0):
        w = window_around(d)
        assert w.hypotheses == 2 * PANUM_HALF_WIDTH_PX + 1
        assert w.dmin >= 0
        assert w.dmin <= round(d) <= w.dmax
    # clamped at zero, width preserved
    w = window_around(0.4)
    assert w.dmin == 0
    assert w.hypotheses == 2 * PANUM_HALF_WIDTH_PX + 1
    with pytest.raises(ValueError, match="non-negative"):
        window_around(10.0, -1)


def test_the_panum_anchor_is_what_it_claims(scene) -> None:
    """A MODELLING CHOICE, not a measurement — pinned so it cannot drift silently.

    Panum's fusional area near the fovea, 5-10 arcmin, at f = 700 px.
    """
    _, _, _, params = scene
    f = params["f_px"]
    px_per_arcmin = f * (1.0 / 60.0) * (math.pi / 180.0)
    assert f == 700.0
    assert 5 * px_per_arcmin == pytest.approx(1.018, abs=1e-3)
    assert 10 * px_per_arcmin == pytest.approx(2.036, abs=1e-3)
    assert PANUM_HALF_WIDTH_PX == 2  # the upper end


def test_the_window_must_be_narrower_than_the_scene_or_v_degenerates(scene) -> None:
    """Half-width 4 or more covers the whole scene in one vergence.

    Recorded as a test because it is the constraint that fixes the width, and a
    fixture change that widened the depth range would silently invalidate the
    experiment's design. That change would be fc-004 and needs an ADR.
    """
    _, _, depth_gt, params = scene
    d = true_disparity(depth_gt, params)
    span = float(d.max() - d.min())
    assert span == pytest.approx(8.847, abs=1e-3)
    assert span > 2 * PANUM_HALF_WIDTH_PX + 1, "the window must not cover the scene"
    assert span <= 2 * 4 + 1, "half-width 4 would be degenerate; that is why 2 was chosen"
