# exp013 — findings

**Measured** at `f2fc52c`, 8 seeds × 40 fixations × 2 arms, one shared capture per
seed, Blender **5.2.0 LTS** equirectangular at 2048×1024, Cycles, 1 sample;
Python 3.13.15 / numpy 2.5.2.

**Outcome (c): U beats F, in every band, on both metrics, in 8 of 8 seeds.**

**And the comparison as built cannot show (a). Saying so is part of the result.**

---

## CLOSED-vs-OPEN was not run, and that is a finding

fc-013: eye centres are fixed and `eye_rotations` returns rotations, so a second
capture of a uniform full sphere contains what the first did — bio-082 measured
two orientations reproducing the same analytic function of direction to 80 µm.
**With coverage 1.0 in both arms the two arms would produce identical
measurements by construction**, and the null would be arithmetic.

This is also why both arms here share **one render per seed**. Eight renders
total, not 8 × 40 × 2.

---

## The result

`d = F − U`, so positive is F worse. All three criteria; **the sd binds in every
cell**, with the materiality floor two orders of magnitude smaller.

| band | metric | U | F | mean_diff | sd | floor | bar | binds | sign | p |
|---|---|---|---|---|---|---|---|---|---|---|
| EQUATOR | median | 0.0690 | 0.7756 | +0.7067 | 0.2035 | 0.0014 | 0.2035 | sd | 0/8 | 7.8e−3 |
| EQUATOR | p90 | 0.2968 | 3.4556 | +3.1588 | 0.4712 | 0.0059 | 0.4712 | sd | 0/8 | 7.8e−3 |
| MID | median | 0.0552 | 0.7753 | +0.7201 | 0.1707 | 0.0011 | 0.1707 | sd | 0/8 | 7.8e−3 |
| MID | p90 | 0.2411 | 2.6420 | +2.4009 | 0.5885 | 0.0048 | 0.5885 | sd | 0/8 | 7.8e−3 |
| POLE | median | 0.1326 | 1.0304 | +0.8978 | 0.2257 | 0.0027 | 0.2257 | sd | 0/8 | 7.8e−3 |
| POLE | p90 | 0.6085 | 2.7323 | +2.1237 | 0.4298 | 0.0122 | 0.4298 | sd | 0/8 | 7.8e−3 |
| **ALL** | **median** | **0.0745** | **0.8727** | **+0.7983** | 0.1971 | 0.0015 | 0.1971 | sd | **0/8** | **7.8e−3** |
| **ALL** | **p90** | **0.3558** | **2.8821** | **+2.5263** | 0.4642 | 0.0071 | 0.4642 | sd | **0/8** | **7.8e−3** |

The effect is **4× the bar** on ALL median. The front end itself is good — median
range error **0.0668 m** on a 1.5–12.6 m scene, 69.4% of cells scored, 0.80 s.

### The mechanism, measured rather than asserted

| | solid angle receiving >1% of peak weight |
|---|---|
| U | **1.0000** |
| F | **0.2149** |

**F leaves four fifths of the sphere at the prior.** A 2.78° fovea and 40
fixations cannot cover a sphere.

---

## What this does and does not mean

**It does not mean allocation is worthless.** A foveal weight models an **acuity
gradient**. A uniform capture has none, so weighting by gaze **discards
information already in hand and buys nothing back**. That is fc-013's argument
arriving in an experiment, and od-004's case from the other side: the weight is
justified by a *sensor property*, and this sensor does not have it.

**The comparison cannot show (a), and that limits what the null means.** In the
pinhole loop, foveal advantage has two sources:

1. the acuity weight `w`, and
2. **`scale_to_depth`'s linearisation remainder** — `sig_model = D·(η/d_fix)²`,
   which `loop.py`'s own comment says "confines each fixation's confident estimate
   to its foveal neighbourhood".

**The sine rule is exact, so source 2 has no spherical analogue.** F therefore has
upside only if down-weighting helps, which it cannot. So this experiment raises,
without settling, a sharper question than the one it was set:

> **exp011's accuracy term may be a property of the SCALING LAYER — a first-order
> expansion about a fixation-dependent pedestal — rather than of allocation.**

**U is not exp011's OPEN.** OPEN also foveated; U does not, so U is a *stronger*
arm than either exp011 arm. A faithful transposition of exp011's pair is
impossible here because CLOSED-vs-OPEN is degenerate, and this is the nearest
well-posed question, **not the same one**.

---

## Part C's prediction: real mechanism, pre-empted

`dr/dd = −b·sin(θ_L)/sin²(d)`, so **var_r ∝ 1/sin²θ** — 33× the equator's at 10°,
3283× at 1°. The derivation predicts argmax-variance is **drawn to the epipoles**,
where stereo carries no depth at all. *(This points opposite to the
specification, which expected a preference for the equator; that would hold for a
policy seeking good measurements, and argmax-variance seeks uncertain ones.)*

**Measured: it is not.** Gaze median **62.8°**, and only **10.3%** of fixations
land within 30° of an epipole.

**The mechanism is real and something else gets there first.** Near the epipoles
the angular disparity is sub-column — 1.2 columns at θ = 10° at this resolution —
so those cells fail the matcher's validity test and are **excluded from selection
before the policy can prefer them**. Two independent effects pointing the same
way, one arriving first.

---

## Four apparatus faults, all mine

Each produced plausible output, and one had a **wrong explanation written down**
before the real cause was found.

1. **`ground_truth` applied the camera pose to plane normals already in the world
   frame** — median error 1.96 m on a 2–5 m scene.
2. **The seeds varied only the noise texture**, so every seed scored the same
   geometry and the seed-to-seed sd was **exactly 0.0000** in every band. That
   makes exp001's clause 1 vacuous: it asks whether an effect exceeds
   *scene-to-scene* variation, and there was one scene.
3. **The edit passing per-seed distances to the renderer never applied**, so the
   render kept the unperturbed geometry while the ground truth used the perturbed
   one — 0.146 m median disagreement, 1.39 m max. **My first written explanation
   was wrong** (I blamed an edge-attribution error from a 0.97 shrink). What found
   it was reading the depth-pass range per seed and seeing all eight identical.
4. **Widening the disparity search from 16 to 18 columns was blamed for a tripled
   error and was not the cause.**

Ground truth now comes from the **depth pass**, which bio-077 established as
radial to 73 µm — one fewer thing that has to agree with the renderer by
construction rather than by measurement.

## What this does not do

No variable-resolution sampling, no C2, no od-002, no od-003, no sweep of any
`never_examined` constant. No foreclosure taken — fc-013 was taken in Part A,
before this was built. `INHIBITION_RADIUS` is used as an angle by the same
conversion applied to `fovea_sigma`: **a change of units, not of status.**
