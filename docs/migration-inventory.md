# Migration inventory — active-stereo and bioeye

A read-and-report classification of the contents of the two reference repositories
against the carry criterion. No code was copied out of `.reference/`; nothing in
either reference was modified.

## Provenance

| Item | Value | Status |
|---|---|---|
| `visgraf/active-stereo` `main` | `3f7a263011d9c5c53a4733957ac34cd28c2e85ba` | measured (`git ls-remote`, then `rev-parse` after checkout) |
| `visgraf/bioeye` `main` | `e90817018e629ce1cd23af0c9e8bc4a6aa15daff` | measured (same) |
| active-stereo tracked files | 246 | measured (`git ls-tree -r HEAD`) |
| bioeye tracked files | 20 | measured (same) |
| Clones | fresh, into `.reference/`, no existing local copy used | measured |

All four preconditions stated in the task were verified before setup: this repository
had exactly one commit (`e3a17cf`, `chore: initial stub`) with only `README.md` and
`.gitignore` tracked, and `.gitignore` contains `.reference/`.

## Marking convention

Every row is marked **[M] measured** — I opened and read the file (or the named
region of it) — or **[A] assumed** — I did not open it, and the classification is
inferred from path, name, size, and from measured cross-repository facts such as the
test-import map and the ADR-mention map. Assumed rows are classified; they are not
verified.

Files read in full: `src/activestereo/geometry/{__init__,horopter,oculomotor,projection}.py`,
`src/activestereo/types.py`, `tests/conftest.py`, `tests/unit/{test_geometry,test_oculomotor,test_projection_toedin,test_scaling}.py`,
`CLAUDE.md`, `docs/decisions/README.md`, `docs/roadmap.md`, `.claude/commands/*.md` (all four),
and every bioeye file except the PNG/EXR binaries and `.gitignore` beyond its first 20 lines.
Read in part: `tests/unit/{test_scenes,test_middlebury,test_adr_hook,test_hook_wiring}.py`,
`docs/method/*.md` (headers and first findings), `CONTRIBUTING.md`, `docs/workflow.md`,
`pyproject.toml`, `.github/workflows/ci.yml`, `LICENSE`, all 18 ADR titles and status lines.

## The criterion as applied

Carry only what can fail.

- **carry** — the item states something a later thing can violate: a test (fails
  against code), a method note or working rule (fails against a session that
  violates it), a gate (fails in CI), a type or convention that tests assert
  against, and an ADR pinned by a surviving test — the rationale for a live
  constraint, without which the test gets deleted in six months.
- **leave** — the item records intent, history, or output: roadmaps, plans,
  changelogs, briefings, lab-notebook entries, findings, slides, rendered figures,
  and ADRs no test pins. These cannot fail.
- **decide** — the criterion genuinely does not resolve it.

Two consequences of applying this literally, both of which shape the tables below.
First, `can fail` is a *necessary* condition, not a sufficient one: where an item
can fail but is redundant with a better-pinned equivalent, that is stated as the
reason for leaving it. Second, for code, "can fail" is read as "a test pins it" —
code that nothing asserts against can error but cannot be wrong, and unpinned
source (`scripts/`, `experiments/*/run.py`) is classified accordingly.

The criterion is not imported. active-stereo already states it, in
`.claude/commands/adr.md`: *"Name the test(s) that pin the decision. If none exist,
say so explicitly and propose them — an ADR without a test is an intention, not a
decision."* [M]

---

# Part 1 — active-stereo

## 1.1 `src/` (per file)

Measured cross-cutting fact: `StereoRig` (`src/activestereo/types.py:31-34`) declares
`baseline`, `focal_px`, `principal_point`, `vergence`, and `focal_px` has **no
default** and must be positive. Every construction of a rig therefore carries a
pinhole focal length, whether or not the code under test reads it. This is the
single most consequential fact in this report; see §3.

| Path | Class | Reason |
|---|---|---|
| `src/activestereo/types.py` | carry | [M] `StereoRig`, `Fixation`, `Estimate`, `RefusalReason`, `FixationProposal`, `TargetRefused`. Pinned by `test_types.py` and imported by 20 test modules — the most heavily asserted file in the repo. |
| `src/activestereo/geometry/__init__.py` | carry | [M] The 16-symbol public surface every geometry test imports through; a dropped re-export is a red suite. |
| `src/activestereo/geometry/oculomotor.py` | carry | [M] `eye_rotations`, `rectification_rotation`, `target_to_fixation`, `fixation_distance/point`, `is_forward_gaze`. Pinned by 40 tests. The successor's ray/direction layer is this file's subject. |
| `src/activestereo/geometry/projection.py` | carry | [M] Holds both models side by side — off-axis (`depth_to_disparity`) and toed-in (`project_toed_in`). Pinned by 19 tests. This *is* the swappable-projection boundary the plan assumes. |
| `src/activestereo/geometry/horopter.py::vieth_muller_points` | carry | [M] Pinned by 4 tests in `test_projection_toedin.py`; reads `fixation.vergence`, intrinsics-free. |
| `src/activestereo/geometry/horopter.py::vieth_muller_radius` | carry | [M] Pinned by 2 tests in `test_geometry.py`. |
| `src/activestereo/geometry/horopter.py::vieth_muller_circle` | leave | [M] No test references it. Its own module docstring calls the file "documentation of where L1 is heading, not a description of what L1 currently does" — unpinned aspiration. |
| `src/activestereo/scaling/{metric,fusion}.py` | carry | [A] `scale_to_depth`, `fuse_mle` pinned by 6 tests in `test_scaling.py` [M]. The scaling closure is asserted, not just documented. |
| `src/activestereo/control/{kalman,vergence}.py` | carry | [A] Pinned by `test_control.py` and `tests/regression/test_adr0001_windowed_vergence.py`. |
| `src/activestereo/policy/{saliency,foveation}.py` | carry | [A] Pinned by `test_adr0002_saliency_validity.py`, `test_adr0003_foveal_confinement.py`; `policy.foveation` and `policy.saliency` are imported by tests [M]. |
| `src/activestereo/policy/gaze.py` | leave | [A] 38 lines; no test module imports it and no regression test names it. Unpinned. |
| `src/activestereo/encoding/{base,energy,multiscale}.py` | carry | [A] Pinned by `test_encoding.py`, `test_multiscale_encoder.py`. |
| `src/activestereo/inference/{base,block,sgbm,energy_decoder}.py` | carry | [A] Pinned by `test_inference.py`, `test_energy_decoder.py`. |
| `src/activestereo/metrics.py` | carry | [A] Pinned by `test_metrics.py` (212 lines) and by ADR-0011's mask taxonomy. |
| `src/activestereo/scenes/{base,registry,rds}.py` | carry | [A] Pinned by `test_scenes.py`, `test_scene_registry.py`. `rds.py` is the analytic stimulus generator with closed-form ground truth. |
| `src/activestereo/scenes/{middlebury,middeval3}.py` | carry | [A] Pinned by `test_middlebury.py` (447 lines) and `test_middeval3.py`. Falsifiable corpus adapters; bound to a corpus the successor has not committed to, which is a scope question, not a criterion question. |
| `src/activestereo/scenes/blender.py` | carry | [A] 722 lines, pinned by `test_blender_loader.py` (585 lines). |
| `src/activestereo/scenes/depthmaps.py` | leave | [A] 93 lines; no test module names it. Unpinned. |
| `src/activestereo/utils/windows.py` | carry | [A] Pinned by `test_utils_windows.py`. |
| `src/activestereo/utils/{config,runs}.py` | leave | [A] Run-id and config plumbing; no test module names them. Unpinned. |
| `src/activestereo/cli.py` | leave | [A] Entry point; unpinned. |
| `src/activestereo/{io,viz}/__init__.py` | leave | [M] 5 and 3 lines; no public symbols. |
| `src/activestereo/{control,encoding,inference,policy,scaling,scenes,utils}/__init__.py`, `src/activestereo/__init__.py` | carry | [A] Re-export surfaces the tests import through. |

## 1.2 `tests/` (per file)

Every test carries: a test is the paradigm case of a thing that fails against code.
The reason column therefore records *what* each pins, which is the information the
inventory exists to preserve.

| Path | Class | Reason |
|---|---|---|
| `tests/conftest.py` | carry | [M] `rig`, `parallel_rig`, `rng`, `synthetic_pair`, `depth_estimate`. Determinism by construction — no global RNG. Note: `rig` fixes `focal_px=800.0`; see §3. |
| `tests/unit/test_geometry.py` | carry | [M] 7 tests: off-axis projection round trip, sign convention, horopter radius. |
| `tests/unit/test_oculomotor.py` | carry | [M] 40 tests. The largest and most load-bearing geometry file: Listing, Helmholtz, composition order, rectification, the pixel→rotation boundary, refusal contract, variance propagation. |
| `tests/unit/test_projection_toedin.py` | carry | [M] 12 tests: per-eye toed-in projection, vertical disparity, the ADR-0007 item-4 horopter closure. |
| `tests/unit/test_types.py` | carry | [A] Pins `Fixation`/`StereoRig` validation and the boundary result types (`test_boundary_result_types_are_frozen`, line 150) [M]. |
| `tests/unit/test_scaling.py` | carry | [M] 6 tests; 2 touch geometry. Pins `var(Z) ~ Z^4`. |
| `tests/unit/test_scenes.py` | carry | [A] 20 tests; 1 touches geometry [M]. Pins RDS occlusion behaviour and the `known` mask (ADR-0011). |
| `tests/unit/test_middlebury.py` | carry | [A] 27 tests; 1 touches geometry [M]. Pins PFM parsing, calib→rig mapping, downsampling. |
| `tests/unit/test_middeval3.py` | carry | [A] Pins the MiddEval3 adapter and the mm→m boundary conversion. |
| `tests/unit/test_scene_registry.py` | carry | [A] Pins config inheritance (`INHERITED_KEYS`) and the splat bug it records. |
| `tests/unit/test_blender_loader.py` | carry | [A] 585 lines; pins ADR-0010 multi-layer EXR and ADR-0003. |
| `tests/unit/test_metrics.py` | carry | [A] Pins the ADR-0011 four-mask taxonomy. |
| `tests/unit/test_encoding.py`, `test_multiscale_encoder.py` | carry | [A] Pin the binocular energy model and its multiscale extension. |
| `tests/unit/test_inference.py`, `test_energy_decoder.py` | carry | [A] Pin matcher and decoder behaviour. |
| `tests/unit/test_control.py` | carry | [A] Pins the vergence/Kalman control path. |
| `tests/unit/test_utils_windows.py` | carry | [A] Pins windowing under ADR-0002 masking. |
| `tests/unit/test_adr_hook.py` | carry | [M, header] Pins the decision table and fail-closed direction of `.claude/hooks/adr_append_only.py`, hermetically, as a subprocess. |
| `tests/unit/test_hook_wiring.py` | carry | [M, header] Pins that `settings.json` actually invokes the hook — written because a merge silently orphaned the script and the suite stayed green. |
| `tests/regression/test_adr0001_windowed_vergence.py` | carry | [A] Pins ADR-0001. |
| `tests/regression/test_adr0002_saliency_validity.py` | carry | [A] Pins ADR-0002, the masking rule CLAUDE.md §3 says caused a real failure. |
| `tests/regression/test_adr0003_foveal_confinement.py` | carry | [A] Pins ADR-0003. |
| `tests/regression/test_adr0012_cross_check_tie_rounding.py` | carry | [A] Pins ADR-0012 tie-rounding. |
| `tests/regression/test_exp003_textureless_hallucination.py` | carry | [A] Pins the exp003 hallucination finding as a permanent guard. |
| `tests/integration/test_rds_end_to_end.py` | carry | [A] Pins the RDS pipeline end to end under ADR-0002. |
| `tests/integration/__init__.py` | carry | [A] Package marker for the above. |

## 1.3 `docs/decisions/` (per file)

Measured ADR→test map (from `grep -roE "ADR-[0-9]{4}" tests/`): 0001, 0002, 0003,
0006, 0007, 0010, 0011, 0012, 0013, 0014, 0015, 0016, 0017 are named in `tests/`.
0004, 0005, 0008, 0009 are not.

| Path | Class | Reason |
|---|---|---|
| `0001-windowed-median-vergence.md` | carry | [A] Pinned by `test_adr0001_windowed_vergence.py` [M, via map]. |
| `0002-saliency-validity-masking.md` | carry | [A] Pinned by 7 test modules — the most-cited ADR in the suite. |
| `0003-foveal-confinement-linearization-error.md` | carry | [A] Pinned by `test_adr0003_foveal_confinement.py` and `test_blender_loader.py`. |
| `0004-layer-module-boundaries.md` | leave | [M, status+map] No test pins it. Searched for an import-linter or boundary test in `tests/`, `pyproject.toml` and `ci.yml`: none exists. The six-layer split is convention, not a checked constraint. |
| `0005-uncertainty-first-class.md` | carry | [M, map] Not cited by name in any test, but its decision is made concrete in the `Estimate` type, whose shape invariant and `valid`/`precision` semantics `test_types.py` pins and which 10 test modules assert against. The constraint fails loudly; the citation is simply absent. |
| `0006-scenes-as-a-separate-package.md` | carry | [A] Pinned by `test_middlebury.py` ("the stimulus must not be produced by the estimator's code path") [M]. |
| `0007-offaxis-not-toein.md` | carry | [A] Status is *Superseded by 0013*, but `test_projection_toedin.py` pins its item-4 closure explicitly [M]. A superseded ADR with a live test is still the rationale for that test. |
| `0008-python-floor-312.md` | carry | [M] Not named in `tests/`, but pinned by `pyproject.toml:10` `requires-python = ">=3.12"` and the CI matrix `["3.12","3.14"]` with a blocking mypy gate. A gate that fails is a pin. |
| `0009-blender-api-version-adaptive.md` | leave | [M, map] Not named in `tests/`; one mention in `src/`. Nothing fails if the decision is reversed. |
| `0010-multilayer-exr-not-compositor.md` | carry | [A] Pinned by `test_blender_loader.py`. |
| `0011-ground-truth-known-mask.md` | carry | [A] Pinned by 5 test modules. |
| `0012-middlebury-real-data-corpus.md` | carry | [A] Pinned by 3 test modules including a dedicated regression test. |
| `0013-fixation-as-oculomotor-state.md` | carry | [A] Pinned by `test_oculomotor.py`, `test_projection_toedin.py`, `test_types.py`. Supersedes 0007; the decision the successor's geometry layer inherits. |
| `0014-listing-coefficient-as-parameter.md` | carry | [M, title+status] Pinned by `test_oculomotor.py`. Its *prediction* (null at k=0.25) was corrected by 0016; its *decision* (k is a parameter, not a constant) stands and is pinned by the `k` argument's presence in three signatures. |
| `0015-helmholtz-gaze-composition.md` | carry | [A] Pinned by `test_oculomotor.py` (5 mentions). The composition order the whole fixation geometry rests on. |
| `0016-plane-of-regard-alignment-optimum.md` | carry | [A] Pinned by `test_oculomotor.py` and `test_projection_toedin.py` (9 mentions, the joint-most). Records that k = 1/2, not 0.25, zeroes vertical disparity in the plane of regard. |
| `0017-rectification-rotation-member.md` | carry | [A] Pinned by `test_oculomotor.py`. Selects one member of the R_rect family; see §3.5 for the one place its criterion is irreducibly pinhole. |
| `0000-template.md` | carry | [M] The ADR form itself, including the *Alternatives considered* requirement. A template fails against a future ADR that ignores it. |
| `docs/decisions/README.md` | carry | [M] Self-describing as "a table of contents, not a decision". Carries because its footer records the enforcement mechanism and its known gap (Bash is a separate tool path; `sed -i` does not pass through the hook) — a boundary statement a future session can violate. |

## 1.4 `docs/method/` (per file)

The paradigm carry case: each fails against a future session that violates it.

| Path | Class | Reason |
|---|---|---|
| `001-enforcement-and-disclosure.md` | carry | [M] Enforcement and disclosure are separate boundaries; routing around a deny rule is a breach even when disclosed. Already normative in CLAUDE.md §4. |
| `002-state-across-surfaces.md` | carry | [M] Stale cross-surface state, and probes that miss their target. Fails against any session reasoning from a snapshot. |
| `003-premature-reduction.md` | carry | [M] The reduction ledger — `abs`, `max`, difference, shared mask — each annihilating the property under test. Directly governs how the geometry tests in §3 are written (per-eye rather than differential). |
| `004-reproducibility-and-the-reverse-direction.md` | carry | [M] `max` over a random point cloud annihilates reproducibility; and the measured/assumed disclosure rule this document's own marking convention obeys. |

## 1.5 Remaining active-stereo contents (per directory, homogeneous)

| Path | Class | Reason |
|---|---|---|
| `CLAUDE.md` | carry | [M] Normative constitution: invariants, closures, the working agreement, the handoff contract. Fails against a session that violates it. **Carried with a known defect:** §3 states depth `Z` is "metres, cyclopean frame", and `oculomotor.py:337-348` states that invariant is false — L4 returns rectified-left-camera `z`, and the two coincide only at `elevation_down == 0`. The contradiction is recorded in the source, not in §3. |
| `.claude/commands/` (4 files) | carry | [M] All four are audit or construction procedures with pass/fail semantics: `check-invariants.md` (audits §3 and the three closures), `regress.md` (test-first, must fail before the fix), `adr.md` (name the pinning test), `plan-experiment.md` (falsifiable hypothesis or say so). |
| `.claude/hooks/adr_append_only.py` | carry | [M, via its tests] A security control that fails closed, pinned by `test_adr_hook.py`. |
| `.claude/settings.json` | carry | [A] Pinned by `test_hook_wiring.py` [M, header] — the deployment, not just the script. |
| `.github/workflows/ci.yml` | carry | [M, grep] The gate that makes every carried test fail loudly: python matrix, ruff, mypy, pytest. |
| `pyproject.toml` | carry | [M, grep] Dependency, python-floor, lint, type and pytest configuration. Fails at build/lint/type time. |
| `LICENSE` | carry | [M] MIT, © 2026 Luiz Velho, VISGRAF/IMPA. A licence constrains redistribution; the successor needs one. |
| `CONTRIBUTING.md` | carry | [M, head] Branch naming, issue-before-code, criteria-before-results, definition of done. Constraints a contributor can violate. |
| `.github/ISSUE_TEMPLATE/`, `.github/pull_request_template.md` | carry | [A] Forms that require a hypothesis and acceptance criteria before code — the same discipline as `plan-experiment.md`. |
| `.gitignore`, `.claudeignore` | carry | [A] Hygiene; a wrong ignore rule is a detectable defect. |
| `.devcontainer/`, `.vscode/` | leave | [A] Editor and container convenience. Nothing fails if absent. |
| `Makefile` | leave | [A] Command shortcuts over `pytest`/`ruff`/`mypy`, which CI already gates. Redundant with a carried gate. |
| `README.md` | leave | [A] Descriptive front matter. |
| `CHANGELOG.md` | leave | [M, criterion] Named in the criterion as an intent/history document. |
| `docs/roadmap.md` | leave | [M] Named in the criterion, and self-declaring: *"Unlike findings or ADRs, there is nothing in the repo to verify it against."* Phases A–E, including "Phase E — geometry consolidation". |
| `docs/plans/` (2 files) | leave | [M, criterion] `fixation-migration.md`, `toed-in-projection.md`. Plans. Note: `test_projection_toedin.py` cites `fixation-migration.md:69-85` for the vacuous-pass guard — the *guard* carries as a test; the plan does not. |
| `docs/architecture.md` | **decide** | [A] Half restates ADR-0004's layer split (unpinned → leave-shaped); half documents the three closures, which CLAUDE.md §1 declares must be preserved by any refactor and `check-invariants.md` audits (carry-shaped). The criterion does not say which half governs the file. |
| `docs/workflow.md` | **decide** | [M, head] Half duplicates CLAUDE.md §5's normative handoff rules (carry-shaped); half describes an active-stereo-specific surface arrangement — Overleaf bridge, Cowork, GitHub issue ledger (leave-shaped). Same unresolved split. |
| `docs/briefings/` (8 files, 1666 lines) | leave | [A] Narrative summaries of the architecture and exp001–exp006. Records, not constraints. |
| `docs/lab-notebook/` (14 files, 1895 lines) | leave | [A] Dated session records. Cited by ADRs and docstrings as provenance; provenance is history. |
| `docs/issues/` (1 file) | leave | [A] An issue write-up, superseded by ADR-0013. |
| `experiments/` (7 experiments × `run.py`/`config.yaml`/`findings.md`) | leave | [A] `findings.md` are records pinned to a run-id and SHA — history. `run.py` and `config.yaml` are unpinned by any test: they can error, but nothing detects a wrong answer. The one exp003 finding that became a constraint already carries, as `tests/regression/test_exp003_textureless_hallucination.py`. |
| `configs/` (11 files) | leave | [A] Dataset, matcher and scene parameter sets. Measured: no test reads `configs/` — the four `tests/` mentions are prose in docstrings only. A parameter file cannot fail. |
| `scripts/` (14 files, 4811 lines) | leave | [A] CLI entry points, fetchers, Blender renderers, figure and deck builders. Unpinned by any test. `render_stereo.py` (1112 lines) holds the render contract, but nothing asserts it. |
| `slides/` (4 decks, 45 files) | leave | [A] Generated `.png` figures, `data.json`, and `slides.md`. Outputs. |
| `paper/` (3 files) | leave | [A] `main.tex`, `refs.bib`, README; Overleaf-synced prose. |
| `data/` (2 files) | leave | [M, via CLAUDE.md §2] Pointers and a `.gitkeep`; "never write to `data/`". |

---

# Part 2 — bioeye

Measured structural facts. bioeye has **no tests** — not a `tests/` directory, not a
test file, not an assertion outside `argparse`. It is 4 Python files, 1 data
directory, 1 environment file, and 12 rendered PNGs. Its geometry is a rectified
parallel rig throughout: `d_gt = f_px * baseline / Z`, `D = f*I/d_fix`,
`Z = D - (D^2/I)*(eta/f)`. There is no rotation, no SO(3), and no ray anywhere in
the repository. Its state variable for fixation is a **scalar disparity in pixels**
(`ActiveStereo.vergence` returns `d_fix`), not a direction.

Classified at function granularity for `active_stereo_demo.py`, since that one
432-line file holds all six layers and the parts differ.

| Path / item | Class | Reason |
|---|---|---|
| `active_stereo_demo.py::make_synthetic_scene` (L47-77) | carry | [M] The analytic scene generator. Fronto-parallel cards on a background, right eye produced by inverse-warping left through the ground-truth disparity, so a correct matcher recovers `d_gt = f*I/Z` exactly. Falsifiable against its own closed form. |
| `active_stereo_demo.py::ActiveStereo` (L225-313) | carry | [M] The loop: `step` (argmax-variance fixation → vergence → foveated metric measurement → precision-weighted fusion) and `run` (RMSE per fixation). The behavioural claim — RMSE falls with fixation count — is falsifiable and nothing currently asserts it. |
| `active_stereo_demo.py::scale_to_depth` (L208-218) | carry | [M] The vergence-scaling relation and its Jacobian, first-order-exact at fixation. Falsifiable in closed form. Stated entirely in pixels and focal length. |
| `active_stereo_demo.py::save_result_fig` (L370-395) | carry | [M] The four-panel figure, measured as `plt.subplots(2, 2)`: posterior mean depth with scanpath overlay, posterior std, \|error\| vs ground truth, depth RMSE vs fixation number. What carries is the panel set — the claim each panel makes — not the matplotlib. |
| `active_stereo_demo.py::vergence_scaling_experiment` (L319-352) | **decide** | [M] Holds a genuinely falsifiable analytic claim — a fractional vergence error `e` produces relative depth error `(1+e)^2 - 1 ≈ 2e` — and computes the measured curve against the `2\|e\|` reference. But it only plots the comparison; nothing asserts agreement. Carry-shaped as a claim, leave-shaped as a figure, and the criterion does not resolve which it is. |
| `active_stereo_demo.py::{cost_volume,decode_disparity,lr_consistency}` (L112-160) | leave | [M] Box-aggregated SSD cost volume, WTA + parabola subpixel, LR consistency. Can fail, but redundant with `src/activestereo/inference/block.py`, which is pinned by `test_inference.py`. |
| `active_stereo_demo.py::{front_end_block,front_end_sgbm}` (L168-202) | leave | [M] Matcher back ends, redundant with `inference/{block,sgbm}.py`. The README records that SGBM's variance is "a roughness heuristic" — the same anti-calibration active-stereo measured in exp004/exp006 and already carries as a finding there. |
| `active_stereo_demo.py::load_blender_scene` (L81-105) | leave | [M] Loads `left.png`/`right.png`/`depth_left.exr`/`params.json`. Redundant with `scenes/blender.py`, which is pinned by a 585-line test and implements ADR-0010 multi-layer EXR instead of a separate depth pass. |
| `active_stereo_demo.py::{save_scene_fig,main}` | leave | [M] A three-panel input figure and the argparse entry point. Outputs and plumbing. |
| `generate_scene_blender.py` | leave | [M, head] Builds a textured Blender scene from scratch. Unpinned; redundant with active-stereo's `scripts/render_stereo.py` and `scenes/blender.py`. |
| `render_stereo_blender.py` | leave | [M, head] Stereo + depth render helpers and the `params.json` data contract. Unpinned. Its contract — parallel cameras offset along local X — is the off-axis model ADR-0007 already records. |
| `README.md` | leave | [M] Descriptive, including the layer map and a "what it deliberately drops" list. The dropped items (process dynamics, trans-saccadic remapping, AC/A, vertical-disparity cue, non-myopic policy) are intent, not constraints. |
| `data/` (`left.png`, `right.png`, `depth_left.exr`, `params.json`) | leave | [M for `params.json`; A for binaries] One rendered 320×240 fixture set. An artefact. |
| `out_block/`, `out_sgbm/`, `out_blender/`, `fig_result.png` (10 PNGs) | leave | [A] Rendered outputs of the three demo runs. |
| `environment.yml` | leave | [M] Conda env (python=3.12, numpy, scipy, matplotlib, imageio, opencv). Redundant with active-stereo's `pyproject.toml`, which is stricter and CI-gated. |
| `.gitignore` | leave | [M, head] Stock 218-line Python ignore file. Redundant with the one already committed here. |

---

# Part 3 — Geometry-test analysis

## 3.1 Scope and method

**Measured.** Tests that touch `geometry/` were identified by import, not by prose:
`grep -rn "geometry" tests/` returns 9 files, of which 6 actually import from
`activestereo.geometry`. The other three (`test_types.py`, `test_blender_loader.py`,
`test_exp003_textureless_hallucination.py`) mention the word in a docstring only and
were excluded — verified line by line.

- **Core set (59 tests):** the three files whose subject *is* `geometry/` —
  `test_geometry.py` (7), `test_oculomotor.py` (40), `test_projection_toedin.py` (12).
- **Incidental set (4 tests):** single-function uses from other layers'
  files — `test_scaling.py` (2), `test_scenes.py` (1), `test_middlebury.py` (1).

Counts are of test functions as written. Six functions in `test_oculomotor.py` and
none elsewhere are `@pytest.mark.parametrize`d; expanding them would raise the total
without changing any classification, since parametrisation varies angles and pixels,
never the presence of an intrinsic.

**Classification applied.** The three-way split turns on what the *assertion* needs:

- **direction-only** — the assertion is on unit vectors, rotations, angles or SO(3)
  relations, and no focal length, principal point or pixel coordinate appears
  anywhere in the test.
- **pinhole-dependent** — the assertion's truth depends on a pinhole intrinsic: it
  asserts a pixel-valued quantity, or names `focal_px` / `principal_point` directly.
- **mixed** — the assertion needs no intrinsic, but the fixture or setup constructs
  one. In practice this is almost always the `StereoRig` type itself.

## 3.2 Counts

| Set | direction-only | mixed | pinhole-dependent | total |
|---|---|---|---|---|
| `test_geometry.py` | 0 | 2 | 5 | 7 |
| `test_oculomotor.py` | 4 | 32 | 4 | 40 |
| `test_projection_toedin.py` | 0 | 5 | 7 | 12 |
| **Core total** | **4** (6.8%) | **39** (66.1%) | **16** (27.1%) | **59** |
| Incidental | 0 | 0 | 4 | 4 |
| **Grand total** | **4** (6.3%) | **39** (61.9%) | **20** (31.7%) | **63** |

The headline number: **43 of 59 core geometry tests (72.9%) assert nothing that
requires a focal length, a principal point, or a pixel coordinate.**

The reason `mixed` dominates rather than `direction-only` is one measured structural
fact, not 39 independent ones. `StereoRig` (`types.py:31-34`) declares `focal_px` as a
required field with no default and a positive-value check, so *every* rig construction
carries an intrinsic — including in the 32 `test_oculomotor.py` tests whose assertions
are pure SO(3) and whose code paths never read `focal_px` at all. `eye_rotations`,
`fixation_distance`, `fixation_point`, `rectification_rotation` and
`vieth_muller_points` all read `rig.baseline` and never `rig.focal_px` [M, read in
full]. The coupling is in the type, not in the mathematics.

This is the same split `docs/roadmap.md` Phase A already names — "Split `StereoRig`
(anatomy: baseline, focal length, principal point — fixed hardware) from a new
`Fixation` type" — carried out for the oculomotor half and not for the intrinsic half.

## 3.3 Every pinhole-dependent test, named

**`tests/unit/test_geometry.py` (5)**

1. `test_projection_roundtrip` — round-trips depth through `depth_to_disparity`, whose output is pixels; there is no intrinsics-free restatement.
2. `test_parallel_rig_reduces_to_fb_over_z` — asserts `d == parallel_rig.focal_px * baseline / Z`. Names the focal length in the assertion.
3. `test_zero_disparity_on_the_horopter` — asserts a pixel disparity is 0 at the fixation distance. The zero is focal-invariant; the asserted quantity is not.
4. `test_disparity_sign_convention` — asserts the sign of a pixel disparity either side of fixation.
5. `test_invalid_depth_maps_to_nan` — asserts `nan` propagation through the pinhole map. The validity contract is model-independent; the function is not.

**`tests/unit/test_oculomotor.py` (4)**

6. `test_plane_of_regard_alignment_optimum_is_k_half` — the ADR-0016 pin. Asserts `max_vertical_disparity(...) < 1e-12` px at k = 1/2 and `> 1e-3` px at k ∈ {0, 0.25}, through a test-local `project_px(P, R, C, f)`. Sweeps three explicit (baseline, focal) pairs: (0.064, 800), (0.10, 1200), (0.03, 400).
7. `test_rectification_puts_the_plane_of_regard_on_the_principal_row` — asserts `row == wide_rig.principal_point[0]`. The principal point *is* the intrinsic; see §3.5.
8. `test_rectification_rotation_is_sufficient_for_rectification` — asserts `row_l == row_r` exactly, over pixel rows from a test-local `project_rect`.
9. `test_target_to_fixation_is_2pi_invariant_in_the_current_elevation` — the wrap assertion is angular, but the test closes with `closed_form = 7.0 + arctan((pixel[0] - wide_rig.principal_point[0]) / wide_rig.focal_px)` and asserts the returned elevation equals `closed_form - 2π`. Names both intrinsics in the assertion.

**`tests/unit/test_projection_toedin.py` (7)**

10. `test_fixation_point_images_on_the_principal_point` — asserts both projections equal `[0, 0]` px.
11. `test_plane_of_regard_images_on_each_eyes_own_meridian_at_k_half` — asserts per-eye `|row|` < 1e-12 px at k = 1/2, > 0.05 px at k ∈ {0, 0.25}. Three (baseline, focal) pairs.
12. `test_offaxis_divergence_is_a_depth_offset_plus_a_quadratic_in_eccentricity` — asserts on signed pixel differences between the toed-in and off-axis models, including `|difference| < 1e-12` px at η = 0.
13. `test_principal_point_offset_is_honoured_in_row_col_order` — asserts the projection shifts by exactly `[120.0, 160.0]` px when the principal point moves. Irreducibly about the intrinsic, by design.
14. `test_zero_horizontal_disparity_on_the_vieth_muller_circle` — the ADR-0007 item-4 closure. Asserts `|d_h| < 1e-12` px, and at oblique gaze compares against `predicted = col * mu * az * el**2 * (k - 0.5) / 2` where `col` is a **pixel column**.
15. `test_vertical_disparity_on_the_vieth_muller_circle_is_nonzero_at_elevated_gaze` — asserts `|d_v| > 0.05` px and `< 1e-12` px at zero elevation.
16. `test_perturbed_vergence_breaks_the_horopter_zero` — asserts `|d_h| > 0.1` px after a 1% vergence perturbation; the predicted scale is `f * delta_mu`.

Additionally, tests 14–16 gate every assertion through `assert_preconditions`, which
requires `mask.sum() > 100` and peripheral reach `> 100.0` px against
`IMAGE_HALF_WIDTH = 160.0` — a **sensor-defined** validity window baked into the
guard that keeps these tests from passing vacuously.

**Incidental set (4)**

17. `test_scaling.py::test_scale_to_depth_recovers_ground_truth` — round-trips through pixel disparity.
18. `test_scaling.py::test_depth_variance_grows_with_distance` — asserts `var(Z)` ratio `== 2^4`; the ratio is focal-invariant, but the `Z^4` law is a property of `d = f b / Z`.
19. `test_scenes.py::test_depth_and_disparity_are_mutually_consistent` — asserts scene depth matches `disparity_to_depth(s.disparity)`, in pixels.
20. `test_middlebury.py::test_depth_uses_middleburys_formula_not_ours` — asserts `depth_from_disparity(d, calib) == disparity_to_depth(d, rig)` across a pixel-disparity range, with `calib` an intrinsic matrix read from a Middlebury `calib.txt`.

## 3.4 The four invariants singled out

**Listing coefficient at k = 1/2.** First, a correction to the premise, measured:
`k` is *not* pinned at 1/2 as a parameter value. The default is **0.25** in all three
signatures — `eye_rotations(rig, fixation, k=0.25)`, `project_toed_in(..., k=0.25)`,
`toed_in_disparity(..., k=0.25)` — and ADR-0014's decision is that `k` is a free
parameter, deliberately not range-restricted so the sweep can explore. What is pinned
at k = 1/2 is the **plane-of-regard alignment optimum** (ADR-0016, which *corrects*
ADR-0014's prediction of a null at 0.25 without superseding it). Three tests assert at
k = 0.5:

| Test | Class |
|---|---|
| `test_plane_of_regard_alignment_optimum_is_k_half` | pinhole-dependent (max vertical disparity, px) |
| `test_plane_of_regard_images_on_each_eyes_own_meridian_at_k_half` | pinhole-dependent (per-eye row, px) |
| `test_tilted_listing_at_k_half_is_helmholtz` | **mixed** — assertion is pure SO(3) |

The third is the load-bearing one for migration. Its own docstring states the reason:
*"Needs no projection, so it fails independently of
test_plane_of_regard_alignment_optimum_is_k_half."* It asserts
`R == helmholtz_rotation(az_e, el_e)` for each eye at k = 1/2, with a negative control
at k = 0.25, and touches no pixel. **The k = 1/2 result survives without a pinhole.**

**The Helmholtz identity.** Four tests, none pinhole-dependent:

| Test | Class |
|---|---|
| `test_rectification_rotation_matches_helmholtz_with_azimuth_zeroed` | **direction-only** |
| `test_rectification_rotation_ignores_azimuth_and_vergence` | **direction-only** |
| `test_tilted_listing_at_k_half_is_helmholtz` | mixed |
| `test_vergence_to_zero_limit_is_continuous` | mixed (asserts the zero-vergence gaze equals the cyclopean Helmholtz direction) |

The two direction-only tests are the only tests in the core set that construct no rig
at all in their assertion path — `rectification_rotation` takes a `Fixation` and
nothing else. Both request a `wide_rig` fixture they never use; that argument is
vestigial [M].

**The `R_e = A(p→g)·A(ẑ→p)` composition order.** Pinned by five tests, **all mixed,
none pinhole-dependent**: `test_k0_reduces_to_strict_listing` (the second factor
collapses to identity at k = 0), `test_gaze_lines_intersect_the_fixation_point`,
`test_tilted_listing_at_k_half_is_helmholtz`, `test_sagittal_mirror_symmetry`,
`test_rotation_matrices_are_special_orthogonal`.

One thing here is easy to misread and worth stating precisely.
`test_gaze_lines_intersect_the_fixation_point` is described in its own docstring as
failing "by 13-32 px of optical-axis error if the primary-orientation factor
`A(z -> p_e)` is dropped" — but that pixel figure appears only in the prose. The
assertions are `np.linalg.norm(perpendicular) < 1e-12` in **metres** and
`recovered == approx(mu)` in **radians**. The strongest test of the composition order
is metric and angular, not pixel-valued.

**The rectification rotation.** Six tests, and this is the one place where the split
is genuinely load-bearing:

| Test | Class | What it pins |
|---|---|---|
| `test_rectification_rotation_matches_helmholtz_with_azimuth_zeroed` | direction-only | the *identity* — R_rect **is** `helmholtz_rotation(0, el)` |
| `test_rectification_rotation_ignores_azimuth_and_vergence` | direction-only | azimuth-independence, structural under ADR-0015 |
| `test_transposing_the_rectifier_breaks_the_round_trip` | mixed | direction convention (rect→head), by faulting the module |
| `test_round_trip_negative_controls_are_visible` | mixed | that the transpose/origin/swap faults are visible at all |
| `test_rectification_puts_the_plane_of_regard_on_the_principal_row` | **pinhole-dependent** | ADR-0017's **selection criterion** |
| `test_rectification_rotation_is_sufficient_for_rectification` | **pinhole-dependent** | sufficiency: vertical disparity vanishes |

The definition of R_rect is intrinsics-free. Its *selection* is not, and not
incidentally: R_rect is determined only up to a rotation about the baseline, and
ADR-0017 picks this member because it "puts the plane of regard on the principal
row". A principal row is a pinhole concept by construction — there is no
principal row without a principal point. This dependency is definitional, not a
fixture artefact, and no change of fixture removes it.

## 3.5 What this measures about the plan's assumption

The plan assumes the geometry tests are statable without a pinhole intrinsic matrix.
Measured, that assumption holds for the ray-and-direction content and fails in two
identifiable places.

Holds: every invariant the successor's geometry layer is committed to — Listing
tilt including the k = 1/2 optimum, Helmholtz composition, the composition order,
the domain guards, the refusal contract, SO(3) well-formedness, mirror symmetry,
the zero-vergence limit — has at least one pin whose assertion contains no focal
length, principal point, or pixel. 43 of 59.

Fails, in two places: (a) ADR-0017's rectification selection criterion, which is
definitionally about a principal row; (b) the toed-in projection's pixel-valued
observables — vertical disparity, the meridian tests, the horopter closure — which
are 7 of 12 tests in `test_projection_toedin.py`. Both sit in the *projection*
model, which the plan already treats as a swappable implementation with pinhole as
one instance, not in the ray/direction layer.

One further measured fact bears on the plan's ordering, and it comes from bioeye
rather than active-stereo: bioeye's loop is parameterised by a **scalar fixation
disparity in pixels** (`ActiveStereo.vergence` returns `d_fix`; `scale_to_depth`
takes `d_fix, f_px, I`). Unlike the active-stereo geometry tests, this is not a
fixture coupling that a type split would remove — the pinhole quantity is the loop's
state variable. And bioeye has no tests, so nothing pins it either way.

---

# Part 4 — Falsifiers

## Falsifier 1 — "If the geometry tests are substantially pinhole-dependent, the geometry step is a re-derivation, not a migration."

**Did not fire, for the geometry layer as the plan scopes it. Fired in a narrow, nameable region.**

Against the plan's actual claim — that the tests are statable without a pinhole
intrinsic matrix — the measurement supports it: 43 of 59 core geometry tests
(72.9%) have assertions containing no intrinsic, and 16 (27.1%) do not. Every
invariant named in the task has at least one intrinsics-free pin, including the one
most at risk: the k = 1/2 optimum is pinned twice in pixels and once, independently,
as an SO(3) identity that "needs no projection".

The qualification that keeps this from being a clean pass. Only 4 of 59 tests are
strictly intrinsics-free *as written*; the other 39 construct a `StereoRig`, which
cannot be built without a `focal_px`. So a literal lift-and-shift of the geometry
tests does drag the pinhole intrinsic along, in almost every case. The distinction
that matters is that this is a single type-level coupling with a single cause —
`StereoRig` bundling anatomy with intrinsics — and not 39 separate derivations. The
mathematics is already intrinsics-free: the five geometry functions that carry the
ray/direction content read `rig.baseline` and never `rig.focal_px` (read in full,
measured). Removing the coupling is a change to one dataclass and the fixtures that
build it, which is a migration cost, not a re-derivation.

Where the falsifier genuinely fires: ADR-0017's rectification selection criterion
cannot be stated without a principal point — that is definitional, and it is a real
re-derivation if the successor's rectification is not expressed in pixels. And 7 of
the 12 toed-in projection tests are pixel-valued observables. Both belong to the
projection model the plan already declares swappable. Whether that is inside or
outside "the geometry step" is a scoping question this inventory does not settle;
it is stated here so the decision is made deliberately rather than discovered.

## Falsifier 2 — "If more than roughly a third of items land in decide, the criterion is not discriminating enough."

**Did not fire.**

| | count |
|---|---|
| Inventory rows total | 114 |
| carry | 77 (67.5%) |
| leave | 34 (29.8%) |
| **decide** | **3** (2.6%) |

Rows by section: `src/` 23, `tests/` 25, `docs/decisions/` 19, `docs/method/` 4,
remaining active-stereo 27, bioeye 16.

The three: `docs/architecture.md`, `docs/workflow.md`, and bioeye's
`vergence_scaling_experiment`. The first two share one shape — a file half-composed
of normative content and half of active-stereo-specific description, where the
criterion does not say which half governs the file. The third is a falsifiable
analytic claim rendered only as a plotted comparison, with no assertion.

The criterion discriminated well because "can this fail?" turned out to be answerable
from the artefact itself in nearly every case, and because active-stereo's own
`grep`-able structure supplied the evidence: the ADR→test map resolved 18 ADRs
mechanically, and the test-import map resolved the `src/` rows.

Two honesty checks on this number, since a low `decide` count is exactly what an
inventory would produce if it were quietly guessing rather than resolving. First,
the cases that could have been parked in `decide` and were not, with the reason
each resolved: ADR-0005 (not cited in any test, but its decision is made concrete in
the `Estimate` type that `test_types.py` pins → carry); ADR-0008 (not cited in
`tests/`, but pinned by `pyproject.toml:10` and the CI matrix → carry); ADR-0007
(superseded, but with a live test pinning its item-4 closure → carry);
`horopter.py` (split, because `vieth_muller_circle` is unpinned while the other two
functions are pinned); `CONTRIBUTING.md` (resolved to carry — its rules are
violable, unlike `workflow.md`'s surface description). Second, and cutting the other
way: 61.9% of geometry-test rows landed in `mixed`, the middle category of the §3
classification. That is a real concentration, but it has one measured cause named in
§3.2, and the two flanking categories are populated and individually named — so it
is a finding about `StereoRig`, not a category doing the work `decide` would
otherwise do.

---

# Part 5 — Measured/assumed ledger

**Measured.** Both reference SHAs and the four preconditions. All file trees and line
counts. The full contents of the five geometry source files and the three geometry
test files, `types.py`, and `conftest.py`. All 63 geometry-test classifications in
§3, each read in the source. The ADR→test map, the test-import map, and the
`configs/`-not-read-by-tests result (all by `grep` over the checkout). All 18 ADR
titles and statuses. `CLAUDE.md` in full. `docs/roadmap.md` in full. All four
`.claude/commands/` files. Every bioeye item except the binaries. The `StereoRig`
required-`focal_px` fact and the `focal_px`-never-read-by-oculomotor fact.

**Assumed.** Every `[A]` row: the classification of 20 `src/` files, 19 `tests/`
files, and 15 ADRs that I did not open, inferred from the measured maps above. The
contents of `docs/briefings/`, `docs/lab-notebook/`, `docs/issues/`, `docs/plans/`,
`experiments/`, `scripts/`, `slides/`, `paper/`, `configs/`, `.github/`,
`.devcontainer/`, `.vscode/`, `Makefile`, `CHANGELOG.md`, `README.md`, and the ADR
bodies — classified from path, name, size, and category, not from reading. The
bioeye PNG and EXR binaries were not decoded; their classification as rendered
output rests on filenames and the code paths that write them.

**Known defect carried, not resolved here.** `CLAUDE.md` §3's depth-frame invariant
is contradicted by `geometry/oculomotor.py:337-348`, which states the invariant is
false and that section 3 is the wrong side. Recorded because carrying `CLAUDE.md`
carries the false clause with it.
