# exp008 — findings

**Measured** at `7dcaac7`, 4 levels × 8 seeds × 3 arms, budget 40, Blender
**5.2.0 LTS** (`fbe6228777e7`); Python 3.13.15 / numpy 2.5.2.

**No foreclosure is reversed.** `gap-010` is annotated, not closed. `od-002`
stays open and its stale `why_not_scheduled` is corrected.

## Outcome (d) — NON-MONOTONE, with a peak at 8.84% occlusion and a collapse above it

The sweep did not produce a slope. It produced an **optimum and a ceiling**, which
the specification correctly identified as the stronger claim: it sizes every
stimulus after this one.

E vs A′ on p90, as the ratio of the arm means — the view the growing bar cannot
distort:

| occlusion | 1.97% | 4.26% | **8.84%** | 17.16% |
|---|---|---|---|---|
| E / A′ p90 | 1.27 | 1.16 | **3.10** | **1.01** |
| `x_bar` | 9.04× | 2.20× | 15.83× | 0.56× |

**The allocation question is most visible at ~8.84% occluded surface, and stops
being askable at 17.16%.**

### Why it collapses — the stimulus saturates

At the top level every arm converges on the same error:

| occlusion | A′ p90 | D p90 | E p90 | spread |
|---|---|---|---|---|
| 1.97% | 0.0330 | 0.4200 | 0.0420 | 0.3869 |
| 4.26% | 0.0459 | 0.2758 | 0.0532 | 0.2298 |
| 8.84% | 0.1470 | 0.6545 | 0.4563 | **0.5075** |
| 17.16% | **1.4792** | **1.4828** | **1.4957** | **0.0165** |

A blind raster and a variance-driven policy become indistinguishable at 17.16%
occlusion. The ceiling is not arbitrary: **the prior is 3.0 m and the background
is 4.5 m, so an unmeasured background pixel reads exactly 1.5 m of error.** All
three arms sit there. When enough surface is unmeasurable, every policy leaves
most of the frame at the prior and no allocation strategy can distinguish itself.

This is the same value exp005 measured as the fixture's AT-band floor (1.494 m),
reached here by a different route: exp005 found it in the artefact band of a
degenerate stimulus, exp008 finds it by making an honest stimulus degenerate.

### D vs E — outcome (c), monotone decrease

| occlusion | 1.97% | 4.26% | 8.84% | 17.16% |
|---|---|---|---|---|
| `x_bar` median | 41.96× | 22.42× | 3.83× | 1.79× |

**Monotone decrease**, `r²` 0.724, log-log exponent −1.55. The validity mask's
worth *falls* as occlusion rises — and at 17.16% on p90, D is nominally
*better* than E (0.43×, indistinguishable).

This is outcome (c) and it contradicts nothing, once read with the saturation
above: knowing where the data is matters less when there is less data anywhere.
`fc-008`'s 65:1 ratio was measured at effectively 0% occlusion, and this says that
ratio is a property of a nearly-unoccluded stimulus rather than a constant.

## Why `x_bar` alone would have misled — the bar grows faster than the effect

The specification required `mean_diff` and `bar` separately, and it was right:

| comparison | metric | bar at 1.97% | bar at 17.16% | growth |
|---|---|---|---|---|
| E vs A′ | median | 0.000173 | 0.004359 | **25×** |
| E vs A′ | p90 | 0.000994 | 0.029584 | **30×** |
| D vs E | median | 0.000272 | 0.009334 | **34×** |

Seed-to-seed spread explodes with occlusion. A falling `x_bar` at high occlusion
is therefore ambiguous between "the effect shrank" and "the noise grew", and only
the arm-mean ratio separates them. It says both happen: at 17.16% the arms
genuinely converge (ratio 1.01) *and* the spread grows.

## The x-axis — and a correction to exp007's headline

**exp007's "5.09% lateral overlap" is ~61% frame border.** The gap between the two
overlap measures is a **constant 3.12%** at every geometry tested — card heights
from 15% to 100%, split counts from 1 to 8. That constant is left pixels whose
correspondent falls outside the right image because the right camera sits a
baseline to the side. It is a property of the camera, not the scene.

| k | left-occluded (x-axis) | right-unmatched | border | card area | AT band |
|---|---|---|---|---|---|
| 1 | **1.97%** | 5.09% | 3.12% | 46.0% | 25 985 |
| 2 | **4.26%** | 7.38% | 3.12% | 30.2% | 33 691 |
| 4 | **8.84%** | 11.97% | 3.12% | 26.5% | 48 147 |
| 8 | **17.16%** | 20.29% | 3.12% | 24.6% | 48 400 |

Genuine occlusion in exp007's stimulus is **1.97%**, not 5.09%. Pinned by tests,
including that the border stays constant — if it ever moves, this decomposition
stops holding.

**The AT band saturates too**: 48 147 → 48 400 between the last two levels, a 0.5%
increase for a 94% increase in occlusion. By `k = 8` nearly the whole frame is
within 10 px of a discontinuity, so the band stratification stops discriminating —
an independent sign of the same saturation.

## Band series

`x_bar`, E vs A′ on p90:

| occlusion | AT | MIDDLE | AWAY |
|---|---|---|---|
| 1.97% | 3.60× | 4.69× | 1.53× |
| 4.26% | 1.34× | 2.20× | 0.47× |
| **8.84%** | **18.16×** | 3.20× | 1.17× |
| 17.16% | 0.29× | 0.69× | 0.94× |

At the optimum the effect is overwhelmingly in the AT band (18.16×), which is what
the mechanism predicts: allocation pays where surface is unmeasurable. At
saturation it is gone from every band.

## Limits — and they are substantial

- **Four points.** Linear and saturating are not distinguishable, and the `k = 2`
  dip (E vs A′ falls below `k = 1` on both metrics) is not explained. It may be
  noise in a four-point series; it may be real. **The peak at `k = 4` is not
  established as the maximum of a smooth curve — it is the largest of four
  measured points.**
- **Card area is a confound**, declared in advance: it falls 46.0% → 24.6% as
  occlusion rises, monotonically, so this sweep cannot fully separate occlusion
  fraction from how much card is in frame. It moves 1.9× while occlusion moves
  8.7×, which weakens but does not remove the confound.
- **One geometry family, one texture family, one camera.** The lever cuts cards
  into strips; a different way of raising occlusion might not saturate at the same
  place.
- **The saturation ceiling is a property of the PRIOR**, 3.0 ± 3.0 m, not of
  occlusion as such. A different prior would move the ceiling and probably the
  optimum with it. Nothing here sweeps that.

## What this changes, and what it does not

**It does not lift `gap-010`.** `gap-010` is about the *fixture* having no true
half-occlusions. This characterises how much occlusion a *rendered* stimulus
needs, which is a different question — and it now has an answer: **around 9%, and
below 17%.** Annotated on `gap-010`, not closed.

**`od-002` stays open**, and its `why_not_scheduled` is corrected. It read "the
repository does not run yet, and od-001 has not been implemented"; the loop now
runs on two stimuli and od-001 closed at `fc-009`. Both conditions are met. The
reason it is still not scheduled is now different and better: its subject is
*contrast* at occlusion boundaries, which needs material changes rather than
geometry — and it should be asked at the occlusion fraction this sweep identifies
rather than at an arbitrary one.

**No policy changed. No acquisition. `od-003` untouched.**
