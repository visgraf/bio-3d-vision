"""Layers 1-2: box-SSD cost volume, subpixel decode, block-matching front end.

FAITHFUL PORT of ``cost_volume``, ``lr_consistency``, ``decode_disparity`` and
``front_end_block`` from
``visgraf/bioeye@e908170:active_stereo_demo.py:112-174``. Numerically unchanged.

``front_end_sgbm`` is deliberately NOT ported: it needs OpenCV, and this port is
pure NumPy/SciPy so that its numbers are version-independent enough to be checked
against the original. The block matcher is the whole of Layer 2 here.
"""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import uniform_filter

FloatArray = NDArray[np.float32]
BoolArray = NDArray[np.bool_]
IntArray = NDArray[np.int_]


def cost_volume(
    left: FloatArray, right: FloatArray, dmin: int, dmax: int, win: int = 7
) -> tuple[NDArray[np.float32], IntArray]:
    """Box-aggregated SSD cost volume. ``cost[y,x,k]`` for disparity ``ds[k]``."""
    H, W = left.shape
    ds = np.arange(dmin, dmax + 1)
    cost = np.full((H, W, len(ds)), np.inf, np.float32)
    for k, d in enumerate(ds):
        rs = np.empty_like(right)  # right shifted right by d
        if d > 0:
            rs[:, :d] = right[:, :1]
            rs[:, d:] = right[:, : W - d]
        else:
            rs[:] = right
        diff = (left - rs) ** 2
        cost[:, :, k] = uniform_filter(diff, size=(win, win))
    return cost, ds


def lr_consistency(
    d_left: FloatArray,
    left: FloatArray,
    right: FloatArray,
    dmin: int,
    dmax: int,
    win: int,
    tol: float = 1.5,
) -> BoolArray:
    """Left-right consistency: match right->left too and flag disagreements
    (the standard occlusion detector). Returns a boolean 'consistent' mask.
    """
    H, W = left.shape
    cost_r, ds = cost_volume(right[:, ::-1], left[:, ::-1], dmin, dmax, win)
    d_right = ds[np.argmin(cost_r, axis=2)][:, ::-1].astype(np.float32)
    xs = np.arange(W)[None, :].repeat(H, 0)
    xr = np.clip(xs - np.round(d_left).astype(int), 0, W - 1)
    agree: BoolArray = np.abs(d_left - d_right[np.arange(H)[:, None], xr]) <= tol
    return agree


def decode_disparity(cost: NDArray[np.float32], ds: IntArray) -> tuple[FloatArray, FloatArray]:
    """Winner-take-all + parabola subpixel refinement; per-pixel variance in px^2."""
    k = np.argmin(cost, axis=2)
    H, W, K = cost.shape
    yy, xx = np.mgrid[0:H, 0:W]
    c0 = cost[yy, xx, k]
    kl = np.clip(k - 1, 0, K - 1)
    kr = np.clip(k + 1, 0, K - 1)
    cl = cost[yy, xx, kl]
    cr = cost[yy, xx, kr]
    denom = cl - 2 * c0 + cr  # local curvature
    curv = np.maximum(denom, 1e-6)
    delta = 0.5 * (cl - cr) / curv  # subpixel offset in [-1,1]
    delta = np.clip(delta, -1, 1)
    d_sub = ds[k].astype(np.float32) + delta
    d_sub = np.where((k > 0) & (k < K - 1), d_sub, ds[k].astype(np.float32))
    # Measurement variance in disparity: noise / curvature (Cramer-Rao-like).
    #
    # This is the curvature proxy the predecessor's exp004/exp006 later showed to
    # be anti-calibrated at half-occlusions on photographs: a sharp cost minimum
    # at the WRONG disparity reads as precision. See gap-001. Ported unchanged.
    noise = np.median(c0) + 1e-6
    var_d = noise / curv
    var_d = np.clip(var_d, 1e-3, 1e3).astype(np.float32)
    return d_sub.astype(np.float32), var_d


def front_end_block(
    left: FloatArray, right: FloatArray, dmin: int, dmax: int, win: int
) -> tuple[FloatArray, FloatArray, BoolArray]:
    """Box-SSD cost volume + WTA parabola subpixel + ratio-test/LR-consistency.

    Returns ``(d_sub, var_d, valid_fe)`` where ``valid_fe`` excludes only
    occlusion/low-confidence; the image border is added by the caller.
    """
    cost, ds = cost_volume(left, right, dmin, dmax, win)
    d_sub, var_d = decode_disparity(cost, ds)
    srt = np.sort(cost, axis=2)
    distinct = (srt[:, :, 1] - srt[:, :, 0]) / (srt[:, :, 1] + 1e-6)
    agree = lr_consistency(d_sub, left, right, dmin, dmax, win)
    valid: BoolArray = (distinct > 0.10) & agree
    return d_sub.astype(np.float32), var_d.astype(np.float32), valid
