"""The uninformed arms D and E (exp002).

The load-bearing claim about these two is negative — they do not read posterior
variance — and a negative claim needs a test that would catch a violation.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from bio3dvision.fixture import make_synthetic_scene
from bio3dvision.loop import ActiveStereo
from bio3dvision.policy import (
    INHIBITION_RADIUS,
    RASTER_PITCH,
    policy_a_prime,
    policy_d,
    policy_e,
    raster_lattice,
)

BUDGET = 40


@pytest.fixture(scope="module")
def engine():
    left, right, gt, params = make_synthetic_scene(seed=0)
    e = ActiveStereo(left, right, params, matcher="block")
    e.run(3, depth_gt=gt)
    return e


def test_pitch_is_derived_from_the_inhibition_radius() -> None:
    """p = R*sqrt(pi): equal areal footprint per fixation, not a chosen number."""
    expected = INHIBITION_RADIUS * math.sqrt(math.pi)
    assert abs(RASTER_PITCH - expected) < 1e-12
    assert abs(RASTER_PITCH - 35.449) < 1e-3
    # Each lattice cell claims the same area as an inhibition disc.
    assert abs(RASTER_PITCH**2 - math.pi * INHIBITION_RADIUS**2) < 1e-9


def test_raster_spacing_is_not_tighter_than_the_inhibition_radius(engine) -> None:
    """D and E must not win by being more spread than A' is required to be."""
    lattice = raster_lattice(engine.valid.shape)
    pts = np.array(lattice, dtype=float)
    d = np.hypot(pts[:, None, 0] - pts[None, :, 0], pts[:, None, 1] - pts[None, :, 1])
    np.fill_diagonal(d, np.inf)
    assert d.min() >= INHIBITION_RADIUS


@pytest.mark.parametrize("policy", [policy_d, policy_e])
def test_uninformed_policies_ignore_posterior_variance(policy, engine) -> None:
    """The defining property, and the one worth a test that could fail.

    Replace the posterior variance with noise, then with a constant, and the
    choice must not move. A' is included as a positive control: if scrambling the
    variance does not move A' either, the probe is not probing anything.
    """
    visited = engine.scanpath[:2]
    baseline = policy(engine, visited)
    control_before = policy_a_prime(engine, visited)

    original = engine.var.copy()
    rng = np.random.default_rng(0)
    try:
        engine.var = (rng.random(engine.var.shape) * 9.0).astype(np.float32)
        assert policy(engine, visited) == baseline
        engine.var = np.full_like(original, 4.2)
        assert policy(engine, visited) == baseline
        # positive control: A' does move
        engine.var = (rng.random(engine.var.shape) * 9.0).astype(np.float32)
        assert policy_a_prime(engine, visited) != control_before, (
            "scrambling the variance did not move A' either; the probe is vacuous"
        )
    finally:
        engine.var = original


def test_e_only_ever_fixates_valid_pixels(engine) -> None:
    visited: list[tuple[int, int]] = []
    for _ in range(BUDGET):
        p = policy_e(engine, visited)
        assert p is not None
        assert engine.valid[p], f"E fixated an invalid pixel {p}"
        visited.append(p)
    assert len(set(visited)) == BUDGET, "E must not revisit within its budget"


def test_d_fixates_outside_the_valid_region(engine) -> None:
    """Not a defect — it is the measured cost of using no information."""
    visited: list[tuple[int, int]] = []
    for _ in range(BUDGET):
        p = policy_d(engine, visited)
        assert p is not None
        visited.append(p)
    invalid = sum(1 for p in visited if not engine.valid[p])
    assert invalid > 0, "D must be able to waste fixations, or it is not blind"
    assert len(set(visited)) == BUDGET


def test_e_lattice_supports_the_declared_budget() -> None:
    """Min 45 points across the 16 declared seeds; the budget is 40."""
    for seed in (0, 7, 12, 13, 15):
        left, right, _, params = make_synthetic_scene(seed=seed)
        e = ActiveStereo(left, right, params, matcher="block")
        visited: list[tuple[int, int]] = []
        for _ in range(BUDGET):
            p = policy_e(e, visited)
            assert p is not None, f"E exhausted its lattice on seed {seed}"
            visited.append(p)


def test_uninformed_policies_are_deterministic(engine) -> None:
    a = [policy_d(engine, [(0, 0)] * i) for i in range(BUDGET)]
    b = [policy_d(engine, [(0, 0)] * i) for i in range(BUDGET)]
    assert a == b
    c = [policy_e(engine, [(0, 0)] * i) for i in range(BUDGET)]
    d = [policy_e(engine, [(0, 0)] * i) for i in range(BUDGET)]
    assert c == d


def test_d_survives_fixating_deep_in_the_invalid_band() -> None:
    """vergence falls back to raw d_sub and clamps; nothing goes non-finite."""
    left, right, gt, params = make_synthetic_scene(seed=0)
    e = ActiveStereo(left, right, params, matcher="block")
    for pt in [(0, 0), (0, 35), (213, 0)]:
        info = e.step(fixation=pt)
        assert 0.5 <= info["D_fix"] <= 8.0
    assert np.isfinite(e.mean).all()
    assert np.isfinite(e.var).all()
