# exp011 — findings

**Measured** at `16c9356`, 24 seeds × 4 levels × 2 arms × 40 fixations —
4032 renders, ~46 minutes — Blender **5.2.0 LTS** (`fbe6228777e7`), Cycles, 1
sample; Python 3.13.15 / numpy 2.5.2.

**Which falsifiers occurred:** **(b)** on question 1, **(c)** on question 2.
**(a) did not.** **(d) did not fire anywhere** — the gain never reverses. On
question 3 the answer is **coverage, by between 33× and 341×**.

**Read this first: exp010's verdicts were too confident, and this run corrects
them.** Every band's `x_bar` fell at 24 seeds, because exp010's 8-seed standard
deviations were underestimates. Details below.

---

## Question 1 — the AT effect does not survive, and the sd went the wrong way

At k=4, exp010's level. `d = CLOSED − OPEN`; negative is CLOSED better.

| band | effect @8 | effect @24 | × | sd @8 | sd @24 | × | x̄ @8 | x̄ @24 | verdict |
|---|---|---|---|---|---|---|---|---|---|
| **AT** | −0.01396 | −0.01864 | 1.34 | 0.01459 | **0.02049** | **1.40** | 0.96 | **0.91** | indistinguishable |
| MIDDLE | −0.00996 | −0.01379 | 1.38 | 0.00383 | **0.01228** | **3.21** | 2.60 | **1.12** | CLOSED better |
| AWAY | −0.00458 | −0.00500 | 1.09 | 0.00108 | 0.00178 | 1.64 | 4.26 | **2.82** | CLOSED better |
| POOLED | −0.01122 | −0.01410 | 1.26 | 0.00816 | 0.01266 | 1.55 | 1.37 | **1.11** | CLOSED better |

**Outcome (b).** AT is still indistinguishable, and `x_bar` moved the wrong way —
0.96 → 0.91. **The effect grew by 1.34× and the sd grew by 1.40×**, so tripling
the seeds made the case slightly weaker, not stronger.

This is exactly what the pre-registration said would happen and why. The bar is
`np.std(d, ddof=1)`, a sample standard deviation, not a standard error; it has no
`1/sqrt(n)`. Tripling `n` refined the estimate and the refined estimate was
*larger*.

**Every band's `x_bar` fell.** MIDDLE went 2.60 → 1.12, a 3.21× rise in its sd.
**exp010's eight seeds understated the seed-to-seed spread in all four bands**, so
its verdicts stand but with far less margin than reported — MIDDLE is now barely
over the bar rather than comfortably over it. That is a correction to exp010's
headline and it is recorded as one.

### The sign is nearly unanimous and the verdict is still "indistinguishable"

**23 of 24 seeds favour CLOSED in the AT band at k=4.** Across every band and
level the count runs **21–24 of 24**. The bar is not a sign test: it asks whether
the effect exceeds one standard deviation of the per-seed differences, and an
effect can be almost perfectly consistent in direction while remaining small
relative to its own spread. **That is the whole of what "AT indistinguishable"
means here**, and it should not be read as "no effect".

### The seed count that would resolve it, as a number

**Under the bar as written, there is none.** The bar is a threshold at effect
size `d = 1`; seeds refine the estimate of `d` but cannot move the threshold.
At n=24, `d = 0.909` with `s.e.(d) ≈ 0.243`, so `d` lies in **[0.67, 1.15]** at
one standard error — consistent with both sides of the bar.

Pinning `d` down does have a cost, and it is large: **141 seeds to know `d` to
±0.1, 565 to ±0.05.** Even then, if the true `d` is below 1 the bar is never
crossed, because whether it crosses is a property of the stimulus, not the
sample.

**Under a standard-error reading the answer is the opposite and already
settled**: `x_bar` would be 4.46 for AT at 24 seeds (and 5.50, 13.81, 5.46 for
MIDDLE, AWAY, POOLED). The gap between the two readings is the answer to
question 1, and it is a fact about exp001's bar rather than about active vision.

---

## Question 2 — outcome (c): the gain peaks at 8.84% and falls, where allocation did

POOLED, common set, arms compared within each level:

| level | occlusion | OPEN | CLOSED | mean_diff | bar | binds | x̄ | relative gain | verdict |
|---|---|---|---|---|---|---|---|---|---|
| k1 | 0.0197 | 0.0117 | 0.0074 | −0.00428 | 0.00164 | sd | 2.61 | 36.6% | CLOSED better |
| k2 | 0.0426 | 0.0172 | 0.0115 | −0.00569 | 0.00509 | sd | 1.12 | 33.0% | CLOSED better |
| **k4** | **0.0884** | 0.0289 | 0.0148 | **−0.01410** | 0.01266 | sd | 1.11 | **48.8%** | CLOSED better |
| k8 | 0.1716 | 0.0364 | 0.0252 | −0.01117 | 0.00902 | sd | 1.24 | 30.7% | CLOSED better |

**The raw effect rises to a peak at 8.84% and falls at 17.16%** — in absolute
metres (0.00428 → 0.00569 → **0.01410** → 0.01117) and in relative terms (36.6%
→ 33.0% → **48.8%** → 30.7%).

> **That is the same location exp008 found for allocation.** exp008 measured the
> allocation question sharpest at 8.84% and collapsing by 17.16%. Acquisition
> peaks at the same level. The two were measured on different questions with
> different arms, and they agree on where this stimulus family is most
> informative.

**The bar moves too, and in the same direction**, which is why the verdicts do
not track the effect: `x_bar` reads 2.61, 1.12, 1.11, 1.24 while the effect
nearly triples and then falls. **Reporting `x_bar` alone would have shown a
collapse from k1 to k2 that the effect does not have** — the effect *grew* there
by 33%. This is exp008's warning reproduced exactly, on a different experiment.

The `sd` binds at every level and in every band; the 2% materiality floor is 4–30×
smaller throughout and never decides anything.

**Per band, the verdicts are level-dependent and non-monotone:**

| band | k1 | k2 | k4 | k8 |
|---|---|---|---|---|
| AT | **1.60** ✓ | 0.80 ✗ | 0.91 ✗ | **1.18** ✓ |
| MIDDLE | 2.31 ✓ | 1.09 ✓ | 1.12 ✓ | 1.32 ✓ |
| AWAY | 3.52 ✓ | 1.51 ✓ | 2.82 ✓ | **0.97 ✗** |
| POOLED | 2.61 ✓ | 1.12 ✓ | 1.11 ✓ | 1.24 ✓ |

**AT is distinguishable at k1 and k8 but not at k2 and k4** — so "the closed loop
does not help at discontinuities" is *not* a level-independent statement, and
exp010 measured the one level where the AT case is weakest. AWAY goes the other
way and loses distinguishability at k8.

**(d) did not fire.** `mean_diff` is negative — CLOSED better — in **every band at
every level**, 16 of 16 cells.

---

## Question 3 — coverage is the result, and it is not close

On the yardstick declared in the pre-registration: **mean absolute error over all
76 800 cells, unmeasured cells left at the prior.**

| level | occl | ever OPEN | ever CLOSED | ALL-cells OPEN | ALL-cells CLOSED | x̄ | accuracy term | coverage term | ratio |
|---|---|---|---|---|---|---|---|---|---|
| k1 | 0.0197 | 0.6954 | **0.9791** | 0.4503 | **0.0718** | 42.03 | 0.01045 | **0.36810** | **35×** |
| k2 | 0.0426 | 0.6736 | 0.9614 | 0.5001 | 0.1265 | 37.36 | 0.00165 | 0.37199 | **225×** |
| k4 | 0.0884 | 0.6218 | 0.9275 | 0.6304 | 0.2318 | 23.79 | 0.01155 | 0.38704 | **34×** |
| k8 | 0.1716 | 0.5427 | 0.8800 | 0.7969 | 0.4151 | 23.95 | 0.00112 | 0.38066 | **341×** |

The decomposition is exact: accuracy term + coverage term = total all-cells gain,
to five decimals at every level.

**On the cells OPEN never reached:**

| level | OPEN (at the prior) | CLOSED | cells |
|---|---|---|---|
| k1 | 1.3545 m | **0.0570 m** | 21 788 |
| k2 | 1.3540 m | 0.0616 m | 22 105 |
| k4 | 1.3878 m | 0.1216 m | 23 477 |
| k8 | 1.3768 m | **0.2485 m** | 25 910 |

### The judgement, made explicitly

> **The coverage gain is the result. The accuracy gain on shared cells is a
> rounding error beside it — between 33× and 341× smaller, at every level.**

A closed loop's value here is not that it measures the same cells better. It is
that **it measures cells an open loop cannot measure at all**, and leaves 1.35–1.39
m of silent prior error on 28–34% of the belief when it does not. `ActiveStereo.valid`
excludes the border and the 64-column disparity-search margin, so from a fixed
viewpoint those cells are permanently unmeasurable; a saccade is what reaches them.

**The coverage term is almost perfectly flat across occlusion — 0.368, 0.372,
0.387, 0.381 m** — while the accuracy term bounces between 0.001 and 0.012. So the
peak in question 2 is a feature of the *accuracy* channel only. **The dominant
term does not scale with occlusion at all**, which means question 2's peak, while
real, is a peak in the smaller half of the effect.

*(The decomposition uses means so the terms add; the question-2 table uses medians,
as exp010 did. Means on the common set are outlier-sensitive, which is why the
accuracy term is noisier across levels than the median-based table looks.)*

---

## Completion and cost

**96/96 runs reached budget in both arms. Zero refusals.** CLOSED's vergence
ranged 0.0089–0.1031 across all 96 runs — wider than exp010's 0.0103–0.0599, and
still never out of range. **fc-010's mechanism did not fire at four occlusion
levels and 24 seeds**, which is stronger evidence than exp010's for the same
negative.

| | renders | render s | front end s |
|---|---|---|---|
| OPEN | 1 | 0.58 | 0.06 |
| CLOSED | 41 | 23.78 | 2.52 |

**41×**, unchanged from exp010, and the number that belongs beside every figure
above.

## What this does not establish

That the closed loop helps at discontinuities **in general** — it does at k1 and
k8 and does not at k2 and k4, and no level-independent statement is available.
That the peak at 8.84% is a property of acquisition rather than of this stimulus
family — exp008 found allocation's peak at the same level, which is as consistent
with the stimulus being informative there as with a fact about loops.

And it does not touch exp010's unsettled caveat: **neither arm's fusion accounts
for correlation between successive measurements, and OPEN's 40 come from one
disparity map.** More seeds and more levels cannot address that, and the coverage
result above does not depend on it — an unmeasured cell is unmeasured however its
neighbours are fused.
