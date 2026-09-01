# exp014 — is exp011's accuracy term allocation or scaling?

**Pre-registered. Committed alone, before the runner exists.**

exp011's design with one arm added. Same seeds, same budget, same levels, same
bar, **same renders** — 4.0 GB of exp011 captures are on disk and no new one is
made.

---

## Two corrections to the specification, both structural

### 1. OPEN already re-linearises. (a) cannot mean "collapses to OPEN".

`run_arm` calls `engine.measurement(yf, xf)` **for both arms at every fixation**,
and `measurement` calls `self.vergence(yf, xf)` internally. So **OPEN's pedestal
tracks its gaze exactly as CLOSED's does** — only its *images* are stale.

The CLOSED−OPEN gap is therefore **not** "CLOSED re-linearises and OPEN does
not". Both do. Whatever the gap is, it is not pedestal tracking *per se*.

**So (a) is restated:** *CLOSED-FROZEN loses most or all of the CLOSED−OPEN
accuracy gap.* It may land **below** OPEN, since OPEN tracks its pedestal and
CLOSED-FROZEN does not — and that would still be the outcome (a) describes,
reached from the other side.

### 2. A free-running frozen arm would need new renders. It is YOKED instead.

Freezing the pedestal changes the measurements, which changes the belief, which
changes the scanpath — so a free-running CLOSED-FROZEN would ask for captures at
fixations CLOSED never visited, and there are none on disk.

> **CLOSED-FROZEN replays CLOSED's own fixation sequence**, reusing CLOSED's
> renders exactly. The eye still moves, `w` still follows it, the loop still
> re-renders and re-matches. Only the linearisation stops tracking gaze.

**This is better isolation, not a compromise.** With the scanpath held fixed, a
difference between CLOSED and CLOSED-FROZEN cannot be attributed to *where the
eye went*; it can only be the pedestal. **What it gives up** is the free-running
question — how a frozen-pedestal loop would choose to look — and that is a
different experiment, named here so it is not read into the result.

---

## The arms

| arm | renders | pedestal | scanpath |
|---|---|---|---|
| **OPEN** | one, at the anchor | recomputed per fixation | its own |
| **CLOSED** | one per fixation | recomputed per fixation | its own |
| **CLOSED-FROZEN** | CLOSED's, reused | **computed once at fixation 0, then held** | **CLOSED's, replayed** |

`d_fix` at fixation 0 is computed **exactly as CLOSED computes it** — the same
`win=6` window, the same `gain=0.7` four-step leaky integrator, the same
`[f·I/8, f·I/0.5]` clamp. Nothing is substituted; a scene average or a
ground-truth pedestal would be a different arm.

## What freezing does to the clamps

**The `[d_lo, d_hi]` clamp cannot newly bind.** It is applied inside `vergence`
to `d_fix` itself, and `d_fix` is computed once, so freezing removes the
opportunity for it to bind again rather than creating one. **Reported anyway**:
whether fixation 0's `d_fix` was clamped, per run.

**Where freezing shows up is the downstream `np.clip(Zmeas, 0.3, 10.0)`.** A
first-order expansion evaluated far from its expansion point produces absurd
depths, and that clip is what catches them. **The fraction of valid pixels it
binds on is reported per arm per level** — it is the quantity that would
otherwise absorb the effect silently.

## The decomposition, and its own falsifier

exp011's decomposition, per level, for all three arms: the **accuracy term** (the
common-set gain × the common share) and the **coverage term** (the CLOSED-only
gain × that share), which sum to the all-cells gain.

> **The coverage term must be IDENTICAL for CLOSED and CLOSED-FROZEN.** Freezing
> the pedestal changes nothing about which cells are visible. **If it is not,
> something else is coupled to `d_fix`, and finding out what matters more than
> the headline.** Reported as a check, not assumed.

*(Note: `ever_measured` depends on precision being non-zero, and `meas_prec`
contains `1/var_Z` which contains `sig_model`. A frozen pedestal could in
principle drive `var_Z` high enough that a cell registers no measurement. That is
the coupling the check is for, and it is why the check is pre-registered rather
than asserted.)*

**All three criteria per exp012** — sd bar, sign test with its p, materiality
floor — with **which one binds named in every cell**. `x_bar` never alone.

## Falsifiers

- **(a) CLOSED-FROZEN loses most or all of the CLOSED−OPEN accuracy gap.** The
  accuracy term was the scaling layer. exp011's correct description becomes
  "re-verging helps", the result belongs to L4 rather than L6, **and it would
  transfer to a passive rig.** Report first if it happens.
- **(b) CLOSED-FROZEN retains most of the gain.** Allocation is doing the work,
  the concern is dead, exp011 stands as described. **Say so plainly — Chat raised
  this and would be wrong.**
- **(c) Between them.** Report the split as a fraction of the CLOSED−OPEN gap,
  per band, and note whether it differs AT and AWAY from discontinuities —
  `sig_model` is `η²` and `η` is largest exactly where depth changes.
- **(d) CLOSED-FROZEN beats CLOSED.** Tracking the pedestal actively *harms*: a
  mis-verged pedestal poisons that fixation's whole field, and fc-010 recorded
  that the estimator has no signed out-of-range error. **Report first — it would
  make od-003 urgent rather than deferred.**

### Declared predictions

**The reading this iteration exists to test predicts (a).** If `sig_model`
carries the effect, removing pedestal tracking should remove it.

**I predict (b), and the reason is correction 1.** OPEN already re-linearises at
every fixation, so pedestal tracking cannot be what separates CLOSED from OPEN —
both have it. The CLOSED−OPEN gap must come from the fresh captures: 41
independently matched images against one. If that is right, freezing CLOSED's
pedestal should cost it something, but not the gap over OPEN.

**The two predictions differ, and the measurement decides.** I am recording mine
because a pre-registration that only carries the hypothesis it was written to
test is not a falsifier.

**Most likely mode of surprise: CLOSED-FROZEN below OPEN.** A stale pedestal on
fresh images is a worse combination than a stale pedestal on stale images,
because the scene in view changes while the expansion point does not.

## What this does not do

No new renders, no spherical work, no C2, no od-002, no od-003, no constant
sweep, no policy change. **No foreclosure is reversed or annotated beyond
recording what this measured** — if (a) fires, the annotation is the maintainer's
decision, not a consequence to be applied here.
