"""Shared fixtures. The Blender one is where this repository's test boundary sits.

``fresh_render`` runs the real renderer if a Blender binary is on PATH, and skips
with a reason if not. The skip is deliberate and is a reported result, not a
silently green test: falsifier 1b cannot be answered without a renderer, and
answering it against a simulated render would be worse than not answering it.
Nothing here fabricates render output.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RENDERER = REPO / "src" / "bio3dvision" / "blender_render.py"

# Fronto-parallel planes, in metres. Chosen to span the fixture's own range and
# to be exactly representable, so the analytic comparison has no rounding excuse.
CARD_DISTANCES = [2.0, 3.0, 4.5]

# The convention calibration render. A SEPARATE scene, and it has to be: the
# tiled scene above holds three depths, and infer_depth_convention is written to
# decline anything that is not a single fronto-parallel surface.
WALL_DISTANCE = 3.0

SKIP_REASON = (
    "no Blender binary on PATH, so falsifier 1b cannot be answered here. This is "
    "a real gap, not a passing test: the loader is still checked against the "
    "shipped Blender 4.x render (falsifier 1a), but nothing checks the current "
    "renderer. Install Blender and re-run."
)


def blender_binary() -> str | None:
    return shutil.which("blender")


def _render(binary: str, out: Path, scene_args: list[str]) -> Path:
    result = subprocess.run(
        [
            binary,
            "--background",
            "--factory-startup",
            "--python",
            str(RENDERER),
            "--",
            "--out",
            str(out),
            *scene_args,
            "--res",
            "320",
            "240",
            "--samples",
            "8",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=900,
    )
    if result.returncode != 0 or not (out / "depth_left.exr").exists():
        pytest.fail(
            "the Blender render failed, which is a result about the renderer and "
            "not a reason to skip.\n"
            f"exit={result.returncode}\n"
            f"files={sorted(p.name for p in out.iterdir())}\n"
            f"--- stdout ---\n{result.stdout[-3000:]}\n"
            f"--- stderr ---\n{result.stderr[-3000:]}"
        )
    return out


@pytest.fixture(scope="session")
def fresh_render(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Planes at known distances, tiled across the frame. For the depth falsifier."""
    binary = blender_binary()
    if binary is None:
        pytest.skip(SKIP_REASON)
    out = _render(
        binary,
        tmp_path_factory.mktemp("render_cards"),
        ["--cards", *[str(z) for z in CARD_DISTANCES]],
    )
    (out / "cards.json").write_text(json.dumps(CARD_DISTANCES))
    return out


@pytest.fixture(scope="session")
def fresh_wall_render(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A single flat wall. The only input the convention guard will answer on."""
    binary = blender_binary()
    if binary is None:
        pytest.skip(SKIP_REASON)
    out = _render(binary, tmp_path_factory.mktemp("render_wall"), ["--wall", str(WALL_DISTANCE)])
    (out / "wall.json").write_text(json.dumps({"distance": WALL_DISTANCE}))
    return out
