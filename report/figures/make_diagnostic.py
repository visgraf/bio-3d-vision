"""Figure 3 — the four-panel diagnostic, fixture beside render of the same geometry.

WHAT IT DRAWS
-------------
exp004's comparison, at seed 0: the ported loop under policy A' for 18 fixations,
run twice on the SAME geometry from two sources -- the analytic fixture (F), whose
right image is resampled from its left, and a Blender render (R), where occluded
pixels genuinely have no correspondent. Four panels per source: posterior mean
depth with the scanpath, posterior standard deviation, absolute error against
ground truth, and depth RMSE against fixation number.

REGENERATED, NOT READ, BECAUSE THE ARRAYS WERE NEVER STORED
-----------------------------------------------------------
``experiments/exp004_scene_model_check/results.json`` records band statistics and
both scanpaths but no 2-D arrays, so the panels cannot be read off the record and
are rebuilt from committed code at the pinned seed -- the same route
``make_scanpath.py`` takes. The rebuild reuses exp004's OWN ``run_arm`` and
``render_seed`` rather than a copy of them, so the arms cannot drift from the
experiment.

**This figure needs a Blender binary** (5.2.0 LTS, matching exp004's
``rendered_with``). Without one it raises rather than substituting anything: a
four-panel comparison with a fabricated right-hand column would be worse than no
figure. The render is Cycles at 1 sample, 320x240, and takes a second or two.

THE GUARD
---------
Both regenerated scanpaths are asserted against the ones exp004 recorded --
18 fixations each, exact -- before anything is drawn. That is a sharp check: the
scanpath is the whole trajectory of the policy through the belief, and the two
sources diverge from step 0, which is exp004's third line of evidence.

Run:  python report/figures/make_diagnostic.py
"""

from __future__ import annotations

import json
import pathlib
import shutil
import sys
import tempfile

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from experiments.exp004_scene_model_check.run import (  # noqa: E402
    render_seed,
    run_arm,
)
from figstyle import (  # noqa: E402
    COLOUR_ACCENT,
    COLOUR_BUILT,
    FIGURE_WIDTH_IN,
    plt,
    rcparams,
    save,
)

from bio3dvision.fixture import make_synthetic_scene  # noqa: E402

OUT = pathlib.Path(__file__).with_name("diagnostic.pdf")
RESULTS = REPO / "experiments" / "exp004_scene_model_check" / "results.json"
SEED = 0


def main() -> None:
    binary = shutil.which("blender")
    if binary is None:
        raise SystemExit(
            "Figure 3 needs a Blender binary on PATH: it compares the analytic "
            "fixture against a RENDER of the same geometry, and exp004 stored no "
            "arrays to read instead. Install Blender 5.2.0 LTS (exp004's "
            "`rendered_with`) and re-run. Nothing is substituted."
        )

    recorded = json.loads(RESULTS.read_text())["per_seed"][SEED]

    f_left, f_right, f_gt, f_params = make_synthetic_scene(seed=SEED)
    with tempfile.TemporaryDirectory() as tmp:
        r_left, r_right, r_gt, r_params, _ = render_seed(SEED, pathlib.Path(tmp), binary)
        arm_f = run_arm(f_left, f_right, f_params, f_gt)
        arm_r = run_arm(r_left, r_right, r_params, r_gt)

    # The guard: both trajectories, exactly as exp004 recorded them.
    for name, arm in (("F", arm_f), ("R", arm_r)):
        got = [[int(y), int(x)] for y, x in arm.engine.scanpath]
        assert got == recorded["scanpath"][name], (
            f"{name} scanpath differs from exp004's record\n"
            f"  rebuilt : {got}\n  recorded: {recorded['scanpath'][name]}")

    arms = [("fixture (F)", arm_f, COLOUR_BUILT), ("render (R)", arm_r, COLOUR_ACCENT)]

    with plt.rc_context(rcparams()):
        fig, axes = plt.subplots(2, 4, figsize=(FIGURE_WIDTH_IN, 3.5))
        for row, (label, arm, colour) in enumerate(arms):
            mean = arm.depth_est
            std = np.sqrt(np.asarray(arm.engine.var, dtype=float))
            err = np.abs(mean - arm.depth_gt)
            rmse = [h["rmse"] for h in arm.history]

            a = axes[row, 0]
            a.imshow(mean, cmap="viridis", vmin=2.0, vmax=5.2)
            ys = [p[0] for p in arm.engine.scanpath]
            xs = [p[1] for p in arm.engine.scanpath]
            a.plot(xs, ys, "-", color="white", lw=0.7, alpha=0.9)
            a.plot(xs, ys, "o", mfc="white", mec="black", mew=0.4, ms=2.4)
            a.set_title("posterior depth\n+ scanpath" if row == 0 else "", fontsize=7.4)
            a.set_ylabel(label, fontsize=8.2, color=colour, fontweight="bold")

            a = axes[row, 1]
            a.imshow(std, cmap="magma", vmin=0.0, vmax=2.6)
            a.set_title("posterior std" if row == 0 else "", fontsize=7.4)

            a = axes[row, 2]
            a.imshow(np.where(np.isfinite(err), err, 0.0), cmap="inferno",
                     vmin=0.0, vmax=1.6)
            a.set_title("|error| vs GT" if row == 0 else "", fontsize=7.4)

            for col in (0, 1, 2):
                axes[row, col].set_xticks([])
                axes[row, col].set_yticks([])
                for sp in axes[row, col].spines.values():
                    sp.set_linewidth(0.4)

            a = axes[row, 3]
            a.plot(range(1, len(rmse) + 1), rmse, "o-", color=colour, lw=1.1, ms=2.6)
            a.set_title("depth RMSE (m)" if row == 0 else "", fontsize=7.4)
            a.set_xlabel("fixation" if row == 1 else "", fontsize=7.4)
            a.set_ylim(0.0, 0.85)
            a.tick_params(labelsize=6.4)
            a.spines[["top", "right"]].set_visible(False)
            a.grid(alpha=0.25, lw=0.4)

        fig.tight_layout(pad=0.35)
        save(fig, OUT)

    print(f"  seed                 : {SEED}")
    print(f"  fixations per arm    : {len(arm_f.history)}")
    print("  scanpaths            : both match exp004's recorded trajectories")
    print(f"  scanpath agreement   : {recorded['scanpath_agreement']} of "
          f"{len(arm_f.history)} fixations (exp004)")
    for label, arm, _ in arms:
        print(f"  {label:<13} final RMSE : {arm.history[-1]['rmse']:.5f} m")
    at = recorded["pooled_CONFOUNDED"]["AT"]
    print(f"  exp004 AT p90        : F {at['F']['p90']:.4f} m   R {at['R']['p90']:.4f} m")


if __name__ == "__main__":
    main()
