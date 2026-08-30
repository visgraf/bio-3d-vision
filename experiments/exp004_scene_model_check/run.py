"""exp004 — run the ported loop on the fixture and on a render of the same scene.

Pre-registered in ``preregistration.md``, committed before this file existed.

Needs a Blender binary and the ``blender`` extra. Both halves of every claim it
makes are marked in the output: ``rendered_with`` names the Blender that produced
each arm's stimulus, and ``environment`` the interpreter that ran the loop.
"""

from __future__ import annotations

import json
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import distance_transform_edt

from bio3dvision.blender_load import load_render, render_provenance
from bio3dvision.figure import save_result_fig
from bio3dvision.fixture import make_synthetic_scene
from bio3dvision.loop import ActiveStereo
from bio3dvision.policy import POLICIES
from bio3dvision.scene_model import rasterise_depth, scene_from_fixture, write_scene

# --- declared in the preregistration; not tuned here -------------------------
SEEDS = tuple(range(8))
STEPS = 18
POLICY = "A_prime"
DISCONTINUITY_STEP_PX = 1.0
AT_MAX_PX = 10.0
AWAY_MIN_PX = 24.0
AT_SWEEP = (6.0, 8.0, 10.0, 12.0)
AWAY_SWEEP = (16.0, 20.0, 24.0, 28.0, 32.0)
MATERIALITY = 0.02

REPO = Path(__file__).resolve().parents[2]
RENDERER = REPO / "src" / "bio3dvision" / "blender_render.py"


@dataclass(frozen=True)
class ArmResult:
    depth_est: np.ndarray
    depth_gt: np.ndarray
    valid: np.ndarray
    history: list[dict[str, Any]]
    engine: Any


def discontinuity_distance(depth_step: np.ndarray, params: dict) -> np.ndarray:
    """Euclidean distance to the nearest ground-truth depth discontinuity, in px.

    Computed from the model's STEP depth map, not the fixture's smoothed one: the
    discontinuities are a property of the scene, and smoothing them is a property
    of one source's ground truth.
    """
    d_gt = float(params["f_px"]) * float(params["baseline"]) / depth_step
    edge = np.zeros(d_gt.shape, dtype=bool)
    dx = np.abs(np.diff(d_gt, axis=1)) > DISCONTINUITY_STEP_PX
    dy = np.abs(np.diff(d_gt, axis=0)) > DISCONTINUITY_STEP_PX
    edge[:, :-1] |= dx
    edge[:, 1:] |= dx
    edge[:-1, :] |= dy
    edge[1:, :] |= dy
    return np.asarray(distance_transform_edt(~edge), dtype=float)


def front_end_stats(engine: ActiveStereo, d_true: np.ndarray, mask: np.ndarray) -> dict[str, float]:
    """Matcher quality on ``mask``, before any fixation. **Post-hoc diagnostic.**

    Not pre-registered. Added after the declared metrics came out with the
    rendered source BETTER at discontinuities, which the preregistration did not
    anticipate in either direction it named. This looks underneath the loop at the
    front end alone, so that the divergence is attributed to matching rather than
    to the policy or to the posterior.

    ``gross`` is the fraction of pixels the matcher marks VALID whose disparity is
    wrong by more than 2 px — confidently wrong, as distinct from honestly
    invalid. That distinction is the whole diagnostic.
    """
    valid = np.asarray(engine.valid, dtype=bool) & mask
    if valid.sum() == 0:
        return {
            "n": 0,
            "valid_fraction": float("nan"),
            "median_px": float("nan"),
            "gross_fraction": float("nan"),
        }
    err = np.abs(np.asarray(engine.d_sub, dtype=float) - d_true)
    return {
        "n": int(valid.sum()),
        "valid_fraction": float(valid.sum() / max(int(mask.sum()), 1)),
        "median_px": float(np.median(err[valid])),
        "gross_fraction": float((err[valid] > 2.0).mean()),
    }


def run_arm(
    left: np.ndarray,
    right: np.ndarray,
    params: dict,
    gt: np.ndarray,
    fixations: list[tuple[int, int]] | None = None,
) -> ArmResult:
    """One arm: the ported loop, policy A', STEPS fixations. Nothing varies but the source.

    ``fixations`` forces a scanpath instead of letting the policy choose. That is
    the post-hoc control described in ``findings.md``: it separates a difference
    the SOURCE caused from one the POLICY caused by diverging.
    """
    engine = ActiveStereo(left, right, params, matcher="block")
    policy = POLICIES[POLICY]
    history: list[dict[str, Any]] = []
    for i in range(STEPS):
        choice = fixations[i] if fixations is not None else policy(engine, engine.scanpath)
        info = engine.step(choice)
        # MEASUREMENT ONLY, exactly as ActiveStereo.run does it: read after step
        # has returned and never fed back in. Recorded here because stepping the
        # engine directly skips run()'s bookkeeping, and without it the fourth
        # figure panel is blank — which reads as a broken artifact rather than as
        # a missing key.
        mask = np.isfinite(gt) & engine.valid
        info["rmse"] = float(np.sqrt(np.mean((engine.mean[mask] - gt[mask]) ** 2)))
        history.append(info)
    return ArmResult(
        depth_est=np.asarray(engine.mean, dtype=float),
        depth_gt=np.asarray(gt, dtype=float),
        valid=np.asarray(engine.valid, dtype=bool),
        history=history,
        engine=engine,
    )


def render_seed(seed: int, work: Path, binary: str) -> tuple[np.ndarray, ...]:
    """Write the scene model for ``seed`` and render it. Returns the loaded arrays."""
    scene_dir = work / f"scene_{seed}"
    out_dir = work / f"render_{seed}"
    model = scene_from_fixture(seed=seed)
    write_scene(model, scene_dir)
    result = subprocess.run(
        [
            binary,
            "--background",
            "--factory-startup",
            "--python",
            str(RENDERER),
            "--",
            "--out",
            str(out_dir),
            "--scene",
            str(scene_dir),
            "--samples",
            "1",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
    if result.returncode != 0 or not (out_dir / "depth_left.exr").exists():
        raise RuntimeError(
            f"render failed for seed {seed} (exit {result.returncode})\n"
            f"{result.stdout[-2000:]}\n{result.stderr[-2000:]}"
        )
    left, right, depth, params = load_render(out_dir)
    return left, right, depth, params, out_dir  # type: ignore[return-value]


def stratum_stats(arm: ArmResult, mask: np.ndarray) -> dict[str, float]:
    """Error statistics over ``mask``. Empty masks report nan rather than raising."""
    sel = mask & arm.valid & np.isfinite(arm.depth_gt) & np.isfinite(arm.depth_est)
    if sel.sum() == 0:
        return {"n": 0, "median": float("nan"), "p90": float("nan"), "rmse": float("nan")}
    err = np.abs(arm.depth_est[sel] - arm.depth_gt[sel])
    return {
        "n": int(sel.sum()),
        "median": float(np.median(err)),
        "p90": float(np.percentile(err, 90)),
        "rmse": float(np.sqrt(np.mean(err**2))),
    }


def main() -> None:
    binary = shutil.which("blender")
    if binary is None:
        raise SystemExit(
            "exp004 needs a Blender binary. Falsifier 1 compares a render against "
            "the fixture and cannot be answered without one. Refusing to run a "
            "half of it and report the half as the whole."
        )

    work = Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "results" / "exp004_work"
    work.mkdir(parents=True, exist_ok=True)

    per_seed: list[dict[str, Any]] = []
    provenance: dict[str, Any] = {}

    for seed in SEEDS:
        f_left, f_right, f_gt, f_params = make_synthetic_scene(seed=seed)
        r_left, r_right, r_gt, r_params, out_dir = render_seed(seed, work, binary)
        if not provenance:
            provenance = render_provenance(out_dir)

        model = scene_from_fixture(seed=seed)
        dist = discontinuity_distance(rasterise_depth(model, smooth=False), f_params)

        arms = {
            "F": run_arm(f_left, f_right, f_params, f_gt),
            "R": run_arm(r_left, r_right, r_params, r_gt),
        }
        intersection = arms["F"].valid & arms["R"].valid

        row: dict[str, Any] = {
            "seed": seed,
            "coverage": {
                "F_valid": int(arms["F"].valid.sum()),
                "R_valid": int(arms["R"].valid.sum()),
                "intersection": int(intersection.sum()),
                "F_only": int((arms["F"].valid & ~arms["R"].valid).sum()),
                "R_only": int((arms["R"].valid & ~arms["F"].valid).sum()),
            },
            "strata": {},
            "sweep": {},
            "excluded": {},
            "pooled_CONFOUNDED": {},
        }

        for name, mask in (
            ("AWAY", dist >= AWAY_MIN_PX),
            ("AT", dist <= AT_MAX_PX),
            ("ALL", np.ones_like(dist, dtype=bool)),
        ):
            row["strata"][name] = {
                arm: stratum_stats(arms[arm], mask & intersection) for arm in ("F", "R")
            }
            # Pooled: each arm over its OWN valid set. Confounded by construction.
            row["pooled_CONFOUNDED"][name] = {
                arm: stratum_stats(arms[arm], mask) for arm in ("F", "R")
            }

        # What each arm reaches that the other does not, with its own error.
        row["excluded"] = {
            "F_only": stratum_stats(arms["F"], arms["F"].valid & ~arms["R"].valid),
            "R_only": stratum_stats(arms["R"], arms["R"].valid & ~arms["F"].valid),
        }

        for t in AWAY_SWEEP:
            row["sweep"][f"AWAY_{t:g}"] = {
                arm: stratum_stats(arms[arm], (dist >= t) & intersection) for arm in ("F", "R")
            }
        for t in AT_SWEEP:
            row["sweep"][f"AT_{t:g}"] = {
                arm: stratum_stats(arms[arm], (dist <= t) & intersection) for arm in ("F", "R")
            }

        # POST-HOC CONTROL, labelled. Re-run R on F's scanpath, so the only thing
        # that differs between the arms is the stimulus. Without it, a divergence
        # anywhere is ambiguous between "the render differs" and "the policy
        # diverged because the render differs somewhere else".
        r_forced = run_arm(
            r_left,
            r_right,
            r_params,
            r_gt,
            fixations=[tuple(map(int, h["fixation"])) for h in arms["F"].history],
        )
        forced_inter = arms["F"].valid & r_forced.valid
        row["common_scanpath_CONTROL_POST_HOC"] = {
            name: {
                "F": stratum_stats(arms["F"], mask & forced_inter),
                "R_forced": stratum_stats(r_forced, mask & forced_inter),
            }
            for name, mask in (("AWAY", dist >= AWAY_MIN_PX), ("AT", dist <= AT_MAX_PX))
        }
        row["scanpath_agreement"] = int(
            sum(
                1
                for a, b in zip(
                    [tuple(h["fixation"]) for h in arms["F"].history],
                    [tuple(h["fixation"]) for h in arms["R"].history],
                    strict=True,
                )
                if a == b
            )
        )

        # Post-hoc, labelled: the matcher alone, under the loop.
        d_true = (
            float(f_params["f_px"])
            * float(f_params["baseline"])
            / rasterise_depth(model, smooth=False)
        )
        row["front_end_POST_HOC"] = {
            name: {arm: front_end_stats(arms[arm].engine, d_true, mask) for arm in ("F", "R")}
            for name, mask in (("AWAY", dist >= AWAY_MIN_PX), ("AT", dist <= AT_MAX_PX))
        }

        row["scanpath"] = {
            arm: [list(map(int, f)) for f in arms[arm].history[-1].get("scanpath", [])]
            or [list(map(int, h["fixation"])) for h in arms[arm].history]
            for arm in ("F", "R")
        }
        if seed == 0:
            # CLAUDE.md: every iteration regenerates the same artifact beside the
            # previous one's. Same scene, same seed, both sources side by side, so
            # the comparison is something you can look at and not only read.
            figs = REPO / "results" / "exp004_scene_model_check"
            for arm in ("F", "R"):
                d = figs / f"{arm}_seed0"
                d.mkdir(parents=True, exist_ok=True)
                save_result_fig(arms[arm].engine, arms[arm].depth_gt, arms[arm].history, out=str(d))

        per_seed.append(row)
        print(
            f"seed {seed}: AWAY med F={row['strata']['AWAY']['F']['median']:.5f} "
            f"R={row['strata']['AWAY']['R']['median']:.5f} | "
            f"AT med F={row['strata']['AT']['F']['median']:.5f} "
            f"R={row['strata']['AT']['R']['median']:.5f} | "
            f"cover F={row['coverage']['F_valid']} R={row['coverage']['R_valid']}"
        )

    out = {
        "experiment": "exp004_scene_model_check",
        "policy": POLICY,
        "steps": STEPS,
        "seeds": list(SEEDS),
        "thresholds": {
            "discontinuity_step_px": DISCONTINUITY_STEP_PX,
            "at_max_px": AT_MAX_PX,
            "away_min_px": AWAY_MIN_PX,
            "materiality": MATERIALITY,
        },
        "rendered_with": provenance,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
        },
        "per_seed": per_seed,
    }
    dest = REPO / "results" / "exp004_scene_model_check"
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "results.json").write_text(json.dumps(out, indent=2))
    (Path(__file__).parent / "results.json").write_text(json.dumps(out, indent=2))
    print(f"\nwrote {dest / 'results.json'}")


if __name__ == "__main__":
    main()
