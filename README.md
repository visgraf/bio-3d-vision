# bio-3d-vision

Experiments on active 3D vision: does choosing where to look improve binocular
depth estimation?

The framework models stereo as a six-layer active Bayesian inference loop over
biologically grounded oculomotor geometry — eyes rotating about fixed centres,
vergence setting the horopter, torsion determined by gaze under Listing's law —
with a belief accumulated across fixations.

Thirteen pre-registered experiments answer the question as posed, and give a
specific reason to doubt it was posed correctly. **The findings are in
[`report/`](report/); this file is a map to the record behind them.**

## The record

The distinctive thing about this repository is not the code. It is a complete,
public account of what was decided, on what evidence, and what was ruled out.

| | |
|---|---|
| [`docs/state.yaml`](docs/state.yaml) | The **decision ledger**. Every foreclosure with its evidence, its stated limits and the cost of reopening it; every open decision; every falsifier verdict; the plan and its amendments. |
| [`docs/inherited-measurements.yaml`](docs/inherited-measurements.yaml) | The **measurement ledger**. Every number with its provenance — the commit that produced it, the environment it was measured in, and its status: measured here, inherited from a predecessor, or a recorded gap. Carried *methods* are marked the same way, including the ones never examined. |
| [`experiments/`](experiments/) | One directory per experiment: `preregistration.md` written and committed **before** the runner existed, then `run.py`, `results.json`, `verdicts.json` and `findings.md`. |
| [`report/claims-verified.md`](report/claims-verified.md) | Every factual claim in the report, checked at source, marked confirmed, corrected, under-qualified or unsupported. |
| [`docs/workflow.md`](docs/workflow.md), [`CLAUDE.md`](CLAUDE.md) | How the work was done and the rules it ran under. |

Corrections are recorded as amendments, never as edits. Where a conclusion was
drawn and later qualified, both appear with the evidence that moved between
them. The history is forward-only.

## Reading it

Start with the report. If you want the evidence behind a specific claim, its
foreclosure id (`fc-0NN`) or measurement id (`bio-0NN`) resolves in the two
ledgers above, and every experiment's `findings.md` states what it measured,
what it could not, and which of its falsifiers fired.

`docs/state.yaml`'s `sequence` block records where the work is and what remains.
Note the distinction it draws: the *position* half is derivable from the ledger;
the *plan* half is intent and is marked as such.

## The code

`src/bio3dvision/` is a flat package, deliberately — a directory per layer
invites filling it, and in the predecessor that produced a library four tenths
stimulus infrastructure and one tenth the three layers the framework is named
for.

`oculomotor.py` geometry · `sampling.py` index-to-ray, pinhole and spherical ·
`matching.py` the front end · `loop.py` the fixation loop · `belief.py` the
head-anchored belief · `policy.py` the gaze policies · `fixture.py` the analytic
stimulus · `scene_model.py` and `blender_*.py` the rendered one.

`spikes/` is a lane with different rules: no decision record, not importable by
the library or by experiments, and its only permitted output is a decision or a
deletion.

## Running it

pip install -e ".[dev]" # add ",blender" for the EXR reader
pytest
make -C report # builds report/main.pdf; needs a TeX installation


Rendering needs Blender 5.2 LTS on `PATH`; tests that require it skip with a
stated reason rather than passing quietly. CI runs the suite on every pull
request and compiles the report.

## Lineage

Two predecessors, both public, both cited in the report at the commits this
repository pinned them to:

- **[`visgraf/bioeye`](https://github.com/visgraf/bioeye)** — a thin vertical
  slice: a few hundred lines, one file, running end to end. It closed the
  accumulation loop and not the perception–action loop.
- **[`visgraf/active-stereo`](https://github.com/visgraf/active-stereo)** — a
  full implementation with verified geometry and a decision record. The loop
  never ran.

This repository was built to have the running loop of the first and the rigour
of the second, with a standing rule that a working measurement comes before
infrastructure. What was carried across is marked as inherited — priors awaiting
re-test, not established facts.

## Provenance

This project was carried out by one researcher working with two AI surfaces: a
conversational one for derivation, experiment design and adversarial review, and
an agentic coding one that implemented and verified against the files. The
researcher directed the work, took every decision recorded as a foreclosure, and
merged every change.

Both surfaces produced corrections that reached the record, in both directions,
and those corrections are in it rather than smoothed out of it. Appendix A of
the report describes the arrangement and why authorship is attributed as it is.
