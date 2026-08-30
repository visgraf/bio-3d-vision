"""The lateral-overlap measurement exp007's every claim is qualified by.

`bio-038` records that the fixture's geometry produces 5.09% half-occlusion,
incidental rather than designed. exp007's findings lean on that number in both
directions — it is what makes the rendered stimulus better than the fixture, and
what stops it being a controlled occlusion stimulus. A number doing that much
work should not be free to drift.
"""

from __future__ import annotations

import numpy as np
import pytest
from experiments.exp007_rendered_policy_sweep.run import lateral_overlap


def test_the_measured_overlap_matches_the_recorded_figure() -> None:
    """5.09% of right-image pixels unmatched, runs to 10 px — as `bio-038` records."""
    ov = lateral_overlap()
    assert ov["right_pixels_unmatched"] == 3910
    assert ov["right_fraction"] == pytest.approx(0.0509, abs=1e-4)
    assert ov["left_pixels_occluded"] == 1510
    assert ov["left_fraction"] == pytest.approx(0.0197, abs=1e-4)
    assert ov["max_run_px"] == 10


def test_the_overlap_agrees_with_the_exp004_measurement() -> None:
    """Independently computed in `tests/test_scene_model.py`, and must agree.

    `bio-031` measured the same quantity from exp004's side with different code.
    Two routes to one number is worth keeping: if they diverge, one of them is
    wrong and neither result is safe to cite.
    """
    from bio3dvision.scene_model import rasterise_depth, scene_from_fixture

    model = scene_from_fixture(seed=0)
    depth = rasterise_depth(model, smooth=False)
    d_gt = model.params["f_px"] * model.params["baseline"] / depth
    height, width = depth.shape
    cols = np.arange(width)[None, :].repeat(height, 0)
    target = np.rint(cols - d_gt).astype(int)

    occluded = 0
    for y in range(height):
        order = np.argsort(-depth[y])
        xs = target[y, order]
        inside = (xs >= 0) & (xs < width)
        seen = np.zeros(width, dtype=bool)
        seen[xs[inside]] = True
        occluded += int((~seen).sum())

    assert occluded == lateral_overlap()["right_pixels_unmatched"]


def test_the_overlap_is_small_enough_to_qualify_every_claim() -> None:
    """Under 10%, which is why exp007 does not lift `gap-010`.

    Stated as a test rather than as prose because it is the premise of a
    limitation, and a limitation whose premise silently stops holding is worse
    than no limitation at all. If a later scene model raises the overlap past
    this, `gap-010`'s status genuinely changes and this test should fail so that
    someone decides rather than inherits.
    """
    assert lateral_overlap()["right_fraction"] < 0.10
