"""The four-panel figure is an invariant, not an output.

This repository regenerates the same artifact beside the previous one's on every
iteration and reads the difference (CLAUDE.md). That only works if the artifact
is reproducible under a fixed seed: otherwise a comparison between iterations
measures the noise floor rather than the change, and the gradient the project is
built around does not exist.

So the reproducibility test below is not hygiene. It is the precondition for the
method.
"""

from __future__ import annotations

import numpy as np
import pytest

from bio3dvision import run_baseline, save_result_fig
from bio3dvision.figure import DEFAULT_FIGURE_PATH, PanelArrays

PANELS = ("posterior_mean", "posterior_std", "absolute_error", "rmse_trajectory")


def test_two_runs_at_the_same_seed_are_identical() -> None:
    """All four panels, bit-identical across two independent runs.

    Exact equality, not a tolerance: the loop takes no randomness after the
    fixture is drawn, so anything short of identity is a real defect rather than
    accumulated float noise.
    """
    a = run_baseline(steps=18, seed=0).panels
    b = run_baseline(steps=18, seed=0).panels

    for name in PANELS:
        x, y = getattr(a, name), getattr(b, name)
        assert x.shape == y.shape, name
        assert x.dtype == y.dtype, name
        np.testing.assert_array_equal(x, y, err_msg=f"panel {name!r} is not reproducible")
    assert a.scanpath == b.scanpath


def test_a_different_seed_moves_every_panel() -> None:
    """The negative control: without it, a function returning constants would pass.

    A reproducibility test that cannot tell two different runs apart is pinning
    nothing.
    """
    a = run_baseline(steps=18, seed=0).panels
    c = run_baseline(steps=18, seed=1).panels
    for name in PANELS:
        assert not np.array_equal(getattr(a, name), getattr(c, name)), (
            f"panel {name!r} did not move when the seed changed"
        )


def test_panels_carry_the_four_documented_quantities() -> None:
    run = run_baseline(steps=18, seed=0)
    p = run.panels
    assert isinstance(p, PanelArrays)
    assert p.posterior_mean.shape == (240, 320)
    assert p.posterior_std.shape == (240, 320)
    assert p.absolute_error.shape == (240, 320)
    assert p.rmse_trajectory.shape == (18,)
    assert len(p.scanpath) == 18
    # std is the square root of the posterior variance, error is against truth
    np.testing.assert_allclose(p.posterior_std**2, run.engine.var, rtol=1e-6)
    np.testing.assert_allclose(p.absolute_error, np.abs(run.engine.mean - run.depth_gt), rtol=1e-6)


def test_figure_is_written_to_a_stable_path(tmp_path) -> None:
    """Same filename every run, so the current figure is always at one address."""
    run = run_baseline(steps=3, seed=0)
    out = tmp_path / "iteration-01"
    out.mkdir()
    panels = save_result_fig(run.engine, run.depth_gt, run.history, out=str(out))
    written = out / "fig_result.png"
    assert written.is_file() and written.stat().st_size > 0
    np.testing.assert_array_equal(panels.posterior_mean, run.panels.posterior_mean)
    assert DEFAULT_FIGURE_PATH.endswith("fig_result.png")


def test_rendering_does_not_perturb_the_run() -> None:
    """Drawing the figure must not change what it is a picture of."""
    run = run_baseline(steps=4, seed=0)
    before = run.engine.mean.copy()
    save_result_fig(run.engine, run.depth_gt, run.history, out=None)
    np.testing.assert_array_equal(run.engine.mean, before)


@pytest.mark.parametrize("name", PANELS)
def test_no_panel_is_all_nan(name: str) -> None:
    """A panel of nan renders as a blank square and would pass an equality test."""
    panels = run_baseline(steps=6, seed=0).panels
    assert np.isfinite(getattr(panels, name)).any(), f"panel {name!r} is entirely non-finite"
