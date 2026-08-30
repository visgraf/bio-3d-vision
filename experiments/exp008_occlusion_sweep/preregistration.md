# exp008 — does allocation value scale with occlusion?

**Pre-registered. Committed alone, before the runner exists.**

exp007 measured E-vs-A′ at **9.04× bar** on p90 on a rendered stimulus with ~2%
occluded surface, against the fixture's pooled **1.85×**. Occlusion fraction is
therefore a live variable and has never been swept.

**The result sought is a SLOPE, not a verdict**: how effect size varies with the
fraction of geometrically unmeasurable surface. This is instrument calibration as
much as a result — every question after this one will be asked on some stimulus,
and nobody knows what occlusion fraction makes those questions live.

**This bears on `gap-010` but does not lift it.** `gap-010` is about the FIXTURE
having no true half-occlusions; this characterises how much occlusion the
RENDERED stimulus needs. Annotate, do not close.

## A correction to exp007's headline number, measured before writing this

exp007 reported "5.09% lateral overlap". That figure **overstates genuine
occlusion**, and the reason is now measured:

| level | right-unmatched | left-occluded | difference |
|---|---|---|---|
| cards at 15% height | 3.48% | 0.36% | 3.12% |
| cards at 30% height | 3.81% | 0.68% | 3.12% |
| **exp007's geometry** | **5.09%** | **1.97%** | **3.12%** |
| cards split ×8 | 20.29% | 17.16% | 3.12% |

**The difference is constant at 3.12% regardless of the geometry.** It is the
frame border: left pixels whose correspondent falls outside the right image
because the right camera sits a baseline to the side. That is not occlusion, and
it does not vary with the scene.

So exp007's two measures differ "by more than a factor of two" (as the
specification notes) because one of them is ~61% frame border. **Genuine
occlusion in exp007's stimulus is 1.97%, not 5.09%.**

**`left_fraction` is therefore the x-axis of this sweep.** `right_fraction` is
reported at every level alongside it, with the border component shown, because
the specification is right that they are not the same quantity — and now it is
clear which one is which.

## The lever — one parameter, and the achieved fraction is measured

Each card is cut into `k` vertical strips separated by gaps that reveal
background, **within its original extent**. Depths, texture, seeds, materials and
camera are untouched. More strips means more vertical depth edges, and occluded
area is the sum over edges of (edge height × disparity step).

**Occlusion fraction is a measured outcome, not a dial.** Achieved values,
measured before this was written and to be re-measured by the runner:

| level | k | surfaces | **left-occluded (x-axis)** | right-unmatched | card area |
|---|---|---|---|---|---|
| **L1** | 1 | 4 | **1.97%** | 5.09% | 46.0% |
| L2 | 2 | 7 | **4.26%** | 7.38% | 30.2% |
| L3 | 4 | 13 | **8.84%** | 11.97% | 26.5% |
| L4 | 8 | 25 | **17.16%** | 20.29% | 24.6% |

**L1 is exp007's geometry exactly**, so the new series connects to a measured
point. The span is **8.7×** in genuine occluded fraction — roughly an order of
magnitude, from one lever.

`k = 10` was measured and **rejected**: occlusion turns over (19.86%, below
`k = 8`) because strips narrow past the 8.85 px disparity step and the geometry
degenerates. The sweep stops at `k = 8` for that reason, declared here rather
than discovered.

**A confound, declared: card area falls as `k` rises** — 46.0% to 24.6%,
monotone. It moves ~1.9× while occlusion moves 8.7×, but it moves in the same
direction, so this sweep **cannot fully separate occlusion fraction from card
area**. Card area is reported per level as a covariate. A design that held it
fixed would need the strips spread over a wider span than the original card
extent, which does not fit the frame for the two right-hand cards.

## What is run

| | |
|---|---|
| arms | A′, D, E |
| comparisons | **E vs A′** and **D vs E** |
| seeds | 0–7 |
| budget | **40**, matching exp002 and exp007 |
| levels | L1–L4 above |

Budget 40 is not negotiable downward: exp007 measured that at 18 steps E has
visited 26% of its 70-site lattice and reads four times worse than A′ — a
budget artefact, not an allocation result. Shortening it would reproduce that.

D and E are unchanged; no policy is modified.

## Scoring — the part most easily got wrong

> **Compare arms WITHIN a condition. Compare effect sizes ACROSS conditions.**

**No pixel set is ever taken across levels.** Coverage falls as overlap grows, so
a cross-condition intersection would shrink toward the least-occluded scene and
the sweep would measure its own masking. Within each level, exp003's intersection
rule applies between arms as usual.

exp001's two-clause bar, verbatim. **`mean_diff` and `bar` are reported
separately at every level, not `x_bar` alone** — both numerator and denominator
will move across the sweep and the trend is uninterpretable if they are
collapsed. `binds` is recorded so a materiality-bound verdict is visibly
different from a spread-bound one.

**Band-reported as in exp007** — AT, MIDDLE, AWAY, pooled, thresholds inherited
from exp004 unchanged. **As overlap grows the AT band grows with it**, and that
composition change is reported per level rather than folded into a pooled figure.
The bands are recomputed per level from that level's own geometry, since the
geometry is what changed.

## Falsifiers — four directions, and the one that occurred will be named

| | |
|---|---|
| **(a) MONOTONE INCREASE** | effect size grows with occluded fraction — the hypothesis. Report the slope, whether it is linear in the fraction or in something else, state the fit, and **do not over-read four points** |
| **(b) FLAT** | effect size independent of occlusion in this range. exp007's 9.04× was not about occlusion, and the gap from the fixture's 1.85× was the artefact's removal rather than occlusion's presence. **Would redirect the next iteration toward the loop rather than the stimulus** |
| **(c) MONOTONE DECREASE** | allocation matters *less* where surface is unmeasurable — contradicts the mechanism assumed throughout, and the most interesting outcome available |
| **(d) NON-MONOTONE** | a peak or threshold. Report where. An optimum occlusion fraction is a stronger claim than a slope and would size every stimulus after this one |

Classification is on `x_bar` at pooled, per comparison per metric, with the band
series reported alongside. Monotonicity is judged on the four measured points in
order of achieved `left_fraction`, not of `k`.

### Declared predictions, under the hypothesis

- **E vs A′ — (a), on both metrics.** If variance's value comes from marking
  geometrically unmeasurable surface, more such surface should mean more value.
  The p90 effect should grow faster than the median, since occlusion is a tail
  phenomenon.
- **D vs E — (b) or a weak (a).** D vs E measures the *validity mask's* worth,
  which exp005 and exp007 both found band-invariant and overwhelming
  (26–48× bar). A quantity that large and that stable is unlikely to track
  occlusion within this range.
- **Least confident about the shape.** Four points cannot distinguish linear from
  saturating, and (d) is entirely possible if the effect saturates once occlusion
  exceeds the matcher's window.

## What this does not do

- **No contrast axis. `od-002` stays open.** Its subject is contrast at occlusion
  boundaries, which needs *material* changes rather than geometry, and it is
  better asked once this sweep says which occlusion fraction makes the regime
  visible. **`od-002`'s `why_not_scheduled` is stale and will be corrected**: it
  reads "the repository does not run yet, and od-001 has not been implemented",
  and both conditions have been met — the loop runs on two stimuli and od-001
  closed at `fc-009`.
- **No acquisition, no `od-003`, no change to any policy.**
- **`gap-010` annotated, not closed.**
