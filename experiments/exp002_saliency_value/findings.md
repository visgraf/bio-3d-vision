# exp002 — variance does carry information, and the mask carries far more

**Run:** 6 arms × 16 seeds × 40 fixations, raster pitch 35.449, commit `c0b54a4`
**Pre-registration:** [`preregistration.md`](preregistration.md), committed alone at `9179a55` before the runner existed
**Evidence:** [`results.json`](results.json), [`verdicts.json`](verdicts.json), [`extension45.json`](extension45.json)

**Verdict: falsifier 1 does NOT fire. Falsifier 2 fires — D does not tie with E.**

## Harness check first

Declared in advance: seeds 0–7 at step 18 must reproduce exp001, or nothing here
is comparable. **They reproduce exactly** — `max|Δ| = 0.000e+00` for A, A′, B and
C. exp001 is re-derivable from this run.

## Results

Means over 16 seeds at fixation 40. Primary metrics in bold.

| arm | information used | **median \|err\| (m)** | **p90 (m)** | rmse (m) | distinct/40 | on invalid |
|---|---|---|---|---|---|---|
| D — blind raster | none | **0.02912** | **0.6026** | 0.5061 | 40.00 | **19.44** |
| E — masked coverage | mask only | **0.01059** | **0.4281** | 0.4744 | 40.00 | 0 |
| A — argmax v | v | **0.01414** | **0.4314** | 0.4781 | 10.06 | 0 |
| B — argmax Δ_c | v | **0.01339** | **0.4333** | 0.4763 | 15.00 | 0 |
| C — argmax Δ_total | v | **0.01097** | **0.3766** | 0.4738 | 30.38 | 0 |
| A′ — argmax v + IOR | v | **0.01030** | **0.3785** | 0.4735 | 40.00 | 0 |

## Falsifier 1 — does NOT fire. Variance carries information beyond the mask.

| comparison | metric | diff | bar | × bar | verdict |
|---|---|---|---|---|---|
| E vs A′ | median | +0.00028 | 0.00021 | 1.38 | **DISTINGUISHABLE, E worse** |
| E vs A′ | p90 | +0.04957 | 0.02535 | 1.96 | **DISTINGUISHABLE, E worse** |
| E vs C | median | −0.00038 | 0.00052 | 0.74 | indistinguishable |
| E vs C | p90 | +0.05154 | 0.02375 | 2.17 | **DISTINGUISHABLE, E worse** |

E is distinguishably worse than A′ on **both** primary metrics and worse than C on
p90. So **posterior variance does contribute beyond the validity mask on this
stimulus**, and the strong outcome — that the allocation half of the framework's
claim is empty — does not hold here.

Per the pre-registration, the consequence is that **exp001's null was narrower
than it appears**: a null about the *choice among variance-derived objectives*,
not about saliency. `fc-007`'s scope is annotated accordingly, and the annotation
is added rather than the original verdict edited.

### The caveat that nearly overturned this, and the check that resolved it

The declared convergence analysis showed **A′ and C had converged by step 40
while D and E had not**:

| arm | median improvement over steps 35→40 | p90 improvement |
|---|---|---|
| A′ | −0.00006 (flat) | −0.00018 (flat) |
| C | +0.00002 (flat) | −0.00005 (flat) |
| **E** | **+0.00209** | **+0.10411** |
| **D** | **+0.00224** | **+0.31970** |

At that rate the E–A′ median gap was **0.7 steps of E's own improvement**, and the
p90 gap 2.4 steps. On those numbers the headline was plausibly an *approach-rate*
artefact — exactly the possibility the pre-registration extended the budget to
detect — and E could not simply be given more budget, because its lattice holds
only 45–48 points.

So E, A′ and D were re-run to **45 fixations**, E's lattice minimum. **Post-hoc,
and not part of the pre-registered verdict.** It went against the caveat:

| metric | A′ @40 → @45 | E @40 → @45 | E vs A′ @45 |
|---|---|---|---|
| median | 0.01030 → 0.01036 | 0.01059 → **0.01060** | +0.00024, 1.17× bar — **distinguishable** |
| p90 | 0.37853 → 0.37878 | 0.42810 → **0.44496** | +0.06618, 1.55× bar — **distinguishable** |

E has stopped improving (median moved 1e-5; **p90 got worse**), and the gap
persists. The difference is not approach rate. Falsifier 1's verdict stands, and
stands on stronger evidence than the pre-registered budget alone provided.

## Falsifier 2 — fires. D does not tie with E, by a wide margin.

| metric | E | D | diff | bar | × bar |
|---|---|---|---|---|---|
| median | 0.01059 | 0.02912 | +0.01854 | 0.00039 | **47.0** |
| p90 | 0.42810 | 0.60255 | +0.17445 | 0.02967 | **5.9** |
| rmse | 0.47436 | 0.50612 | +0.03176 | 0.00949 | 3.4 |

The validity mask is not free information. D spends **19.44 of its 40 fixations
(49%) outside the valid region** — its lattice is blind to where the data is, so
roughly half its budget lands where no measurement can be made.

## The two gaps, named and quantified

The pre-registration declared these names in advance to prevent conflating them.

| | median \|err\| | p90 |
|---|---|---|
| D (nothing) | 0.02912 | 0.6026 |
| E (mask only) | 0.01059 | 0.4281 |
| A′ (mask + variance) | 0.01030 | 0.3785 |
| **value of the validity mask** (D→E) | **0.01854 m — 63.7% of D** | **0.17445 m — 29.0% of D** |
| **value of posterior variance beyond the mask** (E→A′) | **0.00028 m — 2.7% of E** | **0.04957 m — 11.6% of E** |
| ratio, mask : variance | **65 : 1** | **3.5 : 1** |

Recorded as `bio-014`..`bio-017`.

**The channels are worth very different amounts, and the ordering is not close.**
On the median, knowing *where the data is* is worth 65× more than knowing *how
uncertain it is*. On p90 the ratio narrows to 3.5:1 — variance earns most of its
keep in the tail, which is where the hard pixels are and is the one place a
saliency signal should matter.

Stated the other way round, because it is the honest framing: **a policy that
knows only where the data is recovers 97.3% of the median-error benefit of the
full variance-driven policy, and 88.4% of the p90 benefit.** Variance is not
worthless. It is a small correction on top of a much larger effect that is purely
about coverage.

## Trajectories

Mean median |err| by fixation (16 seeds). Rasters are terrible until they have
swept the frame, then overtake:

| step | A | A′ | B | C | D | E |
|---|---|---|---|---|---|---|
| 1 | 0.39409 | 0.39409 | 0.50514 | 0.21776 | 0.60000 | 0.60000 |
| 5 | 0.01228 | 0.01228 | 0.02436 | 0.01960 | 0.59993 | 0.58908 |
| 10 | 0.01247 | 0.01204 | 0.01305 | 0.01330 | 0.51508 | 0.24437 |
| 18 | 0.01294 | 0.01118 | 0.01316 | 0.01083 | 0.51341 | 0.04438 |
| 25 | 0.01341 | 0.01036 | 0.01342 | 0.01091 | 0.03591 | 0.04574 |
| 40 | 0.01414 | 0.01030 | 0.01339 | 0.01097 | 0.02912 | 0.01059 |

**Convergence indices** (smallest step from which a pair stays indistinguishable):
E vs A′ — never within 40; E vs C — median at 36, p90 never; D vs E — never;
C vs A′ — p90 at 11, median never. **No pair reaches a common asymptote within the
budget.** The arms are not converging to one answer at different rates; they
converge to different answers.

**A's lockup is far worse at 40 steps than at 18**: 10.06 distinct fixations of 40,
and its median error *rises* monotonically from 0.01197 at step 6 to 0.01414 at
step 40. Extending the budget makes the ported baseline worse, not better.

## Re-check of exp001's C_vs_B — it flips

exp001 recorded `C_vs_B` indistinguishable at a margin of 0.00181 against a bar of
0.00187 (0.97× — under 4% clear). Re-evaluated at exp001's own endpoint, step 18,
with 16 seeds instead of 8:

| | exp001 (8 seeds) | exp002 (16 seeds) |
|---|---|---|
| median diff | +0.00181 | **+0.00233** |
| bar | 0.00187 | 0.00210 |
| × bar | 0.97 | **1.11** |
| verdict | indistinguishable | **DISTINGUISHABLE, B worse** |

**It flips.** The exp001 findings are amended **by addition** — the original
verdict is left in place, as declared. exp001's falsifier-2 conclusion is
unaffected: it fired on the argmax disjunct (0/144 agreement), which this does not
touch, and the flip strengthens rather than weakens it.

## Not pre-registered, but worth recording: C vs A′ also separates

At 40 fixations with 16 seeds, C is distinguishably **worse** than A′ on median
(+0.00066, 1.05× bar), where exp001 found them indistinguishable at 18 fixations
with 8 seeds. Marginal, and it points the same way `fc-007` already went — the
cheap remedy is at least as good as the field integral — so `fc-007` is
strengthened, not threatened. Flagged as a post-hoc observation at 1.05× its bar,
not a result.

## The limit

**This fixture has no true half-occlusions.** Its right image is resampled from
its left, so high posterior variance here never marks a region that is
geometrically *unmeasurable* — only one that is hard to match. Every number above
therefore describes a stimulus in which the two structurally different sources of
high variance are represented by one of them.

**So this holds for a stimulus without half-occlusions and no further.** The
finding most exposed to that limit is the headline ratio: on a stimulus with real
occlusions, the variance channel would be carrying a signal about geometric
unmeasurability that it simply cannot carry here, and 65:1 could move a long way.

Lifting the limit needs a rendered stimulus with a controlled contrast axis at
occlusion boundaries — `gap-001`, `od-002`. **The fixture will not be grown**
(`fc-004`).

## Threats

- **The E–A′ median verdict is close.** 1.38× the bar at 40 and 1.17× at 45. The
  p90 verdict is more robust (1.96× and 1.55×), and the D–E verdict is not close
  at all (47×).
- **The 45-step extension is post-hoc.** It is reported as a check on a caveat,
  not as a verdict, and the pre-registered verdict at 40 is stated separately.
- **E's raster is nearly exhausted at 45**, so "more budget" is not available to
  E without changing the pitch, which would change the arm.
- **One fixture, one matcher, one pitch.** All arms inherit the port's three
  defects.
