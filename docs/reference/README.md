# Reference prose — NON-AUTHORITATIVE

These files are verbatim copies of `experiments/*/findings.md` from
`visgraf/active-stereo` at `3f7a263011d9c5c53a4733957ac34cd28c2e85ba`. They are
byte-identical to the originals; nothing has been edited, corrected, or annotated.

**They are background, not a source of fact for this repository.**

The citable artifact is [`../inherited-measurements.yaml`](../inherited-measurements.yaml).
Cite an `id` from that file. Do not cite a number out of this directory: the prose
here is not a record that a future measurement can contradict, it carries claims that
the record deliberately excludes (configuration values, thresholds, arguments,
speculation), and at least one number in it was corrected in place after first
writing (exp004, "up to 12×" → 34.5×) — so a quotation from here has no way to
signal which version it is.

Kept because the record holds values and provenance, not reasoning. When you need to
know *why* a measurement was taken, what it was expected to show, what threats were
declared, or what the authors concluded, that is here and nowhere else.

| file | experiment | run SHA in `active-stereo` |
|---|---|---|
| `exp001-findings.md` | matcher baseline (RDS) | **`(pre-commit)`** — not recoverable |
| `exp002-findings.md` | energy-model validation (RDS) | `965a3ad` |
| `exp003-findings.md` | appearance and matching (rendered chart) | `3fe9985` |
| `exp004-findings.md` | real-data transfer (Middlebury 2014) | `8b067fc` |
| `exp005-findings.md` | energy decoder (RDS + Middlebury) | `5f407bd`, `83d48ab` |
| `exp006-findings.md` | multiscale energy (RDS + Middlebury) | `4ea8400`, `fc34275` |
| `exp007-findings.md` | MiddEval3 training placement | `65476a0` |

`visgraf/bioeye` at `e90817018e629ce1cd23af0c9e8bc4a6aa15daff` contributes nothing to
this directory: it has no findings files and no tests. See the `gap-` entries in the
record.
