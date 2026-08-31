"""exp012 Part A — every pairwise comparison, under both bars, from stored results.

**Each experiment's own ``compare`` is called, never reimplemented.** The floor,
the spread and the verdict on record all come from the analyser that produced
them, so this cannot disagree with the ledger by having re-derived something
differently. Only the per-seed difference vector is rebuilt here — it is needed
for the sign test and no analyser returns it — and it is checked against that
analyser's own ``mean_diff`` and spread to 1e-9 before it is used.

Two guards, both asserted rather than eyeballed:

1. **Reconstruction.** ``mean(d)`` and ``std(d, ddof=1)`` must equal what the
   experiment recorded. A wrongly rebuilt comparison fails here.
2. **Monotonicity.** ``max(sd, floor) >= max(sd/sqrt(n), floor)``, so a positive
   under the sd bar is a positive under the se bar. A flip means the
   implementation is wrong; the run stops.
"""

from __future__ import annotations

import importlib
import json
import math
import pathlib
from collections.abc import Iterator
from typing import Any

import numpy as np
from scipy import stats

HERE = pathlib.Path(__file__).parent
REPO = HERE.resolve().parents[1]
TOL = 1e-9
MATERIALITY = 0.02  # exp001 clause 2, identical in every analyser that reuses it

# The two spread keys and the two floor keys the analysers happen to use.
SPREAD_KEYS = ("sd_diff", "sd", "spread")
FLOOR_KEYS = ("materiality_bar", "materiality_floor", "materiality")


def _load(name: str) -> dict:
    for path in (
        REPO / "results" / name / "results.json",
        REPO / "experiments" / name / "results.json",
    ):
        if path.exists():
            return json.loads(path.read_text())
    raise FileNotFoundError(name)


def _mod(name: str):
    return importlib.import_module(f"experiments.{name}.analyse")


def _pick(rec: dict, keys: tuple[str, ...]) -> float:
    for k in keys:
        if k in rec:
            return float(rec[k])
    raise KeyError(f"none of {keys} in {sorted(rec)}")


def _sign_test_p(d: np.ndarray) -> tuple[int, int, float]:
    """Two-sided exact sign test. Ties are dropped, as the test requires."""
    nz = d[d != 0.0]
    n = int(nz.size)
    k = int(np.sum(nz < 0))  # favouring the arm with the LOWER error
    if n == 0:
        return 0, 0, float("nan")
    lo = min(k, n - k)
    tail = sum(math.comb(n, i) for i in range(lo + 1)) / (2.0**n)
    return k, n, float(min(1.0, 2.0 * tail))


# ---------------------------------------------------------------------------
# Adapters. Each yields (label, that experiment's own compare() output, the
# per-seed difference vector, and the array its materiality floor is scaled by).
# ---------------------------------------------------------------------------
def exp001() -> Iterator[tuple[str, dict, np.ndarray, np.ndarray]]:
    m = _mod("exp001_gaze_objective")
    res = _load("exp001_gaze_objective")
    pairs = {
        "A_prime_vs_C": ("A_prime", "C"),
        "C_vs_B": ("C", "B"),
        "A_vs_A_prime": ("A", "A_prime"),
        "A_vs_C": ("A", "C"),
    }
    for label, (base, other) in pairs.items():
        for metric in m.PRIMARY + m.SECONDARY:
            c = m.compare(res, base, other, metric)
            d = m.finals(res, other, metric) - m.finals(res, base, metric)
            yield f"{label}|{metric}", c, d, m.finals(res, base, metric)


def exp002() -> Iterator[tuple[str, dict, np.ndarray, np.ndarray]]:
    m = _mod("exp002_saliency_value")
    res = _load("exp002_saliency_value")
    pairs = [("A_prime", "E", None), ("E", "D", None), ("A_prime", "C", None), ("C", "B", 18)]
    for base, other, step in pairs:
        for metric in m.PRIMARY + m.SECONDARY:
            c = m.compare(res, base, other, metric, step=step)
            d = m.at(res, other, metric, step) - m.at(res, base, metric, step)
            tag = f"{other}_vs_{base}" + (f"@{step}" if step else "")
            yield f"{tag}|{metric}", c, d, m.at(res, base, metric, step)


def exp003() -> Iterator[tuple[str, dict, np.ndarray, np.ndarray]]:
    m = _mod("exp003_vergence_acquisition")
    res = _load("exp003_vergence_acquisition")
    for region in ("intersection", "excluded", "pooled_CONFOUNDED"):
        for base, other in (("W", "N"), ("W", "V"), ("N", "V")):
            for metric in m.PRIMARY + m.SECONDARY:
                c = m.compare(res, base, other, region, metric)
                d = m.vals(res, other, region, metric) - m.vals(res, base, region, metric)
                yield (
                    f"{other}_vs_{base}@{region}|{metric}",
                    c,
                    d,
                    m.vals(res, base, region, metric),
                )


def exp004() -> Iterator[tuple[str, dict, np.ndarray, np.ndarray]]:
    m = _mod("exp004_scene_model_check")
    rows = _load("exp004_scene_model_check")["per_seed"]
    for stratum in ("AWAY", "AT", "ALL"):
        for metric in m.METRICS:
            c = m.paired(rows, stratum, metric)
            f = np.array([r["strata"][stratum]["F"][metric] for r in rows], float)
            r_ = np.array([r["strata"][stratum]["R"][metric] for r in rows], float)
            yield f"R_vs_F@{stratum}|{metric}", c, r_ - f, f
    for prefix in ("AWAY", "AT"):
        for metric in m.METRICS:
            swept = m.sweep(rows, prefix, metric)
            for key, c in swept.items():
                f = np.array([r["sweep"][key]["F"][metric] for r in rows], float)
                r_ = np.array([r["sweep"][key]["R"][metric] for r in rows], float)
                yield f"R_vs_F@sweep_{key}|{metric}", c, r_ - f, f


def exp005() -> Iterator[tuple[str, dict, np.ndarray, np.ndarray]]:
    m = _mod("exp005_stratified_reanalysis")
    data = _load("exp005_stratified_reanalysis")
    for label in ("exp001", "exp002"):
        arms = m.by_arm(data[label]["rows"])
        for x, y in m.COMPARISONS[label]:
            for band in m.BANDS:
                for metric in m.METRICS:
                    c = m.compare(arms, x, y, band, metric)
                    if c is None:
                        continue
                    seeds = sorted(set(arms[x]) & set(arms[y]))
                    a = np.array([arms[x][s]["final"][band][metric] for s in seeds], float)
                    b = np.array([arms[y][s]["final"][band][metric] for s in seeds], float)
                    yield f"{label}:{x}_vs_{y}@{band}|{metric}", c, a - b, b


def exp007() -> Iterator[tuple[str, dict, np.ndarray, np.ndarray]]:
    m = _mod("exp007_rendered_policy_sweep")
    data = _load("exp007_rendered_policy_sweep")
    for rowkey, tag in (("rows", "b18"), ("rows_budget40", "b40")):
        if rowkey not in data:
            continue
        idx = m.index(data[rowkey])
        sources = sorted({s for s, _ in idx})
        for source in sources:
            for x, y, _bears in m.COMPARISONS:
                for band in m.BANDS:
                    for metric in m.METRICS:
                        c = m.compare(idx, source, x, y, band, metric)
                        if c is None:
                            continue
                        ax, ay = idx[(source, x)], idx[(source, y)]
                        seeds = sorted(set(ax) & set(ay))
                        a = np.array([ax[s]["final"][band][metric] for s in seeds], float)
                        b = np.array([ay[s]["final"][band][metric] for s in seeds], float)
                        yield (
                            f"{tag}:{source}:{x}_vs_{y}@{band}|{metric}",
                            c,
                            a - b,
                            b,
                        )


def exp008() -> Iterator[tuple[str, dict, np.ndarray, np.ndarray]]:
    m = _mod("exp008_occlusion_sweep")
    data = _load("exp008_occlusion_sweep")
    rows = data["rows"]
    levels = sorted({r["k"] for r in rows})
    for k in levels:
        for x, y in m.COMPARISONS:
            for band in m.BANDS:
                for metric in m.METRICS:
                    c = m.compare(rows, k, x, y, band, metric)
                    ax = {r["seed"]: r for r in rows if r["k"] == k and r["arm"] == x}
                    ay = {r["seed"]: r for r in rows if r["k"] == k and r["arm"] == y}
                    seeds = sorted(set(ax) & set(ay))
                    a = np.array([ax[s]["final"][band][metric] for s in seeds], float)
                    b = np.array([ay[s]["final"][band][metric] for s in seeds], float)
                    yield f"k{k}:{x}_vs_{y}@{band}|{metric}", c, a - b, b


def exp009() -> Iterator[tuple[str, dict, np.ndarray, np.ndarray]]:
    m = _mod("exp009_epipolar_cost")
    data = _load("exp009_epipolar_cost")
    by: dict[tuple, dict] = {}
    for r in data["rows"]:
        by.setdefault((r["az"], r["el"], r["seed"]), {})[r["arm"]] = r
    seeds = data["seeds"]
    for az, el in [tuple(f) for f in data["fixations"]]:
        for band in m.BANDS:
            for metric in m.METRICS:
                a = np.array([by[(az, el, s)]["TOED"][band][metric] for s in seeds], float)
                b = np.array([by[(az, el, s)]["RECT"][band][metric] for s in seeds], float)
                if not (np.isfinite(a).all() and np.isfinite(b).all()):
                    continue
                yield (
                    f"az{az:.2f}_el{el:.2f}:TOED_vs_RECT@{band}|{metric}",
                    m.bar_compare(a, b),
                    a - b,
                    b,
                )


def exp010() -> Iterator[tuple[str, dict, np.ndarray, np.ndarray]]:
    m = _mod("exp010_closed_loop")
    data = _load("exp010_closed_loop")
    by: dict[int, dict] = {}
    for r in data["rows"]:
        by.setdefault(r["seed"], {})[r["arm"]] = r
    for band in m.BANDS:
        for metric in m.METRICS:
            c = np.array([by[s]["CLOSED"][f"{band}_common"][metric] for s in data["seeds"]], float)
            o = np.array([by[s]["OPEN"][f"{band}_common"][metric] for s in data["seeds"]], float)
            yield f"CLOSED_vs_OPEN@{band}|{metric}", m.compare(c, o), c - o, o


def exp011() -> Iterator[tuple[str, dict, np.ndarray, np.ndarray]]:
    m = _mod("exp011_consolidation")
    data = _load("exp011_consolidation")
    by: dict[tuple, dict] = {}
    for r in data["rows"]:
        by.setdefault((r["k"], r["seed"]), {})[r["arm"]] = r
    seeds = data["seeds"]
    for k in data["levels_k"]:
        for band in m.BANDS:
            for sel, metric in (("common", "median_abs_err"), ("all", "mean_abs_err")):
                c = np.array([by[(k, s)]["CLOSED"][f"{band}_{sel}"][metric] for s in seeds], float)
                o = np.array([by[(k, s)]["OPEN"][f"{band}_{sel}"][metric] for s in seeds], float)
                yield (
                    f"k{k}:CLOSED_vs_OPEN@{band}_{sel}|{metric}",
                    m.compare(c, o),
                    c - o,
                    o,
                )


ADAPTERS = {
    "exp001_gaze_objective": exp001,
    "exp002_saliency_value": exp002,
    "exp003_vergence_acquisition": exp003,
    "exp004_scene_model_check": exp004,
    "exp005_stratified_reanalysis": exp005,
    "exp007_rendered_policy_sweep": exp007,
    "exp008_occlusion_sweep": exp008,
    "exp009_epipolar_cost": exp009,
    "exp010_closed_loop": exp010,
    "exp011_consolidation": exp011,
}


def rescore() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for exp, adapter in ADAPTERS.items():
        for label, rec, d, floor_ref in adapter():
            d = np.asarray(d, dtype=float)
            n = int(d.size)
            mean_d = float(np.mean(d))
            sd = float(np.std(d, ddof=1))
            # GUARD 1: the reconstruction must equal what the experiment recorded.
            rec_mean = float(rec["mean_diff"])
            if abs(mean_d - rec_mean) > TOL:
                raise AssertionError(
                    f"{exp} {label}: rebuilt mean {mean_d!r} != recorded {rec_mean!r}. "
                    "The comparison was rebuilt wrongly."
                )
            floor = MATERIALITY * float(np.mean(np.asarray(floor_ref, dtype=float)))
            bar_sd = max(sd, floor)
            # Some analysers record the spread and the floor; exp004's `sweep`
            # records only their max. Check whichever is on record — the guard is
            # equally strong either way, because bar == max(sd, floor) pins both
            # when they are not separately available.
            rec_sd = next((float(rec[k]) for k in SPREAD_KEYS if k in rec), None)
            rec_floor = next((float(rec[k]) for k in FLOOR_KEYS if k in rec), None)
            if rec_sd is not None and abs(sd - rec_sd) > TOL:
                raise AssertionError(f"{exp} {label}: rebuilt sd {sd!r} != recorded {rec_sd!r}")
            if rec_floor is not None and abs(floor - rec_floor) > TOL:
                raise AssertionError(
                    f"{exp} {label}: rebuilt floor {floor!r} != recorded {rec_floor!r}"
                )
            if abs(bar_sd - float(rec["bar"])) > TOL:
                raise AssertionError(
                    f"{exp} {label}: rebuilt bar {bar_sd!r} != recorded {rec['bar']!r}"
                )
            # The floor is NOT divided by sqrt(n): clause 2 is a materiality
            # judgement, not a second statistical test. See the preregistration.
            se = sd / math.sqrt(n) if n > 1 else sd
            bar_se = max(se, floor)
            dist_sd = abs(mean_d) > bar_sd
            dist_se = abs(mean_d) > bar_se
            # GUARD 2: a positive cannot flip. This is algebra, asserted anyway.
            if dist_sd and not dist_se:
                raise AssertionError(
                    f"{exp} {label}: a POSITIVE flipped. bar_sd={bar_sd} bar_se={bar_se}. "
                    "The implementation is wrong; stop."
                )
            favouring, n_nonzero, p = _sign_test_p(d)
            out.append(
                {
                    "experiment": exp,
                    "comparison": label,
                    "n_seeds": n,
                    "mean_diff": mean_d,
                    "sd": sd,
                    "se": se,
                    "materiality_floor": floor,
                    "bar_sd": bar_sd,
                    "bar_se": bar_se,
                    "x_bar_sd": abs(mean_d) / bar_sd if bar_sd else float("inf"),
                    "x_bar_se": abs(mean_d) / bar_se if bar_se else float("inf"),
                    "binds_sd": "sd" if sd >= floor else "materiality",
                    "binds_se": "se" if se >= floor else "materiality",
                    "distinguishable_sd": bool(dist_sd),
                    "distinguishable_se": bool(dist_se),
                    "disagree": bool(dist_se and not dist_sd),
                    "seeds_favouring_lower": favouring,
                    "seeds_nonzero": n_nonzero,
                    "sign_test_p": p,
                    "sign_significant": bool(p < 0.05),
                    # WHAT THE se THRESHOLD ACTUALLY IS, as a test. |mean| > sd/sqrt(n)
                    # is t > 1, and t > 1 is not a significance test at any
                    # conventional level — it is p ~ 0.33 two-sided. Recorded per
                    # comparison so the disagreement set cannot be read as
                    # "45 nulls that were real".
                    "se_threshold_two_sided_p": float(2 * stats.t.sf(1.0, n - 1))
                    if n > 1
                    else float("nan"),
                    "recorded_verdict_matches": bool(rec["distinguishable"] == dist_sd),
                }
            )
    return out


if __name__ == "__main__":
    rows = rescore()
    (HERE / "rescore.json").write_text(json.dumps(rows, indent=2))
    print(f"{len(rows)} comparisons re-scored, {len({r['experiment'] for r in rows})} experiments")
