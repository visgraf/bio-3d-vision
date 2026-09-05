"""Figure 6 — the foreclosure ledger, and which conclusions were later qualified.

WHAT IT DRAWS AND HOW IT IS DERIVED
-----------------------------------
Reads ``docs/state.yaml`` and builds the figure from the SHAPE of the
foreclosure entries rather than from a hand-typed table. A foreclosure that
acquires a later annotation acquires it as a NEW KEY on its own entry -- that is
how this repository records a qualification, in place and by addition, rather
than by editing the original -- so the keys are the timeline.

Each entry is scanned for keys naming a later iteration (``..._exp005``,
``..._exp007``, ``..._exp012``, ``..._at_step_15``), and each such key's text is
classified by the verdict word it carries:

    STANDS / CONFIRMED / SURVIVES / SUPPORTED / UNAFFECTED / NOT MOVED  -> upheld
    QUALIFIED                                                          -> qualified
    DEFERRED / ANSWERED / amendment                                    -> amended

Nothing is typed in by hand except the classification vocabulary, so a
foreclosure annotated tomorrow appears here without editing this script. The
counts are printed and asserted against what the ledger contains.

**fc-009 is the one to read closely.** Its falsifier-2 verdict was written
ADDITIVE, corrected in place to DEFERRED because the original was an
overstatement rather than a verdict data had reversed, and then ANSWERED as
ADDITIVE at step 15 once a ray actually crossed the boundary. Three states, all
on the record, none of them an edit of the last.

Run:  python report/figures/make_ledger.py
"""

from __future__ import annotations

import pathlib
import re
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from figstyle import (  # noqa: E402
    COLOUR_ACCENT,
    COLOUR_HYPOTHETICAL,
    COLOUR_MEASURED,
    COLOUR_QUALIFIED,
    FIGURE_WIDTH_IN,
    plt,
    rcparams,
    save,
)

REPO = pathlib.Path(__file__).resolve().parents[2]
OUT = pathlib.Path(__file__).with_name("ledger.pdf")

UPHELD, QUALIFIED, AMENDED = "upheld", "qualified", "amended"
MARK = {UPHELD: ("o", COLOUR_MEASURED), QUALIFIED: ("s", COLOUR_QUALIFIED),
        AMENDED: ("D", COLOUR_ACCENT)}

_UPHELD_WORDS = ("STANDS", "CONFIRMED", "SURVIVES", "SUPPORTED", "UNAFFECTED",
                 "NOT MOVED", "CHECKED AND")
_QUALIFIED_WORDS = ("QUALIFIED",)
_AMENDED_WORDS = ("DEFERRED", "ANSWERED", "CORRECTED", "OVERSTATEMENT")


def classify(text: str) -> str:
    up = text.upper()
    if any(w in up for w in _QUALIFIED_WORDS):
        return QUALIFIED
    if any(w in up for w in _AMENDED_WORDS):
        return AMENDED
    if any(w in up for w in _UPHELD_WORDS):
        return UPHELD
    return UPHELD


#: Keys that record a correction made IN PLACE, on the entry itself, rather than
#: at a later iteration. fc-009's falsifier-2 verdict is the case this exists
#: for: written ADDITIVE, corrected to DEFERRED because the original overstated
#: what had been measured. That correction names no experiment, so it would be
#: invisible on an iteration axis -- and it is exactly the kind of movement this
#: figure is about.
IN_PLACE_KEYS = ("amendment", "falsifier_2_outcome")


def iteration_of(key: str) -> tuple[int, str] | None:
    """Order index and label for a key that names a later iteration."""
    if key in IN_PLACE_KEYS:
        return -1, "in place"
    m = re.search(r"exp(\d{3})", key)
    if m:
        return int(m.group(1)), f"exp{m.group(1)}"
    m = re.search(r"step_?(\d+)", key)
    if m:
        return 100 + int(m.group(1)), f"step {m.group(1)}"
    return None


def main() -> None:
    state = yaml.safe_load((REPO / "docs" / "state.yaml").read_text())
    fcs = state["foreclosures"]

    events: dict[str, list[tuple[int, str, str]]] = {}
    columns: dict[int, str] = {}
    for fc in fcs:
        found = []
        for key, value in fc.items():
            it = iteration_of(key)
            if it is None or not isinstance(value, str):
                continue
            order, label = it
            columns[order] = label
            found.append((order, label, classify(value)))
        # Two keys can name the same iteration (fc-009 has two at step 15).
        # Collapse them, most severe first, so one marker means one verdict.
        severity = {AMENDED: 2, QUALIFIED: 1, UPHELD: 0}
        best: dict[int, tuple[int, str, str]] = {}
        for order, label, kind in found:
            prev = best.get(order)
            if prev is None or severity[kind] > severity[prev[2]]:
                best[order] = (order, label, kind)
        events[fc["id"]] = sorted(best.values())

    order_keys = sorted(columns)
    xpos = {k: i for i, k in enumerate(order_keys)}
    ids = [fc["id"] for fc in fcs]

    n_annotated = sum(1 for v in events.values() if v)
    n_events = sum(len(v) for v in events.values())
    assert n_events, "no annotations found — the ledger's shape has changed"

    with plt.rc_context(rcparams()):
        fig, ax = plt.subplots(figsize=(FIGURE_WIDTH_IN, 3.5))
        for i, fid in enumerate(ids):
            y = len(ids) - 1 - i
            ax.axhline(y, color="#e8e8e8", lw=0.7, zorder=0)
            ev = events[fid]
            if ev:
                ax.plot([xpos[e[0]] for e in ev], [y] * len(ev), "-",
                        color="#cccccc", lw=0.9, zorder=1)
            for order, _label, kind in ev:
                marker, colour = MARK[kind]
                ax.plot([xpos[order]], [y], marker, color=colour, ms=6.2,
                        mec="white", mew=0.7, zorder=3)
            if not ev:
                ax.text(-0.72, y, "no later annotation", fontsize=6.4, va="center",
                        ha="right", color=COLOUR_HYPOTHETICAL, style="italic")

        ax.set_yticks(range(len(ids)))
        ax.set_yticklabels(list(reversed(ids)))
        ax.set_xticks(range(len(order_keys)))
        ax.set_xticklabels([columns[k] for k in order_keys])
        ax.set_xlim(-4.2, len(order_keys) - 0.4)
        ax.set_ylim(-0.8, len(ids) - 0.2)
        ax.set_xlabel("when the annotation was made — in place on the entry, "
                      "or at a later iteration")
        ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)

        handles = [plt.Line2D([], [], marker=MARK[k][0], color=MARK[k][1], ls="",
                              ms=6.2, label=lab)
                   for k, lab in ((UPHELD, "upheld / unaffected"),
                                  (QUALIFIED, "qualified"),
                                  (AMENDED, "verdict amended"))]
        ax.legend(handles=handles, loc="lower left", frameon=False, ncol=3,
                  fontsize=7.0, bbox_to_anchor=(0.0, -0.34))

        fig.tight_layout(pad=0.4)
        save(fig, OUT)

    print(f"  foreclosures        : {len(ids)}")
    print(f"  with later annotation: {n_annotated}")
    print(f"  annotation events   : {n_events}")
    for fid in ids:
        if events[fid]:
            print(f"    {fid}: " + ", ".join(f"{lab}={kind}" for _, lab, kind in events[fid]))


if __name__ == "__main__":
    main()
