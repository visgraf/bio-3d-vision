"""Figure 1 — the scanpath under argmax-variance with no inhibition of return.

Regenerates the ported baseline's 18-fixation run and draws its scanpath over the
posterior mean depth. Eight distinct pixels, then a ninth that captures the last
ten fixations and never releases them.

WHY THIS REGENERATES RATHER THAN READS A RESULTS FILE
-----------------------------------------------------
``results/`` is git-ignored (``.gitignore:23``), so no committed artifact holds
this trajectory and a clean checkout has nothing to read. Regeneration from
committed code at a pinned seed is therefore the only route, and the run is
cheap: the analytic fixture is closed-form and the whole run is well under a
second, with no Blender and no network.

The trajectory is NOT hard-coded here. It comes out of
``bio3dvision.baseline.run_baseline`` and ``bio3dvision.figure.panel_arrays`` --
the same committed code the suite pins -- and this script only draws it.

THE RUN, PINNED
---------------
    run_baseline(steps=18, seed=0)

which is ``DEFAULT_STEPS``/``DEFAULT_SEED`` in ``bio3dvision.baseline``, on the
analytic fixture ``make_synthetic_scene(H=240, W=320, f_px=700.0,
baseline=0.065, seed=0)`` with the block matcher (win 7, dmin 0, dmax 56,
fovea_sigma 34.0, prior 3.0 +/- 3.0). That is the configuration recorded for
bio-001..bio-009 in ``docs/inherited-measurements.yaml``.

WHAT IS BEING DRAWN, AND WHAT IT IS NOT
---------------------------------------
This is the PREDECESSOR'S loop, ported bit-identically (bio-009). The figure
shows inherited behaviour and the defect that motivates the work -- it is a
baseline, not a result about anything new. It runs on the analytic fixture, which
CLAUDE.md calls a test fixture rather than a scene family; that is legitimate
here precisely because no finding rests on it. The claim is about the policy's
own dynamics, and the fixture is the medium the predecessor's own measurement was
taken in.

STYLE, SET ONCE FOR THE WHOLE REPORT
------------------------------------
Figure width 6.5 in, which is ``\\textwidth`` for the report's ``article`` class
at letterpaper with 1 in margins, so a figure included at ``width=\\textwidth``
is reproduced 1:1 with no rescaling of its type. Font DejaVu Serif at 9 pt --
matplotlib ships it, so the figure builds identically anywhere without a font
search, and 9 pt against the document's 11 pt body reads as a caption-weight
label. Output is vector PDF. The next five figures should use FIGURE_WIDTH_IN and
_rcparams() rather than restating any of this.

Run:  python report/figures/make_scanpath.py
"""

from __future__ import annotations

import pathlib
from collections import Counter

import matplotlib

matplotlib.use("Agg")  # no display; deterministic rasterisation of the vector path

import matplotlib.pyplot as plt  # noqa: E402

from bio3dvision.baseline import run_baseline  # noqa: E402

#: Shared by every figure in this report. See "STYLE" above.
FIGURE_WIDTH_IN = 6.5
FONT_SIZE_PT = 9.0
FONT_FAMILY = "DejaVu Serif"

OUT = pathlib.Path(__file__).with_name("scanpath.pdf")

# The run, from docs/inherited-measurements.yaml. These are ASSERTED, not drawn:
# the figure is built from the regenerated trajectory, and these guard it against
# silently drifting away from the record it illustrates.
STEPS = 18
SEED = 0
LEDGER_DISTINCT = 9  # bio-001
LEDGER_LOCKUP_PIXEL = (170, 94)  # bio-002
LEDGER_LOCKUP_VISITS = 10  # bio-002
LEDGER_FIRST_STEP = 8  # bio-002


def _rcparams() -> dict[str, object]:
    """Report-wide matplotlib style. Every figure calls this."""
    return {
        "font.family": "serif",
        "font.serif": [FONT_FAMILY],
        "font.size": FONT_SIZE_PT,
        "axes.titlesize": FONT_SIZE_PT,
        "axes.labelsize": FONT_SIZE_PT,
        "xtick.labelsize": FONT_SIZE_PT - 1,
        "ytick.labelsize": FONT_SIZE_PT - 1,
        "legend.fontsize": FONT_SIZE_PT - 1,
        "pdf.fonttype": 42,  # embed TrueType, so the PDF is self-contained
        "pdf.compression": 6,
        "svg.hashsalt": "bio-3d-vision",  # kills the one remaining random id source
    }


def main() -> None:
    run = run_baseline(steps=STEPS, seed=SEED)
    scanpath = run.panels.scanpath
    counts = Counter(scanpath)
    (lockup, visits), = counts.most_common(1)

    # Guard: the drawing must agree with the record it is captioned against.
    assert len(scanpath) == STEPS, f"{len(scanpath)} fixations, expected {STEPS}"
    assert len(counts) == LEDGER_DISTINCT, f"{len(counts)} distinct, bio-001 says {LEDGER_DISTINCT}"
    assert lockup == LEDGER_LOCKUP_PIXEL, f"lockup at {lockup}, bio-002 says {LEDGER_LOCKUP_PIXEL}"
    assert visits == LEDGER_LOCKUP_VISITS, f"{visits} visits, bio-002 says {LEDGER_LOCKUP_VISITS}"
    assert scanpath.index(lockup) == LEDGER_FIRST_STEP, "lockup does not start where bio-002 says"

    with plt.rc_context(_rcparams()):
        ys = [p[0] for p in scanpath]
        xs = [p[1] for p in scanpath]
        height, width = run.panels.posterior_mean.shape
        # Image aspect, plus a strip for the colorbar and the axis title.
        fig_h = FIGURE_WIDTH_IN * height / width * 1.02
        fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_IN, fig_h))

        im = ax.imshow(run.panels.posterior_mean, cmap="viridis")
        cbar = fig.colorbar(im, ax=ax, fraction=0.0455, pad=0.02)
        cbar.set_label("posterior mean depth (m)")
        cbar.outline.set_linewidth(0.5)

        # The path, then the eight pixels it visits once, then the one it does not leave.
        ax.plot(xs, ys, "-", color="white", lw=1.0, alpha=0.9, zorder=2)
        once = [p for p in scanpath if counts[p] == 1]
        ax.plot(
            [p[1] for p in once],
            [p[0] for p in once],
            "o",
            mfc="white",
            mec="black",
            mew=0.6,
            ms=5,
            zorder=3,
        )
        ax.plot(
            [lockup[1]],
            [lockup[0]],
            "o",
            mfc="#d94801",
            mec="black",
            mew=0.8,
            ms=10,
            zorder=4,
        )
        # Step 6 lands at (169, 94), one pixel above the lockup pixel, so its
        # label is pushed left to clear the marker that swallows it.
        for i, (y, x) in enumerate(scanpath):
            if (y, x) == lockup:
                continue
            near = abs(y - lockup[0]) < 12 and abs(x - lockup[1]) < 12
            ax.annotate(
                str(i),
                (x, y),
                textcoords="offset points",
                xytext=(-11, 4) if near else (5, 3),
                color="white",
                zorder=5,
            )
        ax.annotate(
            f"{visits} of {STEPS} fixations\nsteps {LEDGER_FIRST_STEP}–{STEPS - 1}, "
            f"pixel ({lockup[0]}, {lockup[1]})",
            lockup[::-1],
            textcoords="offset points",
            xytext=(34, -30),
            color="#7f2704",
            fontweight="bold",
            zorder=6,
            bbox={"fc": "white", "ec": "#d94801", "lw": 0.6, "boxstyle": "round,pad=0.3",
                  "alpha": 0.92},
            arrowprops={"arrowstyle": "-", "color": "#d94801", "lw": 0.8,
                        "shrinkA": 2, "shrinkB": 7},
        )

        ax.set_title(
            f"{STEPS} fixations, {len(counts)} distinct: "
            f"{visits} of {STEPS} land on one pixel (seed {SEED})"
        )
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_linewidth(0.5)

        fig.tight_layout(pad=0.4)
        # CreationDate omitted so two runs are byte-identical (falsifier 2).
        fig.savefig(OUT, format="pdf", metadata={"CreationDate": None})
        plt.close(fig)

    print(f"wrote {OUT}")
    print(f"  fixations        : {len(scanpath)}")
    print(f"  distinct         : {len(counts)}")
    print(f"  lockup pixel     : (y={lockup[0]}, x={lockup[1]})")
    print(f"  visits to lockup : {visits} (steps {LEDGER_FIRST_STEP}-{STEPS - 1})")
    print(f"  seed             : {SEED}")


if __name__ == "__main__":
    main()
