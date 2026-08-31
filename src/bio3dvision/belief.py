"""A depth belief held in the **cyclopean head frame**, with measurements reprojected in.

Why this exists
---------------
``ActiveStereo`` holds its posterior as two ``(H, W)`` arrays in **image
coordinates** and fuses in place (``loop.py:212-213``). That is sound only
because the image never changes: every measurement lands in the same frame, so
fusing in place is correct **by accident of the loop being open**. The moment the
eyes rotate, measurements from different fixations arrive in different image
frames, and fusing them in place is simply wrong.

Neither predecessor ever had this. bioeye's README lists "process dynamics F +
trans-saccadic remapping" under what it deliberately drops, and active-stereo has
no posterior at all outside the demo.

**Nothing here rotates an eye.** This is the representation, built and controlled
before anything depends on it.

The frame, stated at the type and not in a governance file
----------------------------------------------------------
Cells are **unit directions in the cyclopean head frame**: origin between the
eyes, +X right, +Y down, +Z forward, right-handed. ``fc-006`` records why this is
declared here: the predecessor's ``CLAUDE.md`` §3 declared a frame that was false
for eleven days, and a sentence in a governance file has nothing to fail against.

Reprojection is through ``eye_rotations``, and 17a's was not
------------------------------------------------------------
**17a tied this frame to ``rectification_rotation``, and that was wrong.** The
rectifier zeroes azimuth AND vergence by construction, so the frame it defines is
a *rectifier* frame, not a head frame. The consequence was not a cost: across a
17 degree azimuth saccade the mapping moved **zero cells**, while the world
direction a given cell actually views moved **17 degrees**. The same cell received
measurements of unrelated world directions and fused them, and a
precision-weighted fusion of two unrelated depths is a confident average of
neither.

17a's own docstring described that azimuth-invariance and called it "a real
limitation of this operator". **An honest description of a defect is not the same
as noticing it is one.** 17b then priced it — 0.0% grid loss at every azimuth
amplitude — and a number that implausible was the thing that made it visible.

Reprojection now goes through ``eye_rotations``, which carries azimuth, elevation
and vergence.

Anchoring, and why the frame is defined by a fixation
-----------------------------------------------------
``eye_rotations`` at any fixation is already toed in by half the vergence, so a
raw head-to-eye map is **not** the identity even at the origin fixation, and the
fixed-eye control would break. The frame is therefore defined **by the origin
fixation's own eye orientation**, and reprojection uses the RELATIVE rotation
``R_current.T @ R_anchor``. At the anchor that is exactly the identity — the
control is preserved structurally — while azimuth and vergence enter everywhere
else.

**The left eye, and it is a decision.** The measurement is a depth field attached
to the LEFT image's pixels: disparity is left-image convention, ``d = f*I/Z`` has
``Z`` in the rectified left-camera frame, and ``target_to_fixation`` unprojects
about the left optical centre. So the map is the left eye's frame to the head.
**A single reprojection cannot be right for both eyes** — measured, the two
rotations differ by 1.7 degrees at vergence 0.03 and 9.2 degrees at 0.16, which is
21 px and 112 px at ``f = 700``. That costs nothing today because the loop
produces exactly one depth field and it is left-indexed; it becomes a per-eye
belief the moment anything consumes a right-eye measurement, and that is a finding
about the representation rather than an inconvenience.

Discretisation, and what it costs
---------------------------------
The grid is the **sampling model's directions at the origin fixation**, carried
into the head frame by that fixation's own left-eye rotation. Three consequences,
all of them load-bearing:

* **At the origin fixation the reprojection is the identity map**, exactly —
  each cell resolves to the index it came from, because ``index(direction(i))``
  is exact on this lattice over all 76 800 indices (``bio-043``). The fixed-eye
  control is therefore bit-exact **structurally**, not to a tolerance.
* **It is not the image frame by construction.** A cell is a direction; a
  rotation moves the samples relative to the cells and the gather does real work.
  Were the head frame the image frame, a rotation would move nothing — which is
  the outcome that would look like success and be worthless.
* **The discretisation coincides with the image lattice at the origin
  fixation**, and that is a real limitation rather than a neutral choice: cell
  density is the sensor's, so a rotation that moves samples off their cells
  quantises. Said plainly because it is the part a reader would otherwise assume
  away.

An angular grid or a sphere would trade that quantisation for an interpolation
cost and would not be bit-exact at identity without extra care. This choice
admits the omnidirectional case — resampling a sphere under a rotation — without
a signature change, because :meth:`reproject` already takes an arbitrary rotation
and returns indices; nothing here is built toward it.

Resampling and variance
-----------------------
**Nearest-neighbour, and the variance question therefore does not arise.**
Interpolation correlates neighbouring cells and changes the effective sample
count, which is what makes resampling a variance question at all. Gathering the
nearest cell introduces no correlation, so no variance correction is applied and
none is hidden.

The predecessor recorded that bilinear resampling's effect on variance is
**estimator-sign-dependent and unresolved** — under-estimating for a count-based
model, inflating for a parabolic-curvature one, inflating for a profile second
moment, and structurally blind for a constant — and recorded it as *derived from
reasoning, not measured*, filed as its issue #44. This repository's front end is
the parabolic-curvature one, for which the reasoned direction is *inflates*.
**That problem is not inherited here, because nothing is interpolated.** It
becomes live the moment anyone adopts bilinear, and the sign is not picked in
advance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from numpy.typing import NDArray

from bio3dvision.oculomotor import (
    K_LISTING_DEFAULT,
    Fixation,
    StereoRig,
    eye_rotations,
)

FloatArray = NDArray[np.float64]
PosteriorArray = NDArray[np.floating[Any]]
BoolArray = NDArray[np.bool_]

__all__ = ["HeadFrameBelief", "HEAD_FRAME"]

#: The one frame this module speaks, named so a second one cannot arrive quietly.
HEAD_FRAME = "cyclopean_head"


@dataclass
class HeadFrameBelief:
    """A per-cell Gaussian depth belief on a grid of head-frame directions.

    Attributes
    ----------
    directions : (H, W, 3)
        Unit vectors in :data:`HEAD_FRAME`. The grid, and the only thing that
        makes this a head-frame belief rather than a renamed image buffer.
    mean, var : (H, W)
        Depth mean and variance per cell, **metres** and **metres squared**.
        ``float32``, matching ``ActiveStereo``'s posterior exactly so the
        fixed-eye control can be bit-exact rather than nearly so.
    origin_fixation : Fixation
        The fixation whose rectified frame the grid was built from. Reprojection
        from this fixation is the identity.

        Named ``origin_fixation`` rather than the obvious ``reference`` because
        ``tests/test_scaffold.py`` forbids the pinned-clone directory's name
        appearing anywhere in governed code, and an attribute of that name would
        have produced exactly that string after a dot. A false positive from a
        substring check — and renaming was the right response rather than
        loosening the check: a guard is not weakened to accommodate a name, and
        this one says what the fixation is the origin OF.
    """

    directions: FloatArray
    mean: PosteriorArray
    var: PosteriorArray
    origin_fixation: Fixation
    rig: StereoRig
    anchor_rotation: FloatArray
    k: float = K_LISTING_DEFAULT
    eye: str = "left"

    frame: str = HEAD_FRAME

    @classmethod
    def from_sampling(
        cls,
        sampling: Any,
        reference: Fixation,
        rig: StereoRig,
        prior_depth: float = 3.0,
        prior_std: float = 3.0,
        k: float = K_LISTING_DEFAULT,
        eye: str = "left",
    ) -> HeadFrameBelief:
        """Build a belief whose cells are ``sampling``'s directions at ``reference``.

        ``rig`` is required and was not in 17a: without a baseline there is no
        ``eye_rotations``, and without ``eye_rotations`` the frame can only be the
        rectifier's — which is the fault this construction repairs.

        The prior defaults match ``ActiveStereo``'s, because the control compares
        against it and a different prior would make every subsequent number differ
        for a reason that has nothing to do with the frame.
        """
        if eye not in ("left", "right"):
            raise ValueError(f"eye must be 'left' or 'right', got {eye!r}")
        height, width = sampling.shape
        rows, cols = np.mgrid[0:height, 0:width]
        index = np.stack([rows, cols], axis=-1).astype(np.float64)
        # The ANCHOR: this eye's orientation at the origin fixation. Carrying the
        # sensor directions through it defines the head frame BY that fixation,
        # which is what keeps the reprojection an exact identity there.
        anchor = np.asarray(getattr(eye_rotations(rig, reference, k=k), eye), dtype=np.float64)
        directions = sampling.direction(index) @ anchor.T
        return cls(
            directions=np.asarray(directions, dtype=np.float64),
            mean=np.full((height, width), prior_depth, np.float32),
            var=np.full((height, width), prior_std**2, np.float32),
            origin_fixation=reference,
            rig=rig,
            anchor_rotation=anchor,
            k=k,
            eye=eye,
        )

    @property
    def shape(self) -> tuple[int, int]:
        return (int(self.directions.shape[0]), int(self.directions.shape[1]))

    def reproject(self, fixation: Fixation, sampling: Any) -> tuple[NDArray[np.int_], BoolArray]:
        """Where each head-frame cell lands in the image at ``fixation``.

        Returns ``(index, visible)``: an ``(H, W, 2)`` array of ``(row, col)`` and
        an ``(H, W)`` mask of cells that fall inside the sensor.

        **The direction of the map matters and is the thing that can be wrong.**
        ``eye_rotations`` returns head <- eye, so eye <- head is the transpose.
        Getting it backwards is invisible at the anchor, where the relative
        rotation is the identity, so any test of it must move the gaze.

        **Azimuth, elevation and vergence all enter**, which is the whole
        correction. 17a routed this through ``rectification_rotation``, which
        zeroes azimuth and vergence, so a purely azimuthal saccade reprojected
        nothing while the world direction each cell viewed moved by the full
        saccade amplitude. Cells then fused measurements of unrelated directions.
        """
        current = np.asarray(
            getattr(eye_rotations(self.rig, fixation, k=self.k), self.eye), dtype=np.float64
        )
        # The RELATIVE rotation, anchor -> current. Exactly the identity at the
        # anchor, which is what preserves the fixed-eye control.
        head_to_eye = current.T
        in_eye = self.directions @ head_to_eye.T
        index = np.asarray(sampling.index(in_eye))
        visible = np.asarray(sampling.contains(index)) & (in_eye[..., 2] > 0.0)
        return index, visible

    def world_direction(self, index: Any, fixation: Fixation, sampling: Any) -> FloatArray:
        """The head-frame direction a sensor sample views at ``fixation``.

        Computed straight from ``eye_rotations``, deliberately NOT through
        :meth:`reproject`. It is the independent side of the invariance test: a
        cell must keep viewing the same world direction across a saccade, and
        checking that with the operator under test would prove nothing.
        """
        rotation = np.asarray(
            getattr(eye_rotations(self.rig, fixation, k=self.k), self.eye), dtype=np.float64
        )
        return np.asarray(sampling.direction(np.asarray(index, dtype=np.float64)) @ rotation.T)

    def gather(
        self, field: PosteriorArray, fixation: Fixation, sampling: Any, fill: float
    ) -> PosteriorArray:
        """Resample an image-frame ``field`` onto the head grid. Nearest-neighbour.

        Cells that fall outside the sensor take ``fill``. No interpolation, so no
        correlation is introduced and no variance correction is owed — see the
        module docstring.
        """
        index, visible = self.reproject(fixation, sampling)
        height, width = sampling.shape
        rows = np.clip(index[..., 0], 0, height - 1)
        cols = np.clip(index[..., 1], 0, width - 1)
        out = np.asarray(field)[rows, cols]
        return np.where(visible, out, fill).astype(field.dtype)

    def fuse(
        self,
        measurement: PosteriorArray,
        precision: PosteriorArray,
        fixation: Fixation,
        sampling: Any,
    ) -> None:
        """Reproject a measurement into the head frame and fuse it, in place.

        The arithmetic is ``ActiveStereo.step``'s, character for character — a
        scalar precision-weighted (Kalman) update with the same ``1e-6`` floor.
        Any deviation would make the fixed-eye control fail for a reason that is
        about arithmetic rather than about the frame, which is exactly the
        confusion the control exists to prevent.

        ``measurement`` and ``precision`` are in the image frame at ``fixation``.
        Cells that see nothing take zero precision, so they are left untouched by
        construction rather than by a mask.
        """
        z = self.gather(measurement, fixation, sampling, fill=0.0)
        prec = self.gather(precision, fixation, sampling, fill=0.0)
        prior_prec = 1.0 / np.maximum(self.var, 1e-6)
        post_prec = prior_prec + prec
        self.mean = (prior_prec * self.mean + prec * z) / post_prec
        self.var = 1.0 / post_prec

    def to_image(self, fixation: Fixation, sampling: Any) -> tuple[PosteriorArray, PosteriorArray]:
        """Read the belief back out in the image frame at ``fixation``.

        The inverse direction of :meth:`gather`, and the same nearest-neighbour
        operator. At the reference fixation it is the identity, so a caller that
        never rotates sees exactly the arrays it would have held in image
        coordinates.
        """
        index, visible = self.reproject(fixation, sampling)
        height, width = sampling.shape
        mean_img = np.full((height, width), np.nan, dtype=self.mean.dtype)
        var_img = np.full((height, width), np.nan, dtype=self.var.dtype)
        rows = index[..., 0][visible]
        cols = index[..., 1][visible]
        mean_img[rows, cols] = self.mean[visible]
        var_img[rows, cols] = self.var[visible]
        return mean_img, var_img
