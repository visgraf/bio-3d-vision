# exp011 — consolidate the closed-loop result

**Pre-registered. Committed alone, before the runner exists.**

**24 seeds** (three times exp010's eight), **four levels** — exp008's k1, k2, k4,
k8 at measured left-occluded fractions **0.0197, 0.0426, 0.0884, 0.1716** —
**budget 40**, both arms rectified, same policy, same bar. 4032 renders, measured
at 0.58 s each: **about 40 minutes**.

Adds seeds and levels to exp010. No new code, no new design, no new stimulus. The
foveal weight stays pixel-native and the vergence estimator is untouched.

---

## Before predicting anything: exp001's bar does not fall with n

Question 1 asks whether AT becomes distinguishable at 24 seeds, and asks for the
seed sd at 8 and at 24 "so the reader can see whether the bar fell as `sqrt(n)`
or the effect moved". **It cannot fall as `sqrt(n)`, and this has to be said
before the run rather than discovered in the table.**

The bar is `np.std(d, ddof=1)` — verified in `exp001`, `exp005`, `exp007` and
`exp008`'s analysers, all four. That is the **sample standard deviation of the
per-seed differences**, a consistent estimator of a population constant. It is
not a standard error and it has no `1/sqrt(n)`.

> **`x_bar = |mean_diff| / sd` is an effect size — Cohen's `d` — and the bar is
> a threshold at `d = 1`. It converges as `n` grows; it does not shrink.**

The difference is not academic. AT at n=8: effect 0.01396, sd 0.01459,
`x_bar` 0.957. Under a standard-error reading the same numbers would give
`x_bar` 2.71 at n=8 and 4.69 at n=24 — AT would already be distinguished, and
so would almost everything. **exp001's bar is deliberately the stricter of the
two**, and this experiment cannot make it looser by adding seeds.

**So what can 24 seeds actually change?** Only the *estimate* of the sd. Its own
relative uncertainty is `1/sqrt(2(n-1))`: **26.7% at n=8, 14.7% at n=24**. The
n=8 sd need be an overestimate by only **4.3%** for AT to cross. That is well
inside its own error bar, so the question is real — but it is a question about
whether one noisy variance estimate was high, not about statistical power.

---

## Question 1 — does the AT effect survive more seeds?

Reported: `mean_diff`, `sd`, `bar`, `x_bar` at **n = 8** (exp010, restated) and
**n = 24**, per band, so the reader can see which of the two moved.

**Predicted: (b).** Under the reading that exp010's AT effect is real but
underpowered, the reading is itself the thing this experiment falsifies: the
effect is not *underpowered*, it is **under-separated** — 0.96 sd of seed-to-seed
spread, and seeds do not reduce that. AT's sd is 3.8× MIDDLE's and 13.5× AWAY's,
and exp005 already located why: the AT band is where the fixture's error is
largest and most seed-dependent.

**If (b), the number to report is not a seed count.** No seed count resolves it
under this bar. What would is a **reduction in the seed-to-seed variance of the
AT band itself**, which comes from the stimulus, not from the sample. The
extrapolation asked for will be given in both readings — the sd-based one (no
finite n) and the standard-error one (already resolved at n=2) — because the gap
between them *is* the answer.

**(a) remains possible** and is not being argued away: a 4.3% overestimate of the
sd at n=8 is unremarkable.

## Question 2 — does the gain scale with occlusion?

Arms compared **within a level**; effect sizes compared **across levels**. Never
a pixel set across levels — exp008's rule, and coverage moves violently here.
`mean_diff` and `bar` reported **separately at every level**.

**Predicted: (c), a peak.** Two mechanisms pull opposite ways and exp008 already
measured one of them. Coverage pressure rises monotonically with occlusion, which
favours CLOSED. But exp008 measured the stimulus to **stop discriminating by
17.16%**, where every arm sits at the 3.0 m prior against a 4.5 m background and
the spread between a field integral and a blind raster is 0.0165 m. A closed loop
cannot distinguish itself where nothing can.

**(d) is most likely at k8** and would be reported first. Occlusion boundaries
move most between viewpoints there, so CLOSED's re-renders disagree with each
other most, and its fusion has no term for that.

## Question 3 — is the coverage gain the larger result?

Reported per arm per level, **beside the common-set headline and not in an
excluded-sets block**: ever-measured fraction, and CLOSED's own-set error on the
cells OPEN never reached.

**The judgement is required, so the yardstick is declared now rather than chosen
after the tables.** The two gains are in different units — metres on shared cells
against a count of cells — so they are compared on the quantity a consumer of the
belief would actually experience:

> **Mean absolute error over ALL 76 800 cells, with unmeasured cells left at the
> prior.** An unmeasured cell is not absent; it holds 3.0 m ± 3.0, and against a
> 2.4–4.5 m scene that is an error of up to 1.5 m carried silently.

This is an aggregation of what exp010 already measured, not a new measurement.
It is stated here because the alternative — picking the aggregation after seeing
which answer it gives — is the failure this pre-registration exists to prevent.

**Predicted: coverage, and not close.** CLOSED converts 30.6% of the grid from
"at the prior" to "measured at 0.0146 m median". The accuracy gain on shared
cells is 0.0112 m on 62.2% of them. On the all-cells yardstick the coverage term
should dominate by an order of magnitude.

---

## Falsifiers — one will be named as having occurred

- **(a)** AT distinguishable at 24 seeds, effect scaling with occlusion. The
  framework's original motivation confirmed. **Reported with the 41× cost in the
  same breath.**
- **(b)** AT still not distinguishable. The claim stays "helps on easy surface,
  unclear at the hard part", with the seed count that would resolve it given in
  both readings of the bar.
- **(c)** The gain does not scale, or peaks and falls as allocation did. **Report
  where** — a peak sizes every closed-loop experiment after this one.
- **(d)** The gain reverses at some level. **Reported first if it happens.** It
  would bound the claim rather than break it.

(a)–(d) are not exclusive: question 1 and question 2 can land differently, and
the report will say so rather than choosing one label for the whole run.

## What this does not do

No step 18, no omnidirectional work, no od-002 contrast axis, no od-003 retest,
no policy change, no new stimulus, no foreclosure. It does not fix the
pixel-native foveal weight (fc-009), the foveal aim offset (bio-065), or the
vergence estimator (fc-010). It does not revisit fc-012.

It also does not address exp010's unsettled caveat — that neither arm's fusion
accounts for correlation between successive measurements, and OPEN's are far more
correlated. **More seeds and more levels cannot touch that**, and a larger result
here would not make it smaller.
