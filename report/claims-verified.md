# Claim verification for the technical report

**Verified at `d62693f`** against the experiments' `findings.md`,
`preregistration.md` and `results.json`, `docs/state.yaml` and
`docs/inherited-measurements.yaml`. No experiment was re-run; one figure script
was re-executed to confirm a scanpath.

**No prose was written and no `.tex` file was touched.** This document is a
verification pass, not a draft.

---

## The count

This tally is itself a measurement about the drafting process, and it is the
reason this iteration exists.

| verdict | n | claims |
|---|---|---|
| **CONFIRMED** | **10** | 2, 4, 5, 8, 9, 17, 18, 20, 21, 22 |
| **CORRECTED** | **3** | 6, 12, 16 |
| **UNDER-QUALIFIED** | **8** | 1, 3, 7, 10, 11, 13, 14, 15 |
| **UNSUPPORTED** | **0** | — |
| **PARTIAL** | **1** | 19 (verified except its page range) |
| total | 22 | |

**Of the 18 substantive claims, 7 stand as written.** Eight are true in the
band, arm or metric they came from and wrong or unsupported pooled — the
category the specification called the most useful, and it is the largest. Three
are wrong on the number.

**Nothing was unsupported.** Every claim traces to something real in the record;
the failure mode throughout is scope and metric, not invention.

**The recurring defect, in one sentence:** a figure measured on one metric, one
band or one arm is carried into a sentence that does not name it. Claims 1, 12
and 16 are the same mistake at increasing cost, and claim 16 inverts the
finding.

---

## Policy and allocation

### 1. "The validity mask is worth roughly sixty times what posterior variance adds on top of it."

**UNDER-QUALIFIED.** The ratio is **65.3 — on median absolute error only. On p90
it is 3.5.**

- Comparison: `(D − E) / (E − A′)` per metric, at fixation 40 — bio-017.
- Arms: **D** blind raster, **E** masked coverage, **A′** variance + inhibition of return.
- 16 seeds, budget 40, over valid known pixels on the **analytic fixture**. Not banded, not pooled across stimuli — exp002 has one stimulus.
- Source: `docs/inherited-measurements.yaml` bio-017, derived from bio-015 and bio-016; `experiments/exp002_saliency_value/verdicts.json`.

bio-017's own note is a warning the report must carry: *"MOST EXPOSED TO gap-010
of anything in this record… this ratio could move a long way. Do not cite it as
a general property of the framework."* exp008 then measured exactly that — the
mask's worth falls monotonically with occlusion, `x̄` 41.96 → 1.79 from 1.97% to
17.16% occluded, and *"fc-008's 65:1 ratio was measured at effectively 0%
occlusion"* (`experiments/exp008_occlusion_sweep/findings.md`).

**Proposed:** "On median error, on a stimulus with effectively no occlusion,
knowing *where* the data is was worth 65× what knowing *how uncertain* it is
added on top. On p90 the ratio narrows to 3.5:1, and it falls with occlusion."

### 2. "Two gaze objectives never once selected the same pixel, at any step, on any seed."

**CONFIRMED, and "never once" is literally true — not a rounded near-zero.**

- **A vs C: `argmax_agreement` = 0.0 across 144 comparisons** (8 seeds × 18 steps) — bio-011.
- **B vs C: `argmax_agreement` = 0.0 across 144 comparisons** — bio-012.
- Source: `experiments/exp001_gaze_objective/run.py::agreement_probe` and `::agreement_probe_bc`.

Two facts that strengthen it and should travel with it. The fields are
**moderately rank-correlated** (Spearman +0.348 for A/C, +0.278 for B/C), so
this is a statement about the argmax and not about the objectives being
unrelated — bio-011's note says that is precisely why the argmax rate is the
number to act on. And B-vs-C's picks sit a **median 115.2 px apart, 3.4 fovea
sigma** — different regions of the image, not neighbouring pixels.

**Scope to state:** one fixture, and the probe evaluates both objectives *at the
same state on the same stride-4 candidate grid*, driven along one arm's
trajectory so only the objective varies. It is not two arms running
independently.

### 3. "Their results were statistically indistinguishable."

**UNDER-QUALIFIED — the word "statistically" is the problem.** The criterion in
force was **not a significance test**, and exp012 exists because of that.

- A′ vs C at 18 fixations: **median diff −0.00063 against a bar of 0.00088; p90 diff +0.00112 against 0.00793** — indistinguishable on both pre-registered primaries, and *"they do not even agree on a direction"* (bio-010).
- The bar is met-001, `max(sd, 0.02 × mean)` with `sd = np.std(d, ddof=1)` — it asks *does the effect exceed scene-to-scene variation*, not *is there an effect*.
- Under the **sign test** the answer agrees: **6 of 8 seeds, p = 0.2891** — `docs/state.yaml:3729`, `fc007_primary_flip`.
- Under the **se bar** it would read distinguishable, but the se bar is `t > 1`, two-sided p 0.328–0.391, *"not a significance test at any conventional level"* — `docs/state.yaml:3737-3739`.

**Proposed:** "Indistinguishable under exp001's pre-registered bar — the effect
did not exceed the seed-to-seed spread — and the sign test agrees there is no
effect (6 of 8 seeds, p = 0.29)." Name the criterion; drop "statistically".

### 4. "Without inhibition of return the policy spent ten consecutive fixations on one pixel after visiting eight distinct locations."

**CONFIRMED, exactly as phrased.**

- 18 fixations, **9 distinct**: 8 pixels once each (steps 0–7), then **pixel (170, 94) for steps 8–17, ten consecutive visits** — bio-001, bio-002; re-derived from `run_baseline(steps=18, seed=0)` when the figure was built.
- Source: `docs/inherited-measurements.yaml` bio-001/bio-002, pinned by `tests/test_loop_port.py::test_nine_distinct_fixations_out_of_eighteen` and `::test_the_loop_locks_up_on_one_pixel`.

**One run, seed 0.** The lockup generalises — arm A averages 9.62 distinct of 18
over 8 seeds (bio-010) and 10.06 of **40** at the longer budget (bio-014), where
its median error *rises* monotonically from step 6 — but "ten consecutive after
eight distinct" is this seed's trajectory. Say "at seed 0" or give the 9.62.

Incidental, and visible in the figure: step 6 lands at **(169, 94)**, one pixel
above the lockup pixel.

### 5. "Uniform weighting beat foveal weighting on every measure, on every seed, on a complete spherical capture."

**CONFIRMED.** `d = F − U`, positive is F worse; **0/8 seeds favour F in every
cell, p = 7.8e−3**, across EQUATOR, MID, POLE and ALL × {median, p90} — 8 cells.
ALL median +0.7983 at **4× the bar**.

- Source: `experiments/exp013_spherical_allocation/findings.md`. 8 seeds × 40 fixations × 2 arms, one shared Blender equirectangular capture per seed.
- Mechanism, measured not asserted: solid angle receiving >1% of peak weight is **1.0000** for U and **0.2149** for F. *"F leaves four fifths of the sphere at the prior."*

**"Every measure" is two metrics** (median, p90) in four band groupings. If the
prose implies more, tighten it.

**The qualification exp013 insists on:** *"It does not mean allocation is
worthless."* A foveal weight models an acuity gradient; a uniform capture has
none, so weighting by gaze discards information already in hand. The result is
about **this sensor**, and exp013 also states the comparison as built cannot
show outcome (a).

---

## Acquisition

### 6. "Verging to acquire cost roughly an order of magnitude in accuracy at several times the compute."

**CORRECTED on both halves — and the accuracy cost is attributed to the wrong
thing.**

| | claimed | measured |
|---|---|---|
| accuracy | ~10× | **7.5×** (median, intersection: W 0.01476 → V 0.11106) |
| compute | "several times" | **2.6×** hypotheses (57 → 147); **19 front-end calls** vs 1 |

- Source: `experiments/exp003_vergence_acquisition/findings.md`, title line and the intersection and cost tables. 3 arms × 16 seeds × 18 fixations, 37 383 shared pixels.

**The misattribution matters more than the number.** The narrow *fixed* arm N is
**equally bad**: N median 0.11074 against V's 0.11106 — a difference of
**0.01× the bar**. Both narrow arms are ~7.5× worse than wide. So **narrowing
the search window did the damage, not verging.** What verging bought was the
tail (p90 2.12 → 1.03, 3.02× the bar) and **+21.7% coverage**.

**Proposed:** "Narrowing the disparity search cost 7.5× in median accuracy, and
verging to re-acquire did not recover it — it halved the tail and bought 21.7%
more coverage, at 2.6× the hypothesis count and 19 front-end calls against one."

### 7. "The vergence controller verged away from its target."

**UNDER-QUALIFIED — true, at a named place, and the run recovers.**

- **Seed 0, fixations 5–7:** the fixation sat on true disparities of **15.17 and 18.96 px** while `d_sub` there read **8.00 and 6.00** — the lower window edge. **The controller verged away: 10.0 → 7.9 → 5.95 px.**
- Source: `experiments/exp003_vergence_acquisition/findings.md:138`.
- Mechanism: `vergence` estimates fixation disparity as the median of `d_sub` over valid pixels in a foveal window. **The pixels carrying the error signal are exactly the pixels the validity mask removes** — at window [8,12] with the near card at 18.96 px, only 41.8% survive as valid and their median reads 10.32, not the truth.

**Across the run it partially recovers:** 64% of fixations end with their true
disparity inside the window, and median |`d_fix` − true| is **0.96 px, 11% of
the scene's range**. exp003's own words: *"not stuck, just badly steered."* Do
not write it as the controller's steady-state behaviour.

### 8. "Closing the loop helped at roughly forty times the cost in renders and matcher time."

**CONFIRMED. 41×, and it is wall-clock seconds over exactly those two things.**

| | renders | render s | front-end matches | front-end s | total |
|---|---|---|---|---|---|
| OPEN | 1 | 0.57 | 1 | 0.05 | **0.62 s** |
| CLOSED | 41 | 23.37 | 41 | 2.24 | **25.6 s** |

- Source: `experiments/exp010_closed_loop/findings.md:106`. **The render is 91% of it.**
- Worth keeping: exp010 records that timing `measurement()` alone *"would have shown 0.02 s for both arms and made this table wrong"* — the matcher cost CLOSED redoes on every saccade was missing from the first version of the runner.

### 9. "Coverage exceeded accuracy by more than an order of magnitude at every occlusion level."

**CONFIRMED at every level, and by far more than an order of magnitude.**

| level | occlusion | accuracy term | coverage term | ratio |
|---|---|---|---|---|
| k1 | 1.97% | 0.01045 | 0.36810 | **35×** |
| k2 | 4.26% | 0.00165 | 0.37199 | **225×** |
| k4 | 8.84% | 0.01155 | 0.38704 | **34×** |
| k8 | 17.16% | 0.00112 | 0.38066 | **341×** |

- Source: `experiments/exp011_consolidation/findings.md`, question 3. 24 seeds × 4 levels × 2 arms. Yardstick pre-registered: mean absolute error over all 76 800 cells, unmeasured cells left at the prior. **The decomposition is exact** — accuracy + coverage = total, to five decimals at every level.
- exp011's prose says *"between 33× and 341×"*; the table's minimum is 34×. Use the table, or say "at least 34×".

exp011's judgement, worth quoting rather than paraphrasing: *"A closed loop's
value here is not that it measures the same cells better. It is that it measures
cells an open loop cannot measure at all"* — leaving 1.35–1.39 m of error on
21 788–25 910 cells OPEN never reached.

### 10. "exp011 held consistently across occlusion levels."

**UNDER-QUALIFIED. Consistent in direction; explicitly *not* consistent in
verdict.**

**What is consistent:** `mean_diff` is negative — CLOSED better — in **every band
at every level, 16 of 16 cells**, and the POOLED verdict is CLOSED-better at all
four levels (`x̄` 2.61, 1.12, 1.11, 1.24).

**What is not**, in exp011's own bold: *"Per band, the verdicts are
level-dependent and non-monotone."*

| band | k1 | k2 | k4 | k8 |
|---|---|---|---|---|
| AT | 1.60 ✓ | 0.80 ✗ | 0.91 ✗ | 1.18 ✓ |
| MIDDLE | 2.31 ✓ | 1.09 ✓ | 1.12 ✓ | 1.32 ✓ |
| AWAY | 3.52 ✓ | 1.51 ✓ | 2.82 ✓ | **0.97 ✗** |
| POOLED | 2.61 ✓ | 1.12 ✓ | 1.11 ✓ | 1.24 ✓ |

**AT is distinguishable at k1 and k8 but not k2 and k4**, and AWAY *loses*
distinguishability at k8. The raw effect is non-monotone too: 36.6% → 33.0% →
**48.8%** → 30.7% relative gain.

**And exp011 corrects exp010 downward, which the report must carry:** *"exp010's
verdicts were too confident."* **Every band's `x̄` fell at 24 seeds** because the
8-seed sd was an underestimate — MIDDLE went 2.60 → 1.12, its sd rising 3.21×.
exp010's verdicts stand *"but with far less margin than reported."*

Also: **23 of 24 seeds favour CLOSED in the AT band at k=4** while the verdict
reads indistinguishable. exp011 is emphatic that this *"should not be read as
'no effect'"* — bio-076 records the sign test at p = 3e−6 across levels.

### 11. "The accuracy gain is attributable to re-acquisition alone, because both arms re-verge and both weight identically."

**UNDER-QUALIFIED, and "alone" is unsupported.** The premise is recorded; the
inference is band-dependent and the attribution has a named, unexcluded
alternative.

**The premise is recorded, and it is exp014's first result.** *"`run_arm` calls
`engine.measurement(yf, xf)` for **both** arms at every fixation, and
`measurement` calls `vergence(yf, xf)` internally. OPEN's pedestal tracks its
gaze exactly as CLOSED's does. Only its images are stale."*
(`experiments/exp014_pedestal_vs_allocation/findings.md`.)

**But the conclusion comes from exp014's arms, not from the premise** — and it
is explicitly **band-dependent**. Retention = (OPEN − FROZEN)/(OPEN − CLOSED):

| level | AT | MIDDLE | AWAY | POOLED |
|---|---|---|---|---|
| k1 | −18.05 | −45.91 | −383.16 | −62.03 |
| k2 | −14.18 | −0.69 | **+1.07** | −1.36 |
| k4 | −4.87 | +1.10 | **+1.10** | +0.14 |
| k8 | −12.58 | +1.21 | **+1.29** | +0.23 |

- **AWAY from discontinuities at k2–k8: the claim holds** — retention 1.07–1.29, *"the pedestal contributes nothing there… allocation, not scaling."*
- **AT discontinuities: exp014 says it cannot separate them.** *"A measurement that puts one arm off-scale cannot apportion a 0.008 m difference, and reporting a ratio of −14 as 'the pedestal's share' would be arithmetic without meaning."*
- **At k1 nothing holds** — POOLED retention −62.03.

**A second, independent reason "alone" is too strong.** exp010 names an
unsettled confound: neither arm's fusion accounts for correlation between
successive measurements, and **OPEN violates the independence assumption worse**
— its 40 measurements come from one disparity map. *"Some unknown part of
CLOSED's advantage may be that rather than better data… The check that would
settle it… Not run."*

**Proposed:** "Away from depth discontinuities, freezing the pedestal costs
nothing — so CLOSED's advantage there comes from the fresh captures rather than
from re-linearisation. At discontinuities the experiment cannot separate the
two, and one confound — OPEN's far more correlated measurements — remains
unexcluded."

---

## The instrument

### 12. "The fixture is roughly an order of magnitude worse than a render of the same geometry at depth discontinuities."

**CORRECTED. The metric decides the number, and "48×" in the record is a bar
multiple, not an error ratio.**

| AT band | fixture F | render R | ratio | × bar |
|---|---|---|---|---|
| median | 0.02050 | 0.01248 | **1.64×** | 4.38 |
| **p90** | **1.49626** | **0.06580** | **22.7×** | **47.80** |

- Source: `experiments/exp004_scene_model_check/findings.md`, falsifier 2. 8 seeds, policy **A′**, 18 fixations, AT = within 10 px of a depth discontinuity.
- Direction: **the render is better** — the opposite of what the specification predicted.

So "roughly an order of magnitude" is **too small for p90 (23×) and far too
large for median (1.6×)**. The 48× that appears in `docs/state.yaml` is
`diff / bar`, a distinguishability multiple, and must not be read as an error
ratio.

**The mechanism is measured and is the better sentence:** the fixture's
reflect-warp smears a stretched copy of the occluding surface's texture across
the depth step, which is highly matchable and geometrically wrong. On AT pixels
the matcher marks **valid**, the fixture is wrong by >2 px in **21.7%** of them
against the render's **4.3%** — **5× the rate of confident gross errors, at a
slightly higher validity rate.** F's p90 depth error at discontinuities is
**1.50 m on a scene 2.4–4.5 m deep.** The common-scanpath control leaves it
intact at **12.28×** the bar, so it is the stimulus and not where the loop
looked.

### 13. "Those pixels are two fifths of the image and carry four fifths of the total error."

**UNDER-QUALIFIED — both figures are right, the denominator is not "the image",
and it is *squared* error.**

| band | pixels | share of pixels | share of total squared error |
|---|---|---|---|
| **AT (≤ 10 px)** | **20 302** | **38.23%** | **82.27%** |
| MIDDLE (10–24 px) | 17 566 | 33.08% | 17.55% |
| AWAY (≥ 24 px) | 15 230 | 28.68% | 0.18% |
| total | 53 098 | 100% | 100% |

- Source: `experiments/exp005_stratified_reanalysis/preregistration.md:35` — **measured before the run**.
- The denominator is the **53 098 valid known pixels**, not the 76 800-pixel image. Over the image AT is **26.4%**, not 38%.
- The share is of **total squared error**, not absolute error.

**Proposed:** "The pixels within 10 px of a depth discontinuity are 38% of the
valid measured pixels and carry 82% of the total squared error."

Do not conflate this with bio-007, which is a different statement about the same
fixture: the **worst 5%** of valid pixels (2 655 of 53 098) carry **80.9%** of
the squared error. Two different pixel sets, both landing near four fifths.

### 14. "The artefact passes left-right consistency."

**UNDER-QUALIFIED — measured as part of the validity mask, but the LR term is
never isolated.**

- `front_end_block` returns `valid = (distinct > 0.10) & agree`, where `agree = lr_consistency(...)` — `src/bio3dvision/matching.py:102-104`. **Passing LR consistency is a necessary condition for `valid`.**
- exp004 measured, on the fixture's AT pixels, a **valid fraction of 0.785** with **21.7% wrong by more than 2 px**. Those pixels therefore did pass the LR check.

**So it is measured, not inferred — but only as a conjunct.** No reported number
separates the LR term from the `distinct > 0.10` distinctiveness term, so the
record cannot say how many pixels the LR check alone would have admitted.

**Proposed:** "The artefact survives the front end's validity test, of which
left–right consistency is one of two conditions: 78.5% of discontinuity pixels
are marked valid and 21.7% of those are wrong by more than 2 px." Do not claim
the LR check was tested in isolation.

### 15. "Policy questions are sharpest near a tenth of the surface occluded, and above roughly a sixth the stimulus stops discriminating."

**UNDER-QUALIFIED — both halves check out for the *allocation* question, and the
plural "policy questions" is what fails.**

**First half, confirmed.** The allocation question is most visible at **8.84%**
occluded surface — E/A′ p90 ratio 3.10, `x̄` 15.83 — and exp011's acquisition
gain peaks at **the same level**, independently.

**Second half survives the hardest check, which the specification was right to
demand.** This is **not** a denominator artefact. It is established on the ratio
of arm means, *"the view the growing bar cannot distort"* — E/A′ p90 falls to
**1.01** at 17.16% — and on the arm means themselves converging:

| occlusion | A′ p90 | D p90 | E p90 | spread |
|---|---|---|---|---|
| 8.84% | 0.1470 | 0.6545 | 0.4563 | 0.5075 |
| **17.16%** | **1.4792** | **1.4828** | **1.4957** | **0.0165** |

The ceiling has a measured cause: *"the prior is 3.0 m and the background is
4.5 m, so an unmeasured background pixel reads exactly 1.5 m of error."* All
three arms sit there. Source: `experiments/exp008_occlusion_sweep/findings.md:23`.

**What fails is the plural.** exp011's **acquisition** comparison still
discriminated at 17.16% — POOLED `x̄` 1.24, CLOSED better, relative gain 30.7%.
So the stimulus did not stop discriminating for every policy question, only for
the allocation one.

**Proposed:** "The *allocation* question is sharpest near a tenth of the surface
occluded and stops being askable above roughly a sixth, where all three arms
converge on the 1.5 m error of an unmeasured background. The acquisition
question still discriminated there."

---

## Inherited

### 16. "Anti-calibration was measured across two matchers, two readouts and two stimulus families in the predecessor repositories."

**CORRECTED, and the correction reverses the sentence's force.** The record does
not show a finding replicating across families. **It shows the families
disagreeing in sign.**

**The counts are wrong.** Three matchers appear (`block`, `energy`,
`multiscale_energy`) and three stimulus families (`rds`, `middlebury2014`,
`rendered_chart`) — gap-001's own `matcher` and `stimulus_family` fields. Three
readouts, not two: as-exp006b records that *"a third readout (SSD curvature,
SGBM, population second moment) agrees."*

**The substantive error.** Block matching's pooled median occluded/matched
variance ratio is **0.324 on Middlebury photographs** and **1.923 on RDS** — *"A
factor of 5.94, and a reversal of sign about 1.0."* On photographs the variance
in half-occlusions is **lower** than in matched regions (dangerous); on RDS it is
roughly **twice as high** (safe). as-exp005a states the consequence directly:
*"The anti-calibration is therefore **NOT a stimulus-independent property** of
block matching's variance, on the evidence that exists."*

**What the record does NOT establish** — the specification asked for this
explicitly:

1. **That it generalises across stimulus families.** It does not; that is gap-001, and it is open.
2. **Whether it is a property of real imagery or of high contrast.** Undetermined. On photographs the two are confounded; the inversion lives specifically in the **high-contrast** cell (0.254 in exp006, below the matched median in 8 of 8 scenes in exp004) while low contrast inflates safely (1.28). **RDS cannot separate them** — a binary random-dot field is contrast-uniform by construction.
3. **Anything measured in this repository.** Every entry is status `inherited`. gap-001: *"Both were measured; neither has been reproduced here."*
4. bio-008 must **not** be cited as bearing on it. Its own note forbids it: the fixture has no half-occlusions (gap-010), and on it the posterior is *positively* correlated with error (Spearman +0.42 / +0.57).

**Proposed:** "In the predecessor repositories, stereo confidence was measured
*anti*-calibrated on photographs — variance lower in half-occlusions than in
matched regions, across three readouts — and *correctly* calibrated on random-dot
stereograms, where the same matcher and statistic give 1.923. The two sit on
opposite sides of 1.0, and whether the inversion belongs to real imagery or to
high contrast is undetermined. None of it has been reproduced here."

### 17. "The Listing tilt k is a parameter whose default is not the plane-of-regard optimum."

**CONFIRMED. Both values, with sources:**

| | value | what it is |
|---|---|---|
| `K_LISTING_DEFAULT` | **0.25** | the default, temporal tilt per radian of vergence |
| plane-of-regard optimum | **0.5** | where vertical disparity in the plane of regard vanishes exactly |

- Source: `src/bio3dvision/oculomotor.py:64-80`, with the distinction stated in the comment and **pinned by `tests/test_oculomotor.py:247::test_the_default_k_is_a_quarter_not_a_half`**.
- It is genuinely a parameter: `eye_rotations(rig, fixation, k=K_LISTING_DEFAULT)` — `src/bio3dvision/oculomotor.py:294`.
- Provenance: met-004, `kind: carried`, `status: carried_but_examined`. ADR-0014 introduced `k` and predicted the alignment null at 0.25; **ADR-0016 corrected that — the null is at 1/2 exactly**, because at k = 1/2 the tilted-Listing composition *is* the Helmholtz rotation of the eye's own gaze.

**Say it is carried, not measured.** met-004: *"It is a modelling constant from
the literature, not a measurable property of this rig."* What was measured is its
consequence (bio-046, at k = 0 against k = 1/2 in a render). The two numbers
*"sit one line apart in the reference and the optimum is the more memorable of
them"* — which is exactly how a report gets it wrong.

### 18. "The inherited bar was a sample standard deviation, so no seed count could resolve anything."

**CONFIRMED, with one precision worth keeping.**

- The bar is `np.std(d, ddof=1)` — *"a sample standard deviation, not a standard error; it has no `1/sqrt(n)`"* (`experiments/exp011_consolidation/findings.md`).
- **Demonstrated, not just argued:** tripling 8 seeds to 24 made the AT case *weaker*. The effect grew 1.34× and the sd grew **1.40×**, so `x̄` fell 0.96 → 0.91.
- exp011 on the seed count: *"Under the bar as written, there is none.* The bar is a threshold at effect size `d = 1`; seeds refine the estimate of `d` but cannot move the threshold… **if the true `d` is below 1 the bar is never crossed, because whether it crosses is a property of the stimulus, not the sample.**"
- Cost of pinning `d` anyway: **141 seeds to ±0.1, 565 to ±0.05.**

**The precision:** seeds are not useless — they pin `d` (at n = 24, `d` = 0.909 ±
0.243). What they cannot do is resolve the *verdict*. "No seed count could
resolve anything" is right about the verdict and wrong about the estimate.

**And the audit count, confirmed:** **13 methods audited, 8 never examined**
(bio-075; `docs/state.yaml:3730-3731`). met-001 itself was used unexamined across
**ten** experiments — exp001–005 and exp007–011, bio-074 `experiments: 10`.
There is no exp006 (am-004).

---

## Citations

Verified against publisher records. **`refs.bib` was not populated**, per the
specification.

### 19. Bajcsy, *Active Perception* — **PARTIAL: verified except its page range**

Ruzena Bajcsy, "Active perception", **Proceedings of the IEEE**, vol. **76**,
no. **8**, August **1988**. DOI **10.1109/5.5968**.

**The page range does not resolve.** Three variants appear across otherwise
reliable sources — **966–1005**, **996–1005**, and **996–1006** — and the IEEE
Xplore record would not render for direct checking. Author, title, venue,
volume, issue, year and DOI are solid; **the pages are not.**

**Recommendation: cite by DOI and issue, or resolve the pages against the print
issue before typesetting.** Do not pick one of the three.

### 20. Aloimonos, Weiss & Bandyopadhyay, *Active Vision* — **CONFIRMED**

John Aloimonos, Isaac Weiss & Amit Bandyopadhyay, "Active vision",
**International Journal of Computer Vision**, vol. **1**, no. **4**, pp.
**333–356**, **1988**. DOI **10.1007/BF00133571**.

### 21. Ballard, *Animate Vision* — **CONFIRMED**

Dana H. Ballard, "Animate vision", **Artificial Intelligence**, vol. **48**, no.
**1**, pp. **57–86**, February **1991**. DOI **10.1016/0004-3702(91)90080-4**.

### 22. Julesz, random-dot stereograms — **CONFIRMED**

Bela Julesz, "Binocular depth perception of computer-generated patterns",
**Bell System Technical Journal**, vol. **39**, no. **5**, pp. **1125–1162**,
September **1960**. DOI **10.1002/j.1538-7305.1960.tb03954.x**.

**Note the title.** The phrase "random-dot stereogram" is not in it — the 1960
paper introduces the technique without the name. If §1 needs the *term*, the
usual citation is Julesz, *Foundations of Cyclopean Perception* (1971), which
this pass did not verify.

---

## What this pass did not do

- **No prose, and no `.tex` file was touched.** No figure was added; `refs.bib` was not populated.
- **Nothing was re-run.** Every number above is read from a committed artifact, except claim 4's scanpath, re-derived from `run_baseline(steps=18, seed=0)`.
- **No claim was checked against a stimulus the record does not contain.** gap-010 binds on claims 1, 2, 3, 4, 13 and 14 — all analytic-fixture results, with no true half-occlusions.

---

# Second pass — the restructured draft

**Verified at `36e914d`**, against the same sources. The draft was restructured
into six numbered sections plus an appendix, and seven passages were written
fresh for it. Those passages had had no verification; this section is their pass,
appended here rather than started as a second document so there is one
verification record.

Carried passages were re-checked against the first pass above.

## The count, second pass

| verdict | n | claims |
|---|---|---|
| **CONFIRMED** | **28** | 23, 24, 26, 27, 30, 31, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 46, 47, 48, 50, 51, 52, 53, 54, 58, 59 |
| **CORRECTED** | **3** | 28, 29, 49 |
| **UNDER-QUALIFIED** | **2** | 25, 45 |
| **UNSUPPORTED** | **2** | 32, 57 |
| total | 35 | |

**Two claims are unsupported, and both are about history rather than
measurement** — how long the first repository took to write, and what the
experimenters knew when they ran things in the order they did. Neither is in the
record because neither is the kind of thing this record holds. They are the first
unsupported claims in either pass.

**Carried passages: one disagreement, the same one as before** (claim 28). It
survived the restructure and is now in the Abstract as well as §4.3.

---

## The Abstract

### 23. "Thirteen pre-registered experiments"
**CONFIRMED.** Thirteen experiment directories, exp001--exp005 and
exp007--exp014, each with a `preregistration.md`. There is no exp006 (am-004).

### 24. "Two objectives that never once selected the same pixel produced indistinguishable results"
**CONFIRMED.** Both halves: 0 of 144 argmax agreements twice (bio-011, bio-012),
and A′-vs-C indistinguishable on both pre-registered primaries (bio-010). See
claims 2 and 3 above for the full scope.

### 25. "Knowing *where* measurement is possible outweighed knowing *how uncertain* it is by 65:1 on median error"
**UNDER-QUALIFIED.** The figure is right (bio-017, 65.3 on median). The metric is
named; the stimulus is not. §4.2 carries *on a stimulus with effectively no
occlusion* and the Abstract drops it, and bio-017's own note says the ratio
"could move a long way" on a stimulus with real half-occlusions and must not be
cited as a general property. exp008 then measured it falling with occlusion,
41.96× to 1.79×. An abstract is the most-quoted paragraph in a report.

### 26. "Foveal weighting on a uniformly sampled sensor was strictly lossy"
**CONFIRMED.** exp013: F worse than U in all eight band × metric cells, 0/8 seeds,
p = 7.8e−3, ALL median at 4× the bar.

### 27. "Verging to acquire made estimation worse, through a mechanism that generalises… a controller driven by a statistic over *valid* measurements is blind to the error that would correct it"
**CONFIRMED.** exp003, and the mechanism is the experiment's own diagnosis:
`vergence` takes the median of `d_sub` over valid pixels in a foveal window, and
at window [8,12] with the near card at 18.96 px only 41.8% of those pixels
survive as valid. fc-010's `mechanism` field records the same thing.

### 28. "The benefit was coverage over accuracy by at least 34×"
**CORRECTED. The exact minimum is 33.5×, at k4.**

Rebuilt from exp011's 192 per-seed rows: 35.2× / 225.4× / **33.5×** / 340.5×.
exp011's table rounds k4 to 34×; exp011's own prose says "between 33× and 341×".
The draft rounds a **lower bound upward**, which is the one direction a lower
bound may not be rounded.

*Source:* `experiments/exp011_consolidation/results.json`, recomputed by
`report/figures/make_coverage.py`, which asserts the rebuild against exp011's
published table. This is the same disagreement the first pass found in §4.3; it
survived the restructure and now appears in the Abstract too.

### 29. "Four of the thirteen experiments were about the stimulus rather than the framework"
**CORRECTED.** The four named in §3.2 are exp004, exp005, exp008 and **exp012**,
and exp012 is not about the stimulus: it is the re-analysis of met-001, the
inherited statistical bar. §3.2's own sentence gets this right — "about the
instrument or the criterion" — and the Abstract's compression to "the stimulus"
loses the second half. Three about the stimulus, one about the criterion.

*Source:* `experiments/exp012_bar_reanalysis/findings.md`; met-001 in
`docs/inherited-measurements.yaml`.

---

## §1.1 Scope

### 30. Three repositories: `bioeye`, `active-stereo`, `bio-3d-vision`
**CONFIRMED.** `docs/migration-inventory.md:12-13` pins the first two at
`3f7a263011d9c5c53a4733957ac34cd28c2e85ba` and
`e90817018e629ce1cd23af0c9e8bc4a6aa15daff`.

### 31. `bioeye` was "a few hundred lines in a single file"
**CONFIRMED, and it is 432.** "that one 432-line file holds all six layers"
(`docs/migration-inventory.md:218`, `active_stereo_demo.py`). bioeye is 4 Python
files and 20 tracked files in total, with **no tests** — "not a `tests/`
directory, not a test file, not an assertion outside `argparse`"
(`docs/migration-inventory.md:210-211`).

### 32. `bioeye` was "written in under a week"
**UNSUPPORTED.** Nothing in this repository records how long either predecessor
took to write. The migration inventory measures files, lines and tests, not
elapsed time, and no commit history for `bioeye` is carried here — only the
pinned SHA. The claim may well be true; it is not established by anything the
record contains, and it is the only claim in §1.1 that is not.

### 33. "running end to end from a synthetic scene to a four-panel figure in one command"
**CONFIRMED.** `make_synthetic_scene` (L47--77), `ActiveStereo` (L225--313),
`save_result_fig` (L370--395) — "the four-panel figure, measured as
`plt.subplots(2, 2)`" — and `main`, "the argparse entry point"
(`docs/migration-inventory.md:223-231`).

### 34. It closed the accumulation loop but not the perception--action loop; "the disparity field was computed once and re-weighted at each fixation"
**CONFIRMED, twice over.** The migration inventory describes `ActiveStereo.step`
as "argmax-variance fixation → vergence → foveated metric measurement →
precision-weighted fusion". exp003's findings state the other half directly:
"`front_end_block` ran once in `ActiveStereo.__init__` and never again", and
name arm V as "the first arm in either repository in which an action changes what
data exists".

### 35. `active-stereo` "produced seven experiments"
**CONFIRMED.** "`experiments/` (7 experiments × `run.py`/`config.yaml`/
`findings.md`)" (`docs/migration-inventory.md:199`).

### 36. "verified oculomotor geometry, a blocking type gate, a decision record and a physically-based rendering path"
**CONFIRMED**, each separately. Geometry: `geometry/{horopter,oculomotor,
projection}.py` and `tests/unit/test_oculomotor.py` read in full
(`docs/migration-inventory.md:32-33`). Type gate: "a blocking mypy gate. A gate
that fails is a pin" (`:150`). Decision record: "all 18 ADR titles and status
lines" (`:35`). Rendering: `scenes/blender.py`, "pinned by a 585-line test"
(`:231`).

### 37. "The loop never ran"
**CONFIRMED.** CLAUDE.md states it as the failure this repository exists not to
repeat: "The predecessors built good components. Neither ever ran the loop those
components were for."

### 38. "scaling, control, gaze policy — received a fraction of the code the input side did"
**CONFIRMED, and quantified.** fc-002's rationale, measured at `3f7a263`:
geometry 830, encoding 374, inference 456, **scaling 95, control 151, policy
200**, scenes 2069, library total 4913. The three active layers are **446/4913 =
9.1%**; stimulus infrastructure alone is 42.1%.

### 39. "One matcher, one analytic stimulus, one rendered stimulus, no real imagery"
**CONFIRMED.** fc-003 forecloses a second renderer; fc-004 forecloses growing the
analytic fixture into a corpus; every measurement in the ledger carries
`matcher: block` or `none`, and `stimulus_family` is `analytic_fixture` or
`rendered_chart` throughout. The only `middlebury2014` entries are `inherited`
from the predecessors.

---

## §1.3 Goals

### 40. The four questions
**CONFIRMED** as a description of what was asked. Each maps to experiments that
exist: the objective (exp001), allocation (exp002, exp005, exp007, exp013),
acquisition (exp003, exp010, exp011, exp014), and what would have to be true
(§5.2, od-004).

### 41. "A fifth question was not planned and became unavoidable: what is the stimulus doing to the answers?"
**CONFIRMED.** exp004 was a consistency check that returned a result, and its
findings say the divergence ran "in the opposite direction from the one the
specification predicted". exp005 and exp008 follow from it.

---

## §3.2 The experiments — the thirteen-row table

Each row checked against that experiment's `findings.md`.

| | row | verdict |
|---|---|---|
| 42 | exp001 — "No — two objectives, zero agreement, indistinguishable results" | CONFIRMED |
| 43 | exp002 — "Only marginally; the mask carries the effect" | CONFIRMED |
| 44 | exp003 — "No — worse, with a diagnosed mechanism" | CONFIRMED |
| 45 | exp004 — "Away from discontinuities yes; at them no…" | UNDER-QUALIFIED |
| 46 | exp005 — "The artefact carried the effects rather than masking them" | CONFIRMED |
| 47 | exp007 — "Yes, and variance recovers more strongly than on the fixture" | CONFIRMED |
| 48 | exp008 — "Sharpest near a tenth; indiscriminate above a sixth" | CONFIRMED |
| 49 | exp009 — "…at 9.4× the matcher time" | **CORRECTED → 9.5×** |
| 50 | exp010 — "Yes, at 41× the cost" | CONFIRMED |
| 51 | exp011 — "Direction yes, margin no; coverage is the result" | CONFIRMED |
| 52 | exp012 — "Not what it was read as testing" | CONFIRMED |
| 53 | exp013 — "No — strictly lossy, on every seed" | CONFIRMED |
| 54 | exp014 — "Re-acquisition, away from discontinuities" | CONFIRMED |

**43 (exp002)** — "only marginally" is the right size: E recovers 97.3% of A′'s
median-error benefit, so variance adds 2.7% (bio-016). Note the sign, which the
row does not state: variance is **distinguishably** better, on both primaries.
exp002's falsifier did not fire.

**45 (exp004)** — **the row reads cleaner than the result.** exp004's headline
does say "Away from depth discontinuities the two sources behave the same", but
its **falsifier 1 fired**: AWAY p90 is distinguishable at **1.06× the bar**, R
better, reported as a knife-edge rather than rounded. The common-scanpath control
then put the same comparison at **0.92×**, on the other side. So "away yes" is
the headline's reading, and the verdict underneath it is a knife-edge that
changes sign when the policy is held fixed. "At them no, and the fixture is the
worse of the two" is exactly right (claim 12).

**47 (exp007)** — "more strongly" is measured: on p90 the rendered E-vs-A′ effect
is **five times the fixture's pooled figure** (median 1.18×, p90 9.04×), which is
what fc-008's `rendered_recheck_exp007` records.

**49 (exp009)** — **CORRECTED. The ratio is 9.5×, not 9.4×**: RECT matcher
0.020 s against TOED 0.188 s (`experiments/exp009_epipolar_cost/findings.md:219`,
which also states 9.5× in the table's own ratio row).

*And the row omits what exp009 concluded from that number.* The matcher is
0.188 s against a **0.57 s render — 33% of it** — and exp009's section is titled
"Chat's prediction is falsified": the loop stays **render-bound**, and the
prediction that a ±2 band would make it matcher-bound "does not" hold. A row
quoting 9.5× without that reads as a larger cost than the experiment found.

---

## §4.1 Summary, first three paragraphs

### 55. "Thirteen experiments produced a set of results that read at first as unrelated"
**CONFIRMED** as a description of the record; the three levels named
(stimulus, policy, closing the loop) are exp004/005/008, exp001/002/013, and
exp010/011.

### 56. "Availability dominates selection" as the unifying claim
**CONFIRMED** as a reading the measurements support: 65:1 on median error
(bio-017), coverage over accuracy by 33.5--341× (exp011), and two objectives at
zero agreement producing indistinguishable results (bio-010, bio-011).

### 57. "The experiments were run in that order without knowing it"
**UNSUPPORTED.** This is a claim about what the experimenters knew at the time,
and the record holds pre-registrations, falsifiers and outcomes but not states of
knowledge. The pre-registrations show what each experiment expected — several
were wrong, and exp007 records four wrong predictions of eight — but none of that
establishes that the ordering was unwitting. Not contradicted either; simply not
the kind of thing this record can settle.

---

## §6 References — the repository SHAs

### 58. "Cite each at the commit the report describes, not at `main`"
**CONFIRMED, and the SHAs are supplied from the record rather than from `main`:**

| repository | commit | source |
|---|---|---|
| `visgraf/bioeye` | `e90817018e629ce1cd23af0c9e8bc4a6aa15daff` | `docs/migration-inventory.md:13`; the SHA every `bio-` port entry cites |
| `visgraf/active-stereo` | `3f7a263011d9c5c53a4733957ac34cd28c2e85ba` | `docs/migration-inventory.md:12`; the SHA every `as-` entry cites |
| `visgraf/bio-3d-vision` | the commit carrying this report | this branch |

Both predecessor SHAs are the ones this repository pinned its inherited
measurements to, so a reader following the citation lands on the code the
measurements were taken from.

---

## Figure 6's brief

### 59. "A rotation about a fixed optical centre does not change what a complete sphere sees"
**CONFIRMED**, and it is a foreclosure rather than an inference. fc-013: the eye
centres are fixed at ±b/2 and `eye_rotations` returns rotations, not
translations, so "a complete capture has no hemisphere to hide". bio-081: a
sphere loses no grid at any saccade amplitude. bio-082: two orientations —
identity, and yawed 37°/pitched 19° — reproduce the same analytic function of
direction to **80 µm**, measured against a real Blender.

**The qualifier is load-bearing** and fc-013 states it: this holds for a sensor
sampled **uniformly**. Under variable resolution the fovea resolves what the
periphery only sampled coarsely, and refixation buys something again — od-004.
The figure's caption carries it.

The *placement* of the figure is a layout proposal, not a factual claim, and is
not verified here.

---

# Resolutions — the maintainer's corrections to the draft

The maintainer replaced `draft.md` with a version applying the second pass. Ten
edits, in eight hunks, all in passages already typeset. **Every edit found in the
diff was on the list supplied with it; nothing else changed.** The typeset
sources were updated to match, and nothing else was touched.

## What resolved

| claim | was | resolution |
|---|---|---|
| **25** | UNDER-QUALIFIED — Abstract's 65:1 dropped the stimulus scope | **RESOLVED.** Now reads "On a stimulus with effectively no occlusion, knowing *where*…" |
| **28** | CORRECTED — "at least 34×" against an exact 33.5× | **RESOLVED.** "at least 33×", in all three places it appears (Abstract, §4.3, §5.1) |
| **29** | CORRECTED — "four … about the stimulus" counted exp012 | **RESOLVED.** "about the instrument or the criterion rather than about the framework", matching §3.2's body text |
| **32** | UNSUPPORTED — `bioeye` "written in under a week" | **RESOLVED by deletion.** The clause is gone |
| **45** | UNDER-QUALIFIED — exp004's row read cleaner than the result | **RESOLVED.** "Away from discontinuities marginally — a knife edge that changes sign under a scanpath control" |
| **49** | CORRECTED — exp009 "9.4×", and the conclusion drawn from it omitted | **RESOLVED, both halves.** "9.5× the matcher time — which still leaves the loop render-bound" |
| **57** | UNSUPPORTED — "run in that order without knowing it" | **RESOLVED by deletion**, with the following sentence reworded so the paragraph still reads |

**Seven of the second pass's nine non-confirmed claims are now closed.** The two
that remain were CONFIRMED-with-scope rather than defects, and needed no edit.

**On 33× rather than 33.5×.** The exact minimum is 33.5× at k4, so "at least 33×"
is a true lower bound where "at least 34×" was not, and it matches exp011's own
prose. A lower bound rounded *down* is the direction that stays true.

## What is still flagged and was not part of this correction

These were raised under falsifier 5 as sentences stating a number without its
scope. They are not errors and were not on the maintainer's list; they remain the
maintainer's call and are recorded here so the flag does not go quiet.

- **§4.1, "the stimulus stops discriminating between policies altogether."**
  Established for the *allocation* question (exp008). exp011's acquisition
  comparison still discriminated at 17.16%, pooled `x̄` 1.24.
- **§4.2, "a median 115 pixels apart, more than three fovea widths."** The
  115.2 px figure is the **B-vs-C** pairing (bio-012); bio-011, the pair the
  sentence introduces first, records no median distance. "Fovea widths" renames
  what the ledger calls fovea *sigma* (34.0 px).
- **§4.1, "Four of thirteen experiments went to establishing that"** — that a
  stimulus is an instrument. The Abstract's parallel sentence was corrected to
  "the instrument or the criterion"; this one still reads as four about the
  stimulus, and exp012 is about the bar.
