"""exp003 — does acquisition buy anything, and does the gain require acting?

Three arms over the pre-registered seeds and budget. Declarations live in
``preregistration.md``; nothing here chooses a threshold, a width or a budget.

    python -m experiments.exp003_vergence_acquisition.run
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import numpy as np

from bio3dvision.acquisition import PANUM_HALF_WIDTH_PX, Window, reacquire, window_around
from bio3dvision.figure import save_result_fig
from bio3dvision.fixture import make_synthetic_scene
from bio3dvision.loop import ActiveStereo
from bio3dvision.policy import POLICIES

# --- pre-registered constants ------------------------------------------------
SEEDS = tuple(range(16))
BUDGET = 18
POLICY = "A_prime"  # fixed across arms; the arms vary the window, not the policy
ARMS = ("W", "N", "V")
OUT = pathlib.Path("results/exp003_vergence_acquisition")


def run_arm(arm: str, seed: int, budget: int = BUDGET) -> dict[str, Any]:
    """One arm, one seed.

    All arms construct wide, because a first ``d_fix`` needs some measurement to
    exist. N and V both re-centre at fixation 1 and are identical there; N then
    stops and V continues, which makes N-vs-V a controlled test of *continuing*
    to verge.
    """
    left, right, depth_gt, params = make_synthetic_scene(seed=seed)
    engine = ActiveStereo(left, right, params, matcher="block")
    policy = POLICIES[POLICY]

    hypotheses = Window(0, 56).hypotheses  # the construction acquisition
    ever_valid = np.zeros_like(engine.valid)
    traj: list[dict[str, float]] = []
    windows: list[list[int]] = []
    d_fixes: list[float] = []

    for step in range(budget):
        choice = policy(engine, engine.scanpath)
        if choice is None:
            break
        # The vergence this fixation commands, read from whatever is currently
        # measured. Never from ground truth.
        d_fix = engine.vergence(*choice)
        d_fixes.append(d_fix)

        if arm == "V" or (arm == "N" and step == 0):
            w = window_around(d_fix, PANUM_HALF_WIDTH_PX)
            hypotheses += reacquire(engine, left, right, w)
            windows.append([w.dmin, w.dmax])
        elif windows:
            windows.append(windows[-1])
        else:
            windows.append([0, 56])

        ever_valid |= engine.valid
        engine.step(fixation=choice)
        m = np.isfinite(depth_gt) & engine.valid
        err = np.abs(engine.mean[m] - depth_gt[m]).astype(np.float64)
        traj.append(
            {
                "median_abs_err": float(np.median(err)),
                "p90": float(np.percentile(err, 90)),
                "rmse": float(np.sqrt(np.mean(err**2))),
            }
        )

    return {
        "arm": arm,
        "seed": seed,
        "hypotheses": int(hypotheses),
        "front_end_calls": 1 + sum(1 for i, w in enumerate(windows) if arm == "V" or i == 0)
        if arm != "W"
        else 1,
        "distinct_windows": len({tuple(w) for w in windows}),
        "windows": windows,
        "d_fix": d_fixes,
        "scanpath": [list(p) for p in engine.scanpath],
        "valid_final": int(engine.valid.sum()),
        "valid_union": int(ever_valid.sum()),
        "trajectory": traj,
        "_mean": engine.mean,
        "_ever_valid": ever_valid,
        "_depth_gt": depth_gt,
        "_engine": engine,
        "_history": [{"rmse": t["rmse"]} for t in traj],
    }


def error_stats(mean: np.ndarray, depth_gt: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    if not mask.any():
        return {"n": 0, "median_abs_err": float("nan"), "p90": float("nan"), "rmse": float("nan")}
    err = np.abs(mean[mask] - depth_gt[mask]).astype(np.float64)
    return {
        "n": int(mask.sum()),
        "median_abs_err": float(np.median(err)),
        "p90": float(np.percentile(err, 90)),
        "rmse": float(np.sqrt(np.mean(err**2))),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {
        "seeds": list(SEEDS),
        "budget": BUDGET,
        "policy": POLICY,
        "half_width_px": PANUM_HALF_WIDTH_PX,
        "per_seed": [],
    }

    for seed in SEEDS:
        runs = {arm: run_arm(arm, seed) for arm in ARMS}
        gt = runs["W"]["_depth_gt"]
        known = np.isfinite(gt)
        # THE COVERAGE RULE: intersection isolates quality, excluded says what
        # coverage was bought, pooled is confounded and labelled as such.
        inter = known.copy()
        for arm in ARMS:
            inter &= runs[arm]["_ever_valid"]

        row: dict[str, Any] = {"seed": seed, "intersection_n": int(inter.sum()), "arms": {}}
        for arm in ARMS:
            r = runs[arm]
            own = known & r["_ever_valid"]
            excluded = own & ~inter
            row["arms"][arm] = {
                "intersection": error_stats(r["_mean"], gt, inter),
                "excluded": error_stats(r["_mean"], gt, excluded),
                "pooled_CONFOUNDED": error_stats(r["_mean"], gt, own),
                "hypotheses": r["hypotheses"],
                "distinct_windows": r["distinct_windows"],
                "valid_union": r["valid_union"],
                "valid_final": r["valid_final"],
                "d_fix": r["d_fix"],
                "windows": r["windows"],
                "trajectory": r["trajectory"],
                "scanpath": r["scanpath"],
            }
            if seed == 0:
                d = OUT / f"{arm}_seed0"
                d.mkdir(parents=True, exist_ok=True)
                save_result_fig(r["_engine"], r["_depth_gt"], r["_history"], out=str(d))
        results["per_seed"].append(row)

        w, n, v = (row["arms"][a] for a in ARMS)
        print(
            f"  seed {seed:2d} inter n={row['intersection_n']:6d} | "
            f"W med {w['intersection']['median_abs_err']:.5f} "
            f"N med {n['intersection']['median_abs_err']:.5f} "
            f"V med {v['intersection']['median_abs_err']:.5f} | "
            f"union W {w['valid_union']} N {n['valid_union']} V {v['valid_union']} | "
            f"hyp {w['hypotheses']}/{n['hypotheses']}/{v['hypotheses']} | "
            f"V windows {v['distinct_windows']}",
            flush=True,
        )

    (OUT / "results.json").write_text(json.dumps(results, indent=1))
    print(f"\nwrote {OUT / 'results.json'}")


if __name__ == "__main__":
    main()
