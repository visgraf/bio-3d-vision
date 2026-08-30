# exp004 — findings

**Measured**, 8 seeds, policy A′, 18 fixations, Blender **5.2.0 LTS**
(`fbe6228777e7`), Python 3.13.15 / numpy 2.5.2. Pre-registered in
`preregistration.md`, committed before the runner existed.

**This is a consistency check, not a result about vision.** It closes no open
decision and annotates no foreclosure. `od-002` stays open.

## Headline

The scene model reproduces the fixture's left image to **2.5e-4** and its depth
map **bit-identically**. Away from depth discontinuities the two sources behave
the same. At discontinuities they diverge enormously — **and in the opposite
direction from the one the specification predicted.** The rendered source is
*better*, by 48× the bar on p90.

The reason is not that the render is unusually good. It is that **the fixture's
reflect-warp manufactures confidently wrong matches** where a real second
viewpoint shows a real occlusion.

## Falsifier 1 — AWAY, indistinguishable: **FIRED**, on p90, at 1.06× the bar

| metric | F (fixture) | R (render) | diff | bar | | |
|---|---|---|---|---|---|---|
| median | 0.00696 | 0.00678 | −0.00018 | 0.00049 | 0.38× | indistinguishable |
| p90 | 0.02340 | 0.02185 | −0.00155 | 0.00146 | **1.06×** | **distinguishable**, R better |

The specification is unambiguous about what follows: *locate the divergence, and
do not move the threshold to absorb it.* The threshold was not moved. Three lines
of evidence locate it, and they agree.

**1. The matcher does not differ away from discontinuities. At all.** The front
end, before any fixation, is identical on AWAY to every digit reported:

| | valid fraction | median \|d_sub − d_true\| | fraction wrong by >2 px |
|---|---|---|---|
| F, AWAY | 0.580 | 0.0329 px | 0.000 |
| R, AWAY | 0.580 | 0.0329 px | 0.000 |

**2. The effect decays monotonically with distance, which a render-path error
would not.** Swept, and reported whichever way it came out:

| AWAY threshold | 16 px | 20 px | 24 px | 28 px | 32 px |
|---|---|---|---|---|---|
| p90, × bar | 2.24 | 1.72 | **1.06** | 0.72 | 0.17 |
| median, × bar | 1.04 | 0.77 | 0.38 | 0.22 | 0.12 |

A uniform defect in the render path would be flat in distance. This is spill from
the discontinuity band, and it is gone by 32 px.

**3. The two loops fixate in different places from the very first step.** Mean
agreement **1.12 of 18** fixations. A′ picks argmax posterior variance over the
*whole* image; the variance field differs at discontinuities, so step 0 already
differs, and the fovea-weighted posterior then differs everywhere — including at
pixels whose measurements are identical.

**The control that settles it** (post-hoc, labelled). Re-run R on F's scanpath, so
the only difference between the arms is the stimulus:

| AWAY, p90 | F | R forced | diff | bar | | |
|---|---|---|---|---|---|---|
| free-running | 0.02340 | 0.02185 | −0.00155 | 0.00146 | 1.06× | distinguishable |
| **common scanpath** | 0.02340 | 0.02664 | +0.00324 | 0.00354 | **0.92×** | **indistinguishable** |

With the policy held fixed the difference is indistinguishable **and its sign
reverses**. A stable render-path error does not change sign when you hold the
scanpath still.

**Verdict, stated plainly.** The falsifier fired on its declared rule, and it
fired at 1.06× — a knife-edge, reported as one rather than rounded, in the manner
`fv-004-2` was. The divergence is **located in the policy path, not the render
path**: the sources' measurements agree exactly away from discontinuities, and
what differs downstream is where the loop chose to look. Nothing here says the
render path is wrong. Nothing here proves it is right either, and the honest limit
is that the control itself sits at 0.92×, on the other side of the same knife
edge.

## Falsifier 2 — AT, diverge with R worse: **diverged, R BETTER**

| metric | F | R | diff | bar | | |
|---|---|---|---|---|---|---|
| median | 0.02050 | 0.01248 | −0.00802 | 0.00183 | 4.38× | R better |
| p90 | **1.49626** | **0.06580** | −1.43046 | 0.02993 | **47.80×** | R better |

The specification named two possible readings of a non-divergence. Neither
applies, because the sources *did* diverge; the direction is what it did not
anticipate. It required the report to say which of its two branches holds, so:

**The first branch is ruled out by direct geometric check.** The rendered scene
does have true half-occlusions. Reprojecting every left pixel through the true
disparity, **5.09%** of right-image pixels have no left correspondent, in runs up
to **10 px** wide. This is asserted as a test, not inferred from the result.

**The second branch is what holds, and more strongly than it was phrased.** The
fixture's reflect-warp does not merely fail to produce occlusions — at a depth
step the forward map is non-monotonic, and bilinear interpolation of a
non-monotonic map yields a *stretched copy of the occluding surface's texture*.
That smear is highly matchable and geometrically wrong. Measured, at the front
end, on AT pixels the matcher marks **valid**:

| | valid fraction | median \|d_sub − d_true\| | **fraction wrong by >2 px** |
|---|---|---|---|
| F, AT | 0.785 | 0.0557 px | **0.217** |
| R, AT | 0.770 | 0.0401 px | **0.043** |

**The fixture produces 5× the rate of confident gross matching errors that a real
render of the same geometry does**, at a slightly *higher* validity rate. It is
not that the fixture hides the hard pixels; it is that it fills them with
plausible, wrong texture and the matcher believes it. F's p90 depth error at
discontinuities is **1.50 m** on a scene 2.4–4.5 m deep.

The common-scanpath control leaves this intact: AT p90 stays distinguishable at
**12.28×** the bar with the policy held fixed, so it is a property of the stimulus
and not of where the loop looked.

**What this does NOT do.** Per the preregistration, and held to: this is an
**observation in `gap-010`'s regime, not a measurement of it**. One scene, one
texture family, 8 seeds, no contrast control. It does **not** close `gap-010`, and
it does **not** annotate `fc-007`, `fc-008` or `fc-010`. It does suggest those
limits may be worse than `gap-010` states — gap-010 says occlusion claims cannot
be measured on the fixture; this suggests the fixture is *actively misleading*
there, not merely silent. Establishing that needs its own pre-registered
experiment with a contrast axis. That is `od-002`, still open.

## Coverage — exp003's rule, applied

Coverage differs, as predicted, and by less than expected: **R reaches 224 more
pixels than F on average**, not fewer.

| | mean pixels | median error |
|---|---|---|
| F valid | 53 182 | — |
| R valid | 53 406 | — |
| intersection (primary) | 51 801 | — |
| F-only (excluded) | 1 381 | 0.0372 |
| R-only (excluded) | 1 605 | 0.0096 |

Both excluded sets are reported with their own error, per the rule. **F's
exclusive pixels are 3.9× worse than R's** — the fixture reaches extra pixels and
is bad on them, while the render reaches more extra pixels and is good on them.
That points the same way as the AT result and is not independent of it.

Pooled numbers are in `verdicts.json` under `pooled_CONFOUNDED` and are labelled
there. They mix a quality change with a coverage change and answer neither.

## Falsifier 3 — scene model adequacy

Parameters the model needs that the fixture does not have. **Nine**, and the first
two were sanctioned in advance.

| # | parameter | value | effect on the comparison |
|---|---|---|---|
| 1 | material | emission, shadeless | **Declared.** Removes lighting as a confound; deliberately unphysical. |
| 2 | texture source | the fixture's own array | **Declared.** Removes noise statistics as a confound. Pinned by a test. |
| 3 | texture interpolation | `Linear` (bilinear) | Chosen to match the fixture's own `order=1` resampler. `Closest` was measured first: it left the right images differing on 38% of pixels against 16%, a confound ~100× larger than the 2.5e-4 residual `Linear` costs on the left image. |
| 4 | pixel filter | `BOX`, width 1e-4 | Point sampling. Without it Cycles averages sub-pixel samples and the render is a slightly blurred copy of the texture. |
| 5 | view transform | `Standard`, outputs raw float EXR | 8-bit sRGB PNG cannot carry "rendered pixel equals texture value" — it quantises to 256 levels and is not linear. |
| 6 | frustum edge extension | baseline + 1 px | **The one that would have been read as a broken render path.** The right camera looks a baseline further than the left, so a surface clipped to the left frustum leaves a ~10 px strip on nothing. Before this existed it accounted for essentially all of the AWAY right-image disagreement. |
| 7 | sensor width | 36 mm, lens derived as 78.75 mm | Not free: the lens is computed from the model's `f_px` so a CLI flag cannot silently make the two scenes different scenes. |
| 8 | render engine | Cycles, 1 sample, denoising off | 1 sample is exact here because the material is a flat emitter. |
| 9 | depth edges | steps, vs the fixture's σ = 0.6 smoothing | **Not a parameter but a real asymmetry.** Confined to a 2–3 px band at each discontinuity, entirely inside AT. |

**How much this weakens the claim.** Items 1–5 and 7–8 are properties of the
*rendering*, and item 6 of the *modelling*; none changes the scene's geometry, and
the check that they are collectively harmless is that the rendered left image
equals the fixture's to 2.5e-4 and the rendered depth equals the model's exactly.
That check is strong: a single error in geometry, camera, texture mapping or
material would shift or reshade the left image, and none does.

Item 9 is the real weakening, and it bears **only on AT**. Against the fixture's
own smoothed ground truth F's AT median is 0.02050; against the step ground truth
it is 0.02183, a 6% change against a 4.38× effect. So the AT verdict is not an
artefact of the ground-truth convention — but AT numbers carry a few percent of
convention in them and should not be quoted to three digits.

**Residual right-image disagreement away from discontinuities and away from the
image border: mean 4.2e-5, max 2.0e-4.** That is float32 noise, and it is the
tightest statement available that the two sources are the same scene.

## Artifacts

`results/exp004_scene_model_check/{F_seed0,R_seed0}/fig_result.png` — the four
panels, same scene, same seed, both sources, side by side.
