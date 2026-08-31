# exp010 — does re-acquiring beat re-weighting?

**Pre-registered. Committed alone, before the runner exists.**

The first experiment in either repository in which **an action changes the
sensory data**. Both predecessors built the components for this and neither ran
it.

## Both arms are rectified, and that is not a formality

| arm | render | match | belief |
|---|---|---|---|
| **OPEN** | ONE RECT+ render at the initial fixation | re-matched per fixation at a new pedestal | fused per fixation |
| **CLOSED** | a RECT+ render at **each** fixation | matched per fixation | fused per fixation through the reprojection |

**The arms differ in one thing: whether the proposed saccade is executed.** Both
propose identically — argmax posterior variance over the belief, resolved to a
ray, carried through `target_to_fixation`. CLOSED moves the eye to it; OPEN does
not. That is the whole contrast, and it is why re-rendering is isolated.

**Why OPEN must also be RECT+.** bio-063 measures `rectified_camera_poses` and
`eye_camera_poses` as *different eye alignments*: `eye_rotations(...).left` points
half a vergence — 1.72° at 0.06 — outside the cyclopean gaze, and the rectified
path keeps 6.4 points more of the belief grid at the policy's reach. An OPEN arm
built on the toed-in path would differ from CLOSED in **eye alignment as well as
re-rendering**, and outcome (a) would be unreadable. Recorded as a measured
property with its 1.72° cause, not as a bonus for rectification.

## The stimulus, and why this level rather than an inherited one

`split_cards(scene_from_fixture(seed), k=4)` — **8.84% left-occluded**, measured,
not assumed.

Chosen because exp008 measured the allocation question to be **sharpest there and
unaskable above it**: E-versus-A′ on p90 peaks at 3.10 at 8.84% and collapses to
1.01 at 17.16%, where a blind raster and a variance-driven policy sit within
0.0165 m of each other because every arm leaves most of the frame at the prior.
A closed-loop benefit, if it exists, is a benefit in *allocation*; measuring it at
a level where allocation itself is undetectable would test nothing. **8 seeds,
budget 40 fixations**, matching exp008's matched block.

## What must be converted, and why — the head frame is not free

`ActiveStereo` returns **planar `z` in the rectified left-camera frame at the
measuring fixation**, which `oculomotor.py:460-466` states is *fixation-dependent*:
the same world point has a different bare `z` at a different fixation.

> **Fusing that across fixations would fuse different quantities into one cell.**

This has been latent in `HeadFrameBelief` since 17a and could not surface, because
nothing had ever moved the eye. It is the same shape as the predecessor's
CLAUDE.md §3 — a frame claim that nothing could contradict until something used it.

Rectification narrows it but does not remove it: the rectified frame's axis is at
azimuth zero always, so `z` depends on the fixation's **elevation** only. Narrower
is not zero.

**So the runner converts each measurement to RANGE FROM THE CYCLOPEAN ORIGIN
before fusing**, with the variance carried through the same Jacobian
`d(range)/dz = (P·m)/D` that `target_to_fixation` already computes. Range from a
fixed origin is frame-free — exp009 established this as the common quantity for
exactly this reason. Scoring is in range. `HeadFrameBelief` is **not** changed;
the conversion is in the experiment, and the latent issue is reported rather than
silently repaired.

## Scoring

**Head frame, one common cell set.** exp003's rule: compare on the intersection of
the two arms' measured sets; **report the excluded sets separately** and label any
pooled figure that crosses them. Ground truth per cell is the anchor render's own
depth pass, converted to range the same way — cell `(i,j)` is anchor pixel `(i,j)`
by construction of the grid.

**Bands per exp004**: AT ≤10 px, MIDDLE 10–24 px, AWAY ≥24 px of a depth
discontinuity, `|Δd_gt| > 1.0 px`.

**Both `mean_diff` and `bar`, never `x_bar` alone.** exp008 showed a verdict
flipping on the denominator while the effect grew.

## The grid-loss budget, which a closed loop pays and an open one does not

Reported per arm: the fraction of the belief **ever measured at all**, the fraction
**surviving the whole run** (on-sensor at every executed fixation), and the
per-saccade loss against bio-063's curve. 17a-fix measured 39.4% of the grid
leaving the sensor at 10° of azimuth and 51.6% at 10° of elevation; CLOSED pays
that on every saccade and OPEN pays it never.

## Carried unchanged, and named so a result is not read into them

- **The foveal weight is a Gaussian in row and column; the vergence window is a
  square in pixels.** fc-009 records this. On a rectified pair the lattice is the
  fixation's own, so it is defensible here — and it is *stated*, not left implicit.
  An angular foveal weight would change none of the geometry below and would
  remove the sensor from the policy path; it is 17/18 work.
- **bio-065: the shift centres the gaze DIRECTION, the target is a POINT.** The
  fixation images `+d/2` from the sensor centre in the left eye — 21 px at
  vergence 0.06 against `fovea_sigma` 34, and 56 px at 0.16. The foveal peak is
  therefore **not on the target**, and the miss grows as the loop verges nearer.
  **Not fixed.** An arm that verges nearer is penalised by the apparatus.
- **fc-010's vergence estimator has no signed out-of-range error.** Carried
  unchanged. **If the closed loop's vergence wanders, that is fc-010's mechanism
  arriving in the loop, not a new finding.**

## Falsifiers

**(a) CLOSED beats OPEN.** The first positive result for active vision in either
repository. **Reported with its cost** — renders, matcher seconds, grid loss —
never as a headline.

**(b) Indistinguishable.** Re-acquiring buys nothing on this stimulus at this
occlusion. State what would have to change: more occlusion (exp008 bounds it
above at 17.16%), a larger budget, or a policy that is not greedy argmax variance.

**(c) CLOSED worse.** **Say where.** Three candidates are already on record and
distinguishing them is the finding: grid loss (bio-063), vergence drift (fc-010),
and accumulated reprojection quantisation (the belief resamples nearest-neighbour
on every saccade).

**(d) CLOSED cannot be run to completion** — vergence wanders out of range, the
belief empties, or `target_to_fixation` refuses. **Report where it fails and at
which fixation.** This is fc-010's mechanism arriving in the loop and it is a
result, not a bug.

**Nothing is tuned to avoid (c) or (d).**

### Declared predictions

- **(c) or (d) over (a).** The loop has three known-broken parts pointed at it
  simultaneously — a foveal weight that misses its target by 0.6σ, a vergence
  estimator that cannot report a sign, and a greedy argmax with no inhibition of
  return (`loop.py` DEFECT 3) that has already been measured to revisit one pixel
  for ten consecutive steps. A closed loop makes all three worse, because each now
  also moves the camera.
- If (a) does occur, **the coverage term is the likely mechanism, not accuracy** —
  CLOSED can measure cells OPEN never images at all.

## What this does not do

No angular foveal weight, no od-003 retest, no od-002 contrast axis, no
omnidirectional work, no change to `HeadFrameBelief`, no fix to bio-057's
positive-only cost volume. **If the loop needs any of them to run at all, the
result is that finding, reported — not a loop that runs because something was
quietly fixed.**
