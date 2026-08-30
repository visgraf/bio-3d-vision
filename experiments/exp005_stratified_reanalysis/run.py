"""exp005 — re-run exp001 and exp002, scoring each band separately.

Pre-registered in ``preregistration.md``, committed before this file existed.

A RE-ANALYSIS. Arms, seeds, budgets and the loop are the originals'; the only
change is that :func:`metrics_by_band` scores four pixel sets instead of one. The
run loop below is deliberately the same shape as
``exp002_saliency_value/run.py::run_arm``, including its ``terminated_at``
contract, so that a difference in results cannot come from a difference in
harness.

Needs no Blender: the band definition comes from the scene model's geometry,
which is arithmetic, not a render.
"""

from __future__ import annotations

import json
import pathlib
import platform
import sys
import time
from typing import Any

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

from bio3dvision.fixture import make_synthetic_scene
from bio3dvision.loop import ActiveStereo
from bio3dvision.policy import (
    CANDIDATE_STRIDE,
    INHIBITION_RADIUS,
    POLICIES,
    SALIENCY_SIGMA,
    _inhibit,
    candidate_grid,
    delta_single,
    delta_total,
)
from bio3dvision.scene_model import rasterise_depth, scene_from_fixture

# --- inherited from exp004 unchanged, not re-derived -------------------------
DISCONTINUITY_STEP_PX = 1.0
AT_MAX_PX = 10.0
AWAY_MIN_PX = 24.0

# --- matching the originals exactly ------------------------------------------
EXP001 = {"arms": ("A", "A_prime", "B", "C"), "seeds": tuple(range(8)), "budget": 18}
EXP002 = {"arms": ("A_prime", "C", "D", "E"), "seeds": tuple(range(16)), "budget": 40}
CONTROL_ARMS = ("A", "A_prime", "B", "C")  # the variance-driven ones

REPO = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).parent


def band_masks() -> dict[str, np.ndarray]:
    """The three bands plus POOLED, from the scene model's step-edge geometry.

    Identical for every seed: the fixture varies its TEXTURE with the seed, not
    its geometry, so the discontinuity set is a property of the scene alone. The
    step depth map is used rather than the fixture's smoothed one for the same
    reason exp004 used it — the discontinuities are in the scene, the smoothing is
    in one source's ground truth.
    """
    model = scene_from_fixture(seed=0)
    params = model.params
    d_gt = float(params["f_px"]) * float(params["baseline"]) / rasterise_depth(model, smooth=False)
    edge = np.zeros(d_gt.shape, dtype=bool)
    dx = np.abs(np.diff(d_gt, axis=1)) > DISCONTINUITY_STEP_PX
    dy = np.abs(np.diff(d_gt, axis=0)) > DISCONTINUITY_STEP_PX
    edge[:, :-1] |= dx
    edge[:, 1:] |= dx
    edge[:-1, :] |= dy
    edge[1:, :] |= dy
    dist = np.asarray(distance_transform_edt(~edge), dtype=float)
    return {
        "AT": dist <= AT_MAX_PX,
        "MIDDLE": (dist > AT_MAX_PX) & (dist < AWAY_MIN_PX),
        "AWAY": dist >= AWAY_MIN_PX,
        "POOLED": np.ones_like(dist, dtype=bool),
    }


def metrics_by_band(
    engine: ActiveStereo, depth_gt: np.ndarray, bands: dict[str, np.ndarray]
) -> dict[str, dict[str, float]]:
    """The originals' three metrics, computed over each band.

    ``POOLED`` is bit-for-bit what exp001 and exp002 computed — the whole valid
    known mask — so the re-analysis reproduces the original numbers as one of its
    own outputs rather than citing them.
    """
    known = np.isfinite(depth_gt) & engine.valid
    out: dict[str, dict[str, float]] = {}
    for name, band in bands.items():
        m = known & band
        if m.sum() == 0:
            out[name] = {
                "n": 0,
                "median_abs_err": float("nan"),
                "p90": float("nan"),
                "rmse": float("nan"),
            }
            continue
        err = np.abs(engine.mean[m] - depth_gt[m]).astype(np.float64)
        out[name] = {
            "n": int(m.sum()),
            "median_abs_err": float(np.median(err)),
            "p90": float(np.percentile(err, 90)),
            "rmse": float(np.sqrt(np.mean(err**2))),
        }
    return out


# --- masked-selection variants, for the post-hoc steering control ------------
#
# These mirror policy.py's four variance-driven arms with the SELECTION domain
# restricted to a mask. They do NOT restrict the objective: delta_single and
# delta_total still integrate over the whole field, because the control asks
# where the policy may LOOK, not what it may VALUE.
#
# tests/test_exp005_masked_policies.py pins that with an all-True mask each of
# these reproduces the unmasked policy's choice exactly, which is what stops them
# drifting from the arms they stand in for.


def masked_policy_a(engine: Any, visited: list, mask: np.ndarray) -> tuple[int, int] | None:
    del visited
    v = gaussian_filter(np.where(engine.valid, engine.var, 0.0), SALIENCY_SIGMA)
    score = np.where(engine.valid & mask, v, -np.inf)
    if not np.isfinite(score).any():
        return None
    yf, xf = np.unravel_index(int(np.argmax(score)), score.shape)
    return int(yf), int(xf)


def masked_policy_a_prime(engine: Any, visited: list, mask: np.ndarray) -> tuple[int, int] | None:
    v = gaussian_filter(np.where(engine.valid, engine.var, 0.0), SALIENCY_SIGMA)
    score = np.where(engine.valid & mask, v, np.nan).astype(np.float64)
    _inhibit(score, visited, INHIBITION_RADIUS)
    if not np.isfinite(score).any():
        return None
    yf, xf = np.unravel_index(int(np.nanargmax(score)), score.shape)
    return int(yf), int(xf)


def _masked_grid(engine: Any, mask: np.ndarray) -> list[tuple[int, int]]:
    return [(y, x) for y, x in candidate_grid(engine, CANDIDATE_STRIDE) if mask[y, x]]


def masked_policy_b(engine: Any, visited: list, mask: np.ndarray) -> tuple[int, int] | None:
    del visited
    cands = _masked_grid(engine, mask)
    if not cands:
        return None
    scores = np.array([delta_single(engine, y, x) for y, x in cands])
    return cands[int(np.argmax(scores))]


def masked_policy_c(engine: Any, visited: list, mask: np.ndarray) -> tuple[int, int] | None:
    del visited
    cands = _masked_grid(engine, mask)
    if not cands:
        return None
    scores = np.array([delta_total(engine, y, x) for y, x in cands])
    return cands[int(np.argmax(scores))]


MASKED = {
    "A": masked_policy_a,
    "A_prime": masked_policy_a_prime,
    "B": masked_policy_b,
    "C": masked_policy_c,
}


def run_arm(
    arm: str,
    seed: int,
    budget: int,
    bands: dict[str, np.ndarray],
    selection_mask: np.ndarray | None = None,
) -> dict[str, Any]:
    """One arm, one seed. Same loop and same ``terminated_at`` contract as exp002."""
    left, right, depth_gt, params = make_synthetic_scene(seed=seed)
    engine = ActiveStereo(left, right, params, matcher="block")
    policy = POLICIES[arm] if selection_mask is None else MASKED[arm]

    terminated_at: int | None = None
    steps = 0
    for step in range(budget):
        choice = (
            policy(engine, engine.scanpath)
            if selection_mask is None
            else policy(engine, engine.scanpath, selection_mask)
        )
        if choice is None:
            terminated_at = step  # the predecessor's contract: stop, do not spin
            break
        engine.step(fixation=choice)
        steps += 1

    return {
        "arm": arm,
        "seed": seed,
        "steps_taken": steps,
        "terminated_at": terminated_at,
        "distinct_fixations": len(set(engine.scanpath)),
        "scanpath": [list(map(int, p)) for p in engine.scanpath],
        "final": metrics_by_band(engine, depth_gt, bands),
    }


def run_block(config: dict, bands: dict[str, np.ndarray], label: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for arm in config["arms"]:
        t0 = time.time()
        for seed in config["seeds"]:
            rows.append(run_arm(arm, seed, config["budget"], bands))
        print(f"  [{label}] {arm:8s} {len(config['seeds'])} seeds in {time.time() - t0:6.1f}s")
    return rows


def main() -> None:
    bands = band_masks()
    print("band sizes (whole frame):", {k: int(v.sum()) for k, v in bands.items()})

    out: dict[str, Any] = {
        "experiment": "exp005_stratified_reanalysis",
        "bands": {
            "discontinuity_step_px": DISCONTINUITY_STEP_PX,
            "at_max_px": AT_MAX_PX,
            "away_min_px": AWAY_MIN_PX,
            "inherited_from": "exp004, unchanged",
        },
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "exp001": {**{k: list(v) if isinstance(v, tuple) else v for k, v in EXP001.items()}},
        "exp002": {**{k: list(v) if isinstance(v, tuple) else v for k, v in EXP002.items()}},
    }

    print("exp001 re-analysis (8 seeds, 18 steps)")
    out["exp001"]["rows"] = run_block(EXP001, bands, "exp001")

    print("exp002 re-analysis (16 seeds, 40 steps)")
    out["exp002"]["rows"] = run_block(EXP002, bands, "exp002")

    print("POST-HOC steering control: selection masked to AWAY")
    control: dict[str, Any] = {}
    for label, config in (("exp001", EXP001), ("exp002", EXP002)):
        rows = []
        for arm in CONTROL_ARMS:
            if arm not in config["arms"]:
                continue
            t0 = time.time()
            for seed in config["seeds"]:
                rows.append(
                    run_arm(arm, seed, config["budget"], bands, selection_mask=bands["AWAY"])
                )
            print(f"  [{label} masked] {arm:8s} in {time.time() - t0:6.1f}s")
        control[label] = rows
    out["control_masked_steering_POST_HOC"] = control

    dest = REPO / "results" / "exp005_stratified_reanalysis"
    dest.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, indent=2)
    (dest / "results.json").write_text(text)
    (HERE / "results.json").write_text(text)
    print(f"\nwrote {dest / 'results.json'}")


if __name__ == "__main__":
    sys.exit(main())
