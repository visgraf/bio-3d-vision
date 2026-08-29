"""Gaze policies for the active loop, as alternatives to the ported default.

``ActiveStereo`` is not modified by anything here. Its ``step(fixation=...)``
already accepts an explicit fixation, so a policy is a function that chooses one
and hands it in — the baseline stays reproducible bit-for-bit (``bio-001``..
``bio-009``) and every arm runs through the same update.

The four policies are pre-registered in
``experiments/exp001_gaze_objective/preregistration.md``.

Expected variance reduction
---------------------------
For a scalar Gaussian posterior with variance ``v_q``, absorbing a measurement of
precision ``p_q`` gives ``v_q' = 1/(1/v_q + p_q) = v_q/(1 + v_q p_q)``, so

    Delta_q(c) = v_q - v_q/(1 + v_q p_q(c))

:func:`measurement_precision` is ``p_q(c)``, transcribed from
``ActiveStereo.step`` rather than re-derived: same ``vergence`` call, same
``D_fix``, same ``dZ_deta``, same ``sig_model``, same ``var_Z``, same fovea
weight, same ``valid`` gate. **Where it agrees with step():** ``p_q(c)`` is
exactly ``meas_prec`` there, and ``Delta_q`` is exactly ``self.var - 1/post_prec``
whenever ``v_q > 1e-6`` — the only divergence is ``step``'s ``max(v, 1e-6)``
guard, which binds at variances no pixel reaches from a prior of 9.0 within this
budget. Asserted in ``tests/test_policy.py::test_delta_matches_the_ported_update``.

``p_q(c)`` depends on the fixation and not only on the pixel, through ``d_fix(c)``
and the fovea weight. So the objective is the field integral ``Delta_total(c)``,
not ``Delta_c(c)``; whether the cheap version tracks it is falsifier 2.
"""

from __future__ import annotations

import math
from typing import Any, Protocol

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import gaussian_filter

FloatArray = NDArray[np.float32]
Fixation = tuple[int, int]

#: The predecessor's default, from
#: visgraf/active-stereo@3f7a263:src/activestereo/policy/gaze.py:13 — recorded
#: in ADR-0002's consequences (item 2). Not tuned here.
#:
#: Cited by repo@sha rather than by the local clone path on purpose: the clone
#: is machine-specific and git-ignored, so a path into it is not a reference
#: anyone else can follow.
INHIBITION_RADIUS = 20.0

#: Candidate stride for the field-integral policy.
#:
#: Pre-registered as 8 with a declared check that halving must not move the
#: step-1 selection. It DID move it — stride 8 picks (128, 176), stride 4 picks
#: (120, 180) — so under the pre-registered rule the grid was too coarse and the
#: stride was reduced to 4 before any arm was scored. Stride 4 passes its own
#: halving check (4 and 2 both pick (120, 180)). See the findings for the full
#: ladder, including that stride 2 -> 1 moves again: the objective is flat near
#: its maximum, so the exact argmax pixel is not stable at fine grids.
CANDIDATE_STRIDE = 4

#: The port's saliency blur, from ActiveStereo.step. Carried, not endorsed.
SALIENCY_SIGMA = 4.0

#: Raster pitch for the uninformed arms (exp002), derived from INHIBITION_RADIUS
#: rather than chosen: A' claims an area of pi*R^2 per fixation, a pitch-p lattice
#: claims p^2, so equalising the areal footprint per fixation gives p = R*sqrt(pi).
#:
#: Matching p to R itself would equalise a length against a radius, making the
#: raster pi times denser — 40 fixations would then claim 30% of the valid area
#: against 95% here, and a blind arm would lose for having looked at less of the
#: image rather than for being blind. See exp002's pre-registration.
RASTER_PITCH = INHIBITION_RADIUS * math.sqrt(math.pi)


class Policy(Protocol):
    """Chooses the next fixation, or ``None`` to terminate."""

    def __call__(self, engine: Any, visited: list[Fixation]) -> Fixation | None: ...


# --- the machinery ----------------------------------------------------------


def measurement_precision(engine: Any, yf: int, xf: int) -> FloatArray:
    """``p_q(c)``: the precision each pixel receives from a fixation at ``c``.

    Transcribed from ``ActiveStereo.step``. See the module docstring for exactly
    where the two agree.
    """
    d_fix = engine.vergence(yf, xf)
    D_fix = engine.f * engine.I / max(d_fix, 1e-3)
    dZ_deta = -(D_fix * D_fix) / (engine.I * engine.f)
    eta = engine.d_sub - d_fix
    sig_model = D_fix * (eta / max(d_fix, 1e-3)) ** 2
    var_Z = (dZ_deta**2) * engine.var_d + sig_model**2
    w = engine._fovea_weight(yf, xf)
    p: FloatArray = engine.valid * w / np.maximum(var_Z, 1e-6)
    return p


def expected_reduction_field(engine: Any, yf: int, xf: int) -> NDArray[np.float64]:
    """``Delta_q(c)`` for every pixel ``q``, given a fixation at ``c``.

    Computed in float64 deliberately. ``v - v/(1+v p)`` subtracts two numbers of
    order the prior variance (9.0) to get a result of order 1e-4, and in float32
    one ulp at 9.0 is 9.5e-7 — so the reduction carries ~0.4% relative error per
    pixel from cancellation alone, and ``Delta_total`` sums 76800 of them.

    Measured, before choosing: the resulting float32-vs-float64 disagreement in
    ``Delta_total`` is 1.4e-2 against a spread of 1.0e5 across candidates and a
    best-to-second-best margin of 89.8, so it does not in fact change the argmax
    here. float64 is used anyway because it costs nothing and the margin is not
    guaranteed to stay that wide. Pinned by
    ``tests/test_policy.py::test_float32_cancellation_does_not_decide_the_argmax``.
    """
    v = np.asarray(engine.var, dtype=np.float64)
    p = measurement_precision(engine, yf, xf).astype(np.float64)
    d: NDArray[np.float64] = v - v / (1.0 + v * p)
    return d


def delta_total(engine: Any, yf: int, xf: int) -> float:
    """``Delta_total(c) = sum_q Delta_q(c)``. One field integral per candidate."""
    return float(np.sum(expected_reduction_field(engine, yf, xf)))


def delta_single(engine: Any, yf: int, xf: int) -> float:
    """``Delta_c(c)``: the reduction at the fixated pixel only. The cheap version."""
    return float(expected_reduction_field(engine, yf, xf)[yf, xf])


def candidate_grid(engine: Any, stride: int = CANDIDATE_STRIDE) -> list[Fixation]:
    """Valid pixels on a regular lattice of the given stride.

    Anchored at the first valid row/column so that halving the stride yields a
    strict superset — which is what makes the declared stride check meaningful.
    """
    ys, xs = np.where(engine.valid)
    rows = np.arange(int(ys.min()), int(ys.max()) + 1, stride)
    cols = np.arange(int(xs.min()), int(xs.max()) + 1, stride)
    return [(int(r), int(c)) for r in rows for c in cols if engine.valid[r, c]]


def _inhibit(score: NDArray[np.float64], visited: list[Fixation], radius: float) -> None:
    """Suppress a disc around every visited location, in place.

    The predecessor's semantics exactly (``policy.gaze.next_fixation``): set the
    disc to ``nan`` so it cannot be selected, and let the caller terminate when
    nothing finite remains.
    """
    if not visited:
        return
    rows, cols = np.indices(score.shape)
    for r0, c0 in visited:
        score[np.hypot(rows - r0, cols - c0) <= radius] = np.nan


# --- the four arms ----------------------------------------------------------


def policy_a(engine: Any, visited: list[Fixation]) -> Fixation | None:
    """A — the ported baseline: argmax of the blurred posterior variance.

    Byte-for-byte the selection inside ``ActiveStereo.step``, including defect 2
    (the blur runs over ``np.where(valid, var, 0.0)``, mixing invalid pixels in
    as zeros before the mask is reapplied). Reproduced here so every arm runs
    through one harness; pinned equal to ``step``'s own choice by
    ``tests/test_policy.py::test_policy_a_reproduces_the_ported_selection``.
    """
    del visited
    v = gaussian_filter(np.where(engine.valid, engine.var, 0.0), SALIENCY_SIGMA)
    v = np.where(engine.valid, v, -np.inf)
    yf, xf = np.unravel_index(int(np.argmax(v)), v.shape)
    return int(yf), int(xf)


def policy_a_prime(engine: Any, visited: list[Fixation]) -> Fixation | None:
    """A' — A plus inhibition of return at the predecessor's 20.0 px radius.

    The only change from A is that already-visited neighbourhoods are removed
    from contention. The objective is untouched.
    """
    v = gaussian_filter(np.where(engine.valid, engine.var, 0.0), SALIENCY_SIGMA)
    score = np.where(engine.valid, v, np.nan).astype(np.float64)
    _inhibit(score, visited, INHIBITION_RADIUS)
    if not np.isfinite(score).any():
        return None
    yf, xf = np.unravel_index(int(np.nanargmax(score)), score.shape)
    return int(yf), int(xf)


def policy_b(
    engine: Any,
    visited: list[Fixation],
    stride: int = CANDIDATE_STRIDE,
    scores: NDArray[np.float64] | None = None,
) -> Fixation | None:
    """B — argmax of the single-pixel approximation ``Delta_c(c)``.

    Same candidate grid as C, so B against C compares the objective alone rather
    than objective-and-grid. No inhibition of return: an expected-reduction
    objective is supposed to self-inhibit.
    """
    del visited
    cands = candidate_grid(engine, stride)
    if scores is None:
        scores = np.array([delta_single(engine, y, x) for y, x in cands])
    return cands[int(np.argmax(scores))]


def policy_c(
    engine: Any,
    visited: list[Fixation],
    stride: int = CANDIDATE_STRIDE,
    scores: NDArray[np.float64] | None = None,
) -> Fixation | None:
    """C — argmax of the field integral ``Delta_total(c)``. The correct objective.

    One full-field evaluation per candidate per step. No inhibition of return,
    for the same reason as B.

    ``scores`` lets a caller pass grid integrals it has already computed; the
    selection is identical either way, pinned by
    ``tests/test_policy.py::test_precomputed_scores_change_nothing``.
    """
    del visited
    cands = candidate_grid(engine, stride)
    if scores is None:
        scores = np.array([delta_total(engine, y, x) for y, x in cands])
    return cands[int(np.argmax(scores))]


# --- the uninformed arms (exp002) -------------------------------------------
#
# Neither reads engine.var. Both are deterministic scans indexed by how many
# fixations have already happened, so they are stateless and reproducible.


def raster_lattice(
    shape: tuple[int, int], pitch: float = RASTER_PITCH, origin: tuple[int, int] = (0, 0)
) -> list[Fixation]:
    """Row-major lattice of the given pitch over ``shape``, from ``origin``."""
    r0, c0 = origin
    rows = np.arange(r0, shape[0], pitch)
    cols = np.arange(c0, shape[1], pitch)
    return [(int(round(r)), int(round(c))) for r in rows for c in cols]


def policy_d(engine: Any, visited: list[Fixation]) -> Fixation | None:
    """D — blind raster. Uses NO information, not even the validity mask.

    A fixed pitch-``RASTER_PITCH`` scan of the whole frame from (0, 0). Roughly
    41% of its lattice falls outside the valid region, and those fixations are
    largely wasted — that is what "uses no information" means, and it is the
    quantity being measured rather than an artefact.

    Fixating deep in the invalid band is safe: ``vergence`` finds no valid pixel
    in its window, falls back to the raw ``d_sub``, and clamps ``D_fix`` into
    [0.5, 8] m.
    """
    lattice = raster_lattice(engine.valid.shape)
    i = len(visited)
    return lattice[i] if i < len(lattice) else None


def policy_e(engine: Any, visited: list[Fixation]) -> Fixation | None:
    """E — masked coverage. Uses the validity mask and nothing else.

    The same pitch as D, laid over the valid region's bounding box and skipping
    invalid lattice points. E is D plus one bit per pixel; the bit is used both
    to place the raster and to skip holes, because E is the "mask only" arm and
    should be the strongest version of that.
    """
    ys, xs = np.where(engine.valid)
    origin = (int(ys.min()), int(xs.min()))
    lattice = [
        p
        for p in raster_lattice(engine.valid.shape, origin=origin)
        if p[0] <= int(ys.max()) and p[1] <= int(xs.max()) and engine.valid[p]
    ]
    i = len(visited)
    return lattice[i] if i < len(lattice) else None


POLICIES: dict[str, Policy] = {
    "A": policy_a,
    "A_prime": policy_a_prime,
    "B": policy_b,
    "C": policy_c,
    "D": policy_d,
    "E": policy_e,
}
