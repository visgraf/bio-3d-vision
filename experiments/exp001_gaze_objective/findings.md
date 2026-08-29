# exp001 — the gaze objective does not matter; not repeating does

**Run:** 4 arms × 8 seeds × 18 fixations, stride 4, commit `ed0683a`
**Pre-registration:** [`preregistration.md`](preregistration.md), committed alone at `19aee2a` before any arm was run
**Evidence:** [`results.json`](results.json), [`verdicts.json`](verdicts.json)
**Verdict: falsifier 1 fires. Falsifier 2 fires. Both.**

## The declared stride check failed, and the protocol was followed

The pre-registration declared stride 8 with a check that halving must not move
the step-1 selection, and: *"if it does, the grid is too coarse and the stride is
reduced before any arm is scored."* It did.

| stride | candidates | step-1 selection | halving |
|---|---|---|---|
| 8 | 824 | (128, 176) | **CHANGED** |
| 4 | 3314 | (120, 180) | unchanged (4→2) |
| 2 | 13269 | (120, 180) | **CHANGED** (2→1) |
| 1 | 53098 | (118, 187) | — |

Stride was reduced to **4**, which passes its own check, and the stride-8 run was
discarded rather than reported. Reported anyway because it qualifies everything
below: **stride 2 fails the same test**. The picks are 7–9 px apart — a fifth of
the 34 px fovea σ — so the objective is *flat near its maximum* and the exact
argmax pixel is not stable under grid refinement. That is a fact about the
objective, and it anticipates the main result.

## Results

Means over 8 seeds, at the final fixation. Primary metrics in bold.

| arm | **median \|err\| (m)** | **p90 (m)** | rmse (m) | distinct/18 | wasted budget |
|---|---|---|---|---|---|
| A — argmax v (ported) | **0.01318** | **0.4118** | 0.4753 | 9.62 | 0.576 |
| A′ — argmax v + IOR | **0.01126** | **0.3674** | 0.4725 | 18.00 | 0.312 |
| B — argmax Δ_c(c) | **0.01244** | **0.4200** | 0.4762 | 11.88 | 0.424 |
| C — argmax Δ_total(c) | **0.01063** | **0.3685** | 0.4729 | 17.50 | 0.000 |

Two of those columns are partly tautological and are flagged rather than left to
mislead. **C's wasted budget is 0.000 by construction** — C maximises Δ_total, so
its choice is never below the grid median; this is a check that C does what it
says, not evidence that it is better. **A′'s 18.00 distinct is also by
construction**, since inhibition of return forbids a revisit within 20 px. The
informative number in that column is **C's 17.50 without any inhibition
mechanism**: the expected-reduction objective self-inhibits, as the
pre-registration predicted it should.

### Verdicts against the pre-registered rule

Rule: distinguishable iff `|mean(dₛ)| > max(sd(dₛ), 0.02 × mean(M_baseline))`.

| comparison | metric | diff | bar | verdict |
|---|---|---|---|---|
| **C vs A′** | median | −0.00063 | 0.00088 | indistinguishable (0.72 of bar) |
| **C vs A′** | p90 | +0.00112 | 0.00793 | indistinguishable (0.14 of bar) |
| C vs A′ | rmse *(secondary)* | +0.00045 | 0.00945 | indistinguishable |
| **B vs C** | median | +0.00181 | 0.00187 | indistinguishable (**0.97 of bar**) |
| **B vs C** | p90 | +0.05155 | 0.09206 | indistinguishable (0.56 of bar) |
| A′ vs A | median | −0.00192 | 0.00175 | **DISTINGUISHABLE, better** |
| C vs A | median | −0.00255 | 0.00132 | **DISTINGUISHABLE, better** |

## Falsifier 1 — FIRES

> *If A′ and C produce indistinguishable trajectories at the declared threshold,
> then controlling for revisiting is sufficient and changing the objective is not
> warranted.*

**A′ and C are indistinguishable on both primary metrics.** C is nominally better
on median (−0.00063 m, 0.72 of the bar) and nominally *worse* on p90 (+0.00112 m,
0.14 of the bar) — the two primaries do not even agree on a direction, which is
what a null looks like. Both are within the seed-to-seed spread.

Meanwhile **both remedies beat the ported baseline** on median |err|, and by
similar margins (A′ −0.00192, C −0.00255). So the lockup is real and costly, and
both fixes work — they just do not differ from each other.

**Therefore: the reframe from variance to expected information gain is
foreclosed.** L6 keeps `argmax v` plus inhibition of return. This is the outcome
that falsifies the hypothesis motivating the experiment, and it is the cheaper
remedy by a wide margin: A′ costs one distance computation per visited point, C
costs 3314 full-field integrals per step — measured at 1.8 s per step against
under a millisecond, roughly **10⁴×**.

### The result that makes the foreclosure interesting rather than merely negative

**A and C never select the same fixation. Not once.** Argmax agreement over 144
comparisons (8 seeds × 18 steps), evaluated at the *same state* on the *same
candidate grid*: **0.000**. Spearman over the grid is +0.348 — moderately
correlated fields with reliably different maxima.

So the two objectives disagree completely about where to look, and produce
indistinguishable outcomes. The conclusion is not "these objectives agree". It is
**"on this fixture, which pixel you fixate barely matters, provided you do not
fixate the same one twice."**

This is exactly why the pre-registration demanded the argmax rate and not only a
rank correlation. Spearman +0.348 invites "the objectives broadly agree, so of
course the outcomes match". The argmax rate says they never agree, and the
outcomes match anyway — a different and stronger claim. **The number to act on is
the argmax rate**; the rank correlation is descriptive and, taken alone here,
actively misleading.

### The declared contingency was checked

The pre-registration declared that *if C beat A′*, a fifth diagnostic arm (A′ with
the predecessor's `masked_blur`) would be run before any foreclosure was written,
because A/A′ maximise a blurred map while B/C maximise unblurred Δ. C did **not**
beat A′, so by the declared terms the confound does not threaten the conclusion —
neither change moved anything — and the fifth arm was not run.

## Falsifier 2 — FIRES

> *If B does not track C — different arms of the argmax, or a materially worse
> trajectory — then the cheap single-pixel approximation is unusable.*

The first disjunct is satisfied unambiguously. **B and C never select the same
candidate**: argmax agreement **0.000** over 144 comparisons, with their picks a
median **115 px apart — 3.4 × the 34 px fovea σ**, so they are choosing
non-overlapping regions of the image, not neighbouring pixels. Spearman +0.278.

On trajectory, B and C are *technically* indistinguishable by the declared rule —
but the median comparison lands at **0.97 of its bar**, a knife-edge, and B is
worse on every primary. Stated plainly rather than rounded to a verdict: the
declared rule returns "indistinguishable" here by a 3% margin, and that verdict is
fragile in a way the A′-vs-C verdict (0.72 and 0.14 of bar, opposite directions)
is not. B also revisits — 11.88 distinct of 18 against C's 17.50 — so it only
partly self-inhibits.

**Therefore: the cheap single-pixel approximation is unusable**, and any
information-gain policy costs a field integral per candidate per step. Recorded in
`docs/state.yaml` as a standing constraint. Note this is now a conditional
constraint, since falsifier 1 forecloses adopting such a policy at all — it binds
whoever reopens the question.

## Trajectories

Mean median |err| by fixation (8 seeds). A and A′ are **identical through step 6**
and diverge at step 7, which is exactly when A first revisits.

| step | A | A′ | B | C |
|---|---|---|---|---|
| 0 | 0.40487 | 0.40487 | 0.50318 | 0.22903 |
| 2 | 0.04511 | 0.04511 | 0.04167 | 0.03219 |
| 5 | 0.01194 | 0.01194 | 0.01334 | 0.01540 |
| 8 | 0.01233 | 0.01179 | 0.01270 | 0.01390 |
| 12 | 0.01264 | 0.01183 | 0.01284 | 0.01161 |
| 17 | 0.01318 | 0.01126 | 0.01244 | 0.01063 |

Two things worth naming. **A gets worse after step 5** (0.01194 → 0.01318): the
lockup does not merely waste budget, it degrades the estimate, because the same
grossly wrong measurement at (170, 94) is fused ten times. And **C is much better
early** (step 0: 0.229 against A's 0.405) but that lead is gone by step 5 — the
field integral buys a better first fixation and nothing durable.

Seed 0 scanpaths, the lockup and its absence:

- **A:** `(24,193) (196,290) (215,80) (78,76) (70,294) (226,216) (169,94) (218,236)` then **(170,94) ten times**.
- **C:** 16 distinct locations spread across the frame, revisiting (164,96) three times late.

## The limit on all of this

**This fixture has no true half-occlusions** (`gap-010`). The right image is
resampled from the left, so the (170, 94) failure that drives the whole lockup is
a **matching failure in a fully visible region**, not an occlusion. The two
structurally different sources of high posterior variance that motivated the
experiment — unmeasured versus unmeasurable — are therefore represented here by
only one of their two mechanisms.

**So this forecloses the question for a stimulus without occlusions, and no
further.** A policy that cannot distinguish "unmeasured" from "unmeasurable" was
never tested against the case where that distinction is geometric rather than
photometric. Everything above is consistent with the objective mattering a great
deal on a stimulus with real occlusions, and this experiment cannot see it.

Lifting the limit needs a rendered stimulus with a controlled contrast axis at
occlusion boundaries — `gap-001`, and `od-002` which names Blender as the only
instrument here that can produce one. **The fixture will not be grown to add
occlusions**: that is `fc-004`, and reopening it needs an ADR and a better reason
than needing one more case.

## Threats

- **n = 8 seeds.** The spread bar is estimated from 8 paired differences, so it is
  itself noisy. The A′-vs-C verdict is not close to its bar (0.72 and 0.14) and is
  robust to that; the B-vs-C verdict at 0.97 is not.
- **One fixture, one budget, one matcher.** 18 fixations on a 240×320 analytic
  scene with block matching. No claim is made beyond it.
- **The objective is flat near its maximum**, shown by the stride ladder. A policy
  whose argmax moves 7 px under grid refinement is not being finely steered by its
  objective, which is consistent with the null and may partly explain it.
- **All four arms inherit the port's three defects**, including the 1e3 sentinel
  and the unmasked blur that mixes invalid pixels in as zeros. Only the gaze
  objective and revisiting were varied.
- **C's advantage at step 0 is real but not durable**, and a shorter budget would
  have reported a different story. Budget was declared in advance at 18.
