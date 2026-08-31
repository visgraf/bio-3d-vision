# exp013 — allocation on a sphere

**Pre-registered. Committed alone, before the runner exists.**

exp002's question transposed to a complete capture. **CLOSED-vs-OPEN is not run,
and saying why is part of the result.**

## CLOSED-vs-OPEN is degenerate here and must not be run

fc-013: the eye centres are fixed and `eye_rotations` returns rotations, so a
second capture of a uniform full sphere contains exactly what the first did —
measured in bio-082, two orientations reproducing the same analytic function of
direction to 80 µm. **With coverage 1.0 in both arms the two arms produce
identical measurements by construction.** Running it would produce a null whose
cause is arithmetic.

## The two arms

| arm | weighting | gaze |
|---|---|---|
| **U** | uniform over the whole sphere | none |
| **F** | angular foveal falloff about the gaze | argmax posterior variance + inhibition of return |

Same seeds, same budget, same bar, **one capture per seed shared by both arms** —
which fc-013 is what licenses.

**What differs is where measurement precision is spent.** Both arms fuse `B`
measurements of the same disparity field. F concentrates precision at `B` chosen
directions and linearises depth about each one's own local disparity; U spreads
it uniformly and must linearise about a single pedestal for the whole sphere.

## The question this answers

exp011 decomposed the closed-loop gain into **0.0105 m of accuracy and 0.368 m
of coverage, 35:1**. Coverage is void here by fc-013. **So: does the accuracy
term survive when neither arm can see more?** If it does, it is real. If it
vanishes, exp011's headline was a field-of-view artefact end to end — which is
the hypothesis this whole step was taken to test.

## Resolution, declared with its cost

A human-scale baseline gives **tiny angular disparities**: at 3 m and θ = 90° the
disparity is 0.0217 rad. In lattice columns that is

| columns | 256 | 512 | **1024** | 2048 | 4096 |
|---|---|---|---|---|---|
| d at 3 m, θ=90° | 1.77 | 3.53 | **7.06** | 14.12 | 28.24 |
| d at 3 m, θ=10° | 0.30 | 0.60 | **1.20** | 2.40 | 4.80 |

**Chosen: a 2048 × 1024 equirect render, transposed to 2048 rows × 1024 columns**
— column pitch π/1024 = 3.07e-3 rad. That is **half** the pinhole's angular
resolution (f = 700 px/rad needs 2199 columns), chosen so the run is tractable
and declared rather than tuned.

**The cost of a sphere is 82×, and it is od-004's economy argument arriving from
the other side.** A 320×240 pinhole at f = 700 covers 1.21% of the sphere, so
matching its angular density everywhere costs 82× the pixels — 6.3 Mpx.

**A consequence to carry into the reading:** at θ = 10° the disparity is 1.2
columns, so near the baseline poles the matcher cannot resolve depth *at this
resolution* — independently of Part C's Jacobian argument, which says the same
thing for a different reason.

## Part C's prediction, declared before the run

`dr/dd = −b·sin(θ_L)/sin²(d)`, so at fixed disparity variance

> **var_r ∝ 1/sin²θ** — 4× the equator's at θ = 30°, **33×** at 10°, **3283×** at 1°.

**Posterior variance therefore stays highest near θ = 0 and π, which are the
EPIPOLES — the directions in which stereo carries no depth information at all.**
So argmax-variance should be **drawn toward the poles** and waste budget there.

**This points the opposite way to the specification, which predicted the policy
would "prefer the equator".** The specification's reasoning would hold for a
policy that seeks good measurements; `argmax variance` seeks *uncertain* ones,
and uncertainty is worst exactly where measurement is worst. Recorded as a
disagreement resolved by the derivation, and testable in the result.

## The bar — all three criteria, per exp012

**sd** (does the effect exceed scene-to-scene variation), **the sign test with
its p** (is there an effect at all), and **the materiality floor** (is it large
enough to act on). **Which one binds is named in every cell. `x_bar` is never
reported alone.**

8 seeds, budget 40, matching exp010 and exp011.

## Falsifiers

- **(a) F beats U.** Allocation has value independent of field of view. **Report
  the effect against Part C's θ prediction**: if the gain is concentrated near the
  equator it may be the Jacobian and not the scene.
- **(b) Indistinguishable.** exp011's accuracy term does not survive coverage
  equalisation, and the closed-loop result was field-of-view-bound. **State it
  plainly — it is the outcome that most reduces what this project claims.**
- **(c) U beats F.** Foveal weighting harms on a complete capture. Likeliest
  mechanism: F discards periphery that U keeps, and on a sphere the periphery is
  the rest of the world rather than the frame edge.
- **(d) It cannot be run** — a pinhole assumption survives into spherical code.
  **STOP AND REPORT.** Which assumption survived is worth more than the
  experiment. Candidates already visible: `ActiveStereo` carries `self.f` and
  `self.I` and calls `scale_to_depth`, which is `f*b/z` throughout; its `vergence`
  takes a median over a **square pixel** window; and the disparity window default
  is `f*I/0.8`, a metres-to-pixels conversion with no spherical meaning.

### Declared prediction

**(b) or (c), not (a).** exp011's accuracy term was 0.0105 m against a coverage
term of 0.368 m, and the accuracy term itself was the noisy one — it bounced
between 0.001 and 0.012 across occlusion levels with no trend. A term that small
and that unstable is not obviously a mechanism. **If it survives here it is real
and this is the first evidence for it; the prior is that it will not.**

## What this does not do

No variable-resolution sampling, no C2, no od-002, no od-003, no sweep of any
`never_examined` constant, no change to `INHIBITION_RADIUS` or the disparity
window beyond what the spherical relation requires. No foreclosure taken —
fc-013 was taken in Part A, before this was written.
