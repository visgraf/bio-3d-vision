# exp009 — findings

**Measured** at `1508ce0`, 5 fixations × 4 seeds × 2 arms, vergence 0.06,
Blender **5.2.0 LTS** (`fbe6228777e7`), Cycles, 1 sample, no denoising; Python
3.13.15 / numpy 2.5.2.

**This iteration measured. It did not decide.** No foreclosure is taken, none is
reversed, no default is adopted, and no 17c. `od-002` and `od-003` are untouched.

---

## Before the results: five faults in the apparatus, all mine, all plausible

The first complete run of this experiment produced TOED valid fractions of
**0.019** and range errors of **3.8–17 m** on a scene at 2.4–4.5 m. Those numbers
are not reported as a result because they measured my runner, not the geometry.
Each fault is recorded because each one produced output that could have been
written up.

**1. The matcher assumes a PARALLEL rig, not merely a rectified one.** This is a
finding about `src/`, not about the experiment. `matching.cost_volume` builds its
shifted right image as

```python
if d > 0: rs[:, :d] = right[:, :1]; rs[:, d:] = right[:, : W - d]
else:     rs[:] = right
```

For every `d <= 0` it copies the right image **unshifted**. A rectified pair may
still be converged, and a converged pair puts every scene point beyond the
fixation distance at *negative* disparity. Here vergence 0.06 rad on a 0.065 m
baseline fixates at 1.08 m while the scene lies at 2.4–4.5 m, so the true
disparity range is **−34.2 … −23.0 px** and the search window `[0, 56]` inherited
from fc-010 contains none of it. This is a **third latent assumption**, beside
bio-056's epipolar one and its 1-D-search sibling, and it is the one that would
have been hardest to see: it does not fail, it returns confident garbage.

**2. Depth from `f·b/d` is wrong for a converged pair.** Zero disparity is the
fixation distance, not infinity. Replaced by triangulating the two rays, which
reduces exactly to `f·b/d` on a parallel pair, so both arms take one code path.

**3. `matching.lr_consistency` inherits fault 1.** It mirrors the pair and calls
`cost_volume`, so on a converged pair every cost slice is identical, the argmin
is whichever index comes first, and the check rejects nearly everything. TOED's
valid fraction: **0.009**.

**4. The vertical correction was indexed in the wrong image.** Correcting the
right image by the *left-referenced* `d_v` field indexes that field at
right-pixel columns, ~25 px away. Valid fraction **0.131** — against RECT's
0.932, *at the fixation where the vertical disparity the two arms differ over is
smallest*. That inconsistency is what exposed it. Fixed by running the
right-referenced pass as its own 2-D search.

**5. The 2-D cost volume was a running best, not a cost profile.** Writing the
cost only where it improved on the best-so-far left `inf` at every other `d_h`,
which silently corrupted both `decode_disparity`'s parabola and the ratio test.
Valid fraction **0.146**. Fixed to `min` over `d_v` at each `d_h`: **0.822**.

Two further corrections were needed to make the comparison the preregistration
specifies actually happen: discontinuity bands were being computed in the
fixture's canonical raster — a **third camera frame**, indexing the wrong pixels
in both arms — and the restriction to directions both arms see was specified but
not implemented.

---

## A prediction in the preregistration was wrong, and the error is instructive

The preregistration's `d_v` table gives **0.00 px at az 0.00**. Measured over the
field at vergence 0.06 it is **1.71 px**, the largest of any fixation here.

The 0.00 came from bio-056's `parallel_az0_el0_mu0` row — a **parallel** rig at
**vergence 0**. Symmetric convergence alone produces vertical disparity off the
horizontal meridian, growing with `|x·y|/z²`, and it is largest exactly when the
field is symmetric about the gaze. Carrying a parallel-rig number into a
converged-rig table understated the on-axis case to zero.

Measured maxima over the field, vergence 0.06:

| fixation (az, el) | 0.00, 0.00 | 0.08, 0.05 | 0.15, 0.10 | 0.20, 0.15 | 0.30, 0.20 |
|---|---|---|---|---|---|
| max &#124;d_v&#124; (px) | **1.71** | 1.24 | 1.08 | 1.07 | 1.38 |

**`d_v` is not monotone in saccade amplitude.** The preregistration's
extrapolation — "beyond az ≈ 0.5 rad the ±4 band is too narrow" — rests on a
trend that does not exist. The band is comfortable at every fixation here (1.71 px
against ±4), but for a different reason than the one given: not because the
amplitudes are small, but because convergence dominates and it does not grow with
eccentricity.

---

## Measurement 1 — outcome (b) fires everywhere, and the magnitude is small

Median range error from the cyclopean origin, in metres, over directions **both
arms see**, mean of 4 seeds. exp001's bar: `|mean(d_s)| > max(sd(d_s), 0.02 ×
mean(RECT))`.

| fixation | band | RECT | TOED | diff | bar | ratio | verdict |
|---|---|---|---|---|---|---|---|
| 0.00, 0.00 | ALL | 0.0103 | 0.0121 | +0.0018 | 0.0003 | 1.18 | TOED worse |
| | AT | 0.0124 | 0.0145 | +0.0020 | 0.0005 | 1.16 | TOED worse |
| | AWAY | 0.0092 | 0.0109 | +0.0017 | 0.0003 | 1.18 | TOED worse |
| 0.08, 0.05 | ALL | 0.0076 | 0.0110 | +0.0034 | 0.0002 | 1.45 | TOED worse |
| | AT | 0.0109 | 0.0156 | +0.0046 | 0.0002 | 1.42 | TOED worse |
| | AWAY | 0.0056 | 0.0074 | +0.0019 | 0.0003 | 1.34 | TOED worse |
| **0.15, 0.10** | ALL | 0.0072 | 0.0128 | +0.0056 | 0.0004 | **1.77** | TOED worse |
| | AT | 0.0106 | 0.0190 | +0.0084 | 0.0004 | **1.79** | TOED worse |
| | AWAY | 0.0043 | 0.0069 | +0.0026 | 0.0005 | 1.60 | TOED worse |
| 0.20, 0.15 | ALL | 0.0058 | 0.0107 | +0.0049 | 0.0001 | 1.84 | TOED worse |
| | AT | 0.0087 | 0.0195 | +0.0109 | 0.0007 | **2.26** | TOED worse |
| | AWAY | 0.0038 | 0.0055 | +0.0017 | 0.0003 | 1.46 | TOED worse |
| 0.30, 0.20 | ALL | 0.0069 | 0.0110 | +0.0040 | 0.0005 | 1.58 | TOED worse |
| | AT | 0.0099 | 0.0198 | +0.0099 | 0.0016 | 2.00 | TOED worse |
| | AWAY | 0.0045 | 0.0051 | +0.0006 | 0.0005 | 1.14 | TOED worse |

**(b) at every fixation and in every band — including az 0.00**, where the
preregistration expected (a).

**The bar and the magnitude say different things and both are true.** The
difference clears the bar everywhere because it is extremely reproducible: the
seed-to-seed sd is 0.1–1.6 mm. In absolute terms the penalty is **1.7 to 10.9 mm
on a scene at 2.4–4.5 m** — at worst 0.4% of range. A 1.4 px violation against a
7 px window costs about what the preregistration guessed it would; what the
preregistration got wrong is that this is detectable rather than absent.

**The penalty concentrates AT discontinuities.** AWAY-band ratios stay in
1.14–1.60; AT-band ratios reach 2.26. That is the expected shape: a 2-D search
has 9× the candidates, so where the local surface gives the cost volume little to
discriminate on, the extra freedom is extra opportunity to land wrong.

**Outcome (d) is NOT supported, and the reason matters.** RECT's absolute error
*falls* off-axis (0.0103 → 0.0058). That is not the matcher improving: the
surviving pixel set changes completely, from 93% of the frame to 44%. Absolute
error is **not comparable across fixations here** — only the within-fixation
TOED-vs-RECT difference is, which is why the table is read down a row and not
down a column.

### Coverage — the view-overlap consequence, measured

| fixation | RECT valid | TOED valid | common | **RECT cond.** | **TOED cond.** |
|---|---|---|---|---|---|
| 0.00, 0.00 | 0.933 | 0.820 | 0.925 | 0.960 | 0.881 |
| 0.08, 0.05 | 0.845 | 0.650 | 0.663 | 0.965 | 0.919 |
| 0.15, 0.10 | 0.711 | 0.417 | 0.437 | 0.958 | 0.876 |
| 0.20, 0.15 | 0.575 | 0.283 | 0.287 | 0.980 | 0.889 |
| 0.30, 0.20 | 0.440 | 0.136 | 0.118 | 0.991 | 0.970 |

**The 6× collapse in TOED's valid fraction is an artefact of the fixture, not a
property of the matcher.** The fixture's cards are fixed in the head frame and
span the canonical field; as gaze moves off axis, both arms look past them at
empty space, and RECT — pinned at azimuth zero — looks less far past them. The
unconfounded quantity is validity **conditional on a direction both arms see**,
and it is nearly flat: TOED gives up **8–9 percentage points**, not a factor of
six. This is the single most misreadable number in the experiment and it is the
one a pooled report would have led with.

`common` is the measured form of the preregistration's geometric claim. At the
policy's own maximum reach (0.225 / 0.170 rad) the two arms share **under 29%**
of directions; at 0.30 / 0.20, **12%**.

---

## Measurement 2 — `d_v` is measurable on-axis and away from edges, and not much else

Estimated vertical disparity against the per-pixel geometric prediction. `S/R` is
`pred_rms / residual_rms`. Mean of 4 seeds; `sd` is across seeds.

| fixation | band | n | corr | sd | resid | pred_rms | S/R | offset |
|---|---|---|---|---|---|---|---|---|
| 0.00, 0.00 | AT | 21757 | **+0.757** | 0.012 | 0.365 | 0.436 | 1.19 | −0.030 |
| | **AWAY** | 19629 | **+0.878** | 0.001 | 0.261 | 0.531 | **2.04** | +0.046 |
| 0.08, 0.05 | AT | 18006 | +0.416 | 0.011 | 0.765 | 0.365 | 0.48 | +0.002 |
| | AWAY | 12152 | **+0.796** | 0.008 | 0.277 | 0.362 | 1.30 | +0.046 |
| 0.15, 0.10 | AT | 13433 | +0.294 | 0.027 | 0.824 | 0.362 | 0.44 | −0.153 |
| | AWAY | 5173 | +0.650 | 0.034 | 0.286 | 0.316 | 1.10 | −0.159 |
| 0.20, 0.15 | AT | 7971 | +0.269 | 0.014 | 0.971 | 0.581 | 0.60 | −0.033 |
| | AWAY | 4840 | +0.344 | 0.041 | 0.427 | 0.423 | 0.99 | −0.270 |
| 0.30, 0.20 | AT | 3506 | +0.435 | 0.028 | 0.792 | 1.113 | 1.40 | +0.141 |
| | **AWAY** | 1710 | **UNDEFINED** | — | 0.138 | 0.878 | *6.37* | +0.124 |

**(e) holds AWAY from discontinuities at az 0.00 and 0.08**, and AT
discontinuities at az 0.00 only. **(f) holds** AT discontinuities from az 0.08
onward, and AWAY from az 0.20 onward. The declared prediction — "(f) AT, (e)
AWAY" — is **half right**: it did not anticipate that AT would carry signal
on-axis (+0.757), nor that AWAY would lose it by az 0.20.

**No (g).** Systematic offsets run −0.27 to +0.14 px, well under the residual.

**The az 0.30 AWAY row is a trap and is labelled as one.** Its S/R of 6.37 is the
best number in the table and it means nothing: `est_sd` is **0.0000** in all four
seeds — the estimate is the constant 1 px over every surviving pixel. A constant
cannot correlate, and its residual is small only because the prediction happens to
sit near 1 px there. `est_sd` is recorded in `results.json` precisely so this case
cannot be read as a success. Pooled with the AT row it would have been.

**A ceiling this apparatus imposes, and the check that settles it.** The estimate
is an **integer** `d_v ∈ {−4..4}`: the sub-pixel parabola is fitted along `d_h`
only. Uniform quantisation to 1 px has sd `1/√12 = 0.289`. The AWAY residuals are
**0.261, 0.277, 0.286, 0.427** — three of the four sit *at* that floor. So the
measured residual is consistent with being **quantisation-limited rather than
signal-limited**, and the correlations above are a lower bound on what the cue
supports. This is an observation, not a claim; the check that settles it is to
fit the parabola along `d_v` as well and see whether the residual falls below
0.289. It is not run here — this iteration measures what the existing matcher
does.

---

## Matcher wall-clock — Chat's prediction is falsified

| | seconds | note |
|---|---|---|
| RECT matcher | **0.020** | 1-D, 22 disparities, + LR pass |
| TOED matcher | **0.188** | 2-D, 25 × 9 offsets, + a full right-referenced 2-D pass |
| ratio | **9.5×** | predicted 9× from the band alone; 10.2× from slice count |
| **Blender render** | **0.57** | measured here, 3 calls, all 0.57 s |

Chat predicted that a ±2 band "makes the loop matcher-bound rather than
render-bound, inverting 17b's conclusion." **It does not.** At ±4 — twice the
predicted band, and with the right-referenced pass doubling the cost again — the
matcher is **0.188 s against a 0.57 s render: 33% of it.** The loop stays
render-bound. 17b's conclusion is not inverted.

---

## What this does not establish

Nothing about whether vertical disparity is a **useful** cue: nothing in this
repository consumes `d_v`, and this experiment does not claim to test it. The
decision between rectifying before matching and accepting the violation is the
maintainer's, on these numbers.

Two things that a decision should weigh and that this experiment did not settle:

- **The accuracy penalty is small (≤ 0.4% of range) and the coverage penalty is
  8–9 points.** Both are real and both are modest.
- **Rectification is not free either.** It pins the forward axis at azimuth zero,
  so at the policy's own maximum reach the rectified pair images under 29% of the
  directions the toed-in pair does. That cost is a *scene-coverage* cost, and the
  fixture's finite extent means this experiment measures it in a stimulus that
  exaggerates it. A stimulus that fills the field would separate the two.
