# exp014 — findings

**Measured** at `af05e68`, 4 levels × 24 seeds × 3 arms, budget 40,
**reusing exp011's captures — no new render was made.** Python 3.13.15 / numpy
2.5.2.

**The question as posed contains a false premise, and that is the first result.**

---

## The premise: OPEN already re-linearises

`run_arm` calls `engine.measurement(yf, xf)` for **both** arms at every fixation,
and `measurement` calls `vergence(yf, xf)` internally. **OPEN's pedestal tracks
its gaze exactly as CLOSED's does.** Only its images are stale.

So exp011's accuracy term is *not* "CLOSED re-verges and OPEN does not" — it is
the residual between two arms that both re-verge. **Freezing one of them does not
decompose that residual; it moves that arm into a different regime entirely.**

## Reproduction check

exp014's OPEN and CLOSED arms reproduce exp011's **bit-identically** — max
|difference| **0.000e+00** on `ever_measured`, `common_fraction` and every band
median, across all 96 (level, seed) pairs. Adding the third arm changed nothing.

## The pre-registered coverage check passes exactly

**`ever_measured` is identical for CLOSED and CLOSED-FROZEN in 96/96 runs**,
`common == common_all` in 96/96, max |difference| **0.000e+00**. Nothing else is
coupled to `d_fix`.

---

## What freezing does

**The pedestal freezes at D_fix ≈ 4.55 m in every run — the background — and is
never clamped** (0 of 96 hit `[d_lo, d_hi]`). The fixture spans 2.4–4.5 m, so the
frozen expansion point sits at the far end and everything nearer carries a large
`η`.

The `[d_lo, d_hi]` clamp cannot newly bind under freezing — it lives inside
`vergence`, which runs once. **Where freezing shows up is the downstream
`np.clip(Zmeas, 0.3, 10.0)`**, and it binds monotonically more often:

| level | OPEN | CLOSED | FROZEN |
|---|---|---|---|
| k1 | 0.0122 | 0.0733 | **0.0940** |
| k4 | 0.0425 | 0.0989 | **0.1157** |
| k8 | 0.0823 | 0.1170 | **0.1415** |

## The decomposition — exp011's terms, all three arms

| level | occl | CLOSED acc | **FROZEN acc** | CLOSED cov | FROZEN cov |
|---|---|---|---|---|---|
| k1 | 0.0197 | +0.01045 | **−0.29464** | 0.36810 | 0.33787 |
| k2 | 0.0426 | +0.00165 | **−0.18254** | 0.37199 | 0.34074 |
| k4 | 0.0884 | +0.01155 | **−0.13727** | 0.38704 | 0.36382 |
| k8 | 0.1716 | +0.00112 | **−0.10288** | 0.38066 | 0.35490 |

*(CLOSED's columns reproduce bio-072 exactly. OPEN's reference for the coverage
term is taken from exp011 because OPEN's own-only set is empty by construction —
`common` **is** OPEN's set — and the two OPEN arms are bit-identical.)*

**The coverage term barely moves** (92% of CLOSED's), as pre-registered: it is
about which cells are visible, and those are identical. **The accuracy term
inverts**, from a small positive to a large negative.

## The split, per band — and it is the structure (c) predicted

Retention = (OPEN − FROZEN) / (OPEN − CLOSED) on the common-set **median**.
1.0 means freezing costs nothing; negative means FROZEN is worse than OPEN.

| level | AT | MIDDLE | AWAY | POOLED |
|---|---|---|---|---|
| k1 | −18.05 | −45.91 | **−383.16** | −62.03 |
| k2 | −14.18 | −0.69 | **+1.07** | −1.36 |
| k4 | −4.87 | +1.10 | **+1.10** | +0.14 |
| k8 | −12.58 | +1.21 | **+1.29** | +0.23 |

> **AWAY from depth discontinuities, at k2/k4/k8, freezing the pedestal costs
> NOTHING — retention 1.07 to 1.29. CLOSED's gain over OPEN there is not the
> pedestal.**
>
> **AT discontinuities, freezing is catastrophic at every level.** `sig_model` is
> `η²` and `η` is largest exactly where depth changes — the mechanism, showing up
> where it was predicted to.

**The mean and the median disagree, and both are reported because the
disagreement is the finding.** The decomposition uses the mean and says freezing
is catastrophic everywhere; the median says most of CLOSED's gain survives at
k4/k8. **The damage is in the tail**, which is what an `η²` term does.

### Why k1 is worst — measured, not supposed

The frozen pedestal sits at the background. The damage should scale with how much
of the field is *not* at the background, and it does:

| level | card area | retention (POOLED) |
|---|---|---|
| k1 | 0.4603 | −62.03 |
| k2 | 0.3021 | −1.36 |
| k4 | 0.2648 | +0.14 |
| k8 | 0.2464 | +0.23 |

Monotone. k1 has the most surface away from the frozen expansion point and takes
the most damage.

## Which falsifier occurred

**(c), and the answer is band-dependent rather than global.**

- **AWAY from discontinuities: (b).** Retention ≈ 1.1 at k2–k8. The pedestal
  contributes nothing there, and CLOSED's gain over OPEN comes from the fresh
  captures — **allocation, not scaling.**
- **AT discontinuities: the experiment cannot separate them.** Freezing does not
  remove the pedestal's contribution, it destroys the arm — FROZEN is 0.15 to
  0.25 m worse than OPEN there. **A measurement that puts one arm off-scale
  cannot apportion a 0.008 m difference**, and reporting a ratio of −14 as "the
  pedestal's share" would be arithmetic without meaning.
- **(a) is not supported as stated**, because its inference requires the pedestal
  to be what separates CLOSED from OPEN — and both arms track it.
- **(d) did not occur.** FROZEN never beats CLOSED, in any band at any level.

All three criteria agree throughout: **the sd binds in every cell** and the sign
test is 0/24 or 24/24 at p ≤ 3e−6 almost everywhere.

## What this does not do

No new renders, no spherical work, no C2, no od-002, od-003 or od-004, no
constant sweep, no policy change. **No foreclosure is reversed or annotated
beyond recording what this measured.**
