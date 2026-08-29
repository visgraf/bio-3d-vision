# exp003 — acquisition costs 2.6× and makes the shared pixels 7.5× worse

**Run:** 3 arms × 16 seeds × 18 fixations, policy A′, half-width 2 px, commit `b77b24e`
**Pre-registration:** [`preregistration.md`](preregistration.md), committed alone at `4456337` before the runner existed
**Evidence:** [`results.json`](results.json), [`verdicts.json`](verdicts.json)

**Falsifier 1 does not fire — but the outcome is worse than the condition it was
written to catch. Falsifier 2 does not fire. Falsifier 3 does not fire.**

## This is the first time the loop is closed

Arm V re-runs `front_end_block` at every fixation. Every result before this one
varied where the loop *looks*; none varied what it *measures*. `front_end_block`
ran once in `ActiveStereo.__init__` and never again, and `d_fix` only rescaled
disparity to depth and formed `sig_model`. **V is the first arm in either
repository in which an action changes what data exists** — the loop is closed in
that one specific sense, and in no other: there is still no plant, no rotation,
and no geometry consuming a ray.

## Results, under the coverage rule

### The intersection — isolates quality (primary)

Means over 16 seeds, 37 383 shared pixels.

| arm | **median \|err\| (m)** | **p90 (m)** | rmse (m) |
|---|---|---|---|
| **W** — wide, the port's default | **0.01476** | **0.3215** | 0.4491 |
| **N** — narrow, fixed | **0.11074** | **2.1164** | 1.0119 |
| **V** — narrow, re-centred every fixation | **0.11106** | **1.0288** | 0.5894 |

**Both narrow arms are ~7.5× worse than the wide baseline on the pixels all three
measure.** Narrowing the search window does not improve quality on this stimulus;
it destroys it.

### Each arm's excluded set — says what coverage was bought

| arm | excluded n | median \|err\| (m) | p90 (m) |
|---|---|---|---|
| W | 15 785 | 0.00643 | 0.5354 |
| N | 9 610 | 0.02691 | 1.4672 |
| **V** | **27 348** | **0.23487** | 1.3462 |

### Pooled — **CONFOUNDED**

| arm | n | median \|err\| | p90 |
|---|---|---|---|
| W | 53 168 | 0.01118 | 0.3748 |
| N | 46 993 | 0.08422 | 1.9342 |
| V | 64 731 | 0.15621 | 1.1394 |

**These numbers mix a quality change with a coverage change and answer neither
question.** They are reported only so the record cannot be misread later. Do not
cite this table.

### Cost — beside the error, not after it

| arm | disparity hypotheses | front-end calls | distinct windows | coverage (union valid) |
|---|---|---|---|---|
| W | **57** | 1 | 1.0 | 53 168 |
| N | **62** | 2 | 1.0 | 46 993 (**−6 175**) |
| V | **147** | **19** | 5.2 | 64 731 (**+11 563, +21.7%**) |

Each hypothesis is evaluated twice per front-end call — once in `cost_volume`,
once inside `lr_consistency` — so the absolute figures double; the ratios do not.

**Correction to a prediction, as the pre-registration said would be confirmed by
counting:** V is **147** hypotheses, not the predicted 142. V re-acquires at all
18 fixations including the first, so it is 57 + 18×5, not 57 + 17×5.

## Falsifier 1 — does not fire, and the truth is worse than the falsifier

> *If V is indistinguishable from W on the intersection, acquisition-by-verging
> buys nothing on this stimulus.*

| metric | W | V | diff | × bar | verdict |
|---|---|---|---|---|---|
| median | 0.01476 | 0.11106 | +0.09630 | 2.01 | **DISTINGUISHABLE, V worse** |
| p90 | 0.32149 | 1.02881 | +0.70732 | 1.98 | **DISTINGUISHABLE, V worse** |

**V is not indistinguishable from W, so the falsifier does not fire on its stated
condition — because V is distinguishably WORSE.** The falsifier was written to
catch acquisition buying *nothing*; what was measured is acquisition costing
something. On the shared pixels V is 7.5× worse than doing nothing, at 2.6× the
hypothesis count.

Stated plainly, because it argues against the project's premise: **on this
stimulus, verging to acquire is worse than not verging at all, on every axis
except coverage.** The mechanical plant has no measured warrant here — and less
than "no warrant", it has measured harm.

## Falsifier 2 — does not fire, narrowly and in one place only

> *If N is indistinguishable from V, the gain is narrowing, not acting.*

| metric | N | V | diff | × bar | verdict |
|---|---|---|---|---|---|
| median | 0.11074 | 0.11106 | +0.00031 | **0.01** | indistinguishable |
| p90 | 2.11645 | 1.02881 | −1.08764 | 3.02 | **DISTINGUISHABLE, V better** |
| rmse *(secondary)* | 1.01189 | 0.58944 | −0.42245 | 2.48 | V better |

By the declared rule — indistinguishable iff *neither* primary is distinguishable
— they are **distinguishable**, so the falsifier does not fire. But read the two
rows together before concluding acting is worth something:

- On the **median** the two arms are as close as this bar can express: **0.01× the
  bar**, a difference of 0.0003 m on values of 0.111. Acting changes the typical
  pixel not at all.
- On **p90** acting halves the tail, 2.12 → 1.03, at 3.02× the bar. That is real.

**So acting buys tail behaviour and nothing else** — and both arms remain ~7.5×
worse than W. The honest summary is that acting rescues part of the damage that
narrowing causes, and does not recover the baseline. Whether that counts as "the
active component doing work" is a judgement the reader should make with the
median row in view.

## Falsifier 3 — does not fire

V does not beat both. It loses to W on both primary metrics on the intersection.
There is still no positive result for active vision in either repository.

## Why V fails: the vergence controller has no error signal

Diagnosed during design, and it is the mechanism behind every number above.

`ActiveStereo.vergence` estimates the fixation disparity as **the median of
`d_sub` over valid pixels in a foveal window**. Under a narrow window that
estimator has no way to say "the target is outside your window":

1. A pixel whose true disparity lies outside the window usually **fails the ratio
   and consistency tests and is masked invalid** — so it is *excluded from the
   median*. Measured at window [8,12] with the near card at 18.96 px: only 41.8%
   of those pixels survive as valid, and their median `d_sub` reads **10.32**, not
   the truth.
2. The pixels that do survive return an **arbitrary in-window disparity**, not a
   signed "too near / too far". Observed at seed 0, fixations 5–7: the fixation
   sat on true disparities of 15.17 and 18.96 while `d_sub` there read **8.00 and
   6.00** — the *lower* edge. The controller verged **away** from the target,
   10.0 → 7.9 → 5.95.

**The pixels that carry the vergence error signal are exactly the pixels the
validity mask removes.** A real vergence system is driven by disparities *outside*
the fusional range; this one is driven by the median of what it can already fuse,
which is a fixed point by construction.

Across the run V partially recovers — 64% of fixations end with their true
disparity inside V's own window, and median |`d_fix` − true| is 0.96 px, 11% of
the scene's range — so it is not stuck, just badly steered.

**This is a property of the ported controller, not of the fixture.** The fixture
supports the experiment: A′'s vergence spans 9.98–18.81 px under the wide window,
and V visits 5.2 distinct windows per run.

## The design guard, and a near-miss worth recording

The pre-registration said: *if no window width makes V non-degenerate without
touching the fixture, stop and report.* It does not trigger — but a 4-fixation
smoke test showed V's window frozen at [8,12] and would have produced a **false
stop**. Over the full 18 fixations V visits 4–7 distinct windows. The lesson is
narrow and worth keeping: a degeneracy check run at a fraction of the budget can
report degeneracy that the full budget does not show.

## Limits

- **`gap-010` still binds**: no true half-occlusions here, so nothing above
  speaks to the case where a region is geometrically unmeasurable rather than
  merely out of window. Holds for a stimulus without half-occlusions and no
  further.
- **The half-width is a modelling choice, not a measurement.** Panum's fusional
  area near the fovea, 5–10 arcmin, is 1.018–2.036 px at f = 700 — computed, not
  assumed, but the 5–10 arcmin figure itself is a textbook value carried in as an
  anchor. Nothing here measures it. Marked **assumed**.
- **One width was run.** The width was declared in advance and not swept; a sweep
  would be a different, and post-hoc, experiment.
- **The result is about this controller.** A vergence estimator with a signed
  out-of-range error signal — coarse-to-fine, or disparity energy — is untested
  and is not what was measured.
- All arms inherit the port's three defects, including the `1e3` sentinel, which
  `reacquire` reproduces unchanged.
