# CLAUDE.md

Read at the start of every session. Normative. If a request conflicts with this
file, say so rather than quietly deviating.

## What this is

`bio-3d-vision` is a research project on active 3D vision — successor to
`visgraf/active-stereo` and `visgraf/bioeye`. The predecessors built good
components. Neither ever ran the loop those components were for. That is the
failure this repository exists to not repeat.

Nothing here is science yet. See `docs/state.yaml` for what actually runs.

## The rules

**Carry only what can fail.** A test fails against code. A note fails against a
session that violates it. A roadmap, a plan, a changelog, an ADR that no test
pins — none of these can be wrong, so none of them carry weight here. Inherited
numbers live in `docs/inherited-measurements.yaml` as data with provenance,
because a datum can be contradicted and a paragraph cannot. Every entry there is
`inherited`: using one without re-measuring is an assumption, and it must be
labelled as one.

**Two stimulus sources, and they are not peers.**
- *One rendered source:* Blender. When a result needs an image, it comes from
  there. Adding a second renderer needs an ADR.
- *One analytic fixture:* closed-form, milliseconds, no monocular depth cues.
  It is a **test fixture, not a scene family** — it exists so tests are fast and
  exact. The moment a finding rests on it, it has been misused. Do not grow it
  into a corpus; 42% of the predecessor's library was stimulus infrastructure.

**ADRs are written after the thing they decide has been tried.** An ADR records
what was learned by doing it, not what was planned before. If it has not been
tried, it is a question — put it in `docs/state.yaml` under open decisions. An
ADR names the test that pins it; without one it is an intention.

**Every iteration regenerates the same artifact beside the previous one's** —
same scene, same seed, written next to its predecessor rather than over it. You
compare against the last one by looking. An iteration that produces nothing to
put beside the last is not an iteration.

**`spikes/` is where you try things.** Git-tracked, and that is the whole
ceremony: no ADR, no findings entry, no definition of done, no tests required.
Nothing in `src/` or `experiments/` may import from it, and CI enforces that. A
spike's only permitted output is **a decision or a deletion** — write what you
learned into `docs/state.yaml` and delete it, or delete it. A spike that is still
sitting there unused is neither, and should go.

## Definition of done

A task is done when all of these hold:

1. **It moved something.** It moved a measurement, closed an open decision, or
   is explicitly labelled infrastructure. This clause is first because it is the
   one the predecessor lacked — its five conditions were all about artifact
   quality, so a perfectly-tested component could be added to a loop that had
   never run, and was.
2. New behaviour has a test, and the suite passes.
3. Units and frames are stated where the code states them (see below).
4. `docs/state.yaml` is updated if any of it changed.
5. The diff contains nothing that was not asked for.

"Infrastructure" is a real and honest label — scaffolding, CI, a refactor. Use
it. What it is not is a default: if most tasks in a row are infrastructure, the
project is not moving and that is worth saying out loud.

## Where authority lives

**Units and frames are declared at the function that returns the value, in its
docstring — not here.** This file does not restate them, deliberately.

The predecessor's CLAUDE.md §3 declared depth to be "metres, cyclopean frame".
It was false: `geometry/oculomotor.py:337-348` records that the value is actually
`z` in the rectified left-camera frame, that the two agree only at zero
elevation, and that §3 is the wrong side of the contradiction. The clause sat
there being read at the start of every session, and nothing could catch it —
because a sentence in a governance file has nothing to fail against. A docstring
beside the return statement is checkable against the code under it.

So: this file governs process. Code governs facts about code. When they
disagree, the code is the finding and this file is the bug.

## Working agreement

- **Branch.** `feat/…`, `fix/…`, `exp/…`, `docs/…`, `spike/…`. Never commit to
  `main`.
- **Never commit or push unless asked.** Never force-push or rewrite history.
- **Never weaken, skip, or delete a failing test to get green**, and never move a
  tolerance to make a number pass. A failing test is a result.
- **Never add a dependency without asking.**
- **Say when a number is measured and when it is assumed.** An assumed input
  that goes unnamed is the defect; the assumption itself is not.
- **Ask when the spec is ambiguous.** A wrong assumption corrected now is much
  cheaper than a plausible result trusted for a month.
- Uncertain about a numerical result? Say so, and propose the check that settles
  it.

## Process

`docs/workflow.md` — the four-station loop and its rules.
`docs/state.yaml` — written by Code, read by Chat, never the reverse.

## Commands

```bash
pytest -q                  # suite
ruff check src tests       # lint
ruff format src tests      # format
mypy src                   # types
```
