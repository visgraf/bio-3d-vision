# exp002 — does posterior variance carry any information beyond the validity mask?

**Status: PRE-REGISTERED. Declared before the runner existed, and committed alone.**

## The gap this closes

exp001 compared four arms — A, A′, B, C — and **all four were informed by
posterior variance**. A and A′ maximise it; B and C maximise a quantity derived
from it. So `fc-007` establishes that *the choice among variance-derived
objectives does not matter*. It does not establish that variance matters **at
all**, because nothing uninformed was ever run.

This experiment runs the uninformed arms.

| | policy | information used |
|---|---|---|
| **D** | blind raster — a fixed deterministic scan of the frame | **none** |
| **E** | masked coverage — the same spacing, restricted to valid pixels | **the validity mask only** |

Neither reads `engine.var`. E is D plus one bit per pixel.

## The raster pitch, and why this is the fair choice

The spacing must be comparable to `INHIBITION_RADIUS = 20.0`, or the comparison
confounds *policy type* with *spacing scale*. Raising this before running, as
required, because an incomparable spacing makes the whole experiment unreadable.

**Derivation.** A′ excludes a disc of radius `R` around every fixation, so each
of its fixations claims an area of `πR²`. A square lattice of pitch `p` claims
`p²` per point. Equalising the **areal footprint per fixation** gives

    p = R·√π = 20.0 × 1.77245 = 35.449 px

**Why not `p = R`.** Matching the pitch to the radius equalises a length against
a radius, which makes the raster π× denser than A′'s constraint implies. Measured
on the committed fixture (seed 0, valid area 53098 px):

| pitch | lattice points in valid | area claimed by 40 fixations |
|---|---|---|
| `p = R = 20` | 155 | 16 000 px² — **30% of the valid area** |
| `p = R√π = 35.449` | 46 | 50 265 px² — **95% of the valid area** |

At `p = R` a 40-fixation budget would visit 26% of the lattice and cover under a
third of the frame. D would then lose to A′ because **it looked at less of the
image**, not because it was blind — precisely the confound the requirement exists
to prevent. `p = R√π` makes 40 fixations tile the frame almost exactly once,
which is what A′'s inhibition radius implies for 40 non-overlapping fixations.

A second property, checked: the minimum separation of a pitch-35.449 lattice is
35.449 px, which is **greater** than the 20 px A′ enforces. So D and E are never
*less* spread than A′ is required to be, and cannot win on separation alone.

**Lattice definitions.**

- **D** — pitch 35.449, anchored at `(0, 0)`, spanning the **whole frame**
  (240×320), row-major. **70 points.** D does not know where the valid region is,
  so roughly 41% of its lattice falls outside it and those fixations are largely
  wasted. That is what "uses no information" means here, and it is the measured
  quantity, not an artefact. Verified before declaring: fixating deep in the
  invalid band does not fail — `vergence`'s window finds no valid pixel, falls
  back to the raw `d_sub`, and the result is clamped to `D_fix ∈ [0.5, 8] m`.
- **E** — the same pitch, laid over the **valid region's bounding box** (rows
  8–231, cols 64–311, identical on all 16 seeds because it is fixed by the border
  constraint), row-major, skipping any lattice point that is invalid. **45–48
  points** depending on seed, minimum 45 across the 16 seeds, so a 40-fixation
  budget never exhausts it.

E is given the mask twice over — to place its raster and to skip holes — because
E is the "mask only" arm and should be the strongest version of that. D is given
nothing.

## Reused from exp001, deliberately

Reusing exp001's declared threshold rather than declaring a fresh one is what
makes the two experiments comparable. A new bar chosen now, with exp001's
trajectories already known, would also be exactly the failure that
pre-registration exists to prevent.

- **Primary metrics:** median absolute depth error and p90, over valid known
  pixels. **RMSE secondary**, reported but not decisive (`bio-007`: the worst 5%
  of pixels carry 80.9% of squared error).
- **The two-clause bar, verbatim:**

  > Distinguishable on a metric iff `|mean(dₛ)| > max( sd(dₛ), 0.02 × mean(M_baseline) )`
  > — the margin must exceed both the seed-to-seed spread and a 2% materiality
  > floor. Two arms are indistinguishable iff neither primary metric is
  > distinguishable.

- **Seeds: 0–15 (16).** A **superset** of exp001's 0–7, with those eight as a
  prefix, so exp001's runs are re-derivable from this one and the extra eight are
  genuinely new. Paired across arms, as before.
- **Existing policies are not modified.** D and E are added alongside.

## Added: a budget past 18

**Budget: 40 fixations** (exp001 used 18). If all arms converge to a common
asymptote and differ only in approach rate, that is the finding, and an 18-step
budget cannot see it.

Declared analysis: for each pair and each metric, apply the bar at **every**
fixation index `k`, and report the **smallest `k` such that the pair is
indistinguishable at every `k′ ≥ k`** — the convergence index. If no such `k`
exists within the budget, that is reported as "never within 40".

## Comparisons and what each outcome means

**Falsifier 1.** If **E is indistinguishable from A′ and from C** at the exp001
bars, then posterior variance contributes nothing beyond the validity mask on
this stimulus. The allocation half of the framework's claim is empty here, and
what remains of "active" in this loop is spacing plus knowing where the data is.
**This is the strong outcome and it argues against the project's own premise; it
will be reported plainly if it happens.**

If instead **E is distinguishably worse than A′**, the opposite holds: variance
does carry information, exp001's null was narrower than it looks — a null about
the *choice among objectives*, not about saliency — and `fc-007`'s scope is
annotated to say so.

**Falsifier 2.** If **D ties with E**, even the validity mask contributes nothing
and the result is purely about spacing. If **D is materially worse than E**, the
gap is quantified and recorded in `docs/inherited-measurements.yaml` with
`status: measured`, not left in prose.

A note on naming, declared now to avoid a later conflation: the **D→E** gap
measures the value of the **validity mask**; the **E→A′** gap measures the value
of **posterior variance beyond the mask**. Both will be reported under those
names.

## One check on exp001, while the harness is open

`C_vs_B` was recorded indistinguishable at a margin of 0.00181 against a bar of
0.00187 — under 4% clear, with B worse on all three metrics. It will be
re-evaluated at **step 18** (exp001's own endpoint) with **16 seeds**.

Declared in advance: if it flips, the exp001 findings are amended **by addition**,
leaving the original verdict in place — the disagreement is the information.
Also declared as a harness check: at seeds 0–7 and step 18 this run must
reproduce exp001's recorded values, or the harness has drifted and nothing here
is comparable.

## The limit, unchanged

`gap-010`: **this fixture has no true half-occlusions.** Its right image is
resampled from its left, so high posterior variance here never marks a region
that is geometrically unmeasurable — only one that is hard to match. Whatever is
concluded holds **for a stimulus without half-occlusions and no further**, and
that limit is stated in the foreclosure itself rather than by pointing at
`fc-007`.

**The fixture will not be grown to add occlusions** (`fc-004`).

## Cost, measured before declaring

B and C evaluate 3314 candidates per step at ~0.55 ms each — 1.8 s per step, so
~19 min per arm over 16 seeds × 40 steps. A, A′, D and E are milliseconds.
Total ≈ 45 minutes.

A framework-level foreclosure will be written into `docs/state.yaml` whichever
way this goes.
