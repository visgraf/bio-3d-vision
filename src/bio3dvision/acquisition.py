"""Re-acquisition: changing what data exists, rather than how it is weighted.

Every experiment before exp003 varied *where the loop looks*. None varied *what
was measured*: ``front_end_block`` runs once in ``ActiveStereo.__init__``
(``loop.py:106``) and never again, so the disparity field is a static pass and
the loop only re-weights it. This module lets a driver re-run the front end with
a different disparity window between fixations, which is the first sense in which
this loop is closed rather than a static measurement with a moving weight.

``ActiveStereo`` is **not modified**. :func:`reacquire` writes the new
measurement onto an existing engine.

The duplication, declared rather than hidden
--------------------------------------------
``__init__`` does its acquisition in four steps that are not factored out into a
callable — front end, border mask, valid mask, and the ``1e3`` variance sentinel.
:func:`reacquire` reproduces those four steps **exactly**, including the sentinel,
which is defect 1 of the port and is carried here unchanged rather than fixed.
The alternative was to factor the block out of ``__init__``, which would have
edited ``ActiveStereo``. Keeping the duplication and reporting it was judged the
smaller cost; it is recorded in exp003's findings so it is visible if it ever
drifts. ``tests/test_acquisition.py::test_reacquire_reproduces_construction``
pins the two against each other, so drift is a red suite rather than a silent
divergence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from bio3dvision.matching import front_end_block

FloatArray = NDArray[np.float32]

#: Half-width of the narrow disparity window, in pixels.
#:
#: A MODELLING CHOICE, NOT A MEASUREMENT. Anchored to Panum's fusional area near
#: the fovea, on the order of 5-10 arcmin, which at f = 700 px is 1.018-2.036 px.
#: 2 px is the upper end of that range. Nothing in this repository measures it and
#: no predecessor experiment did; see exp003's pre-registration for why the upper
#: end was taken and why a half-width of 4 or more would make re-centring
#: degenerate on this fixture.
PANUM_HALF_WIDTH_PX = 2

#: The port's acquisition constants, from ActiveStereo.__init__. Carried.
DEFAULT_WIN = 7
INVALID_VARIANCE_SENTINEL = 1e3


@dataclass(frozen=True)
class Window:
    """An integer disparity search window, ``[dmin, dmax]`` inclusive."""

    dmin: int
    dmax: int

    @property
    def hypotheses(self) -> int:
        """Number of disparity hypotheses this window evaluates per pixel."""
        return self.dmax - self.dmin + 1


def window_around(d_fix: float, half_width: int = PANUM_HALF_WIDTH_PX) -> Window:
    """The narrow window centred on a vergence, clamped to ``dmin >= 0``.

    The width is held fixed under clamping, so a fixation verged near zero
    disparity searches the same number of hypotheses as one verged far — the
    arms differ in *where* the window sits, not in how much they evaluate.
    """
    if half_width < 0:
        raise ValueError(f"half_width must be non-negative, got {half_width}")
    width = 2 * half_width
    lo = int(round(d_fix)) - half_width
    lo = max(0, lo)
    return Window(dmin=lo, dmax=lo + width)


def reacquire(
    engine: Any,
    left: FloatArray,
    right: FloatArray,
    window: Window,
    win: int = DEFAULT_WIN,
) -> int:
    """Re-run the front end on ``window`` and write the result onto ``engine``.

    Reproduces ``ActiveStereo.__init__``'s acquisition exactly — front end,
    border constraint, valid mask, ``1e3`` sentinel — with a different disparity
    window. The posterior (``engine.mean``, ``engine.var``) is untouched: this
    changes what is *measured*, not what is *believed*.

    Returns the number of disparity hypotheses evaluated, for cost accounting.
    """
    d_sub, var_d, valid_fe = front_end_block(left, right, window.dmin, window.dmax, win)
    border = np.zeros((engine.H, engine.W), bool)
    m = win + 1
    border[m : engine.H - m, window.dmax + m : engine.W - m] = True
    engine.d_sub = d_sub
    engine.valid = border & valid_fe
    engine.var_d = np.where(engine.valid, var_d, INVALID_VARIANCE_SENTINEL).astype(np.float32)
    return window.hypotheses
