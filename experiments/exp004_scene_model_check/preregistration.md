# exp004 — Does the rendered scene behave like the fixture where it should?

**Pre-registered. Committed alone, before the runner exists.**

Step 12. The scene model expresses the analytic fixture's geometry in Blender.
This experiment asks whether the two sources agree where the model says they must
and disagree where it says they must, and nothing beyond that.

It is a **consistency check, not an experiment about vision.** Its outcome
changes no foreclosure and closes no open decision. `od-002` stays open.

## The prediction

The fixture's right image is a warp of its left, so it has no true occlusions
(`gap-010`). The rendered right image is a real second viewpoint, so it has them.

> The two sources should be **indistinguishable away from depth discontinuities**
> and **diverge at them**, with the rendered source worse.

## Declared before running — thresholds, and they will not be tuned

**The discontinuity set `D`.** Computed from ground truth, not from any result.
Let `d_gt = f_px * baseline / Z_step`, where `Z_step` is the model's depth map
*without* the fixture's smoothing — the true scene geometry, with step edges.

> `D = { pixels where |Δd_gt| > 1.0 px across any 4-neighbour }`

1.0 px is the smallest disparity step that can expose a one-pixel-wide strip in
one eye and not the other, which is what a half-occlusion is.

**Distance.** `dist` = Euclidean distance transform to `D`.

| stratum | rule | why this number |
|---|---|---|
| **AT** | `dist ≤ 10 px` | The widest disparity step in this scene is **8.85 px** (2.4 m against 4.5 m background), so the widest occluded strip is 8.85 px. 10 covers it with a margin and is rounded, not fitted. |
| **AWAY** | `dist ≥ 24 px` | 2.7× the widest occluded strip, and more than the 7×7 matcher window's ±3 px reach beyond that, so a pixel in AWAY has its whole matching window ≥ 21 px from any discontinuity. |

Pixels with `10 < dist < 24` are in neither stratum. That gap is deliberate: a
band that is neither clearly at nor clearly away should not be forced into one.

**Sensitivity is reported, not used to choose.** The verdict is read at the
declared pair. `AWAY ∈ {16, 20, 24, 28, 32}` and `AT ∈ {6, 8, 10, 12}` are
reported alongside so a threshold-dependent verdict is visible as one.

**The image border is excluded from every stratum.** The loop's own valid mask
already drops columns outside `[dmax+8, W-8]` and rows outside `[8, H-8]`. This
is not an extra exclusion; it is the loop's, and it is named here because the
fixture's `mode="reflect"` artefact lives exactly there and would otherwise be
counted as a render disagreement. Measured before this was written: the border
strip accounted for essentially all of the AWAY-stratum image difference.

## Arms

| arm | source | ground truth |
|---|---|---|
| `F` | `make_synthetic_scene(seed=s)` | its own `depth_gt` (Gaussian-smoothed, σ 0.6) |
| `R` | Blender render of `scene_from_fixture(seed=s)` | its own rendered Z pass (step edges, exact) |

Each source is scored against **its own** ground truth. The question is whether
the loop performs the same on both, not whether one depth map matches the other.

Fixed across arms: policy **A′** (`argmax` posterior variance + inhibition of
return — the arm `fc-007` left standing), **18 fixations** (exp001's budget and
the ported baseline's, bio-001..bio-008), block matcher, `seeds 0–7` (exp001's
count, which is where the bar below comes from).

## The coverage rule — inherited from exp003, and binding here

Coverage **will** differ: the rendered pair has genuinely unmatchable regions the
fixture does not, which is the whole point. So, per exp003:

- **Primary: the intersection** of the two arms' valid sets, per seed, per
  stratum. Same pixels, measured two ways. This isolates quality.
- **Reported separately: each arm's excluded set** with its own error
  distribution — what coverage was lost, and at what error.
- **Pooled numbers reported and labelled CONFOUNDED** wherever they appear.

## Primary metrics and the bar — exp001's, reused

`M ∈ {median |depth error|, p90}` at the final step. Per seed `s`, the paired
difference `d_s = M(R, s) − M(F, s)`.

> **R is distinguishable from F on a metric iff**
> `|mean(d_s)| > max( sd(d_s), 0.02 × mean(M(F, s)) )`
>
> **Indistinguishable iff neither primary metric is distinguishable.**

Both clauses must clear: a margin exceeding the seed-to-seed spread, and a 2%
materiality floor.

## Falsifiers

**1. AWAY, the two sources must be INDISTINGUISHABLE at the bar.** If they are
not, the render path or the fixture is wrong. This is the check the step exists
for, and **nothing may rest on either source until the divergence is located.**
The threshold will not be moved to absorb it.

**2. AT, they must DIVERGE, with R worse.** If they do not, exactly one of these
is true and the report must say which:
- the rendered scene has **no true half-occlusions** — the surfaces may not
  laterally overlap, so the geometry is checked before this is concluded; or
- the fixture's reflect-warp **produces occlusion-like artefacts after all**,
  which would change what `gap-010` means and is a more interesting result than
  the one this step was designed to produce.

**3. SCENE MODEL ADEQUACY.** Every parameter the model needs that the fixture
does not have is stated, with its effect. Lighting and material are two and are
accounted for. Any others weaken the claim that these are the same scene, and the
report says by how much.

## Declared limitations, before the fact

- **One scene, one texture family, one seed set, no contrast control.** Falsifier
  2's divergence is an **observation in `gap-010`'s regime, not a measurement of
  it.** It does not close `gap-010` and does not annotate `fc-007`, `fc-008` or
  `fc-010`. Lifting those needs its own pre-registered experiment with a contrast
  axis — `od-002`, still open.
- **The rendered depth has step edges; the fixture's is smoothed by σ 0.6.** That
  difference lives inside a 2–3 px band at each discontinuity, entirely within
  AT and nowhere near AWAY. It is a known asymmetry of the comparison, declared
  rather than corrected, because correcting it means modelling the fixture's blur
  in Blender.
- **The fixture's `mode="reflect"` border artefact** is a region where the
  fixture is wrong and the render is right. It is excluded by the loop's valid
  mask, not by a choice made here.
