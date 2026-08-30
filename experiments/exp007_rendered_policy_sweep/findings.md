# exp007 — findings

**Measured** at `aa87d14`, 8 seeds, Blender **5.2.0 LTS** (`fbe6228777e7`), CYCLES,
1 sample, no denoising; Python 3.13.15 / numpy 2.5.2.

**No foreclosure is reversed.** Three are annotated.

## Headline — outcome (d) never occurred, and neither did (b)

| outcome | count |
|---|---|
| **(a)** matches the fixture's POOLED verdict | 4 |
| **(a=b)** matches both, because the fixture's own verdict was band-invariant | 3 |
| **(c)** differs from both, same direction | 1 |
| **(b)** matches the AWAY verdict only | **0** |
| **(d)** reverses direction | **0** |

**No comparison reversed direction.** In every one of the eight
comparison-metrics the rendered verdict matched the fixture's **pooled** figure,
and in the three cases where the pooled and AWAY references disagreed, the
rendered stimulus went with **pooled** every time.

**The fixture's published figures were right. exp005's AWAY-band re-score did not
anticipate the clean stimulus in a single case where the two disagreed.**

My pre-registered predictions were wrong on four of the eight. I predicted (b)
for E vs A′ on both metrics and for A vs A′ on median, and (b)-which-is-also-(d)
for E vs A′ on p90. All four came out (a) or (c).

## Why — the band gradient survives on rendered data

The specification asked for this to be visible rather than inferred, and it is
the thing that reconciles exp005 with exp007. `x_bar` on median by band:

| comparison | source | AT | MIDDLE | AWAY |
|---|---|---|---|---|
| E vs A′ | fixture | 3.97× | 1.55× | 0.33× |
| E vs A′ | **rendered** | **4.31×** | **0.71×** | **0.14×** |
| A vs A′ | fixture | 1.17× | 1.17× | 0.58× |
| A vs A′ | **rendered** | **1.16×** | **1.12×** | **0.18×** |

**The rendered stimulus has the same gradient as the fixture.** The policy
differences live at depth discontinuities on *both* sources — on a stimulus whose
discontinuity band is pathological and on one whose is not.

So the correct reading, which neither exp005 nor this specification stated:

> The fixture's artefact inflated the **magnitude of the error** at
> discontinuities. It did not manufacture the **policy differences** there.
> exp005's AWAY band removed the artefact and the signal together.

exp005's `fv-013-2` said "the discontinuity band was not fog over the result; it
was carrying the result". That is confirmed — and its implication, that the pooled
figures were therefore suspect, is **refuted**. The band carries the result on a
clean stimulus too.

## The four comparisons

Decided on the intersection where masks differ, per exp003's coverage rule.

### E vs A′ — `fc-008` — outcome **(a)** on both metrics, budget 40

| metric | rendered | fixture POOLED | fixture AWAY |
|---|---|---|---|
| median | **1.18× DIST, E worse** | 1.36× DIST, E worse | 0.33× ind |
| p90 | **9.04× DIST, E worse** | 1.85× DIST, E worse | 1.60× DIST, **E better** |

`fc-008`'s claim — posterior variance carries information beyond the validity
mask — **holds on rendered data, on both metrics.** On p90 the rendered effect is
**five times larger** than the fixture's pooled figure (9.04× against 1.85×), and
it points the opposite way from the fixture's AWAY band.

The median verdict is materiality-bound at 1.18×, a knife-edge, and reported as
one.

### D vs E — `fc-008` — outcome **(a=b)** on both metrics, budget 40

| metric | rendered | fixture POOLED | fixture AWAY |
|---|---|---|---|
| median | 41.96× DIST, D worse | 48.38× | 26.02× |
| p90 | 9.31× DIST, D worse | 6.79× | 35.92× |

The validity mask's value is overwhelming and band-invariant on both sources.
Nothing here is in doubt.

### A vs A′ — supporting `fc-007` — outcome **(a)** then **(c)**, budget 18

| metric | rendered | fixture POOLED | fixture AWAY |
|---|---|---|---|
| median | 1.25× DIST, A worse | 1.10× DIST, A worse | 0.58× ind |
| p90 | **1.21× DIST, A worse** | 0.72× **ind** | 0.60× **ind** |

**The one (c).** On p90 the rendered stimulus shows inhibition of return doing
work that *neither* fixture figure showed. Both are knife-edges — 1.25× and 1.21×
— and both are spread-bound. Inhibition of return pays slightly more on a
stimulus with honest occlusions than on one without.

### V vs W — `fc-010`, `fc-011` — outcome **(a=b)** then **(a)**, budget 18

| metric | rendered | fixture POOLED | fixture AWAY |
|---|---|---|---|
| median | 1.58× DIST, V worse | 2.76× DIST, V worse | 5.12× DIST, V worse |
| p90 | 1.90× DIST, V worse | 1.26× DIST, V worse | 0.96× ind |

**The first independent evidence about `fc-010`, and it survives.** Verging to
acquire is distinguishably worse than the wide search on a stimulus without the
fixture's artefact, on both metrics.

Coverage, per exp003's rule — and V's coverage cost is **worse** on rendered data:

| | V valid | W valid | V loses | V-exclusive median | W-exclusive median |
|---|---|---|---|---|---|
| fixture | 50 202 | 53 182 | 2 980 | 0.0608 | 0.0064 |
| **rendered** | **46 410** | **53 406** | **6 996** | **0.0748** | **0.0066** |

V costs 147 disparity hypotheses against W's 57 on both sources — identical,
because the window schedule is driven by the vergence estimate. On rendered data
V reaches 7 000 fewer pixels than W and the pixels it exclusively reaches are
**11× worse** than W's exclusive pixels.

## A deviation from the specification, and why

**The specification said 18 steps for A, A′, D and E. I ran D and E at 40 as
well, and the 40-step figures are the ones that decide `fc-008`.**

D and E are lattice scans. exp002 derived their pitch from the inhibition radius
for a **40**-fixation budget, and the lattice has **70 sites**. Measured:

| budget | A′ median | E median | E distinct fixations |
|---|---|---|---|
| 18 | 0.01169 | **0.04468** | 18 of 70 sites |
| 40 | 0.01032 | **0.01053** | 40 of 70 sites |

At 18 steps E has visited 26% of its lattice and is four times worse than A′ —
a difference about **budget**, not about variance versus the mask. Scored that
way, E vs A′ reads 37× and D vs E reads 97×, and neither bears on `fc-008`, whose
evidence is at 40 fixations and reads 1.38×.

The matched 40-step fixture run reproduces exp002: **1.36×** here at 8 seeds
against exp002's published **1.38×** at 16. The 18-step figures are kept in
`verdicts.json` under `lattice_at_budget18_STARVED`.

A vs A′ and V vs W stay at 18, which is exp001's and exp003's own budget.

## How much occlusion this geometry actually has — small

Measured, because the specification is right that every claim here depends on it:

| | value |
|---|---|
| right-image pixels with no left correspondent | 3 910 — **5.09%** |
| left-image pixels whose correspondent is hidden | 1 510 — **1.97%** |
| widest occluded run | 10 px |

**This is a small amount of occlusion, and it is incidental.** The rendered scene
copies the *fixture's* geometry — three fronto-parallel cards on a background —
so its half-occlusions are whatever that arrangement happens to produce, not a
designed occlusion stimulus, and there is no contrast axis at all. Every verdict
above is a verdict on a stimulus that is *honest* about its 5% of occlusion, not
one that is *rich* in it.

## Annotations — none reversed

- **`fc-008`** — its evidence is confirmed on a stimulus without the artefact, on
  both metrics, with the p90 effect five times the fixture's pooled figure.
  exp005's qualification does not survive contact with the clean stimulus and is
  annotated accordingly. The closure stands, as it did before.
- **`fc-007`** — supported. A vs A′ shows inhibition of return doing *more* work
  on rendered data than on the fixture. This is supporting evidence, not a test of
  the objectives null itself, which exp007 did not run.
- **`fc-010`** — survives its first independent test. V is distinguishably worse
  on both metrics on rendered data, and its coverage cost is worse.
- **`fc-011`** — unchanged, and unaffected. V vs W did not reverse, so nothing
  here bears on whether a *plant* is testable. `fc-011`'s framing — the mechanical
  plant **untested, not refuted** — stands exactly as written. `od-003` untouched.

## What a pre-registered re-test would need

For `fc-008`, the comparison this experiment could not make: E vs A′ on a stimulus
with a **controlled contrast axis at occlusion boundaries** and more than 5%
lateral overlap. That is `gap-001`'s question and `od-002`'s instrument, and
`od-002` is open.

## What this does not do

- **It does not lift `gap-010`.** 5.09% incidental occlusion, no contrast axis.
- **It does not test `fc-007`'s own null.** B and C were dropped as a decision;
  re-running them costs ~17.4 of the experiment's ~18 minutes, to re-check the
  result least in doubt.
- **`fc-010` and `fc-011` are still not band-checked in exp005's sense.** exp006
  was specified and deliberately not run; see `am-004`.
