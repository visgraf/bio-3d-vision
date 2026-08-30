# exp007 — the policy comparisons on rendered data

**Pre-registered. Committed alone, before the runner exists.**

exp005 removed the artefact from the **score**. This removes it from the
**stimulus**. exp004 measured the rendered source 22.7× better than the fixture
at depth discontinuities, so the pixels exp005 had to exclude are pixels this
stimulus can include.

**No foreclosure is reversed here.** Every one stays closed; where an annotation
is warranted, it states what a pre-registered re-test would need.

## Two corrections to the specification's assumed state

Both verified against the ledger before this was written. Neither changes what is
run; both change what is *predicted*, so they are recorded rather than absorbed.

**1. "every variance-driven comparison in exp001 and exp002 collapses in the AWAY
band" is imprecise.** Three of eight collapsed. Measured:

| comparison | metric | fixture POOLED | fixture AWAY | what happened |
|---|---|---|---|---|
| exp001 A vs A′ | median | 1.10× DIST | 0.58× ind | collapsed |
| exp002 E vs A′ | median | 1.38× DIST | 0.38× ind | collapsed |
| exp002 C vs A′ | median | 1.05× DIST | 0.19× ind | collapsed |
| **exp002 E vs A′** | **p90** | **1.96× DIST, E worse** | **1.75× DIST, E better** | **REVERSED, still distinguishable** |
| exp001 C vs A′ | both | indistinguishable | indistinguishable | already null |

The E-vs-A′ p90 reversal is the exception, and it is the single most consequential
row in exp005 for `fc-008`.

**2. "D-vs-E survives and strengthens there" is half right.** It survives in every
band. On p90 it strengthens (5.88× → 25.55×); **on median it weakens**
(47.04× → 32.20×), while staying overwhelmingly distinguishable.

## A design change, declared: the fixture arms are re-run at matched settings

The specification says "six arms, one stimulus". Outcomes (a) and (b) below are
defined by agreement with *the fixture's* verdict — and three of the four
comparisons have no fixture verdict at exp007's settings:

| comparison | fixture reference | seeds | budget | matched? |
|---|---|---|---|---|
| A vs A′ | exp001 / exp005 | 8 | 18 | **yes** |
| E vs A′ | exp002 / exp005 | 16 | 40 | no |
| D vs E | exp002 / exp005 | 16 | 40 | no |
| V vs W | exp003 | 16 | 18 | seeds only |

Classifying a rendered 8-seed/18-step figure against a fixture 16-seed/40-step
figure would attribute a budget difference to the stimulus. **So all six arms are
run on BOTH sources at 8 seeds and 18 steps**, and the matched fixture figures are
the reference for classification. The originals' published figures are reported
alongside, labelled as different settings. The arms are cheap — B and C are
dropped — so this costs little and removes the confound entirely.

## Scope — six arms, two sources, seeds 0–7, 18 steps

| arm | what it is |
|---|---|
| A | argmax variance, the ported baseline |
| A′ | A plus inhibition of return |
| D | blind raster |
| E | masked coverage — validity mask only, no variance |
| W | wide disparity search (exp003's baseline) |
| V | verged narrow window (exp003's acquisition arm) |

18 steps for every arm. **exp003's budget is also 18** (verified at `run.py:25`),
so W and V are like-for-like with the rest and no separate budget is needed.
exp003 used 16 seeds; exp007 uses 8, matching exp004's existing renders — a
reduction in seeds, never in budget, and it widens the bar rather than narrowing
it.

**B and C are dropped, as a decision.** `fc-007` — the null on the choice among
variance-derived objectives — is the most robust result in the ledger and exp005
strengthened it (0.72× pooled → 0.32× AWAY on median, and unchanged under masked
steering). **Cost of re-running them:** C is one field integral per candidate per
step, measured at 1.81 s/step (`cn-001` records 1.8 s), so B and C on two sources
× 8 seeds × 18 steps ≈ **17.4 minutes** of the ~18 minutes the whole experiment
would take. They would consume 97% of the runtime to re-check the one result
least in doubt.

## Scoring

Ground truth is **each source's own**: the fixture's smoothed `depth_gt`, the
render's Z pass. Primary metrics **median absolute depth error** and **p90** at
the final step. exp001's two-clause bar, verbatim:

> distinguishable iff `|mean(d_s)| > max( sd(d_s), 0.02 × mean(M(reference, s)) )`

**exp003's coverage rule applies.** A, A′, D and E share one valid mask on a given
stimulus — `ActiveStereo.valid` is set at construction and never reassigned by
`step` (verified at `loop.py:112`), and those four differ only in policy. **V is
the exception**: `reacquire` rewrites the mask with a narrow window. So V-vs-W is
scored on the **intersection**, with each arm's exclusive set reported separately
with its own error, and pooled figures labelled **CONFOUNDED**.

**Reported by band anyway** — AT ≤ 10 px, MIDDLE 10–24 px, AWAY ≥ 24 px, inherited
from exp004 unchanged, computed from the scene model's step-edge geometry. The
rendered source should *not* have a pathological discontinuity band. **If the band
gradient on rendered data looks like the fixture's, the artefact was not the whole
story, and that must be visible rather than inferred from a pooled number.**

Four-panel figures regenerated per arm, both sources, beside each other.

## The four outcomes — enumerated, and one will be reported per comparison

Chat has twice written falsifier sets that named a null and a confirmation and
missed what occurred. For each comparison and metric, the rendered POOLED verdict
is classified against the **matched** fixture references:

| | condition |
|---|---|
| **(a)** | matches the fixture's **POOLED** verdict — same distinguishability and direction. The fixture's pooled figure was right; the artefact did not distort it. |
| **(b)** | matches the fixture's **AWAY-band** verdict. exp005's reading was correct: the artefact carried the effect, and the clean-band re-score anticipated the clean stimulus. |
| **(c)** | differs from both, **same direction**, different magnitude. Neither the pooled nor the banded fixture figure predicted the rendered one; the magnitude is reported. |
| **(d)** | **REVERSES DIRECTION** against a distinguishable fixture verdict. The fixture's verdict was not attenuated but wrong in sign. **Reported first, not buried in a table.** |

Precedence: **(d)** is tested first; then (a) and (b) — which may both hold, and
that is itself informative, meaning the fixture's own verdict was band-invariant;
then (c). A direction flip between two indistinguishable verdicts is noise, not
(d), and is reported as agreement.

## Declared predictions, under exp005's reading

exp005's reading is that the artefact *carried* the variance-driven effects, so a
stimulus without a pathological band should behave like the fixture's AWAY band —
outcome **(b)**. Stated so they can be wrong.

| comparison | metric | predicted | meaning |
|---|---|---|---|
| E vs A′ | median | **(b)** | indistinguishable — variance buys nothing over the mask |
| E vs A′ | p90 | **(b), which is also (d)** | E *better*, reversing the fixture's pooled verdict. The prediction that most changes `fc-008` |
| D vs E | median | **(a) = (b)** | D distinguishably worse; the mask's value is band-invariant |
| D vs E | p90 | **(a) = (b)** | D distinguishably worse |
| A vs A′ | median | **(b)** | indistinguishable — inhibition of return stops paying |
| A vs A′ | p90 | **(a) = (b)** | indistinguishable in both |
| V vs W | both | **(a)** | V still worse. `fc-010`'s mechanism — the vergence estimator has no signed out-of-range error, because the pixels carrying it are the ones validity deletes — is **geometric and stimulus-independent**, so a cleaner stimulus should not rescue it |

**V vs W carries the weakest prior**, and it is the one comparison with no
band-checked reference at all: `fc-010` rests entirely on its pooled figure, V
7.5× worse than W on the intersection. Whichever outcome occurs, this is the first
independent evidence about it.

## What this does not do

- **It does not lift `gap-010`.** The rendered scene copies the *fixture's*
  geometry, so its occlusions are whatever that geometry produces incidentally —
  not a controlled occlusion stimulus, and with no contrast axis. The findings
  will state **how much genuine lateral overlap the geometry actually has**,
  measured, because the strength of every claim here depends on it. `od-002`
  stays open.
- **It does not touch `od-003`.** If V vs W reverses, `fc-011`'s framing — the
  mechanical plant **untested, not refuted** — becomes more clearly right, not
  less. That will be noted and nothing else changed.
- **It reverses no foreclosure**, whichever outcome occurs.
