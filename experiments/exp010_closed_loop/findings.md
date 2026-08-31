# exp010 — findings

**Measured** at `cdd5a85`, 8 seeds × 40 fixations × 2 arms, 8.84%
left-occluded, Blender **5.2.0 LTS** (`fbe6228777e7`), Cycles, 1 sample; Python
3.13.15 / numpy 2.5.2.

**Outcome (a). CLOSED beats OPEN — the first positive result for active vision in
either repository.** Reported below with its cost, which is 41×, and with the
three places it does not hold.

---

## (d) first, because it was the prediction

**It did not fire.** 8/8 seeds reached the 40-fixation budget in both arms.
**Zero refusals** from `target_to_fixation`. The belief never emptied.

**fc-010's vergence estimator did not visibly wander**, which the pre-registration
expected it might. CLOSED's vergence ranged 0.0103–0.0599 against OPEN's fixed
0.0217, ending at 0.0248 on average; `D_fix` stayed inside 2.40–4.63 m with the
0.3/10.0 m clip **never** reached. The declared prediction — "(c) or (d) over
(a)" — was **wrong**, and it was wrong about the specific mechanism it named.

---

## The comparison, on the common cell set only

`d = CLOSED − OPEN`, so negative is CLOSED better. exp001's bar,
`max(sd, 0.02 × mean(OPEN))`. **The common set is 0.622 of the belief and it is
exactly OPEN's set**: OPEN measured nothing outside it, so this compares the two
arms on every cell OPEN reached and on no cell it did not.

| band | metric | OPEN | CLOSED | mean_diff | sd | materiality | bar | x̄ | verdict |
|---|---|---|---|---|---|---|---|---|---|
| AT | median | 0.0310 | 0.0171 | −0.0140 | 0.0146 | 0.0006 | 0.0146 | 0.96 | **indistinguishable** |
| AT | p90 | 0.5003 | 0.5311 | +0.0308 | 0.2143 | 0.0100 | 0.2143 | 0.14 | **indistinguishable** |
| MIDDLE | median | 0.0220 | 0.0121 | −0.0100 | 0.0038 | 0.0004 | 0.0038 | 2.60 | **CLOSED better** |
| MIDDLE | p90 | 0.1581 | 0.0378 | −0.1203 | 0.0211 | 0.0032 | 0.0211 | **5.70** | **CLOSED better** |
| AWAY | median | 0.0155 | 0.0110 | −0.0046 | 0.0011 | 0.0003 | 0.0011 | 4.26 | **CLOSED better** |
| AWAY | p90 | 0.0545 | 0.0322 | −0.0222 | 0.0125 | 0.0011 | 0.0125 | 1.78 | **CLOSED better** |
| POOLED | median | 0.0258 | 0.0146 | −0.0112 | 0.0082 | 0.0005 | 0.0082 | 1.37 | **CLOSED better** |
| POOLED | p90 | 0.3243 | 0.2424 | −0.0818 | 0.1695 | 0.0065 | 0.1695 | 0.48 | **indistinguishable** |

**Both `mean_diff` and `bar` are given because the bar moves.** In every
distinguished cell the bar is the seed sd, not the 2% materiality floor — the
floor is 4–20× smaller throughout, so nothing here is decided by it.

**Per-seed, so this is not one seed carrying it**: CLOSED has the lower POOLED
median in **8/8** seeds, and the lower band median in **8/8** for MIDDLE and AWAY,
**7/8** for AT.

### Where it does not hold, stated as plainly as where it does

**The benefit is not at depth discontinuities.** AT is indistinguishable on both
metrics, and its p90 is the one cell where CLOSED is nominally *worse*
(+0.0308, x̄ 0.14 — well inside the noise). POOLED p90 is indistinguishable
because AT dominates the tail. **A closed loop helps on the smooth interior and
does not help at the edges**, which is where exp005 and exp008 both found the
error concentrated.

---

## Coverage, reported separately per exp003 — and it is the larger effect

| | ever measured | outside the common set |
|---|---|---|
| OPEN | 0.622 | 0.000 |
| CLOSED | **0.928** | 0.306 |

CLOSED measures **49% more of the belief in relative terms**, and 30.6% of its
cells lie outside anything OPEN reached. `ActiveStereo.valid` excludes the border
and the 64-column disparity-search margin, so from one viewpoint those cells are
**permanently unmeasurable**; a saccade brings them inside. Their error is
reported on CLOSED's own set (POOLED median 0.0146, p90 0.2417) and **is not
comparable to OPEN's own-set figure**, which is over a different set of cells.

This was the pre-registration's declared guess for the mechanism if (a) occurred,
and it is at least partly right — but note that the accuracy gain above is on the
common set, where coverage cannot explain it.

---

## The grid-loss budget CLOSED pays and OPEN does not

| | survived the whole run | visible per fixation, mean | min |
|---|---|---|---|
| OPEN | 1.000 | 1.000 | 1.000 |
| CLOSED | **0.000** | 0.615 | 0.247 |

**Not one cell of the belief was on the sensor at all 40 of CLOSED's fixations.**
The loop reached |az| 0.2308 and |el| 0.1691 — the policy's full reach — and
bio-063 prices that at 0.436 of the grid gone in a single saccade. CLOSED pays
38.5% per fixation on average and still wins, which is the finding: **the loop
survives its own grid loss because the belief is persistent and the loss is not
the same cells each time.**

---

## The cost

| | renders | render seconds | front-end matches | front-end seconds | total |
|---|---|---|---|---|---|
| OPEN | 1 | 0.57 | 1 | 0.05 | **0.62 s** |
| CLOSED | 41 | 23.37 | 41 | 2.24 | **25.6 s** |

**41×**, and the render is 91% of it. Timing only `measurement()` would have shown
0.02 s for both arms and made this table wrong; the front-end match CLOSED redoes
on every saccade is where its matcher cost lives, and it was missing from the
first version of this runner.

---

## The caveat I cannot settle here, named rather than buried

**Neither arm's fusion accounts for correlation between successive measurements,
and OPEN's are far more correlated than CLOSED's.** `ActiveStereo.measurement`
recomputes `Zmeas` from `self.d_sub`, which for OPEN **never changes** — its 40
measurements differ only in the pedestal and the foveal weight, drawn from one
disparity map. CLOSED's come from 41 independently matched pairs. The Kalman
fusion assumes independence, so **OPEN violates it worse**, and some unknown part
of CLOSED's advantage may be that rather than better data.

**The check that would settle it** changes the arm definition, so it is a
different experiment: give OPEN a single fuse, or down-weight repeated
measurements of the same map, and see how much of the gap survives. Not run.

**bio-065 is not the explanation.** The foveal peak misses the target by 3.6–21.0
px in CLOSED (mean 7.4) against OPEN's fixed 7.6 px, so the apparatus defect is
essentially equal between arms and cannot account for the difference.

---

## Carried unchanged, as pre-registered

`fc-009`'s pixel-native foveal weight and square vergence window; `bio-065`'s
offset between the shifted principal point and the target's image; `fc-010`'s
vergence estimator with no signed out-of-range error. **Nothing was tuned.** The
one thing the runner changed after its first version was to restrict the policy's
argmax to cells `ActiveStereo.valid` can actually measure — without it OPEN sat on
cell (0,0), an invalid corner, for its whole budget, because a fovea that measures
nothing leaves the prior untouched and stays the argmax. That is `loop.py`'s own
rule (`v = np.where(self.valid, v, -inf)`), not a new one.

## What this does not establish

That active vision helps **at occlusion boundaries** — measured here and it does
not. That it helps at other occlusion levels — 8.84% is one point, chosen because
exp008 measured allocation to be undetectable at 17.16%. That a greedy argmax with
no inhibition of return is a good policy — `loop.py` DEFECT 3 is carried, and OPEN
was observed revisiting a pixel on consecutive steps. And nothing about vertical
disparity, which fc-012 foreclosed and this loop does not have.
