# exp001 — Does the gaze objective matter, once revisiting is controlled for?

**Status: PRE-REGISTERED. Declared before any arm was run, and committed alone.**

Nothing below was written after seeing a trajectory. The practice is the
predecessor's — exp006 posted its selection gate to the issue before any held-out
scene was read — and it exists here for one reason: the threshold at which two
arms count as indistinguishable decides this experiment, and choosing it after
seeing the numbers would let any outcome be the desired one.

## The question

`ActiveStereo.step` selects `argmax` of blurred posterior variance. Posterior
variance is high in two structurally different places:

1. where nothing has been measured yet — informative, and what the policy is for;
2. where measurement is known to be uninformative — a **fixed point**, because
   fixating there fails to reduce the variance that attracted the policy, so the
   argmax returns to it.

(2) is the mechanism behind the reproduced lockup at (170, 94): measured
`bio-002`, the loop spends its last 10 of 18 fixations on one pixel, and
`bio-004`/`bio-005` show why — one visit removes ~1.3% of that pixel's posterior
variance, so it stays the maximum.

There are two candidate remedies, and they are not the same kind of change:

- **Controlling revisiting** — forbid returning to a neighbourhood already
  fixated. Cheap, local, and does not touch what the policy is maximising.
- **Changing the objective** — maximise *expected variance reduction* rather than
  variance. A fixed point of the first is not a fixed point of the second, since
  a pixel that cannot be improved has no expected reduction to offer.

**This experiment is not designed to confirm the second.** If a cheap radius does
as well as a principled objective, the objective change buys nothing, and that
result forecloses a framework-level reframe. It is reported as cleanly as the
alternative.

## The objective, derived from `step()`

For a scalar Gaussian posterior with variance `v_q`, a measurement of precision
`p_q` gives `v_q' = 1/(1/v_q + p_q) = v_q/(1 + v_q·p_q)`, so the reduction is

    Δ_q(c) = v_q − v_q/(1 + v_q·p_q(c))

`p_q(c)` is read off `src/bio3dvision/loop.py::ActiveStereo.step`, not from a
description of it. In `step`, for a fixation at `c = (yf, xf)`:

| quantity | line in `step()` | dependence |
|---|---|---|
| `d_fix = self.vergence(yf, xf)` | window median at `c`, leaky-integrated, clipped | **on `c`** |
| `D_fix = f·I/max(d_fix, 1e-3)` | | on `c` through `d_fix` |
| `dZ_deta = −D_fix²/(I·f)` | from `scale_to_depth` | on `c` |
| `eta = d_sub − d_fix` | | on `c` and on `q` |
| `sig_model = D_fix·(eta/max(d_fix,1e-3))²` | | on `c` and `q` |
| `var_Z = dZ_deta²·var_d + sig_model²` | | on `c` and `q` |
| `w = self._fovea_weight(yf, xf)` | Gaussian, σ = 34.0 px | on `c` and `q` |
| `meas_prec = valid·w/max(var_Z, 1e-6)` | | **this is `p_q(c)`** |

and the update `post_prec = prior_prec + meas_prec`, `self.var = 1/post_prec`,
with `prior_prec = 1/max(v, 1e-6)`.

**Where the derivation and `step()` agree, exactly:** `p_q(c)` is `meas_prec` as
computed in `step`, and `v_q − v_q/(1+v_q·p_q)` is `self.var − 1/post_prec`
whenever `v_q > 1e-6`. The `max(v, 1e-6)` guard makes the two differ only for
posterior variances at or below 1e-6, which no pixel reaches from a prior of 9.0
within this budget. This equivalence is asserted in code, not just claimed here:
`tests/test_policy.py::test_delta_matches_the_ported_update`.

The consequence that matters: **`p_q(c)` depends on the fixation, not only on the
pixel**, through `d_fix(c)` and `w(c)`. So the objective for a candidate is the
field integral

    Δ_total(c) = Σ_q Δ_q(c)

and not `Δ_c(c)`. Whether the cheap single-pixel version tracks it is falsifier 2.

## The four arms

| | policy | changes from A |
|---|---|---|
| **A** | `argmax` blurred `v` — the ported baseline, unchanged | — |
| **A′** | `argmax` blurred `v` + inhibition of return | revisiting only |
| **B** | `argmax Δ_c(c)` — single-pixel approximation | objective only |
| **C** | `argmax Δ_total(c)` over a subsampled grid | objective only |

A is bit-identical to the committed `ActiveStereo` and is re-run as an arm so
every comparison is within one harness. No arm modifies `ActiveStereo`'s
defaults; policies are supplied as alternatives so the baseline stays
reproducible bit-for-bit (`bio-001`..`bio-009`).

**A′ versus C is the decisive comparison.**

Neither B nor C applies inhibition of return, deliberately: an
expected-reduction objective should self-inhibit, because fixating `c` lowers the
variance around `c` and therefore lowers `Δ_total(c)` next step. Whether it
actually does is part of what is being measured.

### Declared parameters

- **Inhibition radius: 20.0 px.** Not chosen here. It is the predecessor's
  default, `inhibition_radius: float = 20.0` at
  `.reference/active-stereo/src/activestereo/policy/gaze.py:13`, whose semantics
  are: suppress a disc of that radius around every visited location, and return
  `None` — terminate rather than spin — when no candidate remains. Recorded in
  ADR-0002's consequences, item 2. (ADR-0002's *headline* decision is the
  validity-masking rule; inhibition of return is its second consequence, so the
  common attribution of IOR to "ADR-0002" is right but imprecise.)
- **Candidate grid for C: stride 8 px** over the valid region (rows 8–231, cols
  64–311), keeping candidates where `valid` is true — 824 candidates. Declared
  check: **halving the stride to 4 must not change the fixation selected at step
  1**; if it does, the grid is too coarse and the stride is reduced before any
  arm is scored. Cost measured before declaring: 0.49 ms per candidate field
  integral, 0.40 s per step, ~7 s per seed-run.
- **Seeds: 8** (0–7), above the required minimum of 5. Same seed means the same
  fixture draw, so arms are compared **paired**.
- **Budget: 18 fixations**, matching the ported baseline so `bio-001`..`bio-008`
  are directly comparable.

## Metrics

**Primary, and the only ones the verdict rests on**, over valid known pixels
(`isfinite(depth_gt) & engine.valid`, 53098 px):

- **median |err|** (m)
- **p90 |err|** (m)

**Secondary, reported but not decisive: RMSE.** Measured on the ported baseline,
the worst 5% of pixels carry **80.9%** of total squared error (`bio-007`), so
RMSE here is four-fifths a report about the tail. It is reported at every step
because it is what the predecessor reported and comparability is worth
preserving, but no verdict turns on it.

Also recorded per arm per seed, descriptive: full trajectories of all three
metrics against fixation number; the scanpath; the distinct-fixation count; and
the fraction of the budget spent on candidates whose `Δ_total` is below the
median over the candidate grid at that step ("wasted budget").

Across arms: at each step, whether **A and C select the same fixation**. Reported
as an **argmax agreement rate** *and* a rank correlation over the candidate grid.

## The indistinguishability threshold — declared

Let `M ∈ {median |err|, p90}` at the **final step**. For each seed `s`, form the
paired difference `d_s = M(C, s) − M(A′, s)`.

> **C is distinguishable from A′ on a metric iff**
> `|mean(d_s)| > max( sd(d_s), 0.02 × mean(M(A′, s)) )`.
>
> **The two arms are indistinguishable iff neither primary metric is
> distinguishable.**

Two clauses, and both must be cleared:

1. `|mean(d_s)| > sd(d_s)` — the margin must exceed the seed-to-seed spread. This
   is the predecessor's own exp001 criterion ("a margin exceeding the seed-to-seed
   spread across 5 seeds"), reused rather than invented.
2. `|mean(d_s)| > 0.02 × mean(M(A′,s))` — a 2% materiality floor. A difference
   smaller than this does not justify a framework-level change even if it is
   perfectly consistent across seeds.

The same rule is applied to **B vs C** for falsifier 2, alongside the argmax
agreement rate.

## Declared limitations, before the fact

- **The fixture has no true half-occlusions** (`gap-010`). The right image is
  resampled from the left, so the (170, 94) failure is a matching failure in a
  **fully visible** region, not an occlusion. Whatever this experiment concludes,
  it forecloses the question **for a stimulus without occlusions and no further**.
  Lifting that limit needs a rendered stimulus with a controlled contrast axis at
  occlusion boundaries — `gap-001`, `od-002`. **The fixture will not be grown to
  add occlusions**: that is `fc-004`, and reopening it needs an ADR and a better
  reason than needing one more case.
- **A/A′ and B/C differ in more than the objective.** A and A′ maximise a
  *blurred* variance map (`gaussian_filter` over `np.where(valid, var, 0.0)`,
  σ=4 — itself defect 2 of the port). B and C maximise Δ, unblurred, because
  blurring an expected-reduction field is not a defined operation in the same
  sense. `Δ_total` is already spatially aggregated by construction — it sums a
  Gaussian-weighted field — so C's objective is smooth without a blur. Still:
  **if C beats A′, the difference cannot be attributed to the objective alone
  from these four arms.** Declared now: should that happen, a fifth diagnostic
  arm (A′ with the predecessor's `masked_blur` in place of the plain blur) will
  be run before any foreclosure is written. If C and A′ are indistinguishable,
  the confound does not threaten the conclusion, since neither change moved
  anything.
- All four arms inherit the port's three defects, including the 1e3 sentinel and
  the unmasked blur. Only the gaze objective and revisiting are varied.

## What each outcome means — declared in advance

- **Falsifier 1 fires** (A′ ≈ C at the threshold above): controlling revisiting
  is sufficient, changing the objective is not warranted, the reframe from
  variance to expected information gain is **foreclosed**, and L6 keeps `argmax v`
  plus inhibition of return. Recorded as a foreclosure at altitude `fw`.
- **Falsifier 1 does not fire and C is better**: the objective matters beyond
  revisiting — subject to the confound above, which is then resolved before
  anything is written down.
- **Falsifier 1 does not fire and A′ is better**: the field integral is not only
  unnecessary but harmful, which would be the most surprising outcome and is
  reported as such.
- **Falsifier 2 fires** (B does not track C): the cheap single-pixel
  approximation is unusable, and any information-gain policy costs a field
  integral per candidate per step. That is a standing constraint on what the loop
  can afford, and it is recorded in `docs/state.yaml` **whether or not falsifier 1
  fires**.

A foreclosure at altitude `fw` will be written into `docs/state.yaml` whichever
way this goes.
