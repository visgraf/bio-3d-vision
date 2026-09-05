"""Figure 4 — coverage against accuracy, the two arms of exp010/exp011.

WHAT IT DRAWS AND WHERE THE NUMBERS COME FROM
---------------------------------------------
Reads ``experiments/exp011_consolidation/results.json`` -- 192 rows, 4 occlusion
levels x 24 seeds x 2 arms -- and rebuilds exp011's question-3 decomposition
rather than restating it:

    total gain    = mean_abs_err(OPEN, all cells) - mean_abs_err(CLOSED, all cells)
    accuracy term = f_common * (OPEN_common - CLOSED_common)
    coverage term = total - accuracy term

on the pre-registered yardstick: mean absolute error over all 76 800 cells, with
unmeasured cells left at the prior. The rebuilt terms are ASSERTED against the
values exp011 published (findings.md, question 3) before anything is drawn, so
the figure cannot drift from the record it illustrates.

Left panel: what each arm ever measured. Right panel: how much of the all-cells
gain each term carries, on a log axis because 34x to 341x does not fit a linear
one -- which is itself the point of the figure.

Run:  python report/figures/make_coverage.py
"""

from __future__ import annotations

import json
import pathlib
import sys
from collections import defaultdict

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

REPO = pathlib.Path(__file__).resolve().parents[2]
RESULTS = REPO / "experiments" / "exp011_consolidation" / "results.json"
OUT = pathlib.Path(__file__).with_name("coverage.pdf")

ALL_CELLS = 76800
LEVELS = [1, 2, 4, 8]

#: exp011 findings.md, question 3. The figure must reproduce these.
PUBLISHED = {
    1: {"occl": 0.0197, "open_ever": 0.6954, "closed_ever": 0.9791,
        "open_all": 0.4503, "closed_all": 0.0718, "acc": 0.01045, "cov": 0.36810, "ratio": 35},
    2: {"occl": 0.0426, "open_ever": 0.6736, "closed_ever": 0.9614,
        "open_all": 0.5001, "closed_all": 0.1265, "acc": 0.00165, "cov": 0.37199, "ratio": 225},
    4: {"occl": 0.0884, "open_ever": 0.6218, "closed_ever": 0.9275,
        "open_all": 0.6304, "closed_all": 0.2318, "acc": 0.01155, "cov": 0.38704, "ratio": 34},
    8: {"occl": 0.1716, "open_ever": 0.5427, "closed_ever": 0.8800,
        "open_all": 0.7969, "closed_all": 0.4151, "acc": 0.00112, "cov": 0.38066, "ratio": 341},
}


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def rebuild() -> dict[int, dict[str, float]]:
    """exp011's decomposition, recomputed from the per-seed rows."""
    rows = json.loads(RESULTS.read_text())["rows"]
    acc: dict[tuple[int, str], dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list))
    for r in rows:
        a = acc[(r["k"], r["arm"])]
        a["ever"].append(r["ever_measured_fraction"])
        a["all"].append(r["POOLED_all"]["mean_abs_err"])
        a["common"].append(r["POOLED_common"]["mean_abs_err"])
        a["n_common"].append(r["POOLED_common"]["n"])

    out: dict[int, dict[str, float]] = {}
    for k in LEVELS:
        o, c = acc[(k, "OPEN")], acc[(k, "CLOSED")]
        total = _mean(o["all"]) - _mean(c["all"])
        f_common = _mean(o["n_common"]) / ALL_CELLS
        accuracy = f_common * (_mean(o["common"]) - _mean(c["common"]))
        out[k] = {
            "open_ever": _mean(o["ever"]), "closed_ever": _mean(c["ever"]),
            "open_all": _mean(o["all"]), "closed_all": _mean(c["all"]),
            "total": total, "acc": accuracy, "cov": total - accuracy,
            "ratio": (total - accuracy) / accuracy,
        }
    return out


def main() -> None:
    got = rebuild()

    # Guard: the rebuild must reproduce what exp011 published.
    for k in LEVELS:
        p, g = PUBLISHED[k], got[k]
        for field, tol in (("open_ever", 5e-4), ("closed_ever", 5e-4),
                           ("open_all", 5e-4), ("closed_all", 5e-4),
                           ("acc", 5e-5), ("cov", 5e-5)):
            assert abs(p[field] - g[field]) < tol, (
                f"k{k} {field}: rebuilt {g[field]:.5f}, exp011 published {p[field]:.5f}")
        assert abs(round(g["ratio"]) - p["ratio"]) <= 1, (
            f"k{k} ratio: rebuilt {g['ratio']:.1f}, exp011 published {p['ratio']}")
        # The decomposition is exact, and exp011 says so. Check it.
        assert abs((g["acc"] + g["cov"]) - g["total"]) < 1e-9

    xs = list(range(len(LEVELS)))
    labels = [f"k{k}\n{PUBLISHED[k]['occl'] * 100:.2f}%" for k in LEVELS]

    with plt.rc_context(rcparams()):
        fig, (axl, axr) = plt.subplots(1, 2, figsize=(FIGURE_WIDTH_IN, 3.2))

        # ---- what each arm ever measured
        wid = 0.36
        axl.bar([x - wid / 2 for x in xs], [got[k]["open_ever"] for k in LEVELS],
                wid, label="OPEN (fixed)", color=COLOUR_BUILT, alpha=0.85)
        axl.bar([x + wid / 2 for x in xs], [got[k]["closed_ever"] for k in LEVELS],
                wid, label="CLOSED (moving)", color=COLOUR_MEASURED, alpha=0.85)
        for x, k in zip(xs, LEVELS, strict=True):
            axl.text(x + wid / 2, got[k]["closed_ever"] + 0.02,
                     f"{got[k]['closed_ever']:.2f}", ha="center", fontsize=6.6,
                     color=COLOUR_MEASURED)
            axl.text(x - wid / 2, got[k]["open_ever"] + 0.02,
                     f"{got[k]['open_ever']:.2f}", ha="center", fontsize=6.6,
                     color=COLOUR_BUILT)
        axl.set_xticks(xs)
        axl.set_xticklabels(labels)
        axl.set_ylim(0, 1.12)
        axl.set_ylabel("fraction of the belief ever measured")
        axl.set_xlabel("occlusion level")
        axl.set_title("what each arm saw\n ", fontsize=8.6)
        axl.legend(loc="upper center", bbox_to_anchor=(0.5, -0.30), frameon=False,
                   fontsize=6.4, ncol=1)
        axl.spines[["top", "right"]].set_visible(False)

        # ---- the decomposition, log axis
        axr.bar([x - wid / 2 for x in xs], [got[k]["acc"] for k in LEVELS], wid,
                label="accuracy term (shared cells)", color=COLOUR_ACCENT, alpha=0.85)
        axr.bar([x + wid / 2 for x in xs], [got[k]["cov"] for k in LEVELS], wid,
                label="coverage term (cells OPEN never reached)",
                color=COLOUR_MEASURED, alpha=0.85)
        axr.set_yscale("log")
        axr.set_ylim(3e-4, 3.2)
        for x, k in zip(xs, LEVELS, strict=True):
            axr.text(x, 1.6, f"{got[k]['ratio']:.0f}×", ha="center",
                     fontsize=8.2, fontweight="bold", color=COLOUR_MEASURED)
        axr.set_xticks(xs)
        axr.set_xticklabels(labels)
        axr.set_ylabel("share of the all-cells gain (m)")
        axr.set_xlabel("occlusion level")
        axr.set_title("where the gain comes from\n(ratio = coverage / accuracy)", fontsize=8.6)
        axr.legend(loc="upper center", bbox_to_anchor=(0.5, -0.30), frameon=False,
                   fontsize=6.4, ncol=1)
        axr.spines[["top", "right"]].set_visible(False)

        fig.tight_layout(pad=0.4)
        save(fig, OUT)

    print("  level  occl     everOPEN everCLOSED   accuracy   coverage   ratio")
    for k in LEVELS:
        g = got[k]
        print(f"  k{k:<5d}{PUBLISHED[k]['occl'] * 100:5.2f}%   "
              f"{g['open_ever']:.4f}   {g['closed_ever']:.4f}   "
              f"{g['acc']:.5f}    {g['cov']:.5f}    {g['ratio']:6.1f}x")
    print(f"  rows read        : {len(json.loads(RESULTS.read_text())['rows'])}")
    print("  decomposition    : exact, and matches exp011's published table")


if __name__ == "__main__":
    main()
