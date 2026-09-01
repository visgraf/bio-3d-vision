"""Layers 3-5: vergence scaling, and the active foveated inference loop.

FAITHFUL PORT of ``scale_to_depth`` and ``ActiveStereo`` from
``visgraf/bioeye@e908170:active_stereo_demo.py:208-313``. Numerically unchanged.

**This is a faithful port with known defects. It is not the intended
architecture.** It is here to be a baseline that can be checked against the
original, because a port that deviates cannot be checked, and an unverified
baseline is not one. Three things are carried over deliberately, and none of them
is to be "cleaned up" as part of using this module:

1. **The ``1e3`` variance sentinel** (``__init__``) — a convention this
   repository rejects, not a bug in the predecessor's own terms. Invalid pixels
   are marked by writing a large float into ``var_d`` rather than ``nan``. A
   sentinel is a real number: it propagates through arithmetic silently and
   cannot be distinguished downstream from a genuine, very uncertain
   measurement.

2. **``gaussian_filter`` over ``np.where(valid, var, 0.0)`` in the gaze policy**
   (``step``) — a defect. Invalid pixels are set to 0.0 and then spatially
   blurred INTO their valid neighbours before the validity mask is reapplied.
   That is mixing before masking: it drags the saliency of every pixel near an
   invalid region toward zero, so the policy systematically avoids the
   neighbourhood of occlusions and borders — exactly where the interesting
   evidence is.

3. **No inhibition of return** — a defect. ``step`` reduces the variance at the
   fixated point by a bounded amount, so if one pixel's posterior variance
   dominates by more than a single visit can remove, the argmax selects it again
   and the loop locks up. Measured on this fixture: it does.

Fixing any of these is a later commit, made one at a time, with its effect on the
trajectory reported. They are decisions, not cleanups.

**Ground truth is measurement-only.** ``depth_gt`` enters this module through
exactly one path — ``run(..., depth_gt=...)``, which uses it to compute an RMSE
for the history and nothing else. It never reaches ``step``, the vergence
estimate, the gaze policy, or the posterior. See the assertion in ``run``.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.ndimage import gaussian_filter

from bio3dvision.fixture import CameraParams
from bio3dvision.matching import front_end_block

FloatArray = NDArray[np.float32]
BoolArray = NDArray[np.bool_]
#: The posterior fields. float32 at runtime — the port is bit-identical to the
#: predecessor, verified — but the update expression is not narrow enough for
#: strict inference to say so, so the declared type is the honest wider one.
PosteriorArray = NDArray[np.floating[Any]]


def scale_to_depth(
    d_sub: FloatArray,
    d_fix: float,
    f_px: float,
    I: float,  # noqa: E741 - the predecessor's name for the baseline; kept for the port
) -> tuple[FloatArray, float]:
    """``Z = D - (D^2/I) * eta_rad``, with ``D = f*I/d_fix`` and ``eta_rad = (d - d_fix)/f``.

    First-order-exact at the fixation, degrading with ``|eta|`` -> foveal accuracy.
    Returns depth (m) and ``dZ/deta`` (Jacobian, for variance propagation).
    """
    D = f_px * I / max(d_fix, 1e-3)
    eta = d_sub - d_fix
    Z = D - (D * D / I) * (eta / f_px)
    dZ_deta = -(D * D) / (I * f_px)  # constant per fixation
    return Z.astype(np.float32), float(dZ_deta)


class ActiveStereo:
    """Per-pixel Gaussian posterior over depth, updated across fixations.

    Faithful port; see the module docstring for the three carried defects.
    """

    def __init__(
        self,
        left: FloatArray,
        right: FloatArray,
        params: CameraParams,
        dmin: int = 0,
        dmax: int | None = None,
        win: int = 7,
        matcher: str = "block",
        fovea_sigma: float = 34.0,
        prior_depth: float = 3.0,
        prior_std: float = 3.0,
        fovea: str = "pixel",
    ) -> None:
        self.f = float(params["f_px"])
        self.I = float(params["baseline"])
        self.H, self.W = left.shape
        if dmax is None:
            dmax = int(self.f * self.I / 0.8)  # up to ~0.8 m near clip
        self.matcher = matcher
        if matcher != "block":
            # front_end_sgbm needs OpenCV and is not part of this port.
            raise ValueError(f"only the block matcher is ported; got matcher={matcher!r}")
        self.d_sub, self.var_d, valid_fe = front_end_block(left, right, dmin, dmax, win)
        self.fovea_sigma = fovea_sigma
        if fovea not in ("pixel", "angular"):
            raise ValueError(f"fovea must be 'pixel' or 'angular', got {fovea!r}")
        #: **"pixel" is the default and nothing changes silently.** The two are
        #: different functions, so switching is a decision and not a refactor; the
        #: divergence and whether any recorded verdict moves under it are measured
        #: in bio-083. "angular" exists because on a spherical lattice a Gaussian
        #: in row and column is not a Gaussian in angle at all.
        self.fovea = fovea
        self._angular_directions: FloatArray | None = None
        if fovea == "angular":
            from bio3dvision.sampling import PinholeSampling

            model = PinholeSampling((self.H, self.W), self.f)
            rows, cols = np.mgrid[0 : self.H, 0 : self.W]
            index = np.stack([rows, cols], axis=-1).astype(np.float64)
            self._angular_directions = np.asarray(model.direction(index))
        # Add the image-border constraint (needs left-side search support).
        border = np.zeros((self.H, self.W), bool)
        m = win + 1
        border[m : self.H - m, dmax + m : self.W - m] = True
        self.valid: BoolArray = border & valid_fe
        # DEFECT 1 (carried): sentinel, not nan. See module docstring.
        self.var_d = np.where(self.valid, self.var_d, 1e3).astype(np.float32)
        # Posterior over depth: per-pixel mean and variance (scalar Gaussian).
        self.mean: PosteriorArray = np.full((self.H, self.W), prior_depth, np.float32)
        self.var: PosteriorArray = np.full((self.H, self.W), prior_std**2, np.float32)
        self.scanpath: list[tuple[int, int]] = []

    def _fovea_weight(self, yf: int, xf: int) -> FloatArray:
        """Acuity falloff about the fixated sample.

        ``"pixel"`` is the ported Gaussian in ROW AND COLUMN, unchanged and still
        the default. ``"angular"`` is the same falloff in the ANGLE between each
        sample's direction and the gaze direction, which is what a non-planar
        lattice needs — see ``policy.angular_falloff`` and bio-083.
        """
        if self.fovea == "angular":
            from bio3dvision.policy import angular_falloff

            dirs = self._angular_directions
            assert dirs is not None
            gaze = dirs[int(yf), int(xf)]
            sigma = float(np.arctan(self.fovea_sigma / self.f))
            out: FloatArray = np.asarray(angular_falloff(dirs, gaze, sigma), dtype=np.float32)
            return out
        yy, xx = np.mgrid[0 : self.H, 0 : self.W]
        r2 = (yy - yf) ** 2 + (xx - xf) ** 2
        w: FloatArray = np.exp(-r2 / (2 * self.fovea_sigma**2)).astype(np.float32)
        return w

    def vergence(self, yf: int, xf: int, gain: float = 0.7, iters: int = 4, win: int = 6) -> float:
        """Scalar disparity-vergence loop: servo the pedestal to the fixated disparity.

        The target disparity is a robust (median) estimate over a small foveal
        window of valid pixels, so a single outlier cannot set an absurd D.
        """
        y0, y1 = max(0, yf - win), min(self.H, yf + win + 1)
        x0, x1 = max(0, xf - win), min(self.W, xf + win + 1)
        patch = self.d_sub[y0:y1, x0:x1][self.valid[y0:y1, x0:x1]]
        target = float(np.median(patch)) if patch.size > 5 else float(self.d_sub[yf, xf])
        d0 = 0.0
        for _ in range(iters):  # leaky integrator toward target
            d0 += gain * (target - d0)
        d_lo = self.f * self.I / 8.0  # clamp D to [0.5 m, 8 m]
        d_hi = self.f * self.I / 0.5
        return float(np.clip(d0, d_lo, d_hi))  # == fixation disparity d_fix

    def measurement(
        self, yf: int, xf: int, d_fix: float | None = None
    ) -> tuple[FloatArray, PosteriorArray, float]:
        """The measurement one fixation produces: ``(Zmeas, precision, D_fix)``.

        Extracted from :meth:`step`, which now calls it — **one implementation, so
        the two cannot drift.** A head-frame belief needs the same measurement
        ``step`` fuses in image coordinates, and a second copy of this arithmetic
        would make the fixed-eye control compare two computations rather than two
        frames, which is the one thing that control must not do.

        Uses no ground truth. Both returned fields are in the **image frame** at
        this fixation; reprojecting them is the caller's business.

        The precision is ``float64`` while ``Zmeas`` is ``float32`` — a promotion
        the arithmetic performs and the annotation states rather than hides. It
        matters: the fusion below is written against exactly these dtypes, and the
        head-frame belief reproduces it bit-for-bit only because it inherits them.
        """
        # ``d_fix`` is normally servoed to THIS fixation. Passing one in freezes
        # the linearisation while the eye keeps moving, which is the only way to
        # separate the two things that co-vary in every experiment so far: the
        # acuity weight ``w`` (allocation) and the expansion point (scaling). It
        # is an override and not a new default; ``None`` is the ported behaviour.
        if d_fix is None:
            d_fix = self.vergence(yf, xf)
        D_fix = self.f * self.I / max(d_fix, 1e-3)
        Zmeas, dZ_deta = scale_to_depth(self.d_sub, d_fix, self.f, self.I)
        Zmeas = np.clip(Zmeas, 0.3, 10.0)  # reject absurd scaled depths
        # Two variance sources: (i) propagated matching noise, (ii) the linearization
        # (Taylor-remainder) error of the first-order scaling, which grows as eta^2 and
        # confines each fixation's confident estimate to its foveal neighbourhood.
        eta = self.d_sub - d_fix
        sig_model = D_fix * (eta / max(d_fix, 1e-3)) ** 2
        var_Z = (dZ_deta**2) * self.var_d + sig_model**2
        # STILL PIXEL-NATIVE, and deliberately so. Step 15 named an angular foveal
        # weight as the change that would make the sensor genuinely optional; a
        # head-frame belief does not by itself fix it, and it is 17b/18 work.
        w = self._fovea_weight(yf, xf)  # acuity falloff: precise at fovea
        meas_prec = self.valid * w / np.maximum(var_Z, 1e-6)  # invalid/peripheral -> ~0
        return Zmeas, meas_prec, D_fix

    def step(
        self,
        fixation: tuple[int, int] | None = None,
        *,
        direction: FloatArray | None = None,
        sampling: Any | None = None,
    ) -> dict[str, Any]:
        """One fixation. Uses no ground truth of any kind.

        ``direction`` accepts the fixation **as a unit ray** in the sampling
        model's frame, which is the boundary ``fc-009`` committed to. It needs
        ``sampling`` to resolve, and that requirement is the finding rather than
        an inconvenience: **the index does not disappear, it moves in here.**

        Everything below the choice is defined on the pixel lattice —
        ``_fovea_weight`` is a Gaussian in row/column, and ``vergence`` takes a
        median over a square pixel window. A ray cannot drive either without a
        sensor to land it on the lattice. So this argument makes the ray cross
        the boundary and does not make the sensor go away; what would is a foveal
        weight defined on angle, which is step 17/18 work and is not built here.

        On a uniform pinhole lattice ``index(direction(i)) == i`` exactly, so
        passing a ray is bit-identical to passing the index it came from.
        """
        if direction is not None:
            if fixation is not None:
                raise ValueError("pass a fixation index or a direction, not both")
            if sampling is None:
                raise ValueError(
                    "a direction needs a sampling model to resolve onto the lattice: "
                    "the foveal weight and the vergence window are both defined in pixels"
                )
            resolved = sampling.index(np.asarray(direction, dtype=np.float64))
            fixation = (int(resolved[0]), int(resolved[1]))

        # (5) choose next fixation = argmax posterior variance over the valid
        #     region (greedy information-gain stand-in)
        if fixation is None:
            # DEFECT 2 (carried): the blur mixes invalid pixels, written as 0.0,
            # into their valid neighbours BEFORE the mask is reapplied below.
            v = gaussian_filter(np.where(self.valid, self.var, 0.0), 4.0)
            v = np.where(self.valid, v, -np.inf)  # only fixate where info is gettable
            # DEFECT 3 (carried): no inhibition of return. Nothing prevents this
            # argmax from selecting the same pixel on the next call, and it does.
            yi, xi = np.unravel_index(int(np.argmax(v)), v.shape)
            yf, xf = int(yi), int(xi)
        else:
            yf, xf = fixation
        self.scanpath.append((yf, xf))

        # (4) vergence -> absolute distance D at the fixation
        # (3) foveated metric measurement + its variance
        Zmeas, meas_prec, D_fix = self.measurement(yf, xf)

        # (5) scalar precision-weighted (Kalman) fusion into the running posterior
        prior_prec = 1.0 / np.maximum(self.var, 1e-6)
        post_prec = prior_prec + meas_prec
        self.mean = (prior_prec * self.mean + meas_prec * Zmeas) / post_prec
        self.var = 1.0 / post_prec
        return dict(fixation=(yf, xf), D_fix=D_fix)

    def run(self, steps: int, depth_gt: FloatArray | None = None) -> list[dict[str, Any]]:
        """Run ``steps`` fixations.

        ``depth_gt`` is MEASUREMENT ONLY: it is read after ``step`` has returned,
        used solely to append an RMSE to the history, and never passed into the
        loop. Removing it must change the trajectory not at all — which is what
        ``tests/test_loop_port.py::test_ground_truth_does_not_enter_control``
        asserts.
        """
        hist: list[dict[str, Any]] = []
        for _ in range(steps):
            info = self.step()
            if depth_gt is not None:
                m = np.isfinite(depth_gt) & self.valid
                rmse = float(np.sqrt(np.mean((self.mean[m] - depth_gt[m]) ** 2)))
                info["rmse"] = rmse
            hist.append(info)
        return hist
