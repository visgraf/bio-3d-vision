# exp012 — re-score every verdict under both bars, and audit what was inherited

**Pre-registered. Committed alone, before the re-scorer exists.**

No runs, no renders. Every number comes from `results.json` files already on disk
for exp001–exp005 and exp007–exp011. There is no exp006 (am-004: specified,
deliberately not run).

---

## (d) cannot occur, and that is a theorem rather than a prediction

> A positive under the sd bar is a positive under the se bar, always.

The verdict is `|mean| > max(bar_clause_1, floor)`. Clause 1 is `sd` in one
reading and `sd/sqrt(n)` in the other, and `sd >= sd/sqrt(n)` for every `n >= 1`,
so `max(sd, floor) >= max(sd/sqrt(n), floor)`. Anything clearing the larger
threshold clears the smaller one.

**So if a positive flips, the implementation is wrong and nothing else in the
report is readable.** It is asserted in code, per comparison, not checked by eye.

**A second, independent guard**: for every comparison, the re-scorer recomputes
`mean_diff` and `sd` from the stored per-seed values and asserts they match that
experiment's own recorded verdict to `1e-9`. A wrongly reconstructed comparison
fails there before it can reach a table.

## The materiality floor is NOT divided by `sqrt(n)`

Clause 2 is a statement about **practical** significance — "a difference smaller
than this does not justify a framework-level change **even if it is perfectly
consistent across seeds**" (`exp001_gaze_objective/preregistration.md:158-160`).
Nothing about that scales with sample size. Dividing it would convert a
materiality judgement into a second statistical test and would make the audit
say something the criterion never said.

**So the se bar is `max(sd/sqrt(n), floor)`.** Where the floor binds, the two
bars agree **by construction**, and the report will say which clause binds in
every cell rather than leaving it inferable.

## What the two bars ask, kept separate

- **sd** — does the effect exceed scene-to-scene variation? *Would this reliably
  help on a new scene?*
- **se** — is the mean effect nonzero? *Did we see a real difference at all?*

**Both are legitimate and neither is declared correct.** The defect on record is
that they were conflated; replacing one with the other would repeat it in the
other direction. Where they agree the report says so and moves on. **The
deliverable is the disagreement set.**

## The prediction, from what is already on record

A null flips iff `x_bar_sd > 1/sqrt(n)`: **0.354 at n=8, 0.250 at n=16, 0.204 at
n=24**. That is a low threshold, so **the disagreement set is predicted to be
large, not small** — (a) and (b) are predicted *not* to occur.

Four flips are already derivable from the ledger without computing anything new,
which is why this prediction is not a guess:

| on record | `x_bar_sd` | n | `x_bar_se` |
|---|---|---|---|
| exp011 AT, k=4 (bio-070) | 0.91 | 24 | **4.46** |
| exp011 AT, k=2 (bio-071) | 0.80 | 24 | 3.92 |
| exp011 AWAY, k=8 (bio-071) | 0.97 | 24 | 4.75 |
| exp010 AT median (bio-066) | 0.96 | 8 | 2.71 |

**Predicted: (c).** exp005's band results are nulls throughout and fc-008 is
qualified by them; fc-007 rests on the A-versus-A′ comparison; fc-010 rests on N
and V against W. All are nulls, and a null needs only `x_bar_sd > 0.354` at n=8
to be in the set. **If (c) holds, the entry to name first is whichever of
fc-007, fc-008, fc-010 is affected**, in that order of appearance in the ledger.

**(a) would be the cheapest outcome and is reported plainly if it occurs** — it
would mean this concern was a methodological point with no empirical
consequence.

## Part B — annotate, never reverse

**No foreclosure changes in this iteration.** A closure reversed on a
re-analysis it did not pre-register is am-002-c's defect, and this re-analysis is
exactly that shape. Each affected entry gets: what the se bar says, that it was
not the criterion in force when the entry was written, and what a pre-registered
re-test would need.

**What a flipped null means, stated before any are found.** It does **not** mean
the finding was wrong. The finding was *"the effect is not larger than
scene-to-scene variation"*. It was read as *"there is no effect"*. **Those are
different claims and the reading is what needs correcting** — the measurement
stands.

## Part C — the inheritance audit

The bar walked in from the predecessor with no status marker and acquired the
authority of a repository decision. `inherited-measurements.yaml` gives carried
**numbers** a `status`; carried **methods** have none.

A `methods` section is added with the same discipline: what was carried, from
where, whether it was ever re-derived here, and what re-deriving would take.
Each entry is classified:

- **measurement** — this repository measured it;
- **choice** — this repository chose it, deliberately, and said so;
- **carried** — it walked in and has never been examined here.

**The third category is the finding.** The count of `carried` entries is
reported and recorded in the ledger.

**Nothing in Part C is re-derived.** The audit is the deliverable; re-deriving
would be a different iteration, and doing it here would bury the count under the
work.

## What this does not do

No new runs, no renders, no policy change, no step 18, no od-002, no od-003, no
foreclosure reversed, no constant re-derived, no analyser rewritten. Existing
`analyse.py` files are imported and read, never modified — their recorded
verdicts are the control this re-score is checked against.
