"""The occlusion levels exp008 sweeps, and the border decomposition beneath them.

exp008's x-axis is a measured property of geometry, not a dial. If these numbers
move, the sweep's x-axis moves with them and its trend means something different,
so they are pinned here as exp007's overlap figure was.
"""

from __future__ import annotations

import numpy as np
import pytest

from bio3dvision.scene_model import (
    occlusion_fractions,
    rasterise_depth,
    scene_from_fixture,
    split_cards,
)

# k -> (left-occluded fraction, right-unmatched fraction), measured at 9f40198.
ACHIEVED = {
    1: (0.0197, 0.0509),
    2: (0.0426, 0.0738),
    4: (0.0884, 0.1197),
    8: (0.1716, 0.2029),
}


@pytest.mark.parametrize("k", sorted(ACHIEVED))
def test_the_swept_levels_achieve_their_recorded_fractions(k: int) -> None:
    """Each level's occlusion is what `bio-040` records it to be."""
    f = occlusion_fractions(split_cards(scene_from_fixture(seed=0), k))
    left, right = ACHIEVED[k]
    assert f["left_occluded_fraction"] == pytest.approx(left, abs=5e-4)
    assert f["right_unmatched_fraction"] == pytest.approx(right, abs=5e-4)


def test_level_one_is_exactly_the_exp007_geometry() -> None:
    """`k = 1` must be the unmodified scene, so the sweep connects to a measured point.

    exp007's stimulus is the anchor of this series. If `split_cards` altered the
    scene at `k = 1`, the sweep would start somewhere new and the connection to
    `bio-038` would be a coincidence rather than an identity.
    """
    base = scene_from_fixture(seed=0)
    assert split_cards(base, 1) is base
    f = occlusion_fractions(base)
    assert f["right_unmatched_fraction"] == pytest.approx(0.0509, abs=5e-4)
    assert f["left_occluded_fraction"] == pytest.approx(0.0197, abs=5e-4)


@pytest.mark.parametrize("k", sorted(ACHIEVED))
def test_the_border_component_is_constant_across_every_level(k: int) -> None:
    """The gap between the two overlap measures is 3.12%, whatever the geometry.

    This is the decomposition that corrects exp007's headline. `right_unmatched`
    counts left pixels whose correspondent falls outside the right image *for any
    reason*, and one of those reasons is that the right camera sits a baseline to
    the side and sees past the frame. That contribution is a property of the
    CAMERA, not of the scene, so it must not move when the scene does — and if it
    ever does, the claim that exp007's 5.09% is 61% border stops holding.
    """
    f = occlusion_fractions(split_cards(scene_from_fixture(seed=0), k))
    assert f["border_fraction"] == pytest.approx(0.0312, abs=5e-4)


def test_occlusion_is_not_monotone_in_k_past_the_disparity_step() -> None:
    """`k = 10` yields LESS occlusion than `k = 8`, which is why the sweep stops at 8.

    Strips narrow past the 8.85 px disparity step and the geometry degenerates:
    a strip narrower than the step it casts cannot occlude a full strip's width.
    Pinned so that a later widening of the sweep has to confront it rather than
    discover it.
    """
    base = scene_from_fixture(seed=0)
    at8 = occlusion_fractions(split_cards(base, 8))["left_occluded_fraction"]
    at10 = occlusion_fractions(split_cards(base, 10))["left_occluded_fraction"]
    assert at10 < at8


def test_split_cards_leaves_depths_texture_and_camera_untouched() -> None:
    """The lever is lateral. Anything else moving would confound the whole sweep."""
    base = scene_from_fixture(seed=0)
    split = split_cards(base, 4)
    assert split.params == base.params
    assert np.array_equal(split.texture, base.texture)
    assert split.smoothing_sigma == base.smoothing_sigma
    assert {s.depth_m for s in split.surfaces} == {s.depth_m for s in base.surfaces}
    assert split.surfaces[0] == base.surfaces[0]  # background untouched
    # Every strip keeps its parent card's rows; only columns change.
    assert {s.rows for s in split.surfaces} == {s.rows for s in base.surfaces}


def test_every_level_still_covers_the_frame() -> None:
    """Gaps reveal background, never a hole. A hole would not be a scene."""
    for k in ACHIEVED:
        depth = rasterise_depth(split_cards(scene_from_fixture(seed=0), k), smooth=False)
        assert depth.min() > 0
