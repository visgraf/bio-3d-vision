"""Shared figure style. Every make_*.py in this directory imports from here.

WIDTH AND FONT, SET ONCE
------------------------
:data:`FIGURE_WIDTH_IN` is 6.5 in, which is ``\\textwidth`` for the report's
``article`` class at letterpaper with 1 in margins (``report/main.tex``), so a
figure included at ``width=\\textwidth`` is reproduced 1:1 and its type is never
rescaled. The font is DejaVu Serif at 9 pt -- matplotlib ships it, so the figures
build identically on any machine without a font search, and 9 pt against the
document's 11 pt body reads as label weight.

DETERMINISM, AND ITS LIMIT
--------------------------
:func:`save` suppresses the PDF ``CreationDate`` and pins ``svg.hashsalt``, which
is what makes two runs on ONE machine byte-identical. It does NOT make a
committed PDF byte-comparable across machines -- see the note in
``make_scanpath.py``. The check that travels is regenerating and comparing the
DRAWN QUANTITIES, which is why every script here prints the numbers it drew and
asserts them against the ledger.
"""

from __future__ import annotations

import pathlib
from typing import Any

import matplotlib

matplotlib.use("Agg")  # no display; deterministic rasterisation of the vector path

import matplotlib.pyplot as plt  # noqa: E402

#: Exactly \textwidth. See the module docstring.
FIGURE_WIDTH_IN = 6.5
FONT_SIZE_PT = 9.0
FONT_FAMILY = "DejaVu Serif"

#: Status palette, shared by the architecture map and the foreclosure timeline so
#: "measured" means the same colour in both.
COLOUR_MEASURED = "#1b7837"
COLOUR_BUILT = "#4575b4"
COLOUR_HYPOTHETICAL = "#9e9e9e"
COLOUR_QUALIFIED = "#d94801"
COLOUR_ACCENT = "#762a83"


def rcparams() -> dict[str, Any]:
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


def save(fig: Any, out: pathlib.Path) -> None:
    """Write ``fig`` to ``out`` as a vector PDF with no creation timestamp."""
    fig.savefig(out, format="pdf", metadata={"CreationDate": None})
    plt.close(fig)
    print(f"wrote {out}")
