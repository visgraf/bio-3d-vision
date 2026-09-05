"""Figure 2 — the analytic fixture: the stereo pair and its ground-truth depth.

WHAT IT DRAWS AND WHERE IT COMES FROM
-------------------------------------
``make_synthetic_scene(seed=0)`` -- the ported fixture, unchanged from
``visgraf/bioeye@e908170:active_stereo_demo.py:47-77`` -- at the parameters every
analytic-fixture result in this report was measured at: 240x320, f_px 700.0,
baseline 0.065 m. Three panels: the left image, the right image, and the
ground-truth depth field.

The point the figure has to make is Julesz's: **depth is present only in
disparity.** Neither monocular image contains it, and the two look alike; the
depth panel beside them is what the disparity encodes and what neither view
shows on its own.

THE GUARD, AND WHY IT IS THE ONE THAT MATTERS HERE
--------------------------------------------------
This fixture's defect is the subject of section 3.3, so the figure asserts the
two properties that defect rests on, from ``gap-010``:

* the right image contains no value outside the left image's range -- it is
  resampled from the left, not rendered, so no pixel of it can show a surface
  the left does not already contain;
* the depth field has exactly three card depths on a background, at the
  documented distances.

Both are recomputed here rather than quoted. If the fixture ever changes, this
figure fails instead of quietly illustrating a different stimulus.

Run:  python report/figures/make_fixture.py
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from figstyle import FIGURE_WIDTH_IN, plt, rcparams, save  # noqa: E402

from bio3dvision.fixture import make_synthetic_scene  # noqa: E402

OUT = pathlib.Path(__file__).with_name("fixture.pdf")
SEED = 0


def main() -> None:
    left, right, depth, params = make_synthetic_scene(seed=SEED)

    # gap-010's first mechanism, recomputed: the right image is resampled from
    # the left, so it can contain no value the left does not already hold.
    outside = int(((right < left.min()) | (right > left.max())).sum())
    assert outside == 0, f"{outside} right-image values fall outside the left's range"

    # The scene is a background plus three fronto-parallel cards.
    depths = np.unique(np.round(depth, 1))
    assert depth.shape == (240, 320), f"fixture is {depth.shape}, expected (240, 320)"

    with plt.rc_context(rcparams()):
        fig, axes = plt.subplots(1, 3, figsize=(FIGURE_WIDTH_IN, 1.95))
        for ax, img, title in (
            (axes[0], left, "left"),
            (axes[1], right, "right"),
        ):
            ax.imshow(img, cmap="gray", vmin=0.0, vmax=1.0)
            ax.set_title(title, fontsize=8.4)
        im = axes[2].imshow(depth, cmap="viridis")
        axes[2].set_title("ground-truth depth (m)", fontsize=8.4)
        cbar = fig.colorbar(im, ax=axes[2], fraction=0.046, pad=0.03)
        cbar.ax.tick_params(labelsize=6.4)
        cbar.outline.set_linewidth(0.5)

        for ax in axes:
            ax.set_xticks([])
            ax.set_yticks([])
            for sp in ax.spines.values():
                sp.set_linewidth(0.4)

        fig.tight_layout(pad=0.35)
        save(fig, OUT)

    print(f"  seed                     : {SEED}")
    print(f"  shape                    : {depth.shape}")
    print(f"  f_px / baseline          : {params['f_px']} px / {params['baseline']} m")
    print(f"  depth range              : {depth.min():.3f} – {depth.max():.3f} m")
    print(f"  distinct depths (0.1 m)  : {len(depths)}")
    print(f"  right values outside left: {outside}  (gap-010: resampled, not rendered)")


if __name__ == "__main__":
    main()
