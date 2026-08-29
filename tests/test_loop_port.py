"""The ported baseline, pinned against the predecessor.

These are not tests of good behaviour. Several of them pin behaviour this
repository considers wrong — the lockup especially — because the point of a
faithful port is that it can be checked, and a defect that is not pinned cannot
be shown to have been fixed later. When a deviation lands, the test that changes
is the record of what the deviation did.

Reference values were measured at ``visgraf/bioeye@e908170`` and independently
reproduced here; see ``docs/inherited-measurements.yaml`` (``bio-`` entries).
"""

from __future__ import annotations

import numpy as np
import pytest
from scipy.stats import spearmanr

from bio3dvision import error_summary, run_baseline
from bio3dvision.fixture import make_synthetic_scene, true_disparity
from bio3dvision.loop import ActiveStereo, scale_to_depth

LOCKUP_PIXEL = (170, 94)


@pytest.fixture(scope="module")
def run():
    return run_baseline(steps=18, seed=0)


# --- the trajectory ----------------------------------------------------------


def test_nine_distinct_fixations_out_of_eighteen(run) -> None:
    assert len(run.fixations) == 18
    assert run.distinct_fixations == 9


def test_the_loop_locks_up_on_one_pixel(run) -> None:
    """DEFECT 3, pinned: no inhibition of return, so the argmax re-selects.

    Steps 8 through 17 are the same pixel — the second half of the run buys
    nothing. This test is expected to CHANGE when inhibition of return lands;
    that change is the measurement, which is why the lockup is pinned exactly
    rather than merely tolerated.
    """
    assert run.fixations[8:] == [LOCKUP_PIXEL] * 10
    assert len(set(run.fixations[:8])) == 8, "the first eight fixations are all distinct"


def test_rmse_flattens_and_then_stops_improving(run) -> None:
    """The trajectory's shape: real progress to step 5, then nothing.

    Not "frozen" in the literal sense — it drifts in the fourth decimal, up to
    step 10 and then very slightly down — so this pins the shape and the
    magnitude of the drift rather than a constant.
    """
    rmse = run.rmse
    assert rmse[0] == pytest.approx(0.7824, abs=5e-4)
    assert rmse[5] == pytest.approx(0.4790, abs=5e-4)
    assert rmse[-1] == pytest.approx(0.4793, abs=5e-4)
    tail = np.array(rmse[5:])
    assert tail.max() - tail.min() < 1e-3, "flat to within a millimetre after step 5"
    # The first five steps are worth an order of magnitude more than the last twelve.
    assert (rmse[0] - rmse[5]) > 100 * abs(rmse[5] - rmse[-1])


# --- the per-pixel diagnostics at the lockup pixel ---------------------------


def test_lockup_pixel_first_visit_diagnostics() -> None:
    """Why the loop locks: a grossly wrong disparity yields a huge, useless variance.

    ``d_sub`` is 32.9 px where the truth is 10.7 px. The linearisation term
    ``sig_model`` then dominates ``var_Z``, the measurement precision is ~0.002
    against a prior precision of ~0.16, and one visit removes only ~1.3% of the
    pixel's posterior variance — so it stays the argmax and is chosen again.
    """
    left, right, gt, params = make_synthetic_scene(seed=0)
    engine = ActiveStereo(left, right, params, matcher="block")
    engine.run(8, depth_gt=gt)
    y, x = LOCKUP_PIXEL

    d_fix = engine.vergence(y, x)
    d_fix_arr, dz_deta = scale_to_depth(engine.d_sub, d_fix, engine.f, engine.I)
    del d_fix_arr
    D_fix = engine.f * engine.I / max(d_fix, 1e-3)
    eta = engine.d_sub - d_fix
    sig_model = D_fix * (eta / max(d_fix, 1e-3)) ** 2
    var_Z = (dz_deta**2) * engine.var_d + sig_model**2
    meas_prec = engine.valid * engine._fovea_weight(y, x) / np.maximum(var_Z, 1e-6)

    assert float(engine.d_sub[y, x]) == pytest.approx(32.916, abs=1e-3)
    assert float(true_disparity(gt, params)[y, x]) == pytest.approx(10.711, abs=1e-3)
    assert d_fix == pytest.approx(10.192, abs=1e-3)
    assert float(eta[y, x]) == pytest.approx(22.724, abs=1e-3)
    assert float(engine.var_d[y, x]) == pytest.approx(1.0124e-2, rel=1e-3)
    assert float(sig_model[y, x]) == pytest.approx(22.191, abs=1e-3)
    assert float(var_Z[y, x]) == pytest.approx(492.456, abs=1e-2)
    assert float(meas_prec[y, x]) == pytest.approx(0.00203, abs=1e-5)


def test_posterior_variance_barely_falls_per_visit() -> None:
    """~0.077 removed per visit from a variance of ~6.3: the lockup's mechanism."""
    left, right, gt, params = make_synthetic_scene(seed=0)
    engine = ActiveStereo(left, right, params, matcher="block")
    engine.run(8, depth_gt=gt)
    y, x = LOCKUP_PIXEL
    assert float(engine.var[y, x]) == pytest.approx(6.30, abs=0.01)
    falls = []
    for _ in range(4):
        before = float(engine.var[y, x])
        engine.step()
        falls.append(before - float(engine.var[y, x]))
    assert falls[0] == pytest.approx(0.0796, abs=1e-3)
    assert all(f == pytest.approx(0.077, abs=4e-3) for f in falls)
    assert falls == sorted(falls, reverse=True), "the fall itself shrinks with each visit"


# --- the error field ---------------------------------------------------------


def test_error_summary_over_valid_known_pixels(run) -> None:
    s = error_summary(run)
    assert s["n_pixels"] == 53098
    assert s["rmse"] == pytest.approx(0.4793, abs=5e-5)
    assert s["median_abs_err"] == pytest.approx(0.0114, abs=5e-5)
    assert s["p90"] == pytest.approx(0.4166, abs=5e-5)
    assert s["p99"] == pytest.approx(2.1048, abs=5e-5)
    assert s["max"] == pytest.approx(2.648, abs=1e-3)


def test_error_is_concentrated_in_a_few_pixels(run) -> None:
    """The top 5% of pixels carry 80.9% of squared error.

    Which is why RMSE alone is a poor description of this run: the median pixel
    is at 11 mm and the mean-square is set by a thin tail.
    """
    assert error_summary(run)["top5pct_share_of_squared_error"] == pytest.approx(0.809, abs=1e-3)


def test_posterior_std_ranks_error_only_moderately(run) -> None:
    """Spearman(|err|, posterior std): +0.42 over valid, +0.57 over all known.

    Positive — the posterior is not anti-calibrated on this fixture — but far
    from a reliable ordering. Note this says nothing about the occlusion case
    (gap-001): the fixture has no true half-occlusions at all (gap-010).
    """
    gt, mean, std = run.depth_gt, run.engine.mean, run.panels.posterior_std
    valid = np.isfinite(gt) & run.engine.valid
    known = np.isfinite(gt)
    assert spearmanr(np.abs(mean[valid] - gt[valid]), std[valid]).statistic == pytest.approx(
        0.4189, abs=5e-4
    )
    assert spearmanr(np.abs(mean[known] - gt[known]), std[known]).statistic == pytest.approx(
        0.5662, abs=5e-4
    )


# --- the control/measurement boundary ---------------------------------------


def test_ground_truth_does_not_enter_control() -> None:
    """Ground truth is measurement-only, and this is what makes that checkable.

    Running with and without ``depth_gt`` must produce the identical scanpath and
    the identical posterior. If ground truth ever leaks into the vergence
    estimate, the gaze policy or the update, these diverge.
    """
    left, right, gt, params = make_synthetic_scene(seed=0)
    with_gt = ActiveStereo(left, right, params, matcher="block")
    hist = with_gt.run(6, depth_gt=gt)
    without = ActiveStereo(left, right, params, matcher="block")
    without.run(6, depth_gt=None)

    assert with_gt.scanpath == without.scanpath
    np.testing.assert_array_equal(with_gt.mean, without.mean)
    np.testing.assert_array_equal(with_gt.var, without.var)
    assert all("rmse" in h for h in hist)


def test_sgbm_is_not_part_of_this_port() -> None:
    """cv2 is not a dependency; the block matcher is the whole of Layer 2 here."""
    left, right, _, params = make_synthetic_scene(seed=0)
    with pytest.raises(ValueError, match="only the block matcher"):
        ActiveStereo(left, right, params, matcher="sgbm")
