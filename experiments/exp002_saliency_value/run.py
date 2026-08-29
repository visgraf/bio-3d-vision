"""exp002 — does posterior variance carry information beyond the validity mask?

Runs six arms over the pre-registered seeds and budget. Declarations live in
``experiments/exp002_saliency_value/preregistration.md``; nothing here chooses a
threshold, a seed count, a pitch or a budget.

    python -m experiments.exp002_saliency_value.run
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import numpy as np

from bio3dvision.figure import save_result_fig
from bio3dvision.fixture import make_synthetic_scene
from bio3dvision.loop import ActiveStereo
from bio3dvision.policy import POLICIES, RASTER_PITCH

# --- pre-registered constants (see preregistration.md) -----------------------
SEEDS = tuple(range(16))  # superset of exp001's 0-7, those eight as a prefix
BUDGET = 40  # exp001 used 18; step 18 is retained for the C-vs-B re-check
ARMS = ("A", "A_prime", "B", "C", "D", "E")
EXP001_ENDPOINT = 18
OUT = pathlib.Path("results/exp002_saliency_value")


def metrics(engine: ActiveStereo, depth_gt: np.ndarray) -> dict[str, float]:
    """Primary: median |err| and p90. Secondary: RMSE. Over valid known pixels."""
    m = np.isfinite(depth_gt) & engine.valid
    err = np.abs(engine.mean[m] - depth_gt[m]).astype(np.float64)
    return {
        "median_abs_err": float(np.median(err)),
        "p90": float(np.percentile(err, 90)),
        "rmse": float(np.sqrt(np.mean(err**2))),
    }


def run_arm(arm: str, seed: int, budget: int = BUDGET) -> dict[str, Any]:
    """One arm, one seed. Records the full per-step trajectory."""
    left, right, depth_gt, params = make_synthetic_scene(seed=seed)
    engine = ActiveStereo(left, right, params, matcher="block")
    policy = POLICIES[arm]

    traj: list[dict[str, float]] = []
    terminated_at: int | None = None
    for step in range(budget):
        choice = policy(engine, engine.scanpath)
        if choice is None:
            terminated_at = step  # the predecessor's contract: stop, do not spin
            break
        engine.step(fixation=choice)
        traj.append(metrics(engine, depth_gt))

    return {
        "arm": arm,
        "seed": seed,
        "scanpath": [list(p) for p in engine.scanpath],
        "distinct_fixations": len(set(engine.scanpath)),
        "fixations_on_invalid": int(sum(1 for p in engine.scanpath if not engine.valid[p])),
        "steps_taken": len(traj),
        "terminated_at": terminated_at,
        "trajectory": traj,
        "final": traj[-1] if traj else None,
        "at_exp001_endpoint": traj[EXP001_ENDPOINT - 1] if len(traj) >= EXP001_ENDPOINT else None,
        "_engine": engine,
        "_depth_gt": depth_gt,
        "_history": [{"rmse": t["rmse"]} for t in traj],
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {
        "seeds": list(SEEDS),
        "budget": BUDGET,
        "raster_pitch": RASTER_PITCH,
        "exp001_endpoint": EXP001_ENDPOINT,
        "arms": {},
    }
    for arm in ARMS:
        runs = []
        for seed in SEEDS:
            r = run_arm(arm, seed)
            if seed == 0:
                d = OUT / f"{arm}_seed0"
                d.mkdir(parents=True, exist_ok=True)
                save_result_fig(r["_engine"], r["_depth_gt"], r["_history"], out=str(d))
            for k in ("_engine", "_depth_gt", "_history"):
                r.pop(k)
            runs.append(r)
            f = r["final"]
            print(
                f"  {arm:8s} seed {seed:2d}: median {f['median_abs_err']:.5f} "
                f"p90 {f['p90']:.4f} rmse {f['rmse']:.4f} "
                f"distinct {r['distinct_fixations']:2d}/{r['steps_taken']} "
                f"onInvalid {r['fixations_on_invalid']:2d}",
                flush=True,
            )
        results["arms"][arm] = runs

    (OUT / "results.json").write_text(json.dumps(results, indent=1))
    print(f"\nwrote {OUT / 'results.json'}")


if __name__ == "__main__":
    main()
