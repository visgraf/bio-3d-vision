"""Figure 5 — spherical stereo geometry: epipolar meridians and the sine rule.

WHAT IT DRAWS AND WHERE IT COMES FROM
-------------------------------------
Both panels are the geometry documented at
``src/bio3dvision/sampling.py:242-264`` -- ``EquirectSampling``'s own docstring --
drawn rather than restated. Nothing here is fitted or sampled; it is closed-form,
so "regenerates deterministically" is trivially true and the guard below is the
real check.

**Left: rows are epipolar.** With the baseline along +x the two epipoles sit at
+/-x, so every epipolar great circle passes through them and the family of such
circles is exactly the set of MERIDIANS about +x. That is why the sensor is
indexed by meridian ``phi`` down the rows and colatitude ``theta`` from +x across
the columns: corresponding points land on the same row, and the matcher's
horizontal shift is a shift along ``theta``.

**Right: the depth relation is not f*b/z.** For a point seen at ``theta_L`` and
``theta_R`` with ``d = theta_R - theta_L``,

    r_L = b * sin(theta_R) / sin(d)

the sine rule on the triangle (left centre, right centre, point). It depends on
``theta``, the angle from the baseline, and the pinhole relation has no analogue.
The docstring states the consequence as a number -- *at a range of 3 m the
disparity is 5.8x larger at theta = 90 deg than at theta = 10 deg* -- and this
script ASSERTS that ratio before drawing, so the figure and the docstring cannot
drift apart.

Baseline 0.065 m, the fixture's, from ``make_synthetic_scene``.

Run:  python report/figures/make_spherical.py
"""

from __future__ import annotations

import pathlib
import sys

import numpy as np

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

OUT = pathlib.Path(__file__).with_name("spherical.pdf")

BASELINE_M = 0.065  # fixture baseline, make_synthetic_scene
RANGE_M = 3.0  # the range the sampling.py docstring quotes


def disparity(theta: np.ndarray, r: float = RANGE_M, b: float = BASELINE_M) -> np.ndarray:
    """Angular disparity ``d = theta_R - theta_L`` for a point at range ``r``.

    Exact, from the sine rule rather than the small-angle form: the left centre
    sits at ``-b/2`` and the right at ``+b/2`` along the baseline, so a point at
    colatitude ``theta`` and range ``r`` from the midpoint is seen at
    ``theta_L`` and ``theta_R`` given by atan2 in the epipolar plane.
    """
    x = r * np.cos(theta)
    y = r * np.sin(theta)
    theta_l = np.arctan2(y, x + b / 2.0)
    theta_r = np.arctan2(y, x - b / 2.0)
    return theta_r - theta_l


def main() -> None:
    # The guard: the docstring's own number, before anything is drawn.
    ratio = float(disparity(np.radians(90.0)) / disparity(np.radians(10.0)))
    assert abs(ratio - 5.8) < 0.1, (
        f"disparity ratio 90deg/10deg is {ratio:.2f}; sampling.py:262 says 5.8x")

    with plt.rc_context(rcparams()):
        fig, (axl, axr) = plt.subplots(1, 2, figsize=(FIGURE_WIDTH_IN, 2.9))

        # ---------- left: meridians about the baseline
        axl.add_patch(plt.Circle((0, 0), 1.0, fill=False, ec="#666666", lw=1.2))
        for phi in np.linspace(0, np.pi, 9, endpoint=False):
            # A meridian about +x, projected: an ellipse through both epipoles.
            t = np.linspace(0, 2 * np.pi, 400)
            x = np.cos(t)
            y = np.sin(t) * np.cos(phi)
            axl.plot(x, y, color=COLOUR_BUILT, lw=0.7, alpha=0.75)
        axl.plot([-1, 1], [0, 0], color=COLOUR_ACCENT, lw=1.4, zorder=3)
        for sx, lab in ((-1, "$-x$"), (1, "$+x$")):
            axl.plot([sx], [0], "o", color=COLOUR_ACCENT, ms=5.5, zorder=4)
            axl.annotate(f"epipole\n{lab}", (sx, 0), textcoords="offset points",
                         xytext=(0, -20 if sx < 0 else -20), ha="center",
                         fontsize=7.0, color=COLOUR_ACCENT)
        axl.annotate("baseline", (0, 0), textcoords="offset points", xytext=(0, 7),
                     ha="center", fontsize=7.4, color=COLOUR_ACCENT)
        axl.annotate(r"meridians about $+x$" "\n" r"= epipolar great circles",
                     (0.0, 1.16), fontsize=7.4, color=COLOUR_BUILT, ha="center")
        axl.set_xlim(-1.35, 1.35)
        axl.set_ylim(-1.35, 1.62)
        axl.set_aspect("equal")
        axl.axis("off")
        axl.set_title("rows are epipolar", fontsize=8.6)

        # ---------- right: the sine rule's dependence on theta
        theta = np.radians(np.linspace(1.0, 179.0, 800))
        d_mrad = np.degrees(disparity(theta)) * 1000.0  # millidegrees
        axr.plot(np.degrees(theta), d_mrad, color=COLOUR_MEASURED, lw=1.6)
        for t_deg, colour in ((10.0, COLOUR_ACCENT), (90.0, COLOUR_ACCENT)):
            d = float(np.degrees(disparity(np.radians(t_deg))) * 1000.0)
            axr.plot([t_deg], [d], "o", color=colour, ms=5)
            axr.annotate(f"{t_deg:.0f}°", (t_deg, d), textcoords="offset points",
                         xytext=(4, -10 if t_deg == 10 else 4), fontsize=7.2,
                         color=colour)
        axr.annotate(f"{ratio:.1f}× larger at 90° than at 10°",
                     (95, float(np.degrees(disparity(np.radians(90.0))) * 1000.0)),
                     textcoords="offset points", xytext=(-4, -26), fontsize=7.4,
                     color=COLOUR_ACCENT, ha="left",
                     bbox={"fc": "white", "ec": COLOUR_ACCENT, "lw": 0.6,
                           "boxstyle": "round,pad=0.28", "alpha": 0.92})
        axr.set_xlim(0, 180)
        axr.set_xticks([0, 30, 60, 90, 120, 150, 180])
        axr.set_xlabel(r"$\theta$, angle from the baseline (deg)")
        axr.set_ylabel("angular disparity (millidegrees)")
        axr.set_title(
            r"$r_L = b\,\sin\theta_R / \sin d$   at $r=3$ m, $b=65$ mm", fontsize=8.6)
        axr.spines[["top", "right"]].set_visible(False)
        axr.grid(alpha=0.25, lw=0.5)

        fig.tight_layout(pad=0.4)
        save(fig, OUT)

    print(f"  baseline            : {BASELINE_M} m")
    print(f"  range               : {RANGE_M} m")
    print(f"  disparity at 10 deg : {np.degrees(disparity(np.radians(10.0))) * 1000:.3f} mdeg")
    print(f"  disparity at 90 deg : {np.degrees(disparity(np.radians(90.0))) * 1000:.3f} mdeg")
    print(f"  ratio 90/10         : {ratio:.3f}x  (sampling.py:262 says 5.8x)")


if __name__ == "__main__":
    main()
