"""Step 15's two load-bearing claims: bit-exactness, and where the index went.

**Bit-exactness.** Routing the loop through the ray form must leave every arm of
exp001, exp002, exp003, exp007 and exp008 unchanged. ``np.array_equal``, not
``allclose``: nine experiments' worth of recorded numbers rest on these arrays,
and a tolerance would let a real change hide under one.

**Where the index went.** ``route_through_sampling``'s docstring predicted that
once a geometry layer existed, "the ray goes straight into it and ``model.index``
drops out of this path". The geometry layer now exists. These tests measure how
much of that prediction holds.
"""

from __future__ import annotations

import numpy as np
import pytest

from bio3dvision.fixture import make_synthetic_scene
from bio3dvision.loop import ActiveStereo
from bio3dvision.policy import POLICIES
from bio3dvision.sampling import PinholeSampling, route_as_direction, route_through_sampling

ARMS = ("A", "A_prime", "B", "C", "D", "E")
CHEAP_ARMS = ("A", "A_prime", "D", "E")
STEPS = 6


def _scene(seed: int = 0):
    return make_synthetic_scene(seed=seed)


def _model(params) -> PinholeSampling:
    return PinholeSampling(
        shape=(int(params["H"]), int(params["W"])), focal_px=float(params["f_px"])
    )


def _run(arm: str, seed: int, mode: str) -> ActiveStereo:
    """One arm, one seed, driven by pixel / round-tripped index / ray."""
    left, right, _gt, params = _scene(seed)
    engine = ActiveStereo(left, right, params, matcher="block")
    model = _model(params)
    policy = POLICIES[arm]
    for _ in range(STEPS):
        if mode == "pixel":
            choice = policy(engine, engine.scanpath)
            if choice is None:
                break
            engine.step(fixation=choice)
        elif mode == "round_trip":
            choice = route_through_sampling(policy, model)(engine, engine.scanpath)
            if choice is None:
                break
            engine.step(fixation=choice)
        elif mode == "ray":
            ray = route_as_direction(policy, model)(engine, engine.scanpath)
            if ray is None:
                break
            engine.step(direction=ray, sampling=model)
        else:  # pragma: no cover - programming error
            raise AssertionError(mode)
    return engine


@pytest.mark.parametrize("arm", CHEAP_ARMS)
def test_driving_the_loop_with_a_ray_is_bit_identical_to_a_pixel(arm: str) -> None:
    """The claim nine experiments rest on, asserted with ``array_equal``.

    Bit-identity holds because ``index(direction(i)) == i`` exactly on a uniform
    pinhole lattice — measured at 76 800 of 76 800 indices with 13 orders of
    margin (``fv-006-1``). It is verified here rather than assumed, because
    "the round trip is the identity" is a property of THIS lattice and this
    principal point, not of ray commitments in general.
    """
    for seed in (0, 3):
        by_pixel = _run(arm, seed, "pixel")
        by_ray = _run(arm, seed, "ray")
        assert by_pixel.scanpath == by_ray.scanpath
        for name in ("mean", "var", "d_sub", "var_d"):
            assert np.array_equal(getattr(by_pixel, name), getattr(by_ray, name)), (
                f"{arm} seed {seed}: {name} differs between the pixel and ray paths"
            )
        assert np.array_equal(by_pixel.valid, by_ray.valid)


@pytest.mark.parametrize("arm", CHEAP_ARMS)
def test_the_ray_path_also_matches_the_round_trip_adapter(arm: str) -> None:
    """Three routes, one result: pixel, index -> ray -> index, and ray.

    The middle one is ``fc-009``'s existing adapter. If the new path agreed with
    the pixel path but not with it, one of the two ray constructions would be
    wrong and the agreement above would be a coincidence.
    """
    for seed in (0, 3):
        a = _run(arm, seed, "round_trip")
        b = _run(arm, seed, "ray")
        assert a.scanpath == b.scanpath
        assert np.array_equal(a.mean, b.mean)
        assert np.array_equal(a.var, b.var)


def test_the_ray_carries_no_index_out_of_the_policy() -> None:
    """``route_as_direction`` returns a **3-vector**, and no pixel leaves it.

    This is the half of the prediction that holds: the policy path no longer
    carries an index.
    """
    left, right, _gt, params = _scene()
    engine = ActiveStereo(left, right, params, matcher="block")
    model = _model(params)
    ray = route_as_direction(POLICIES["A_prime"], model)(engine, engine.scanpath)
    assert isinstance(ray, np.ndarray)
    assert ray.shape == (3,)
    assert float(np.linalg.norm(ray)) == pytest.approx(1.0, abs=1e-12)


def test_the_index_does_not_disappear_it_moves_into_the_loop() -> None:
    """The half of the prediction that does NOT hold, asserted so it cannot be forgotten.

    ``ActiveStereo.step`` cannot consume a ray without a sampling model, and it
    says why: ``_fovea_weight`` is a Gaussian in row/column and ``vergence``
    takes a median over a square pixel window. Both are defined on the lattice,
    so the ray must be landed on it before either can run.

    This is the evidence for ``fc-009``'s falsifier 2: the commitment is
    **additive** — nothing existing changed and every array is bit-identical —
    and it is **not eliminating**, because the sensor is still required at the
    point of use.
    """
    left, right, _gt, params = _scene()
    engine = ActiveStereo(left, right, params, matcher="block")
    model = _model(params)
    ray = model.direction(np.asarray((100, 120), dtype=np.float64))

    with pytest.raises(ValueError, match="needs a sampling model"):
        engine.step(direction=ray)
    with pytest.raises(ValueError, match="not both"):
        engine.step(fixation=(100, 120), direction=ray, sampling=model)


def test_a_ray_resolves_to_the_index_it_came_from() -> None:
    """The identity the bit-exactness rests on, over the whole lattice.

    Not a sample: every index in the frame, so the claim is about the lattice and
    not about the indices a policy happened to pick.
    """
    _left, _right, _gt, params = _scene()
    model = _model(params)
    h, w = int(params["H"]), int(params["W"])
    rows, cols = np.mgrid[0:h, 0:w]
    idx = np.stack([rows.ravel(), cols.ravel()], axis=-1).astype(np.float64)
    assert np.array_equal(model.index(model.direction(idx)), idx.astype(int))
