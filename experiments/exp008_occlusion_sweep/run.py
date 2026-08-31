"""exp008 — sweep occlusion fraction and measure how the allocation effect moves.

Pre-registered in ``preregistration.md``, committed before this file existed.

The rule that shapes this file: **compare arms WITHIN a level, compare effect
sizes ACROSS levels.** No pixel set is ever taken across levels — coverage falls
as overlap grows, so a cross-level intersection would shrink toward the
least-occluded scene and the sweep would measure its own masking. Bands are
likewise recomputed per level, from that level's own geometry.

Needs a Blender binary and the ``blender`` extra.
"""

from __future__ import annotations

import json
import pathlib
import platform
import shutil
import subprocess
import sys
import time
from typing import Any

import numpy as np
from scipy.ndimage import distance_transform_edt

from bio3dvision.blender_load import load_render, render_provenance
from bio3dvision.loop import ActiveStereo
from bio3dvision.policy import POLICIES
from bio3dvision.scene_model import (
    SceneModel,
    occlusion_fractions,
    rasterise_depth,
    scene_from_fixture,
    split_cards,
    write_scene,
)

# --- inherited from exp004, unchanged ----------------------------------------
DISCONTINUITY_STEP_PX = 1.0
AT_MAX_PX = 10.0
AWAY_MIN_PX = 24.0

# --- declared in the preregistration -----------------------------------------
LEVELS = (1, 2, 4, 8)  # k=10 measured and rejected: occlusion turns over
SEEDS = tuple(range(8))
BUDGET = 40  # exp002's and exp007's; never shortened, see the starved-lattice finding
ARMS = ("A_prime", "D", "E")

REPO = pathlib.Path(__file__).resolve().parents[2]
HERE = pathlib.Path(__file__).parent
RENDERER = REPO / "src" / "bio3dvision" / "blender_render.py"


def band_masks(model: SceneModel) -> dict[str, np.ndarray]:
    """Bands from THIS level's geometry, since the geometry is what changed.

    As overlap grows the AT band grows with it. That composition change is a
    property of the level and is reported, not folded away.
    """
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


def render_level(model: SceneModel, k: int, seed: int, work: pathlib.Path, binary: str):
    out_dir = work / f"k{k}_seed{seed}"
    if not (out_dir / "depth_left.exr").exists():
        scene_dir = work / f"scene_k{k}_seed{seed}"
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
            raise RuntimeError(f"render failed k={k} seed={seed}\n{result.stderr[-2000:]}")
    return load_render(out_dir), out_dir


def metrics_by_band(engine, depth_gt, bands, restrict) -> dict[str, dict[str, float]]:
    known = np.isfinite(depth_gt) & engine.valid & restrict
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


def run_arm(arm: str, left, right, params) -> ActiveStereo:
    engine = ActiveStereo(left, right, params, matcher="block")
    policy = POLICIES[arm]
    for _ in range(BUDGET):
        choice = policy(engine, engine.scanpath)
        if choice is None:
            break
        engine.step(fixation=choice)
    return engine


def main() -> None:
    binary = shutil.which("blender")
    if binary is None:
        raise SystemExit(
            "exp008 needs a Blender binary: the sweep varies rendered geometry. "
            "Refusing to report a sweep that was not rendered."
        )
    work = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else REPO / "results" / "exp008_work"
    work.mkdir(parents=True, exist_ok=True)

    out: dict[str, Any] = {
        "experiment": "exp008_occlusion_sweep",
        "levels_k": list(LEVELS),
        "seeds": list(SEEDS),
        "budget": BUDGET,
        "arms": list(ARMS),
        "bands": {
            "at_max_px": AT_MAX_PX,
            "away_min_px": AWAY_MIN_PX,
            "discontinuity_step_px": DISCONTINUITY_STEP_PX,
            "inherited_from": "exp004, unchanged; recomputed per level",
        },
        "environment": {"python": platform.python_version(), "numpy": np.__version__},
        "geometry": {},
        "rows": [],
    }

    for k in LEVELS:
        model0 = split_cards(scene_from_fixture(seed=0), k)
        frac = occlusion_fractions(model0)
        bands = band_masks(model0)
        frac["band_composition"] = {b: int(m.sum()) for b, m in bands.items()}
        out["geometry"][f"k{k}"] = frac
        print(
            f"k={k}: left {frac['left_occluded_fraction'] * 100:.2f}%  "
            f"right {frac['right_unmatched_fraction'] * 100:.2f}%  "
            f"border {frac['border_fraction'] * 100:.2f}%  "
            f"card area {frac['card_area_fraction'] * 100:.1f}%  "
            f"AT band {frac['band_composition']['AT']}"
        )

        t0 = time.time()
        for seed in SEEDS:
            model = split_cards(scene_from_fixture(seed=seed), k)
            (left, right, depth_gt, params), out_dir = render_level(model, k, seed, work, binary)
            engines = {arm: run_arm(arm, left, right, params) for arm in ARMS}
            # exp003's rule, WITHIN this level only.
            inter = np.ones_like(engines[ARMS[0]].valid)
            for e in engines.values():
                inter = inter & e.valid
            for arm, engine in engines.items():
                out["rows"].append(
                    {
                        "k": k,
                        "arm": arm,
                        "seed": seed,
                        "valid": int(engine.valid.sum()),
                        "intersection": int(inter.sum()),
                        "distinct_fixations": len(set(engine.scanpath)),
                        "final": metrics_by_band(engine, depth_gt, bands, inter),
                    }
                )
            if seed == 0:
                out.setdefault("provenance_dir", str(out_dir))
        print(f"    {len(SEEDS)} seeds x {len(ARMS)} arms in {time.time() - t0:.1f}s")

    out["rendered_with"] = render_provenance(pathlib.Path(out["provenance_dir"]))
    dest = REPO / "results" / "exp008_occlusion_sweep"
    dest.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out, indent=2)
    (dest / "results.json").write_text(text)
    (HERE / "results.json").write_text(text)
    print(f"\nwrote {dest / 'results.json'}")


if __name__ == "__main__":
    main()
