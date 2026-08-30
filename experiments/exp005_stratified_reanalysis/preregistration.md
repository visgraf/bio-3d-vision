# exp005 — were exp001 and exp002 measured through an artefact floor?

**Pre-registered. Committed alone, before the runner exists.**

A **re-analysis**, not a new experiment. Same arms, same seeds, same budgets, same
two-clause bar as the originals. The only change is **the pixel set the primary
metrics are computed over**.

## The hypothesis

exp004 measured that on the analytic fixture, error at depth discontinuities is
**22.7× worse** than a Blender render of the same geometry on p90 (F 1.49626 m,
R 0.06580 m, 47.80× bar, R better), and that this survives a forced-scanpath
control at 12.28× — so it is a property of the stimulus, not of where the loop
looked. The mechanism is measured: the fixture's reflect-warp yields a **21.7%**
confident-gross-error rate at depth steps against a real render's **4.3%**
(`bio-029`).

exp001 and exp002 scored over each seed's **whole** valid mask
(`np.isfinite(depth_gt) & engine.valid`, verified at `run.py:41` and `run.py:33`).
If the discontinuity band is a floor no policy can move, their effect sizes were
measured through it. exp001's null on gaze objectives and exp002's ~2% saliency
value are the shape a floor would attenuate.

**This is a hypothesis.** `fc-007`, `fc-008` and `fc-010` remain untouched until
this experiment says otherwise, and are not reversed in this iteration whatever
it says.

## The motivating measurement — verified here, not inherited

Re-measured at `9f40198`, seed 0, policy A, 18 steps, before this was written:

| band | pixels | share of pixels | **share of total squared error** |
|---|---|---|---|
| AT (≤ 10 px) | 20 302 | 38.23% | **82.27%** |
| MIDDLE (10–24 px) | 17 566 | 33.08% | 17.55% |
| AWAY (≥ 24 px) | 15 230 | 28.68% | **0.18%** |
| total | 53 098 | 100% | 100% |

Chat's figures were 38.7% and 82.4%; mine are 38.23% and 82.27%, and the pixel
count 53 098 agrees exactly. The small deltas are recorded rather than
reconciled — most likely a different discontinuity construction — and the numbers
used here are the ones measured above.

**The AWAY band carries 0.18% of the squared error.** This was not in the brief
and it changes what the experiment can show: absolute errors there are tiny, so
differences between arms will be tiny in metres whatever their ratio to the bar.
That is why raw differences and bars are reported separately below.

## Bands — inherited from exp004, not re-derived

`discontinuity_step_px = 1.0`, `at_max_px = 10.0`, `away_min_px = 24.0`, taken
from `exp004/verdicts.json` unchanged. The discontinuity set is computed from the
scene model's **step** depth map, so it is identical across seeds — the fixture
varies its texture with the seed, not its geometry.

Three bands, not two: **AT ≤ 10**, **MIDDLE 10–24**, **AWAY ≥ 24**, plus the
original **POOLED** figure. A monotone gradient across three bands is much
stronger evidence for a floor than a binary split.

## What is re-run

| | arms | seeds | budget | source of the bar |
|---|---|---|---|---|
| exp001 | A, A′, B, C | 0–7 | 18 | exp001's own |
| exp002 | A′, C, D, E | 0–15 | 40 | exp001's, as exp002 used |

Budgets and seeds match the originals exactly. exp002's 45-fixation extension was
post-hoc in the original and is not re-run. **If runtime proves prohibitive,
seeds are reduced and the reduction is reported; the budget is never shortened**,
because a shortened budget is a different measurement.

Comparisons carried forward from the originals: **C vs A′** (fc-007's null),
**B vs C** (cn-001), **A vs A′** (the value of inhibition), **E vs A′** (fc-008's
saliency value), **D vs E** (the validity mask's value).

## The bar — exp001's, reused verbatim

For each seed `s`, `d_s = M(X, s) − M(A′, s)` on `M ∈ {median |err|, p90}`.

> distinguishable iff `|mean(d_s)| > max( sd(d_s), 0.02 × mean(M(A′, s)) )`

**Both components are reported separately for every comparison**, not only
`x_bar`. In the AWAY band the mean difference and the seed-to-seed spread may
both shrink, and `x_bar` alone cannot tell "the effect was real and masked" from
"everything got smaller together". `mean_diff`, `sd_diff`, the materiality floor
and which clause binds are all recorded.

## The control — scoring contamination vs steering contamination

Restricting the metric changes what is **scored**, not what **happened**. Every
arm chose its fixations from saliency computed over the whole image, artefact
band included, so a clean AWAY score still reflects a scanpath the artefact
helped steer.

**Post-hoc control, labelled as such**: re-run the variance-driven arms (A, A′,
B, C) with **selection masked to the AWAY band**, and score on the AWAY band.

Masking restricts *where the policy may fixate* — the argmax domain for A and A′,
the candidate grid for B and C. It does **not** restrict the objective's field
integral for B and C: that would change what the objective values, which is a
different change from where it may look. Reported: scanpath agreement between
masked and unmasked arms, as exp001 reported argmax agreement.

- If restricted **scoring** moves the verdicts and restricted **steering** adds
  nothing, the artefact was in the metric.
- If restricted **steering** moves them further, the artefact was also choosing
  where to look, and the original scanpaths were partly artefact-driven — a
  stronger claim, bearing directly on `fc-007` and `fc-008`.

**Declared limitation of the control, measured before writing this.** The AWAY
band admits only about **41** sites at A′'s 20 px inhibition radius (greedy
packing, one ordering, seed 0). exp002's budget is **40**. So the masked arms sit
at the band's packing limit and may terminate early, and a masked-vs-unmasked
comparison at 40 fixations is partly a comparison of different effective budgets.
`terminated_at` is reported for every masked arm. This is the same shape as
exp002's own "E's lattice limit" and is declared here rather than discovered.

## Falsifiers

**1. If the AWAY-band verdicts MATCH the pooled ones** — same distinguishability,
comparable `x_bar` — **the floor hypothesis is wrong.** exp004's finding is real
about the fixture but does not propagate to the foreclosures; `fc-007`, `fc-008`
and `fc-010` stand as measured, with their `gap-010` limits unchanged. **This
outcome is reported as plainly as the other.**

**2. If effect sizes GROW in the AWAY band** — particularly if exp002's saliency
value rises materially above its measured ~2% of the validity mask's worth, or
exp001's null on objectives becomes distinguishable — then three foreclosures
were measured through a fog. **They are NOT reversed in this iteration.** Each is
annotated with what was found and what a pre-registered re-test would need, and
the closure stands. A foreclosure reversed on a re-analysis it did not
pre-register is the same defect as one closed on evidence that does not bear on
it.

### Predictions, declared

Stated so they can be wrong, and held loosely — nothing here measures them yet.

- **Falsifier 1 more likely than 2 on median, less likely on p90.** The AT band
  holds 82% of *squared* error, which is a tail statistic; p90 is where a floor
  would bite hardest and median least.
- **The AWAY band's absolute differences will be very small** — it carries 0.18%
  of the squared error — so verdicts there may be spread-limited rather than
  materiality-limited. Which clause binds is recorded for every comparison.
- **No prediction is offered on the steering control.** exp001 measured that A
  and C never once selected the same fixation yet produced indistinguishable
  outcomes; that result gives no basis for predicting whether restricting *where*
  the policy looks matters.

## What this does not do

- **It does not lift `gap-010`.** AWAY-band pixels are still on a stimulus whose
  discontinuity regions are pathological; restricting the score does not change
  the stimulus. `gap-010` is lifted by a rendered occlusion experiment.
- **It does not touch `od-002`.**
- **It reverses no foreclosure**, whichever falsifier fires.
