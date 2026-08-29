# exp003 — does acquisition buy anything, and does the gain require acting?

**Status: PRE-REGISTERED. Declared before the runner existed, and committed alone.**

## The question

exp001 and exp002 both varied *where the loop looks*. Neither varied *what data
exists*: `front_end_block` is called once in `ActiveStereo.__init__`
(`loop.py:106`) and never again, and `d_fix` is used only to rescale disparity to
depth and to form `sig_model`. Every result so far is therefore about
re-weighting a fixed measurement.

This experiment changes that. **Arm V re-runs the front end at every fixation**,
which is the first time this loop *re-acquires* rather than re-weights — the
first sense in which it is closed rather than a static pass with a moving weight.

| | search window | what it tests |
|---|---|---|
| **W** | fixed wide, the port's default `dmin=0, dmax=56` | baseline |
| **N** | fixed narrow, centred once on the first fixation's `d_fix`, never updated | narrowing **without** acting |
| **V** | narrow, re-centred on `d_fix` at every fixation | narrowing **by** acting |

**N is the uninformed control and it is the point of the design.** If N matches
V, the gain comes from a smaller window and not from the loop choosing where to
put it — the same shape as exp002, where the mask beat saliency 65 : 1. N is
centred on **the first fixation's own estimate**, never on ground truth.

## The observation this rests on — verified

Supplied Chat-side and unverified; checked at `318bc10` before designing, and it
holds in full. Arm and budget were unstated; they are **arm A, 18 fixations, seed
0**, recovered by reproducing the numbers exactly.

| claim | measured | verdict |
|---|---|---|
| true disparity spans 10.11–18.96 px | 10.1111–18.9583, width 8.847 | ✓ |
| search runs 0–56 | `int(700 × 0.065 / 0.8) = 56` | ✓ |
| ~19% of image width lost to the border constraint | 17.5% from `dmax` alone, 20.0% including `win+1` | ✓ between the two |
| narrowing to `dmax=21` improves median 0.01136 → 0.01112 on the common set | exactly | ✓ |
| and p90 0.4097 → 0.3583 | exactly | ✓ |
| ~7 197 newly reachable pixels | **7 197** (and 28 lost) | ✓ |
| newly reachable are hard: median 0.0200, p90 1.46 | 0.0200, 1.460 | ✓ |
| pooled looks worse | median 0.01138 → 0.01206, p90 0.4166 → 0.5980 | ✓ |

The last two rows are why this experiment needs a coverage rule and the previous
two did not.

## The coverage rule — new, and binding

These arms differ in coverage: a narrower window moves the border constraint left
and makes ~7 200 more pixels reachable. **Metrics over each arm's own valid mask
are not comparable across arms.**

- **Primary: the intersection** of the three arms' valid sets, per seed. This
  isolates *quality* — the same pixels, measured three ways.
- **Reported separately: each arm's excluded set** (its own valid set minus the
  intersection), with its own error distribution. This says what *coverage* was
  bought, and at what error.
- **Pooled numbers are reported too, and are labelled CONFOUNDED** wherever they
  appear, so the record cannot be misread later. They mix a quality change with a
  coverage change and answer neither question.

**Both are results; neither alone is.** An arm that wins on the intersection
while its excluded pixels are terrible has bought coverage it should not have
bought; an arm that wins pooled may only have refused the hard pixels.

An arm's **valid set** is the union over its run of the per-fixation valid masks
— every pixel that received at least one measurement. For W and N the mask is
constant after the narrowing step; for V it moves, which is exactly what is being
measured.

## Window width — declared, and anchored rather than tuned

**Half-width `hw = 2 px`; the window is `[round(d_fix) − 2, round(d_fix) + 2]`, 5
integer disparities, clamped so `dmin ≥ 0` with the width held fixed.**

*Why it must be under ~4.4 px.* The scene's disparity range is 8.847 px wide
(measured). A window wider than that is covered by a single vergence and **V
degenerates into N by construction**. Measured: half-width 4 or more covers the
whole scene in one vergence; half-width 2 needs at least 2, half-width 1 at least
3.

*Why 2 and not 1 or 3.* Panum's fusional area near the fovea is on the order of
**5–10 arcmin**. At `f = 700 px` that is `700 × (arcmin in radians)` = **1.018 px
at 5 arcmin and 2.036 px at 10 arcmin** (computed, not assumed). `hw = 2` is the
**upper end** of that range.

> **This is a MODELLING CHOICE, not a measurement.** The 5–10 arcmin figure is a
> textbook value for human foveal Panum's area, carried in as an anchor so the
> width is not chosen by looking at outcomes. Nothing in this repository measures
> it, no predecessor experiment measured it, and it is not in
> `docs/inherited-measurements.yaml`. It is marked **assumed** everywhere it
> appears.

Taking the **upper** end is deliberate and conservative in the direction that
matters: the widest Panum-consistent window is the one most favourable to **N**,
the do-nothing control. If V still beats N at `hw = 2`, that is not an artefact
of a punitively narrow window.

*Non-degeneracy, checked before declaring.* Under the wide window, arm A′'s
`d_fix` over 18 fixations at seed 0 spans **9.98 – 18.81 px**, a spread of 8.83 px
— far beyond a 5 px window. So the fixture does support a non-degenerate V, and
the guard ("if no width works without touching the fixture, stop and report")
does not trigger. **`make_synthetic_scene` is not modified. fc-004 is not in
play.**

## Design held fixed across arms

- **Policy: A′** (`argmax v` + inhibition of return at 20.0 px) for all three
  arms. Fixed because the arms vary the *window*, not the policy, and because A′
  is what `fc-007`/`fc-008` left standing. Arm A locks up (10.06 distinct
  fixations of 40, `bio-014`), which would hold `d_fix` nearly constant and make V
  degenerate for a reason unrelated to acquisition.
- **All three arms perform the port's wide acquisition at construction**, because
  computing a first `d_fix` requires some measurement to exist. They are identical
  through fixation 1. N and V diverge from fixation 2 onward, which makes the
  N-vs-V comparison a controlled test of *continuing* to re-centre.
- **Re-acquisition happens after the fixation is chosen and before the update**:
  the policy picks `c_k`, `d_fix(c_k)` is read from the current `d_sub`, the
  window is re-centred there, the front end re-runs, and the new measurement is
  fused. That is what verging means.
- **`ActiveStereo` is not modified.** Re-acquisition is a driver that writes
  `d_sub`, `var_d` and `valid` onto the engine between steps. Declared now as a
  known cost: `__init__`'s four-line acquisition block (front end, border mask,
  valid, the `1e3` sentinel) is not factored out, so the driver must reproduce it
  exactly. That duplication is reported in the findings rather than hidden, and
  the `1e3` sentinel is reproduced unchanged — it is a carried defect, not
  something this experiment fixes.

## Reused from exp001, deliberately

- **Seeds 0–15** (16), as exp002.
- **Budget 18 fixations**, as exp001.
- **Primary metrics:** median absolute depth error and p90. **RMSE secondary**
  (`bio-007`).
- **The two-clause bar, verbatim:** distinguishable iff
  `|mean(dₛ)| > max( sd(dₛ), 0.02 × mean(M_baseline) )`. Reusing it rather than
  declaring a new one is what keeps three experiments comparable.

## Cost accounting

**Reported alongside every error metric, not after it.** "Active sampling wins"
is not a claim worth making without the cost beside it.

Per arm per run: **disparity hypotheses evaluated** = Σ over front-end
invocations of `K = dmax − dmin + 1`. Each invocation evaluates `K` full-image
cost slices twice — once in `cost_volume`, once inside `lr_consistency` — so the
figure is doubled where the absolute cost matters. Predicted from the design, to
be confirmed by counting: W = 57, N = 57 + 5 = 62, V = 57 + 17 × 5 = 142.

## What each outcome means — declared in advance

- **Falsifier 1.** If **V is indistinguishable from W on the intersection**,
  acquisition-by-verging buys nothing on this stimulus, the mechanical plant has
  no measured warrant, and step 10 should be taken toward the attentional branch.
  **This argues against the project's premise and will be reported plainly.**
- **Falsifier 2.** If **N is indistinguishable from V**, the gain is narrowing,
  not acting. The active component is again doing no work, and the honest summary
  across three experiments becomes that this loop's gains come from **static
  choices** — the mask, the window — rather than from anything it does over time.
- **Falsifier 3.** If **V beats both**, the gain is quantified in **coverage** and
  in **intersection error** separately, and against the **hypothesis count**. That
  would be the first positive result for active vision in either repository, and
  it is reported with its cost, not as a headline.

## Limits

`gap-010` still binds: **no true half-occlusions on this fixture**, so nothing
here speaks to the case where high variance marks a geometrically unmeasurable
region. Whatever is concluded holds for a stimulus without half-occlusions and no
further. The fixture's depth range is **not** widened to make the experiment work
— that is `fc-004` and it needs an ADR.

A framework-level entry will be written into `docs/state.yaml` whichever way this
goes.
