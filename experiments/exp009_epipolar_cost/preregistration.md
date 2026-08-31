# exp009 — what the epipolar violation costs, and whether d_v is measurable

**Pre-registered. Committed alone, before the runner exists.**

**This iteration measures. It does not decide.** No foreclosure, no default
adopted, no 17c. The decision — rectify before matching, or accept the violation
and search in 2D — is the maintainer's, on these numbers, in the next turn.

## The Chat-side reasoning, checked — and it changes the arm

**The no-parallax half is right.** Rectification is a pure rotation of each camera
about its own optical centre, which induces no parallax, so rendering with the
rectified orientation and rendering toed-in then warping give the same image up to
resampling. Rendering directly avoids an interpolation loss that would correlate
neighbouring pixels — the same variance problem the belief's nearest-neighbour
choice sidesteps. **So the RECT arm renders rectified rather than warping.**

**The second half is wrong, and not because of the member chosen.** The
specification says to compose `rectification_rotation` into `eye_camera_poses`. I
first assumed the problem was ADR-0017's particular member and tried to build a
gaze-aligned one. It produced *the same forward axis*, and the reason is
geometric rather than a matter of choice:

> A rectifying orientation must have its **x-axis along the baseline**. That forces
> its forward axis into the plane perpendicular to the baseline — which is
> **azimuth zero**. No member of the rectification family can point at an
> azimuthally eccentric fixation.

Measured consequence, at f_px 700 on a 320×240 sensor (half-field **12.88°**
horizontal, 9.73° vertical):

| fixation | rect forward vs eye forward | fixation point in frame? |
|---|---|---|
| az 0.00 | 1.72° | yes |
| az 0.10 | 7.44° | yes |
| az 0.15 | 10.31° | yes |
| az 0.20 | ~13.4° | marginal |
| **az 0.225** | **12.89°** | **NO** |
| az 0.30 | 18.89° | **NO** (≈27% view overlap) |

**Rectification keeps the fixated region in frame only for |azimuth| < 0.225 rad**,
unless the principal point is shifted — and the renderer has no principal-point
shift.

**That bound coincides with the policy's reach.** A′ selects argmax variance
*within the current image*, so a saccade is at most half a field: **0.225 rad
azimuth, 0.170 rad elevation**. The amplitude at which rectification loses the
fixation is exactly the largest amplitude 17c can produce. That coincidence is
reported as a finding, not designed.

**What it changes:** the two arms do not image the same region at eccentric gaze,
so a naive pixel-to-pixel comparison would measure scene content rather than
matcher accuracy. The comparison is therefore made in a **common frame over the
region both arms actually see**, defined below.

## The common frame

Both arms' Blender Z passes are in *different camera frames* and are not
comparable. A comparison of two depth maps in two frames is not a measurement.

> **The common quantity is RANGE FROM THE CYCLOPEAN ORIGIN, as a function of
> head-frame direction.** Range from a fixed origin is frame-free.

Per arm, per left-image pixel: the matcher's horizontal disparity scales to a
planar depth `Z` in that arm's left-camera frame; the 3-D point is
`C_left + Z · (unit-z ray)`, carried into the head frame by that arm's own left-eye
rotation. Its head-frame **direction** and its **range** `|P|` follow.

Ground truth is expressed the same way, from that arm's own rendered Z pass, so
each arm is scored against truth **in its own render** and only the resulting
errors are compared. `HeadFrameBelief`'s anchored grid supplies the direction
lattice and the visibility mask; comparison is restricted to directions **both**
arms see.

## Arms and fixations

| arm | cameras | search |
|---|---|---|
| **RECT** | both at `rectification_rotation(fixation)` — a valid rectifier, x-axis exactly `[1,0,0]` | existing 1-D horizontal |
| **TOED** | per-eye from `eye_rotations(fixation)` | 2-D over `(d_v, d_h)` |

Fixations at vergence 0.06, spanning on-axis to beyond the policy's reach:

| az, el (rad) | deg | why |
|---|---|---|
| 0.00, 0.00 | 0.0, 0.0 | the arms must coincide here; d_v is exactly 0.00 px |
| 0.08, 0.05 | 4.6, 2.9 | a modest saccade |
| **0.15, 0.10** | **8.6, 5.7** | **the 17c-plausible amplitude** — comfortably inside the half-field, reachable by a saccade to an image quadrant |
| 0.20, 0.15 | 11.5, 8.6 | near the policy's limit of 0.225/0.170 |
| 0.30, 0.20 | 17.2, 11.5 | stress case, **beyond** the policy's reach: 2.41 px predicted d_v, and the fixation leaves the rectified frame |

Seeds 0–3, four per fixation. Fewer than exp001's eight, and stated: this
measures a matcher property, not a policy outcome, and the seed varies only the
texture.

## The 2-D search band, derived rather than picked

The predicted maximum vertical disparity from `eye_rotations` over scene points at
fixture depths, rounded up with a stated margin:

| fixation | predicted max d_v | |
|---|---|---|
| 0.00, 0.00 | 0.00 px | |
| 0.15, 0.10 | 1.43 px | |
| 0.30, 0.20 | 2.41 px | |

**Band: ±4 px.** That is the 2.41 px maximum rounded up to 3 with a 1 px margin
for the sub-pixel interpolant. **The amplitude beyond which ±4 is too narrow** is
where predicted d_v exceeds 4 px; from the trend that is beyond az ≈ 0.5 rad,
which no policy here can reach. Reported with the results.

## What is also measured

**Matcher wall-clock, both arms.** Chat measured `cost_volume` at 0.071 s for 57
disparities and `front_end_block` at 0.381 s against a 0.57 s render, and predicts
a ±2 band makes the loop matcher-bound rather than render-bound — inverting 17b's
conclusion. **Verified here, not adopted**: a ±4 band is 9 vertical offsets, so the
naive cost is 9×.

## Measurement 2 — is d_v measurable at all

From TOED's 2-D argmin, the estimated vertical disparity per pixel, against the
per-pixel geometric prediction from `eye_rotations`.

**This is NOT a test of whether vertical disparity is a useful cue.** Nothing here
consumes `d_v` — L4 scales on horizontal disparity alone — so its usefulness
cannot be tested and this experiment does not claim to. The question is narrower:
**at 1.0–2.4 px on a 7 px window, is the estimate signal or noise?**

Reported: correlation and residual against the prediction over valid pixels with
`n`, **separately AT (≤10 px) and AWAY (≥24 px) from depth discontinuities** per
exp004's thresholds. If `d_v` is recoverable only where the surface is smooth,
that is the answer and it must be visible rather than pooled away.

## Falsifiers

**Measurement 1** — (a) TOED matches RECT within exp001's bar → the violation is
free and the decision turns on commitments, not accuracy. (b) TOED worse → quantify
against the matcher cost. (c) TOED better → **report before anything else**;
rendering rectified is a different view, so this is possible and would mean
rectification loses something beyond `d_v`. (d) both degrade off-axis relative to
on-axis → something else breaks with eccentric gaze; the vergence estimator and
the pixel-native foveal weight are the two candidates already on record.

**Measurement 2** — (e) `d_v` tracks the prediction → the cue is measurable at this
scale. (f) `d_v` is noise → rectification forecloses nothing of present value;
**this argues against Chat's position in the preceding discussion and will be
reported plainly if it happens.** (g) systematic offset → the geometry or the
search indexing is wrong, not the cue; locate it.

### Declared predictions, under the expectation that the violation is small

- **Measurement 1: (a) at small amplitude, (b) at 0.30/0.20.** A 1.4 px violation
  against a 7 px window should cost little; 2.4 px should start to bite. **Least
  confident about (c)**, which the view-overlap finding makes more plausible than
  it first looked — at az 0.30 the RECT arm images a largely different region and
  its errors are not obviously comparable.
- **Measurement 2: (f) AT discontinuities, (e) AWAY from them.** Sub-pixel
  vertical structure needs a smooth local surface; at an occlusion boundary the
  2-D argmin has no reason to land at the true `d_v`.

## What this does not do

No 17c, no closed loop, no policy change, **no foreclosure**, and no plan
amendment beyond recording that this experiment was inserted before 17c and why.
Does not test whether vertical disparity is a useful cue. Does not touch `od-002`,
`od-003`, or ADR-0013's inherited claim beyond measuring whether the quantity it
names is recoverable.
