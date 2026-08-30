# exp005 — findings

**Measured** at `9f40198`, Python 3.13.15 / numpy 2.5.2. Pre-registered in
`preregistration.md`, committed alone before the runner existed. No Blender
needed: the bands come from the scene model's geometry, which is arithmetic.

**No foreclosure is reversed here**, as declared in advance.

## Headline — neither falsifier fired, and the reason matters

**The floor is real. It did not do what the hypothesis said it did.**

The floor exists, exactly as exp004 predicted and more strongly than expected. In
the AT band, p90 depth error is **policy-invariant**:

| arm | A | A′ | B | C | D | E |
|---|---|---|---|---|---|---|
| AT p90 (m) | 1.5038 | 1.4944 | 1.5100 | 1.4968 | 1.4891 | 1.4906 |

Six policies, from the expensive field integral to a blind raster, spread over
**1.40%**. exp004's independently measured fixture p90 at discontinuities was
**1.49626 m**; every arm here lands inside that. The largest difference between
any two arms (0.0209 m) is **smaller than the 2% materiality floor** (0.0299 m),
so every AT p90 comparison is indistinguishable *because the arms are pinned to
the artefact*.

**But the floor did not attenuate the effects — it sat above them.** The
hypothesis was that removing the band would reveal effects it had been masking.
The opposite happened: **effects shrink in the AWAY band**, and several verdicts
flip from distinguishable to indistinguishable.

Neither falsifier fires as written. Falsifier 1 required the AWAY verdicts to
*match* pooled; they do not. Falsifier 2 required effect sizes to *grow*; they
shrink. The outcome is a third one the specification did not name, and it is
reported as such rather than forced into either.

**What was actually measured: the differences between variance-driven policies
live at and near depth discontinuities, and vanish away from them.** The
discontinuity band was not fog over the result. It was carrying the result.

## The gradient

`x_bar` by band, for the variance-driven comparisons:

| comparison | metric | AT | MIDDLE | AWAY | |
|---|---|---|---|---|---|
| exp002 E vs A′ | median | 2.53 | 1.41 | **0.38** | monotone decreasing |
| exp002 C vs A′ | median | 1.39 | 0.85 | **0.19** | monotone decreasing |
| exp001 C vs A′ | median | 0.46 | 1.06 | 0.32 | not monotone |
| exp001 A vs A′ | median | 1.17 | 1.17 | 0.58 | decreasing at the end |
| exp002 D vs E | median | 13.60 | 24.80 | **32.20** | monotone **increasing** |

The two comparisons that carry `fc-008` — E vs A′ and C vs A′ on median — fall
monotonically to nothing with distance from the discontinuities. **D vs E, the
value of the validity mask, goes the other way**: it is largest in the AWAY band.
The mask's value is real everywhere; the variance's value is not.

## Falsifier 1 — did not fire on its stated trigger

The AWAY verdicts do **not** match pooled. Four flip:

| comparison | metric | POOLED | AWAY |
|---|---|---|---|
| exp001 A vs A′ | median | 1.10× **DIST** | 0.58× indist |
| exp002 E vs A′ | median | 1.38× **DIST** | 0.38× indist |
| exp002 E vs A′ | p90 | 1.96× **DIST**, E worse | 1.75× **DIST**, **E better** |
| exp002 C vs A′ | median | 1.05× **DIST** | 0.19× indist |

So its trigger is not met. **Its conclusion is nonetheless supported, by the
opposite route**: the floor hypothesis said exp001's and exp002's effect sizes
were attenuated by the artefact band, and they were not — they were produced by
it. Reported plainly, as the preregistration required of this outcome.

## Falsifier 2 — did not fire; effects shrank

exp002's saliency value did not rise above its measured ~2%. On median in the
AWAY band it is **indistinguishable** (0.38×). exp001's null on gaze objectives
did not become distinguishable — it became *more* null (C vs A′ 0.72× pooled →
0.32× AWAY on median).

**The one sign reversal**, and it needs its absolute magnitude to read correctly:
E vs A′ on p90 in the AWAY band is distinguishable with **E better**, by
**0.00078 m**. The materiality floor binds there (0.000446 m), and it clears it
by 1.75×. It is material by the declared rule and sub-millimetre in metres. Both
facts are the result; neither alone is.

## Magnitudes, because the ratios alone mislead here

The AWAY band carries **0.18%** of the total squared error (measured in the
preregistration, before any of this ran). Absolute errors there:

| | AT | MIDDLE | AWAY |
|---|---|---|---|
| A′ median (m) | 0.0212 | 0.0109 | **0.0070** |
| A′ p90 (m) | 1.4944 | 0.0747 | **0.0234** |

An AWAY-band verdict is a verdict about differences of 1e-4 m on errors of
7e-3 m. This is why `binds` is recorded for every comparison: at AT p90 the
**materiality floor** binds (every arm is on the artefact), while in AWAY the
**seed-to-seed spread** binds almost everywhere. The two are different regimes
and `x_bar` alone does not distinguish them.

## The control — the artefact was in the metric, not in the steering

Selection masked to the AWAY band, scored on the AWAY band. **No arm terminated
early**, in either experiment — the packing limit declared in the preregistration
was not reached, because only A′ carries inhibition of return and it had exactly
enough room at 40 fixations (40.0 distinct fixations, 0 seeds terminated).

**Scanpath agreement between masked and unmasked arms:**

| | A | A′ | B | C |
|---|---|---|---|---|
| exp001 | **0.0000** | **0.0000** | 0.0903 | **0.0000** |
| exp002 | — | 0.0016 | — | **0.0000** |

**The verdicts are essentially unchanged:**

| comparison | metric | free steering | masked steering |
|---|---|---|---|
| exp001 C vs A′ | median | 0.32× indist | 0.74× indist |
| exp001 C vs A′ | p90 | 0.69× indist | 0.73× indist |
| exp001 A vs A′ | median | 0.58× indist | 0.20× indist |
| exp002 C vs A′ | median | 0.19× indist | 0.87× indist |
| exp002 C vs A′ | p90 | 0.29× indist | 0.50× indist |
| exp001 B vs C | median | 0.31× indist | **1.13× DIST** |
| exp001 B vs C | p90 | 0.46× indist | **1.03× DIST** |

So **restricted scoring changed the verdicts and restricted steering did not add
to it** — the artefact was in the metric. The exception is B vs C, which becomes
distinguishable at 1.13× and 1.03×, both knife-edges, and is reported as such.
`cn-001` rests on the argmax evidence (0 of 144 agreement), not on the trajectory
comparison, so this does not disturb it.

**This is exp001's result again in a new place, and it is the strongest thing
here.** Three arms select *completely different* fixations under masking — 0.0000
agreement over 144 and 640 comparisons — and produce the same verdicts. Where the
loop looks continues not to matter on this stimulus.

## What this does to the foreclosures — annotated, not reversed

**`fc-007` stands, and is strengthened.** Its null on gaze objectives is not an
artefact of the discontinuity band: C vs A′ is *more* indistinguishable in the
AWAY band than pooled, on both metrics, and unchanged under masked steering.

**`fc-008` is qualified, and this is the substantive finding.** Its claim is that
posterior variance carries information beyond the validity mask. That claim rests
on E vs A′, which was distinguishable on both primary metrics pooled. In the AWAY
band it is **indistinguishable on median** and **reversed on p90**. So the
evidence for `fc-008` comes from the AT and MIDDLE bands — the regions exp004
showed are pathological on this fixture.

`fc-008`'s own `but_the_effect_is_small` clause already recorded a 65:1 ratio
between the mask's value and the variance's. This narrows where even that 1 part
comes from. **The foreclosure is not reversed here**, per the preregistration.
What a pre-registered re-test would need: the E-versus-A′ comparison run on a
*rendered* stimulus whose discontinuity regions are not pathological, which is
`od-002`'s instrument and `od-002` is still open.

**`fc-010` is untouched.** exp005 does not test it; it is about search windows.

**`gap-010` is not lifted.** AWAY-band pixels are still on a stimulus whose
discontinuity regions are pathological. Restricting the score does not change the
stimulus.

## Validity of the re-analysis

`POOLED` reproduces exp001's stored final-step metrics **exactly**, to all
recorded digits, on every arm and seed spot-checked before the run
(`median_abs_err`, `p90`, `rmse` for A and A′ at seeds 0 and 3). Same harness,
same measurement — so a band difference is the band and not the plumbing.

## Limits

- **One stimulus.** Everything here is on the analytic fixture. The AWAY band is
  not a clean stimulus; it is the clean part of a stimulus whose other 71% is
  pathological.
- **The AWAY band is nearly error-free**, so its verdicts are spread-limited and
  rest on sub-millimetre differences.
- **The bands are inherited from exp004 and not re-derived.** They were chosen
  for a different experiment's question.
- **B vs C under masked steering** is the one place restricted steering changed a
  verdict, at a knife-edge, and it is not explained here.
