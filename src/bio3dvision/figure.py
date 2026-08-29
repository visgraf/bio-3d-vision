"""The four-panel figure. An invariant, not an output.

FAITHFUL PORT of ``save_result_fig`` from
``visgraf/bioeye@e908170:active_stereo_demo.py:370-395``. The four panels, their
data and their order are unchanged: posterior mean depth with the scanpath
overlaid, posterior std, absolute error against ground truth, and RMSE against
fixation number.

**One structural change, with no numerical effect.** The predecessor computed the
panel data inline inside the plotting call, so nothing could compare two runs
without rendering and diffing PNGs. Here :func:`panel_arrays` computes exactly
the same four arrays and :func:`save_result_fig` renders them. The values are
identical; only the seam is new, and it exists so that
``tests/test_figure.py::test_two_runs_at_the_same_seed_are_identical`` can assert
reproducibility on arrays rather than on pixels.

Why that test matters more than the picture: this repository regenerates the same
artifact beside the previous one's on every iteration and reads the difference
(CLAUDE.md). If the figure is not reproducible under a fixed seed, an
iteration-to-iteration comparison measures the noise floor rather than the
change, and the gradient the project is built around does not exist.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float32]

#: Stable path. Same file every run, so the current figure is always here and a
#: previous iteration's copy can sit beside it under its own name.
DEFAULT_FIGURE_PATH = os.path.join("results", "fig_result.png")


@dataclass(frozen=True)
class PanelArrays:
    """The four panels as data, plus the scanpath drawn over the first.

    Everything a reader of the figure could measure, in a form two runs can be
    compared on.
    """

    posterior_mean: FloatArray
    posterior_std: FloatArray
    absolute_error: FloatArray
    rmse_trajectory: FloatArray
    scanpath: tuple[tuple[int, int], ...]


def panel_arrays(engine: Any, depth_gt: FloatArray, hist: list[dict[str, Any]]) -> PanelArrays:
    """The four panels' data, computed exactly as the predecessor computed them."""
    return PanelArrays(
        posterior_mean=np.asarray(engine.mean, dtype=np.float32),
        posterior_std=np.sqrt(engine.var).astype(np.float32),
        absolute_error=np.abs(engine.mean - depth_gt).astype(np.float32),
        rmse_trajectory=np.asarray([h["rmse"] for h in hist if "rmse" in h], dtype=np.float32),
        scanpath=tuple((int(y), int(x)) for y, x in engine.scanpath),
    )


def save_result_fig(
    engine: Any,
    depth_gt: FloatArray,
    hist: list[dict[str, Any]],
    out: str | None = None,
) -> PanelArrays:
    """Render the four panels to ``out`` and return the data they were drawn from.

    ``out`` is a directory (the predecessor's convention) or ``None`` for
    :data:`DEFAULT_FIGURE_PATH`.
    """
    import matplotlib

    matplotlib.use("Agg")  # no display; deterministic rasterisation
    import matplotlib.pyplot as plt

    panels = panel_arrays(engine, depth_gt, hist)
    path = DEFAULT_FIGURE_PATH if out is None else os.path.join(out, "fig_result.png")
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    fig, ax = plt.subplots(2, 2, figsize=(9, 7))
    im0 = ax[0, 0].imshow(panels.posterior_mean, cmap="viridis")
    ax[0, 0].set_title("posterior mean depth (m)")
    fig.colorbar(im0, ax=ax[0, 0], fraction=0.046)
    ys = [p[0] for p in panels.scanpath]
    xs = [p[1] for p in panels.scanpath]
    ax[0, 0].plot(xs, ys, "w.-", lw=1, ms=6)
    for i, (y, x) in enumerate(panels.scanpath):
        ax[0, 0].text(x + 3, y, str(i), color="w", fontsize=8)

    im1 = ax[0, 1].imshow(panels.posterior_std, cmap="magma")
    ax[0, 1].set_title("posterior std (uncertainty)")
    fig.colorbar(im1, ax=ax[0, 1], fraction=0.046)

    im2 = ax[1, 0].imshow(panels.absolute_error, cmap="inferno")
    ax[1, 0].set_title("|error| vs GT (m)")
    fig.colorbar(im2, ax=ax[1, 0], fraction=0.046)

    ax[1, 1].plot(range(1, len(panels.rmse_trajectory) + 1), panels.rmse_trajectory, "o-")
    ax[1, 1].set_xlabel("fixation #")
    ax[1, 1].set_ylabel("depth RMSE (m)")
    ax[1, 1].set_title("active accumulation")
    for a in (ax[0, 0], ax[0, 1], ax[1, 0]):
        a.axis("off")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return panels
