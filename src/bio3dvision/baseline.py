"""Compose fixture + loop into the runnable baseline, and measure it.

This is the entry point later work imports. It runs the ported loop on the
ported fixture and returns everything needed to check it against the
predecessor: the engine, the history, and the panel data.

Nothing here is new science. See ``loop.py`` for the three carried defects.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from bio3dvision.figure import PanelArrays, panel_arrays
from bio3dvision.fixture import CameraParams, make_synthetic_scene
from bio3dvision.loop import ActiveStereo

FloatArray = NDArray[np.float32]

DEFAULT_STEPS = 18
DEFAULT_SEED = 0


@dataclass(frozen=True)
class BaselineRun:
    """One complete run of the ported baseline."""

    engine: ActiveStereo
    history: list[dict[str, Any]]
    panels: PanelArrays
    depth_gt: FloatArray
    params: CameraParams

    @property
    def fixations(self) -> list[tuple[int, int]]:
        return [h["fixation"] for h in self.history]

    @property
    def rmse(self) -> list[float]:
        return [h["rmse"] for h in self.history if "rmse" in h]

    @property
    def distinct_fixations(self) -> int:
        return len(set(self.fixations))


def run_baseline(steps: int = DEFAULT_STEPS, seed: int = DEFAULT_SEED) -> BaselineRun:
    """Run the ported loop on the ported fixture. Deterministic in ``seed``."""
    left, right, depth_gt, params = make_synthetic_scene(seed=seed)
    engine = ActiveStereo(left, right, params, matcher="block")
    history = engine.run(steps, depth_gt=depth_gt)
    return BaselineRun(
        engine=engine,
        history=history,
        panels=panel_arrays(engine, depth_gt, history),
        depth_gt=depth_gt,
        params=params,
    )


def error_summary(run: BaselineRun) -> dict[str, float]:
    """Error statistics over valid, known pixels — the reproduction check's targets.

    ``depth_gt`` is used here and only here, after the loop has finished.
    """
    valid = np.isfinite(run.depth_gt) & run.engine.valid
    err = np.abs(run.engine.mean[valid] - run.depth_gt[valid])
    sq = err.astype(np.float64) ** 2
    order = np.sort(sq)[::-1]
    top5 = int(np.ceil(0.05 * order.size))
    return {
        "rmse": float(np.sqrt(sq.mean())),
        "median_abs_err": float(np.median(err)),
        "p90": float(np.percentile(err, 90)),
        "p99": float(np.percentile(err, 99)),
        "max": float(err.max()),
        "top5pct_share_of_squared_error": float(order[:top5].sum() / order.sum()),
        "n_pixels": float(valid.sum()),
    }
