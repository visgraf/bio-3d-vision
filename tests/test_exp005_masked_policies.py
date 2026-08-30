"""The masked-selection variants exp005 uses for its steering control.

They stand in for `policy.py`'s four variance-driven arms with the selection
domain restricted. If they drift from the arms they represent, the control stops
being a control and becomes a second experiment nobody declared — so the identity
below is pinned rather than assumed.
"""

from __future__ import annotations

import numpy as np
import pytest
from experiments.exp005_stratified_reanalysis.run import MASKED, band_masks

from bio3dvision.fixture import make_synthetic_scene
from bio3dvision.loop import ActiveStereo
from bio3dvision.policy import POLICIES

ARMS = ("A", "A_prime", "B", "C")


def _engine(seed: int = 0) -> tuple[ActiveStereo, np.ndarray]:
    left, right, depth_gt, params = make_synthetic_scene(seed=seed)
    return ActiveStereo(left, right, params, matcher="block"), depth_gt


@pytest.mark.parametrize("arm", ARMS)
def test_an_all_true_mask_reproduces_the_unmasked_policy(arm: str) -> None:
    """With nothing masked out, each variant must choose exactly what the arm chooses.

    This is the whole guarantee that exp005's control compares the same policies
    the originals ran. A' is included even though it carries inhibition state:
    with an empty visited list the two must still agree.
    """
    engine, _gt = _engine()
    everywhere = np.ones(engine.valid.shape, dtype=bool)
    assert MASKED[arm](engine, engine.scanpath, everywhere) == POLICIES[arm](
        engine, engine.scanpath
    )


@pytest.mark.parametrize("arm", ARMS)
def test_a_masked_policy_selects_inside_the_mask(arm: str) -> None:
    """Every choice must land in the band, or the control does not control anything."""
    engine, _gt = _engine()
    away = band_masks()["AWAY"]
    for _ in range(5):
        choice = MASKED[arm](engine, engine.scanpath, away)
        assert choice is not None
        assert away[choice], f"{arm} selected {choice} outside the AWAY band"
        engine.step(fixation=choice)


def test_a_masked_policy_returns_none_when_the_band_is_exhausted() -> None:
    """Exhaustion must terminate, not spin or select outside the band.

    exp002's contract, reused. Declared in the preregistration as a real
    possibility here: the AWAY band admits only ~41 sites at A''s 20 px
    inhibition radius, against exp002's budget of 40.
    """
    engine, _gt = _engine()
    # Chosen from engine.valid rather than hardcoded: the front-end validity mask
    # is not a simple border, so a plausible-looking coordinate need not be valid.
    ys, xs = np.where(engine.valid)
    site = (int(ys[len(ys) // 2]), int(xs[len(xs) // 2]))
    tiny = np.zeros(engine.valid.shape, dtype=bool)
    tiny[site] = True
    assert MASKED["A_prime"](engine, [], tiny) == site
    # After visiting it, inhibition removes the only candidate.
    assert MASKED["A_prime"](engine, [site], tiny) is None


def test_the_bands_partition_the_frame() -> None:
    """AT, MIDDLE and AWAY are disjoint and cover everything; POOLED is everything.

    A gap or an overlap would make the three-band gradient uninterpretable, and
    the pooled figure would stop being the originals' pixel set.
    """
    bands = band_masks()
    stack = np.stack([bands["AT"], bands["MIDDLE"], bands["AWAY"]])
    assert (stack.sum(axis=0) == 1).all(), "the three bands must partition the frame"
    assert bands["POOLED"].all()


def test_the_band_geometry_does_not_depend_on_the_seed() -> None:
    """The fixture varies texture with the seed, not geometry.

    exp005 computes the bands once and reuses them across seeds; this is the
    assumption that makes that sound.
    """
    from bio3dvision.scene_model import rasterise_depth, scene_from_fixture

    a = rasterise_depth(scene_from_fixture(seed=0), smooth=False)
    b = rasterise_depth(scene_from_fixture(seed=9), smooth=False)
    assert np.array_equal(a, b)
