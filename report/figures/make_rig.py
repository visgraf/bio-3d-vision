"""Figure 6 — the spherical rig: a saccade moves the frame and not the data.

A CONCEPTUAL DIAGRAM, AND THE RULE THAT GOES WITH IT
-----------------------------------------------------
This figure cannot be generated FROM the record: it draws a geometric argument,
not a measurement. So every factual mark in it traces to a ledger entry, the
caption names them, and this script asserts those entries exist before drawing.

    fc-013   the eye centres are FIXED in the head at +/- b/2 and
             ``eye_rotations`` returns ROTATIONS, not translations, so a rotation
             about a fixed optical centre re-indexes a complete capture and adds
             nothing to it. The foreclosure's own words: "a complete capture has
             no hemisphere to hide."
    bio-081  a sphere loses no grid at any saccade amplitude.
    bio-082  two orientations -- identity, and yawed 37 deg / pitched 19 deg --
             reproduce the same analytic function of direction to 80 micrometres,
             MEASURED against a real Blender.

THE POINT, AND WHY THE PINHOLE ROW IS HERE
------------------------------------------
The top row is the spherical rig before and after a saccade: the sampled set is
the whole sphere in both, so the capture is identical and only the gaze frame has
moved. On its own that reads as a picture of nothing happening. The bottom row is
the pinhole contrast that makes it legible -- there the field of view rotates
with the gaze, so a saccade genuinely brings directions into view that were not
sampled before, and the shaded crescent is what acquisition means.

**The qualifier is load-bearing and the caption carries it.** fc-013 forecloses
acquisition-by-rotation only for a sensor sampled UNIFORMLY. Under variable
resolution the fovea resolves what the periphery merely sampled, and refixation
buys something again -- which is od-004, and the reason this figure is an
argument about this sensor rather than about eyes.

Run:  python report/figures/make_rig.py
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from figstyle import (  # noqa: E402
    COLOUR_ACCENT,
    COLOUR_BUILT,
    COLOUR_MEASURED,
    FIGURE_WIDTH_IN,
    plt,
    rcparams,
    save,
)

OUT = pathlib.Path(__file__).with_name("rig.pdf")

CITED = ["fc-013", "bio-081", "bio-082"]

HALF_B = 1.0  # the baseline half-width, in diagram units
R = 1.15  # sensor radius, in diagram units
GAZE_BEFORE = np.radians(90.0)
GAZE_AFTER = np.radians(52.0)
FOV = np.radians(46.0)  # pinhole field of view, for the contrast row


def _ledger_ids() -> set[str]:
    state = yaml.safe_load((REPO / "docs" / "state.yaml").read_text())
    inherited = yaml.safe_load((REPO / "docs" / "inherited-measurements.yaml").read_text())
    return ({f["id"] for f in state["foreclosures"]}
            | {o["id"] for o in state["open_decisions"]}
            | {m["id"] for m in inherited["measurements"]})


def _eyes(ax) -> None:
    """The head: two optical centres fixed at +/- b/2, and the baseline."""
    ax.plot([-HALF_B, HALF_B], [0, 0], "-", color="#555555", lw=1.2, zorder=4)
    for sx in (-HALF_B, HALF_B):
        ax.plot([sx], [0], "o", color="#222222", ms=4.5, zorder=6)
    ax.text(0, -0.30, "$b$", ha="center", va="top", fontsize=7.6, color="#555555")
    ax.text(-HALF_B, -0.30, r"$-b/2$", ha="center", va="top", fontsize=6.8, color="#555555")
    ax.text(HALF_B, -0.30, r"$+b/2$", ha="center", va="top", fontsize=6.8, color="#555555")


def _gaze(ax, angle: float, colour: str) -> None:
    """One gaze direction, drawn through both centres."""
    for sx in (-HALF_B, HALF_B):
        ax.annotate("", xy=(sx + 1.85 * np.cos(angle), 1.85 * np.sin(angle)),
                    xytext=(sx, 0),
                    arrowprops={"arrowstyle": "-|>", "color": colour, "lw": 1.3})


def main() -> None:
    known = _ledger_ids()
    missing = [c for c in CITED if c not in known]
    assert not missing, f"figure cites ids absent from the ledger: {missing}"

    with plt.rc_context(rcparams()):
        fig, axes = plt.subplots(2, 2, figsize=(FIGURE_WIDTH_IN, 4.35))

        for col, (angle, when) in enumerate(
            ((GAZE_BEFORE, "before the saccade"), (GAZE_AFTER, "after the saccade"))
        ):
            # ---------- spherical: the sampled set is the whole sphere, both times
            ax = axes[0, col]
            for sx in (-HALF_B, HALF_B):
                ax.add_patch(plt.Circle((sx, 0), R, facecolor=COLOUR_MEASURED,
                                        alpha=0.17, edgecolor=COLOUR_MEASURED, lw=1.2))
            _eyes(ax)
            _gaze(ax, angle, COLOUR_ACCENT)
            ax.set_title(f"spherical sensor, {when}", fontsize=8.4)
            if col == 0:
                ax.text(-2.9, 0.0, "every direction\nalready sampled", fontsize=7.2,
                        color=COLOUR_MEASURED, rotation=90, ha="center", va="center")
            else:
                ax.annotate("identical capture:\nthe frame moved,\nthe data did not",
                            (0.0, -1.72), ha="center", va="top", fontsize=7.4,
                            color=COLOUR_MEASURED, fontweight="bold")

            # ---------- pinhole: the field rotates with the gaze
            ax = axes[1, col]
            for sx in (-HALF_B, HALF_B):
                if col == 1:  # what the earlier pose covered, for the contrast
                    ax.add_patch(plt.matplotlib.patches.Wedge(
                        (sx, 0), R, np.degrees(GAZE_BEFORE - FOV / 2),
                        np.degrees(GAZE_BEFORE + FOV / 2), facecolor="#bbbbbb",
                        alpha=0.35, edgecolor="none"))
                ax.add_patch(plt.matplotlib.patches.Wedge(
                    (sx, 0), R, np.degrees(angle - FOV / 2),
                    np.degrees(angle + FOV / 2), facecolor=COLOUR_BUILT, alpha=0.30,
                    edgecolor=COLOUR_BUILT, lw=1.1))
            _eyes(ax)
            _gaze(ax, angle, COLOUR_ACCENT)
            ax.set_title(f"pinhole sensor, {when}", fontsize=8.4)
            if col == 0:
                ax.text(-2.9, 0.0, "only the field\nof view sampled", fontsize=7.2,
                        color=COLOUR_BUILT, rotation=90, ha="center", va="center")
            else:
                ax.annotate("new directions enter:\nthis is acquisition",
                            (0.0, -1.72), ha="center", va="top", fontsize=7.4,
                            color=COLOUR_BUILT, fontweight="bold")

        for ax in axes.ravel():
            ax.set_xlim(-3.3, 3.3)
            ax.set_ylim(-2.5, 2.35)
            ax.set_aspect("equal")
            ax.axis("off")

        fig.tight_layout(pad=0.4)
        save(fig, OUT)

    print(f"  ledger ids cited : {', '.join(CITED)} — all present")
    print(f"  gaze before      : {np.degrees(GAZE_BEFORE):.0f} deg")
    print(f"  gaze after       : {np.degrees(GAZE_AFTER):.0f} deg")
    print(f"  pinhole fov      : {np.degrees(FOV):.0f} deg")
    print("  claim drawn      : rotation about a fixed centre re-indexes a complete")
    print("                     capture and adds nothing to it (fc-013)")


if __name__ == "__main__":
    main()
