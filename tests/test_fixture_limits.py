"""The analytic fixture's limits, pinned (gap-010).

A limitation recorded only in prose is a limitation that quietly stops being
true. These tests fail if the fixture ever gains real half-occlusions — which
would be good news, and would mean gap-010 and every claim resting on it need
re-reading rather than silently inheriting.
"""

from __future__ import annotations

import numpy as np

from bio3dvision.fixture import make_synthetic_scene, true_disparity


def test_right_image_contains_nothing_the_left_does_not() -> None:
    """The defining property: the right eye sees no surface the left cannot.

    A half-occlusion is a region visible to one eye and hidden from the other,
    showing a *different* surface. The right image here is a resampling of the
    left, so no such region can exist.
    """
    left, right, _, _ = make_synthetic_scene(seed=0)
    outside = (right < left.min()) | (right > left.max())
    assert outside.sum() == 0, "a right-image value originated outside the left texture"


def test_the_forward_map_is_non_monotonic_where_occlusions_would_be() -> None:
    """Where a renderer would open an occlusion band, the sampler duplicates texture.

    ``x -> x + d(x)`` failing to increase is the signature of a surface passing
    in front of another. There are such places, and the fixture resolves them by
    interpolation rather than by showing what is behind.
    """
    _, _, depth_gt, params = make_synthetic_scene(seed=0)
    H, W = depth_gt.shape
    d = true_disparity(depth_gt, params).astype(np.float64)
    src = np.arange(W)[None, :].repeat(H, 0) + d
    non_increasing = int((np.diff(src, axis=1) <= 0).sum())
    assert non_increasing == 430, (
        "the count of would-be occlusion transitions moved; gap-010 needs re-reading"
    )


def test_reflect_mode_only_explains_the_image_edge() -> None:
    """3.4% of pixels sample out of bounds — the edge, not the depth steps.

    Pinned because the obvious reading of gap-010 is that ``mode="reflect"`` is
    the whole mechanism. It is not: it accounts for the border only, and the
    interior occlusions are lost to interpolation instead.
    """
    _, _, depth_gt, params = make_synthetic_scene(seed=0)
    H, W = depth_gt.shape
    d = true_disparity(depth_gt, params).astype(np.float64)
    src = np.arange(W)[None, :].repeat(H, 0) + d
    out_of_bounds = (src > W - 1) | (src < 0)
    assert out_of_bounds.sum() == 2640
    assert out_of_bounds.mean() < 0.04
    # All of them are at the right-hand edge, none in the interior.
    cols = np.where(out_of_bounds.any(axis=0))[0]
    assert cols.min() > W - 40, "out-of-bounds sampling reached the image interior"


def test_fixture_is_deterministic_and_seed_controlled() -> None:
    a = make_synthetic_scene(seed=0)
    b = make_synthetic_scene(seed=0)
    c = make_synthetic_scene(seed=1)
    for x, y in zip(a[:3], b[:3], strict=True):
        np.testing.assert_array_equal(x, y)
    assert not np.array_equal(a[0], c[0]), "the texture must depend on the seed"
    # Geometry is seed-independent: only the texture is drawn.
    np.testing.assert_array_equal(a[2], c[2])
