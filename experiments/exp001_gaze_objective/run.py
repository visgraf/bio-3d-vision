"""exp001 — does the gaze objective matter, once revisiting is controlled for?

Runs the four pre-registered arms. Reads
``experiments/exp001_gaze_objective/preregistration.md`` for the declarations;
nothing here chooses a threshold, a seed count or a radius.

    python -m experiments.exp001_gaze_objective.run
"""

from __future__ import annotations

import json
import pathlib
from typing import Any

import numpy as np
from scipy.stats import spearmanr

from bio3dvision.figure import save_result_fig
from bio3dvision.fixture import make_synthetic_scene
from bio3dvision.loop import ActiveStereo
from bio3dvision.policy import (
    CANDIDATE_STRIDE,
    candidate_grid,
    delta_single,
    delta_total,
    policy_a,
    policy_a_prime,
    policy_b,
    policy_c,
)

# --- pre-registered constants (see preregistration.md) -----------------------
SEEDS = tuple(range(8))
BUDGET = 18
ARMS = {"A": policy_a, "A_prime": policy_a_prime, "B": policy_b, "C": policy_c}
OUT = pathlib.Path("results/exp001_gaze_objective")


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
    """One arm, one seed. Records the trajectory and the wasted-budget fraction."""
    left, right, depth_gt, params = make_synthetic_scene(seed=seed)
    engine = ActiveStereo(left, right, params, matcher="block")
    policy = ARMS[arm]
    grid = candidate_grid(engine, CANDIDATE_STRIDE)

    traj: list[dict[str, float]] = []
    below_median = 0
    terminated_at: int | None = None

    for step in range(budget):
        # Wasted-budget metric: is the chosen candidate below the median expected
        # reduction available at this state? Computed for every arm, so all arms
        # are scored on the same quantity regardless of what they maximise. C
        # reuses this pass rather than recomputing it.
        grid_delta = np.array([delta_total(engine, y, x) for y, x in grid])
        choice = (
            policy(engine, engine.scanpath, scores=grid_delta)
            if arm == "C"
            else policy(engine, engine.scanpath)
        )
        if choice is None:
            # The predecessor's contract: terminate rather than spin.
            terminated_at = step
            break
        if delta_total(engine, *choice) < float(np.median(grid_delta)):
            below_median += 1
        engine.step(fixation=choice)
        traj.append(metrics(engine, depth_gt))

    steps_taken = len(traj)
    return {
        "arm": arm,
        "seed": seed,
        "scanpath": [list(p) for p in engine.scanpath],
        "distinct_fixations": len(set(engine.scanpath)),
        "steps_taken": steps_taken,
        "terminated_at": terminated_at,
        "trajectory": traj,
        "final": traj[-1] if traj else None,
        "wasted_budget_fraction": below_median / steps_taken if steps_taken else float("nan"),
        "_engine": engine,
        "_depth_gt": depth_gt,
        "_history": [{"rmse": t["rmse"]} for t in traj],
    }


def agreement_probe(seed: int, budget: int = BUDGET) -> dict[str, Any]:
    """Do A and C pick the same candidate *from the same state*?

    Driven along A's trajectory so the state is held fixed and only the objective
    varies. Comparing two independently-run trajectories would measure divergence,
    which is a different question and is reported separately.

    A's score is restricted to C's candidate grid so the two argmaxes are taken
    over the same set.
    """
    from scipy.ndimage import gaussian_filter

    from bio3dvision.policy import SALIENCY_SIGMA

    left, right, depth_gt, params = make_synthetic_scene(seed=seed)
    engine = ActiveStereo(left, right, params, matcher="block")
    grid = candidate_grid(engine, CANDIDATE_STRIDE)

    agree, rhos = [], []
    for _ in range(budget):
        blurred = gaussian_filter(np.where(engine.valid, engine.var, 0.0), SALIENCY_SIGMA)
        score_a = np.array([float(blurred[y, x]) for y, x in grid])
        score_c = np.array([delta_total(engine, y, x) for y, x in grid])
        agree.append(grid[int(np.argmax(score_a))] == grid[int(np.argmax(score_c))])
        rhos.append(float(spearmanr(score_a, score_c).statistic))
        engine.step(fixation=grid[int(np.argmax(score_a))])

    return {
        "seed": seed,
        "argmax_agreement_rate": float(np.mean(agree)),
        "agreement_per_step": [bool(a) for a in agree],
        "spearman_mean": float(np.mean(rhos)),
        "spearman_per_step": rhos,
    }


def stride_check(seed: int = 0) -> dict[str, Any]:
    """Declared check: halving the stride must not move the step-1 selection."""
    left, right, _, params = make_synthetic_scene(seed=seed)
    engine = ActiveStereo(left, right, params, matcher="block")
    out = {}
    for stride in (CANDIDATE_STRIDE, CANDIDATE_STRIDE // 2):
        grid = candidate_grid(engine, stride)
        scores = [delta_total(engine, y, x) for y, x in grid]
        out[f"stride_{stride}"] = {
            "n_candidates": len(grid),
            "selected": list(grid[int(np.argmax(scores))]),
        }
    out["unchanged"] = (
        out[f"stride_{CANDIDATE_STRIDE}"]["selected"]
        == out[f"stride_{CANDIDATE_STRIDE // 2}"]["selected"]
    )
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    results: dict[str, Any] = {
        "seeds": list(SEEDS),
        "budget": BUDGET,
        "stride": CANDIDATE_STRIDE,
        "stride_check": stride_check(),
        "arms": {},
        "agreement": [],
    }
    print(f"stride check: {results['stride_check']}")

    for arm in ARMS:
        runs = []
        for seed in SEEDS:
            r = run_arm(arm, seed)
            if seed == 0:
                # Same scene, same seed, beside the baseline's rather than over it.
                d = OUT / f"{arm}_seed0"
                d.mkdir(parents=True, exist_ok=True)
                save_result_fig(r["_engine"], r["_depth_gt"], r["_history"], out=str(d))
            for k in ("_engine", "_depth_gt", "_history"):
                r.pop(k)
            runs.append(r)
            f = r["final"]
            print(
                f"  {arm:8s} seed {seed}: median {f['median_abs_err']:.5f} "
                f"p90 {f['p90']:.4f} rmse {f['rmse']:.4f} "
                f"distinct {r['distinct_fixations']:2d}/{r['steps_taken']} "
                f"wasted {r['wasted_budget_fraction']:.2f}"
            )
        results["arms"][arm] = runs

    for seed in SEEDS:
        results["agreement"].append(agreement_probe(seed))
        a = results["agreement"][-1]
        print(
            f"  agreement seed {seed}: argmax {a['argmax_agreement_rate']:.3f} "
            f"spearman {a['spearman_mean']:+.3f}"
        )

    (OUT / "results.json").write_text(json.dumps(results, indent=1))
    print(f"\nwrote {OUT / 'results.json'}")


if __name__ == "__main__":
    main()


def agreement_probe_bc(seed: int, budget: int = BUDGET) -> dict[str, Any]:
    """Do B and C pick the same candidate from the same state?

    Falsifier 2 asks whether the cheap approximation lands on a *different arm of
    the argmax*, which the trajectory metrics cannot answer. Driven along C's
    trajectory so the state is held fixed and only the objective varies.
    """
    left, right, _, params = make_synthetic_scene(seed=seed)
    engine = ActiveStereo(left, right, params, matcher="block")
    grid = candidate_grid(engine, CANDIDATE_STRIDE)

    agree, rhos, dists = [], [], []
    for _ in range(budget):
        s_c = np.array([delta_total(engine, y, x) for y, x in grid])
        s_b = np.array([delta_single(engine, y, x) for y, x in grid])
        pick_c = grid[int(np.argmax(s_c))]
        pick_b = grid[int(np.argmax(s_b))]
        agree.append(pick_b == pick_c)
        dists.append(float(np.hypot(pick_b[0] - pick_c[0], pick_b[1] - pick_c[1])))
        rhos.append(float(spearmanr(s_b, s_c).statistic))
        engine.step(fixation=pick_c)

    return {
        "seed": seed,
        "argmax_agreement_rate": float(np.mean(agree)),
        "median_argmax_distance_px": float(np.median(dists)),
        "spearman_mean": float(np.mean(rhos)),
    }


def main_bc() -> None:
    path = OUT / "results.json"
    res = json.loads(path.read_text())
    res["agreement_bc"] = [agreement_probe_bc(s) for s in SEEDS]
    for a in res["agreement_bc"]:
        print(
            f"  B-vs-C seed {a['seed']}: argmax {a['argmax_agreement_rate']:.3f}  "
            f"median dist {a['median_argmax_distance_px']:6.1f} px  "
            f"spearman {a['spearman_mean']:+.3f}"
        )
    path.write_text(json.dumps(res, indent=1))
    print("updated results.json")
