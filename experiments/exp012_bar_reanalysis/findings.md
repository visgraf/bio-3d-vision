# exp012 — findings

**Measured** at `42d5909` from the `results.json` files already on disk.
No runs, no renders. 353 comparisons across 10 experiments.

**Which falsifiers occurred: (c), narrowly. (d) did not, and could not.**

---

## The finding: a null that should never have been read as absence

**Closing the loop helps at depth discontinuities. At every occlusion level. In
23–24 of 24 seeds. Two of the four levels recorded it as "indistinguishable".**

| level | mean_diff | x̄ sd | seeds favouring CLOSED | sign test | recorded as |
|---|---|---|---|---|---|
| k1 | −0.00824 | 1.60 | 24/24 | 1.19e−07 | distinguishable |
| **k2** | −0.00670 | **0.80** | **23/24** | **2.98e−06** | **INDISTINGUISHABLE** |
| **k4** | −0.01864 | **0.91** | **23/24** | **2.98e−06** | **INDISTINGUISHABLE** |
| k8 | −0.01856 | 1.18 | 23/24 | 2.98e−06 | distinguishable |

**This is the framework's original motivation, and it was on record as an
absence.** Active vision was expected to help most where the geometry is hardest.
bio-066 and bio-071 both report "not at discontinuities"; exp010's findings led
with it as "half the result".

**What the null actually said** is that at k2 and k4 the effect is smaller than
the seed-to-seed spread of the AT band — whose sd is 3.8× MIDDLE's and 13.5×
AWAY's (bio-070). That is a statement about **effect size relative to scene
variation**. It was read as a statement about **existence**.

The same shape appears in AWAY at k8: 21 of 24 seeds, p = 2.8e−04, recorded as
indistinguishable at 0.97×.

**Nothing is reversed.** bio-066 and bio-071 were correct under the criterion in
force and stay on record; both are annotated. Recorded as **bio-076**.

---

## Three criteria, named — which is the fix for the defect that produced this

| criterion | question |
|---|---|
| **sd** | does the effect exceed scene-to-scene variation? *Would this reliably help on a new scene?* |
| **sign test** | is there an effect at all? *Is the direction consistent?* |
| **materiality** | is it large enough to act on? |

A single unnamed threshold, answering whichever question the reader had in mind,
is what went wrong in the first place. All three are now reported side by side.

## The se bar is not a significance test — a correction to the specification

`|mean| > sd/sqrt(n)` is **t > 1**. As a two-sided p that is:

| n | 4 | 8 | 16 | 24 | ∞ |
|---|---|---|---|---|---|
| P(\|T\| > 1) | 0.391 | 0.351 | 0.333 | 0.328 | 0.317 |

**No conventional level anywhere.** It is not a weaker sd bar; it is not a test.

> **So the disagreement set of 45 is "where two non-tests disagree", not "45 nulls
> that were real."**

**Of the 45, ELEVEN pass an exact two-sided sign test at p < 0.05; thirty-four do
not.** (Verified independently before recording.) And every one of the eleven
either *is* the AT/AWAY finding above or points the **same way** as the
foreclosure it neighbours — none threatens anything.

This section corrects how the first version of this report was written, not the
numbers in it.

---

## (d) first, because it is the guard on everything else

**Zero positives flipped.** That is algebra rather than luck: the verdict is
`|mean| > max(clause_1, floor)`, clause 1 is `sd` or `sd/sqrt(n)`, and
`sd >= sd/sqrt(n)` for every `n >= 1`. It is asserted per comparison anyway.

**Zero reconstruction mismatches in 353.** Every per-seed difference vector was
rebuilt and asserted against that experiment's own recorded `mean_diff`, spread
and `bar` to `1e-9` before use. Each experiment's own `compare()` supplied the
floor and the recorded verdict; nothing was re-derived, so this re-score cannot
disagree with the ledger by having computed something differently.

---

## Part A — the two bars agree on 87.3% of comparisons

| | count |
|---|---|
| comparisons re-scored | **353** across 10 experiments |
| distinguishable under sd (the criterion in force) | 257 |
| distinguishable under se | 302 |
| nulls under sd | 96 |
| **disagreement set** | **45** — 46.9% of nulls |
| **of those, passing a sign test (p < 0.05)** | **11** |
| of those, failing it | 34 |
| positives that flipped | **0** |
| agreement | **308 / 353 = 87.3%** |

**138 of the agreements are by construction.** The materiality floor binds under
the se bar in 138 comparisons, so clause 2 decides and the choice of clause 1
never gets a vote. That is a larger share of the ledger than the disagreement
set, and it is the reason the audit's consequences are so much smaller than its
raw flip count.

| experiment | flips / nulls | comparisons |
|---|---|---|
| exp001 gaze objective | 5 / 10 | 12 |
| exp002 saliency value | 1 / 5 | 12 |
| exp003 vergence acquisition | 4 / 7 | 27 |
| exp004 scene model check | 4 / 7 | 24 |
| **exp005 stratified re-analysis** | **13 / 26** | 48 |
| exp007 rendered policy sweep | 5 / 15 | 96 |
| exp008 occlusion sweep | 7 / 18 | 64 |
| exp009 epipolar cost | 1 / 2 | 30 |
| exp010 closed loop | 2 / 3 | 8 |
| exp011 consolidation | 3 / 3 | 32 |

**The flips concentrate where the nulls are.** exp005's band results are nulls
throughout and it contributes 13 of the 45 on its own.

---

## Part B — what the disagreement set costs the ledger

### fc-007 — AFFECTED, and NOT MOVED

**`affected: true` must not be read as `contested`.**

Its rationale says the principled objective and the cheap remedy are
*"INDISTINGUISHABLE on both declared primary metrics"*. Under the se bar that
becomes **indistinguishable on one**:

| comparison | x̄ sd | x̄ se | sign test |
|---|---|---|---|
| `A'_vs_C median_abs_err` | 0.72 | **2.03 — flips** | 6/8, p = 0.2891 |
| `A'_vs_C p90` | 0.14 | 0.15 — null under both | 3/8, p = 0.7266 |

**It flips under the se bar and under no real test.** sd says no. The **sign test
says no** — 6 of 8 seeds, p = 0.2891. The effect is **0.63 mm**. The only
criterion that moves it is `t > 1`, which decides nothing.

Every other flip near this entry behaves the same way: exp007's A-versus-A′
comparisons on the fixture flip with sign-test p of 0.289, 0.070, 0.070, 0.289.
**None passes.**

Four of exp005's C-versus-A′ band nulls also flip, so
`stratified_recheck_exp005`'s phrase *"both nulls"* is not se-robust either. Its
direction of travel is unchanged.

### fc-008 — CHECKED, UNAFFECTED

Every comparison it names is a positive under **both** bars: E-versus-A′ median
1.38×/1.38× (the floor binds, so clause 2 decides), p90 1.96×/6.55×; D-versus-E
47.04×/87.57× and 5.88×/20.37×. **Its exp005 qualification survives intact too** —
the AWAY median stays a null under both (0.38×/0.53×), the AWAY p90 stays a
positive under both (1.75×/1.75×).

### fc-010 — CHECKED, UNAFFECTED, and the nearby flip *strengthens* it

On the intersection — the region exp003's coverage rule says to score — N and V
against W are distinguishable under both bars on both primary metrics
(11.30×/45.21×, 14.06×/56.24×, 2.01×/8.04×, 1.98×/7.92×).

The one flip nearby is on a **secondary** metric and points the same way:
`V_vs_W rmse` reads 0.82× sd and 3.28× se, with **V worse in 16 of 16 seeds,
p = 0.0000**. A null that read "no difference" is, under the other bar, V worse in
every seed. That is more support for the closure, not less.

### What a flipped null means, stated precisely

> It does **not** mean the finding was wrong. The finding was **"the effect is not
> larger than scene-to-scene variation."** It was read as **"there is no effect."**
> Those are different claims, and **the reading is what needs correcting.**

**No foreclosure is reversed.** Reversing one on a re-analysis it did not
pre-register is am-002-c's defect, and this re-analysis is exactly that shape.

---

## Part C — the inheritance audit: 8 of 13 have never been examined

`inherited-measurements.yaml` has given carried **numbers** a `status` since step
2. Carried **methods** had none — and the two-clause bar is what that omission
cost: it walked in with no marker and acquired the authority of a repository
decision.

A `methods` section is added, `met-001`…`met-013`.

| kind | count |
|---|---|
| **carried** — walked in, never examined here | **10** |
| choice — chosen here, with a stated reason | 2 |
| measurement — derived here | **1** |

**Never examined: 8** — `met-002` (the 2% floor), `met-005` (LR tolerance 1.5),
`met-006` (ratio test 0.10), `met-007` (window 7), `met-008` (inhibition radius
20.0), `met-009` (saliency sigma 4.0), `met-010` (fovea sigma 34.0), `met-011`
(prior 3.0 ± 3.0). Seven are carried; one — the 2% floor — was chosen here and
never derived.

### Three of the eight are load-bearing in ways already on record

- **`met-008`, `INHIBITION_RADIUS = 20.0`.** fc-007 closes *in favour of* "argmax
  variance plus inhibition of return at the predecessor's 20.0 px radius". **A
  foreclosure names a constant nothing here has measured.**
- **`met-011`, `prior_depth = 3.0`.** bio-072's coverage headline is "1.35–1.39 m
  of silent prior error". **That number is 3.0 minus the true range** — the
  largest effect this repository has measured is denominated in a carried default.
- **`met-010`, `fovea_sigma = 34.0`.** bio-065 expresses the foveal miss in units
  of it without asking where 34 came from.

### The contrast case, included deliberately

**`met-013`, `CANDIDATE_STRIDE`.** Pre-registered at 8 with a declared halving
check, **it failed the check** — stride 8 picks (128, 176), stride 4 picks
(120, 180) — and was moved to 4 before any arm was scored. It is the one constant
here this repository derived, and it is what the other twelve would look like if
they had been examined.

**`carried` is not an accusation that a value is wrong.** It says nobody here
knows whether it is. Recorded as **gap-011**, with the two cheapest first steps
named: re-deriving met-003's band thresholds is arithmetic on each stimulus's
widest disparity step, and met-011 needs only that bio-072 be restated against a
prior-free baseline.

---

## What this does not do

Nothing was re-run, re-rendered, re-derived or reversed. No policy changed, no
analyser was modified — the existing `analyse.py` files are imported and read,
and their recorded verdicts are the control this re-score is checked against.
od-002 and od-003 are untouched.

**And it does not declare either bar correct.** The sd bar asks a real question —
*would this reliably help on a new scene* — and the answer matters. The se bar as
specified asks nothing: `t > 1` is p ≈ 0.33. **The criterion that answers "is
there an effect" is the sign test**, and it is now reported beside both.

The defect on record was one unnamed threshold standing in for three questions.
Replacing it with a different unnamed threshold would repeat it exactly.
