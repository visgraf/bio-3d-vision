"""Figure 2 — the six-layer architecture: built, measured, hypothetical.

THE ONE DIAGRAM, AND WHY IT IS ALLOWED TO BE ONE
------------------------------------------------
Every other figure in this report plots numbers. This one draws structure, and it
is the only figure permitted to come from the ledger's SHAPE rather than from a
numeric result. The permission is narrow: **every box marked MEASURED names the
foreclosure or measurement id that measured it**, and this script asserts that
each of those ids exists in ``docs/state.yaml`` or
``docs/inherited-measurements.yaml`` before it draws. A box whose id has gone
away fails the build rather than printing a claim nobody can check.

The three statuses are distinct and mean different things:

* **MEASURED** — built, and something in the ledger measured its behaviour.
* **BUILT** — implemented and tested, but no measurement bears on the question
  the layer exists to answer. Infrastructure in CLAUDE.md's sense.
* **HYPOTHETICAL** — named in the framework and not built. Open decisions, not
  claims.

"L1".."L6" is Chat-surface vocabulary. fc-011's ``vocabulary_note`` records that
the layer numbering is NOT defined in this repository, and the figure says so.

Run:  python report/figures/make_architecture.py
"""

from __future__ import annotations

import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from figstyle import (  # noqa: E402
    COLOUR_BUILT,
    COLOUR_HYPOTHETICAL,
    COLOUR_MEASURED,
    FIGURE_WIDTH_IN,
    plt,
    rcparams,
    save,
)

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).with_name("architecture.pdf")

MEASURED, BUILT, HYPO = "measured", "built", "hypothetical"

#: (label, sublabel, status, evidence ids). Evidence is checked against the
#: ledger below; HYPOTHETICAL rows cite the open decision that records them.
LAYERS = [
    ("L1  oculomotor", "fixation to two eye rotations,\nListing's law", MEASURED,
     ["fc-012", "bio-082"]),
    ("L2  encode", "rectified stereo pair", BUILT, []),
    ("L3  match", "disparity, variance, validity", MEASURED,
     ["bio-001", "gap-010"]),
    ("L4  scale to depth", "expand about the fixated\ndisparity; eta-squared term", MEASURED,
     ["bio-004", "bio-005"]),
    ("L5  allocation", "where the measurement\nbudget is spent", MEASURED,
     ["fc-008", "bio-017"]),
    ("L6  next fixation", "argmax over the belief", MEASURED,
     ["fc-007", "bio-011"]),
]

SIDE = [
    ("sampling model", "index to unit ray;\nprojection swappable", MEASURED,
     ["fc-009", "bio-077"]),
    ("head-frame belief", "stores directions,\nnot pixels", MEASURED,
     ["fc-013", "bio-081"]),
    ("rig / sensor split", "baseline apart\nfrom focal length", BUILT, []),
]

OUTSIDE = [
    ("mechanical plant", "od-003", HYPO),
    ("variable-resolution\nsampling", "od-004", HYPO),
    ("controlled contrast\nat occlusions", "od-002", HYPO),
]


def _ledger_ids() -> set[str]:
    """Every id a MEASURED box is allowed to cite."""
    state = yaml.safe_load((REPO / "docs" / "state.yaml").read_text())
    inherited = yaml.safe_load((REPO / "docs" / "inherited-measurements.yaml").read_text())
    ids = {f["id"] for f in state["foreclosures"]}
    ids |= {o["id"] for o in state["open_decisions"]}
    ids |= {m["id"] for m in inherited["measurements"]}
    return ids


def main() -> None:
    known = _ledger_ids()
    cited = [e for _, _, _, ev in LAYERS + SIDE for e in ev]
    cited += [sub for _, sub, _ in OUTSIDE]
    missing = sorted({c for c in cited if c not in known})
    assert not missing, f"figure cites ids absent from the ledger: {missing}"

    fill = {MEASURED: COLOUR_MEASURED, BUILT: COLOUR_BUILT, HYPO: COLOUR_HYPOTHETICAL}

    with plt.rc_context(rcparams()):
        fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_IN, 6.0))
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 95)
        ax.axis("off")

        def box(x, y, w, h, name, sub, status, ev, dashed=False):
            """One component. The status tag sits on the title line, right-aligned,
            so it can never collide with a two-line sublabel."""
            ax.add_patch(plt.Rectangle(
                (x, y), w, h, facecolor=fill[status], alpha=0.13 if dashed else 0.16,
                edgecolor=fill[status], lw=1.0 if dashed else 1.1,
                linestyle=(0, (3, 2)) if dashed else "solid"))
            ax.text(x + 1.6, y + h - 2.5, name, fontweight="bold", va="top", fontsize=8.6)
            if sub:
                ax.text(x + 1.6, y + h - 5.4, sub, va="top", fontsize=7.2, color="#333333")
            tag = ("MEASURED  " + ", ".join(ev)) if status == MEASURED else (
                f"HYPOTHETICAL  {ev[0]}" if status == HYPO else status.upper())
            ax.text(x + w - 1.6, y + 1.5, tag, ha="right", va="bottom",
                    fontsize=6.6, color=fill[status], fontweight="bold")

        # The stack, L1 at the bottom, so the loop reads upward.
        x0, w, h, gap = 8.5, 42.0, 12.4, 1.5
        for i, (name, sub, status, ev) in enumerate(LAYERS):
            box(x0, 3.5 + i * (h + gap), w, h, name, sub, status, ev)

        # The loop, drawn clear of the boxes on the left rather than across them.
        top = 3.5 + 5 * (h + gap) + h
        ax.annotate("", xy=(x0 - 2.2, 4.6), xytext=(x0 - 2.2, top - 1.0),
                    arrowprops={"arrowstyle": "-|>", "color": "#666666", "lw": 1.0,
                                "connectionstyle": "arc3,rad=0.30"})
        ax.text(1.1, (top + 3.5) / 2, "the loop", fontsize=7.4, color="#666666",
                rotation=90, ha="center", va="center")

        # The three components that sit outside the stack.
        x1, w1 = 56.0, 41.5
        ax.text(x1, top + 0.4, "outside the stack", fontsize=7.4, color="#333333",
                style="italic", va="bottom")
        for i, (name, sub, status, ev) in enumerate(SIDE):
            box(x1, top - h - i * (h + gap), w1, h, name, sub, status, ev)

        y_h = 3.5
        ax.text(x1, y_h + 3 * 9.6 - 1.0, "named, not built", fontsize=7.4,
                color="#333333", style="italic", va="bottom")
        for i, (name, sub, status) in enumerate(OUTSIDE):
            box(x1, y_h + i * 9.6, w1, 8.6, name, "", status, [sub], dashed=True)

        ax.text(0, 94.0, "L1\u2013L6 is Chat-surface vocabulary and is not defined in this "
                "repository (fc-011).\nEvery MEASURED box names the ledger entry that "
                "measured it.", fontsize=7.0, color="#666666", va="top")

        fig.tight_layout(pad=0.3)
        save(fig, OUT)

    print(f"  layers drawn     : {len(LAYERS)}")
    print(f"  measured boxes   : {sum(1 for r in LAYERS + SIDE if r[2] == MEASURED)}")
    print(f"  built boxes      : {sum(1 for r in LAYERS + SIDE if r[2] == BUILT)}")
    print(f"  hypothetical     : {len(OUTSIDE)}")
    print(f"  ledger ids cited : {len(set(cited))}, all present")


if __name__ == "__main__":
    main()
