# taskplanorder — Authoritative Execution Plan for Retail-Grade Mikester9000/GameRewritten Export

This file is the single source of truth for ordered execution from the current repository state to a retail-grade animation asset pipeline that exports cleanly into `Mikester9000/GameRewritten`.

---

## Authority and Sync Policy

- Authoritative plan: `./taskplanorder.md`
- Reference-only aliases: `./planv1.md` and `./Task_List.md`
- Execute tasks in **document order**, not by legacy task ID number. Legacy task IDs are preserved only to avoid breaking earlier references.
- Planned work, review checkpoints, proof requirements, and historical validation evidence are intentionally separated to prevent execution confusion.

---

## Execution Rules (for low-reasoning local LLMs)

1. Execute tasks strictly in the order they appear in this document.
2. Each task edits or creates one file only.
3. Do not skip validation gates.
4. Do not start the next task until the current task acceptance criteria and proof block are satisfied.
5. Keep every change deterministic and backward compatible unless the task explicitly says otherwise.
6. `READ_LINES` uses only two deterministic formats: numeric ranges (`start-end` comma-separated) or keyword `FULL_FILE` / `DIRECTORY`.
7. Do not treat any historical `PASS` entry as current release evidence until the listed command is rerun.

---

## Art Direction Baseline

All planned outputs must satisfy this visual target:

- Ship assets with a **high-end PS2-era JRPG look** that would still feel plausible on PlayStation 2-class hardware.
- Use *Final Fantasy VII*, *VIII*, *IX*, *X*, and *XII* as the primary visual readability references.
- Keep the motion library broad enough for modern gameplay/features comparable to *Final Fantasy VII Remake* and *Final Fantasy XV* even while preserving the PS2-era presentation target.
- Preserve this direction in generated metadata, manifests, and hand-off documentation so downstream tools can validate it.

---

## Phase A — Foundations and Public Contracts

Lock the data contract, profile registry, and public integration exports before any generation work.

### Task 01
- **Task Name:** Add style metadata envelope to `.anim` payload
- **Narrative Logic:** Retail-ready assets need explicit style identity (FF7/FF8/FF10 nostalgia direction) embedded with animation data so `Mikester9000/GameRewritten` can consume and tag packs reliably.
- **Code Structure Need:** Extend serializer/deserializer schema with optional metadata block while preserving existing format compatibility.
- **READ_FILE:** `./animation_engine/io/anim_format.py`
- **READ_LINES:** `33-38, 49-77, 90-103, 137-158`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `35-36, 96-102, 140-158`
- **Dependency Inputs:** None
- **Risk Class:** Medium
- **Mandatory Reviewer Role:** Animation Systems Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Existing imports still load old `.anim`; new metadata round-trips without loss.
  - **Artifact Path:** `./animation_engine/io/anim_format.py`
- **Acceptance Criteria:** Existing imports still load old `.anim`; new metadata round-trips without loss.

### Task 02
- **Task Name:** Create nostalgia style profile registry
- **Narrative Logic:** Generation must be profile-driven so outputs stay inside the shared PS2-era art direction while still covering modern gameplay needs.
- **Code Structure Need:** Add centralized immutable style profile definitions for motion packs, clip timing, naming, cinematic mood, and explicit art-direction metadata.
- **READ_DIRECTORY:** `./animation_engine/integration`
- **READ_LINES:** `DIRECTORY`
- **File Edited or Created:** Create new file `./animation_engine/integration/style_profiles.py`
- **Lines Being Edited:** `1-260`
- **Dependency Inputs:** None
- **Risk Class:** Medium
- **Mandatory Reviewer Role:** Animation Systems Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Registry exposes stable profile IDs and ordered clip requirements.
  - **Artifact Path:** `./animation_engine/integration/style_profiles.py`
- **Acceptance Criteria:** Registry exposes stable profile IDs and ordered clip requirements.

### Task 03
- **Task Name:** Export style profiles in integration package API
- **Narrative Logic:** Downstream pipeline and CLI should import profiles from a stable public path.
- **Code Structure Need:** Re-export style profile registry via integration package init.
- **READ_FILE:** `./animation_engine/integration/__init__.py`
- **READ_LINES:** `1-10`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `1-10`
- **Dependency Inputs:** Task 02
- **Risk Class:** Medium
- **Mandatory Reviewer Role:** Animation Systems Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** `from animation_engine.integration import ...` exposes profiles and pipeline cleanly.
  - **Artifact Path:** `./animation_engine/integration/__init__.py`
- **Acceptance Criteria:** `from animation_engine.integration import ...` exposes profiles and pipeline cleanly.

---

### Phase A Review Checkpoints
- **Design review:** Confirm every acceptance criterion in this phase is measurable, deterministic, and dependency-safe before implementation is marked ready for review.
- **Code review:** Verify the one-file-per-task rule still holds and that no hidden cross-file coupling was introduced outside the declared dependency inputs.
- **Test review:** Check that new or updated tests cover the changed behavior, preserve backward compatibility where required, and are scheduled immediately after the feature work they validate.
- **Release review:** Confirm the proof block for each task contains a command, expected result, and artifact path that a reviewer can independently replay.

## Phase B — Motion Generation Core

Expand backend generation coverage before pipeline and QA layers depend on it.

### Task 04
- **Task Name:** Expand backend supported motion taxonomy
- **Narrative Logic:** Retail-quality JRPG presentation requires a full move set beyond idle/walk/run/attack.
- **Code Structure Need:** Extend `supported_motion_types` and generation branches for core gameplay, combat, and cinematic loops.
- **READ_FILE:** `./animation_engine/backend.py`
- **READ_LINES:** `72-75, 100-145, 192-200`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `72-75, 102-145`
- **Dependency Inputs:** Task 02, Task 03
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Systems Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Backend advertises and can generate all required motion IDs for profile packs.
  - **Artifact Path:** `./animation_engine/backend.py`
- **Acceptance Criteria:** Backend advertises and can generate all required motion IDs for profile packs.

### Task 05
- **Task Name:** Add profile-aware generation parameters
- **Narrative Logic:** FF nostalgia variants need different cadence and amplitude tuning while sharing common pipeline code.
- **Code Structure Need:** Extend backend generation entry point to accept profile tuning data deterministically.
- **READ_FILE:** `./animation_engine/backend.py`
- **READ_LINES:** `42-48, 89-96, 100-145`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `42-48, 89-96, 102-145`
- **Dependency Inputs:** Task 02, Task 04
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Systems Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Generated clips differ predictably by profile inputs without randomness drift.
  - **Artifact Path:** `./animation_engine/backend.py`
- **Acceptance Criteria:** Generated clips differ predictably by profile inputs without randomness drift.

---

### Phase B Review Checkpoints
- **Design review:** Confirm every acceptance criterion in this phase is measurable, deterministic, and dependency-safe before implementation is marked ready for review.
- **Code review:** Verify the one-file-per-task rule still holds and that no hidden cross-file coupling was introduced outside the declared dependency inputs.
- **Test review:** Check that new or updated tests cover the changed behavior, preserve backward compatibility where required, and are scheduled immediately after the feature work they validate.
- **Release review:** Confirm the proof block for each task contains a command, expected result, and artifact path that a reviewer can independently replay.

## Phase C — Pipeline and Deterministic Manifest Flow

Make pack generation complete, deterministic, and failure-aware before exposing production commands.

### Task 06
- **Task Name:** Replace fixed 4-clip list with profile manifest
- **Narrative Logic:** `Mikester9000/GameRewritten` needs complete pack generation in one pass, not demo-only motion output.
- **Code Structure Need:** Pipeline reads ordered clip manifest from profile registry and generates all required files.
- **READ_FILE:** `./animation_engine/integration/asset_pipeline.py`
- **READ_LINES:** `15-16, 39-44, 64-86`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `39-44, 64-86`
- **Dependency Inputs:** Task 02, Task 04, Task 05
- **Risk Class:** High
- **Mandatory Reviewer Role:** Pipeline Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Manifest includes full ordered clip set; output count equals profile requirement count.
  - **Artifact Path:** `./animation_engine/integration/asset_pipeline.py`
- **Acceptance Criteria:** Manifest includes full ordered clip set; output count equals profile requirement count.

### Task 07
- **Task Name:** Emit pack-level manifest JSON beside `.anim` files
- **Narrative Logic:** `Mikester9000/GameRewritten` import stage requires machine-readable index of all generated assets and metadata.
- **Code Structure Need:** Add deterministic manifest writer with profile ID, clip list, file paths, and generation version.
- **READ_FILE:** `./animation_engine/integration/asset_pipeline.py`
- **READ_LINES:** `39-44, 61-63, 83-86`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `61-63, 83-110`
- **Dependency Inputs:** Task 06
- **Risk Class:** High
- **Mandatory Reviewer Role:** Pipeline Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Pipeline returns and writes manifest with exact exported file inventory.
  - **Artifact Path:** `./animation_engine/integration/asset_pipeline.py`
- **Acceptance Criteria:** Pipeline returns and writes manifest with exact exported file inventory.

### Task 08
- **Task Name:** Add failure-safe generation checkpoints
- **Narrative Logic:** Retail pipeline must not silently ship partial packs.
- **Code Structure Need:** Add per-clip generation error collection and fail-fast summary status in pipeline output.
- **READ_FILE:** `./animation_engine/integration/asset_pipeline.py`
- **READ_LINES:** `64-86`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `64-86`
- **Dependency Inputs:** Task 06, Task 07
- **Risk Class:** High
- **Mandatory Reviewer Role:** Pipeline Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** On any failed clip generation, pipeline marks status failed and reports exact failed motion IDs.
  - **Artifact Path:** `./animation_engine/integration/asset_pipeline.py`
- **Acceptance Criteria:** On any failed clip generation, pipeline marks status failed and reports exact failed motion IDs.

---

### Task 20
- **Task Name:** Add deterministic generation mode defaults
- **Narrative Logic:** Retail output must be reproducible for audits and patch pipelines.
- **Code Structure Need:** Ensure pipeline seed/profile/sample rate defaults are pinned and exposed in manifest.
- **READ_FILE:** `./animation_engine/integration/asset_pipeline.py`
- **READ_LINES:** `28-38, 61-63, 83-86`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `28-38, 61-63, 83-110`
- **Dependency Inputs:** Task 06, Task 07, Task 08
- **Risk Class:** Medium
- **Mandatory Reviewer Role:** Pipeline Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Same inputs produce byte-stable pack outputs (excluding timestamps if any).
  - **Artifact Path:** `./animation_engine/integration/asset_pipeline.py`
- **Acceptance Criteria:** Same inputs produce byte-stable pack outputs (excluding timestamps if any).

### Phase C Review Checkpoints
- **Design review:** Confirm every acceptance criterion in this phase is measurable, deterministic, and dependency-safe before implementation is marked ready for review.
- **Code review:** Verify the one-file-per-task rule still holds and that no hidden cross-file coupling was introduced outside the declared dependency inputs.
- **Test review:** Check that new or updated tests cover the changed behavior, preserve backward compatibility where required, and are scheduled immediately after the feature work they validate.
- **Release review:** Confirm the proof block for each task contains a command, expected result, and artifact path that a reviewer can independently replay.

## Phase D — CLI Generation and QA Gates

Wire generation first, then build validator internals, then expose the validation command after the rules exist.

### Task 09
- **Task Name:** Add CLI command for full nostalgia pack generation
- **Narrative Logic:** One command must produce all assets needed for `Mikester9000/GameRewritten` integration.
- **Code Structure Need:** Add subcommand for output dir, profile choice, skeleton source, and manifest path.
- **READ_FILE:** `./animation_engine/cli.py`
- **READ_LINES:** `94-129, 132-140`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `94-129, 132-140`
- **Dependency Inputs:** Task 06, Task 07, Task 08
- **Risk Class:** High
- **Mandatory Reviewer Role:** Pipeline Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** CLI command exits success and prints generated pack summary.
  - **Artifact Path:** `./animation_engine/cli.py`
- **Acceptance Criteria:** CLI command exits success and prints generated pack summary.

### Task 11
- **Task Name:** Create style validator module
- **Narrative Logic:** Nostalgia target must be measurable, not subjective only.
- **Code Structure Need:** Add profile-aware validation rules for cadence, loop smoothness, and motion coverage.
- **READ_DIRECTORY:** `./animation_engine/qa`
- **READ_LINES:** `DIRECTORY`
- **File Edited or Created:** Create new file `./animation_engine/qa/style_validator.py`
- **Lines Being Edited:** `1-300`
- **Dependency Inputs:** Task 02, Task 06, Task 07, Task 08
- **Risk Class:** High
- **Mandatory Reviewer Role:** Pipeline Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Validator returns structured report with pass/fail, warnings, and error reasons.
  - **Artifact Path:** `./animation_engine/qa/style_validator.py`
- **Acceptance Criteria:** Validator returns structured report with pass/fail, warnings, and error reasons.

### Task 12
- **Task Name:** Export style validator in QA package API
- **Narrative Logic:** CLI and tests need stable import path for new validator.
- **Code Structure Need:** Update QA package exports.
- **READ_FILE:** `./animation_engine/qa/__init__.py`
- **READ_LINES:** `1-29`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `1-29`
- **Dependency Inputs:** Task 11
- **Risk Class:** High
- **Mandatory Reviewer Role:** Pipeline Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Public QA API includes new style validator symbols.
  - **Artifact Path:** `./animation_engine/qa/__init__.py`
- **Acceptance Criteria:** Public QA API includes new style validator symbols.

### Task 13
- **Task Name:** Add pack completeness checker
- **Narrative Logic:** Retail delivery requires no missing motions in any profile pack.
- **Code Structure Need:** Add deterministic rule set that compares generated set vs required profile motion IDs.
- **READ_FILE:** `./animation_engine/qa/style_validator.py`
- **READ_LINES:** `1-300`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `180-300`
- **Dependency Inputs:** Task 11, Task 12
- **Risk Class:** High
- **Mandatory Reviewer Role:** Pipeline Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Missing, duplicate, or misnamed clips are reported as errors.
  - **Artifact Path:** `./animation_engine/qa/style_validator.py`
- **Acceptance Criteria:** Missing, duplicate, or misnamed clips are reported as errors.

---

### Task 10
- **Task Name:** Add CLI command for pack validation gate
- **Narrative Logic:** Export to `Mikester9000/GameRewritten` should be blocked if quality gates fail.
- **Code Structure Need:** Add subcommand to run clip, loop, skeleton, and style validation over generated pack.
- **READ_FILE:** `./animation_engine/cli.py`
- **READ_LINES:** `8-31, 58-77, 94-129`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `8-31, 58-77, 94-140`
- **Dependency Inputs:** Task 09, Task 11, Task 12, Task 13
- **Risk Class:** High
- **Mandatory Reviewer Role:** Pipeline Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Non-zero exit when any required validator fails.
  - **Artifact Path:** `./animation_engine/cli.py`
- **Acceptance Criteria:** Non-zero exit when any required validator fails.

---

### Phase D Review Checkpoints
- **Design review:** Confirm every acceptance criterion in this phase is measurable, deterministic, and dependency-safe before implementation is marked ready for review.
- **Code review:** Verify the one-file-per-task rule still holds and that no hidden cross-file coupling was introduced outside the declared dependency inputs.
- **Test review:** Check that new or updated tests cover the changed behavior, preserve backward compatibility where required, and are scheduled immediately after the feature work they validate.
- **Release review:** Confirm the proof block for each task contains a command, expected result, and artifact path that a reviewer can independently replay.

## Phase E — Regression and Backward-Compatibility Tests

Add the test coverage immediately after the generation, QA, and serialization contracts stabilize.

### Task 14
- **Task Name:** Add integration test for full profile pack generation
- **Narrative Logic:** Prevent regressions where only partial packs are generated.
- **Code Structure Need:** Extend backend/pipeline integration tests with profile matrix checks and manifest assertions.
- **READ_FILE:** `./tests/test_backend_qa_integration.py`
- **READ_LINES:** `15-20, 71-81, 83-92`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `93-170`
- **Dependency Inputs:** Task 06, Task 07, Task 08, Task 09
- **Risk Class:** Medium
- **Mandatory Reviewer Role:** Test Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest ./tests/test_backend_qa_integration.py -q`
  - **Expected Output:** Tests assert all required files exist and match profile order.
  - **Artifact Path:** `./tests/test_backend_qa_integration.py`
- **Acceptance Criteria:** Tests assert all required files exist and match profile order.

### Task 15
- **Task Name:** Add tests for style validator pass/fail behavior
- **Narrative Logic:** Retail quality gates must be deterministic and test-covered.
- **Code Structure Need:** Add QA tests validating both compliant and non-compliant clip sets.
- **READ_FILE:** `./tests/test_backend_qa_integration.py`
- **READ_LINES:** `83-92`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `171-250`
- **Dependency Inputs:** Task 10, Task 11, Task 12, Task 13
- **Risk Class:** Medium
- **Mandatory Reviewer Role:** Test Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest ./tests/test_backend_qa_integration.py -q`
  - **Expected Output:** Controlled fixtures produce expected error/warning outputs.
  - **Artifact Path:** `./tests/test_backend_qa_integration.py`
- **Acceptance Criteria:** Controlled fixtures produce expected error/warning outputs.

### Task 16
- **Task Name:** Add `.anim` metadata round-trip tests
- **Narrative Logic:** New payload metadata must not break old import/export paths.
- **Code Structure Need:** Extend `TestAnimFormat` coverage for optional metadata persistence and backward compatibility.
- **READ_FILE:** `./tests/test_io.py`
- **READ_LINES:** `83-164`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `110-164`
- **Dependency Inputs:** Task 01
- **Risk Class:** Medium
- **Mandatory Reviewer Role:** Test Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest ./tests/test_io.py -q`
  - **Expected Output:** Old payloads still import; new metadata fields survive export/import unchanged.
  - **Artifact Path:** `./tests/test_io.py`
- **Acceptance Criteria:** Old payloads still import; new metadata fields survive export/import unchanged.

---

### Phase E Review Checkpoints
- **Design review:** Confirm every acceptance criterion in this phase is measurable, deterministic, and dependency-safe before implementation is marked ready for review.
- **Code review:** Verify the one-file-per-task rule still holds and that no hidden cross-file coupling was introduced outside the declared dependency inputs.
- **Test review:** Check that new or updated tests cover the changed behavior, preserve backward compatibility where required, and are scheduled immediately after the feature work they validate.
- **Release review:** Confirm the proof block for each task contains a command, expected result, and artifact path that a reviewer can independently replay.

## Phase F — Documentation and Compatibility Handoff

Document commands and handoff rules only after the underlying behavior and tests are in place.

### Task 17
- **Task Name:** Document profile-based pack export for engine users
- **Narrative Logic:** Teams need one deterministic hand-off recipe from generation to runtime load.
- **Code Structure Need:** Add README sections for profile selection, CLI commands, output directory contract, and manifest schema.
- **READ_FILE:** `./README.md`
- **READ_LINES:** `10-24, 137-150`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `25-41, 137-150`
- **Dependency Inputs:** Task 09, Task 10, Task 14, Task 15, Task 16
- **Risk Class:** Low
- **Mandatory Reviewer Role:** Documentation Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `rg -n "generate-pack|validate-pack|workflow|editor" ./README.md`
  - **Expected Output:** README includes exact command flow and expected output tree.
  - **Artifact Path:** `./README.md`
- **Acceptance Criteria:** README includes exact command flow and expected output tree.

### Task 18
- **Task Name:** Update compatibility bridge documentation
- **Narrative Logic:** `Mikester9000/GameRewritten` integration requires clear runtime vs pre-baked workflow for expanded pack output.
- **Code Structure Need:** Update compat guide with profile pack manifest usage and validation expectations before import.
- **READ_FILE:** `./compat/README.md`
- **READ_LINES:** `18-44, 65-143, 192-215`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `18-44, 65-143, 192-235`
- **Dependency Inputs:** Task 10, Task 13, Task 17
- **Risk Class:** Low
- **Mandatory Reviewer Role:** Compatibility Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `rg -n "manifest|failure handling|validation" ./compat/README.md`
  - **Expected Output:** Compat docs explicitly describe pack manifest ingestion and failure handling.
  - **Artifact Path:** `./compat/README.md`
- **Acceptance Criteria:** Compat docs explicitly describe pack manifest ingestion and failure handling.

### Task 19
- **Task Name:** Add converter guidance for full pack batch conversion
- **Narrative Logic:** Retail export path must support generating multiple pre-baked headers from pack manifest.
- **Code Structure Need:** Document and/or script deterministic per-clip conversion workflow for `anim_to_cpp_header.py`.
- **READ_FILE:** `./compat/anim_to_cpp_header.py`
- **READ_LINES:** `12-27, 360-409`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `12-27, 360-374`
- **Dependency Inputs:** Task 07, Task 18
- **Risk Class:** Low
- **Mandatory Reviewer Role:** Compatibility Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `rg -n "batch|manifest|header" ./compat/anim_to_cpp_header.py`
  - **Expected Output:** Batch conversion workflow is explicitly defined for `Mikester9000/GameRewritten` release builds.
  - **Artifact Path:** `./compat/anim_to_cpp_header.py`
- **Acceptance Criteria:** Batch conversion workflow is explicitly defined for `Mikester9000/GameRewritten` release builds.

---

### Task 21
- **Task Name:** Add final smoke test command sequence to docs
- **Narrative Logic:** Small local LLMs need explicit no-ambiguity validation sequence before release.
- **Code Structure Need:** Add exact command list for install, tests, generation, and validation.
- **READ_FILE:** `./README.md`
- **READ_LINES:** `42-103`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `104-136`
- **Dependency Inputs:** Task 17, Task 18, Task 19, Task 20
- **Risk Class:** Low
- **Mandatory Reviewer Role:** Documentation Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `rg -n "generate-pack|validate-pack|workflow|editor" ./README.md`
  - **Expected Output:** Docs provide exact command order and expected success conditions.
  - **Artifact Path:** `./README.md`
- **Acceptance Criteria:** Docs provide exact command order and expected success conditions.

### Phase F Review Checkpoints
- **Design review:** Confirm every acceptance criterion in this phase is measurable, deterministic, and dependency-safe before implementation is marked ready for review.
- **Code review:** Verify the one-file-per-task rule still holds and that no hidden cross-file coupling was introduced outside the declared dependency inputs.
- **Test review:** Check that new or updated tests cover the changed behavior, preserve backward compatibility where required, and are scheduled immediately after the feature work they validate.
- **Release review:** Confirm the proof block for each task contains a command, expected result, and artifact path that a reviewer can independently replay.

## Phase G — Late-Stage Runtime, Tooling, and Assessment Work

Keep late-stage runtime, conversion, and editor enhancements grouped near the end, but ahead of the full GUI completion push.

### Task 23
- **Task Name:** Render skinned mesh wireframe in PS2 viewport
- **Narrative Logic:** The PS2-era preview viewport currently draws skeleton sticks only. Drawing projected triangle edges from a skinned mesh gives artists a true wireframe character preview without GPU dependencies.
- **Code Structure Need:** Call `cpu_skin_mesh(mesh, skin_matrices)` in `_redraw_viewport`; project each vertex with `_project_world_point`; draw triangle edges using `canvas.create_line`.
- **READ_FILE:** `./animation_engine/editor/main.py`
- **READ_LINES:** `1488-1560, 1600-1640`
- **READ_FILE:** `./animation_engine/runtime/skinning.py`
- **READ_LINES:** `36-65`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `1488-1560` (_redraw_viewport body); add helper `_draw_mesh_wireframe` after `_draw_skeleton_world` near line `1608`
- **Dependency Inputs:** Task 14
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Editor Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** When a model with mesh is loaded, viewport draws wireframe triangle edges that move with the current pose.
  - **Artifact Path:** `./animation_engine/editor/main.py`
- **Acceptance Criteria:** When a model with mesh is loaded, viewport draws wireframe triangle edges that move with the current pose.

### Task 24
- **Task Name:** Add F-curve editor panel for keyframe tangent visualisation
- **Narrative Logic:** Fine-tuning FF-style timing (anticipation hold, sharp impact, follow-through) requires seeing the value curve for each channel. A visual F-curve panel reduces manual trial-and-error.
- **Code Structure Need:** Add a `tk.Canvas`-based curve panel below the timeline. Read keyframe values from the selected `AnimationChannel`, plot Bezier segments, draw draggable tangent handles. Write edited tangent data back via `add_keyframe` with `KeyframeType.CUBIC`.
- **READ_FILE:** `./animation_engine/editor/main.py`
- **READ_LINES:** `532-580, 685-760`
- **READ_FILE:** `./animation_engine/animation/channel.py`
- **READ_LINES:** `1-60`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** Add `_build_curve_editor` after `_build_timeline` ~line `577`; add `_redraw_curve_editor` and tangent drag handlers after `_redraw_timeline` ~line `685`
- **Dependency Inputs:** Task 23
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Editor Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Selecting a channel on the timeline shows its value curve; dragging a tangent handle updates the channel keyframe and redraws the preview.
  - **Artifact Path:** `./animation_engine/editor/main.py`
- **Acceptance Criteria:** Selecting a channel on the timeline shows its value curve; dragging a tangent handle updates the channel keyframe and redraws the preview.

### Task 25
- **Task Name:** Expose IK posing mode in editor viewport
- **Narrative Logic:** IK goal-dragging lets animators block foot-plant and hand-contact poses far faster than manual FK entry. These contact poses are essential for FF PS2-era expressive body language.
- **Code Structure Need:** Add IK mode toggle button in toolbar. When active, click on a projected joint to select it as end-effector; drag calls `IKSolver(chain).solve(goal_pos)` and writes the result as a keyframe at `playback.time_seconds`.
- **READ_FILE:** `./animation_engine/editor/main.py`
- **READ_LINES:** `243-299, 1452-1495`
- **READ_FILE:** `./animation_engine/animation/ik_solver.py`
- **READ_LINES:** `30-95`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** Add IK toggle ~line `243` in `_build_toolbar`; add `_on_viewport_ik_drag` ~line `1480`; add `_apply_ik_pose` ~line `1490`
- **Dependency Inputs:** Task 23
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Editor Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Enabling IK mode and dragging a joint in the viewport updates that joint's rotation keyframe; disabling IK mode restores normal orbit behaviour.
  - **Artifact Path:** `./animation_engine/editor/main.py`
- **Acceptance Criteria:** Enabling IK mode and dragging a joint in the viewport updates that joint's rotation keyframe; disabling IK mode restores normal orbit behaviour.

### Task 26
- **Task Name:** Improve procedural walk and run cycle motion quality
- **Narrative Logic:** The current walk/run uses a single root-bob with two keyframes. A proper stride cycle with hip sway, pelvis rotation, counter-shoulder swing, and foot contact pairs produces character-appropriate FF-style locomotion.
- **Code Structure Need:** Replace the `walk` branch with an eight-keyframe root translation + pelvis lateral + shoulder counter-rotation loop. Replace `run` with a tighter four-count version with stronger amplitude. Use the skeleton bone name list to target the correct bones.
- **READ_FILE:** `./animation_engine/backend.py`
- **READ_LINES:** `195-265`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `200-225` (walk branch), `265-310` (run branch)
- **Dependency Inputs:** Task 05
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Systems Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Generated walk clip has keyframes on at least three bone channels (root, pelvis/hip, left_shoulder) with values that produce a visible stride cycle when played back.
  - **Artifact Path:** `./animation_engine/backend.py`
- **Acceptance Criteria:** Generated walk clip has keyframes on at least three bone channels (root, pelvis/hip, left_shoulder) with values that produce a visible stride cycle when played back.

### Task 27
- **Task Name:** Improve procedural combat clip motion quality
- **Narrative Logic:** Current attack/cast/dodge branches produce one or two rotation keyframes with no anticipation or follow-through. FF-style combat requires five-phase staged motion: rest → anticipate → strike → impact → recover.
- **Code Structure Need:** For each combat branch, add keyframes at: `0` (rest), `duration*0.2` (anticipate), `duration*0.45` (strike), `duration*0.55` (impact), `duration*1.0` (recover). Use spine and arm bone channels. Amplitude values should be larger than locomotion.
- **READ_FILE:** `./animation_engine/backend.py`
- **READ_LINES:** `430-670`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** attack `430-480`, heavy_attack `495-540`, cast `550-600`, dodge `615-660`
- **Dependency Inputs:** Task 05
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Systems Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Generated attack clip has at least five keyframes on spine and arm channels; keyframe values at the impact frame differ noticeably from rest and anticipation values.
  - **Artifact Path:** `./animation_engine/backend.py`
- **Acceptance Criteria:** Generated attack clip has at least five keyframes on spine and arm channels; keyframe values at the impact frame differ noticeably from rest and anticipation values.

### Task 28
- **Task Name:** Add pack format version migration utility
- **Narrative Logic:** Old `.anim` files (v1) lack `events`, `gameplay_tags`, and `version` keys. A migration utility lets `AnimImporter` load legacy assets cleanly without requiring re-export.
- **Code Structure Need:** Add `migrate_anim_dict(d: dict) -> dict` that: (1) checks for missing `"version"` key (v1 detection); (2) inserts `"version": 2`, `"events": []`, `"gameplay_tags": {}` if absent; (3) returns the dict unmodified if already v2. Call it at the top of `AnimImporter.load`.
- **READ_FILE:** `./animation_engine/io/anim_format.py`
- **READ_LINES:** `85-120, 160-190`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** Add `migrate_anim_dict` ~line `95`; call it in `AnimImporter.load` ~line `165`
- **Dependency Inputs:** Task 16
- **Risk Class:** Medium
- **Mandatory Reviewer Role:** Animation Systems Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Loading a v1 dict (no `events` key) via `AnimImporter` succeeds and returns a clip; loading the same dict twice is idempotent.
  - **Artifact Path:** `./animation_engine/io/anim_format.py`
- **Acceptance Criteria:** Loading a v1 dict (no `events` key) via `AnimImporter` succeeds and returns a clip; loading the same dict twice is idempotent.

### Task 29
- **Task Name:** Add batch-export-headers CLI subcommand
- **Narrative Logic:** The GameRewritten release build needs all clip packs pre-converted to C++ headers. A single CLI command driven by the pack manifest avoids manual per-clip invocation.
- **Code Structure Need:** Add `_cmd_batch_export_headers(args)` that: reads manifest JSON from `--manifest`; iterates `ordered_files`; calls `AnimToHeaderConverter` on each `.anim` file; writes `<clip_name>.hpp` into `--output-dir`. Register as `batch-export-headers` subcommand in `build_parser`.
- **READ_FILE:** `./animation_engine/cli.py`
- **READ_LINES:** `333-386, 540-566`
- **READ_FILE:** `./compat/anim_to_cpp_header.py`
- **READ_LINES:** `12-30, 360-409`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** Add `_cmd_batch_export_headers` ~line `374`; add parser registration ~line `545`
- **Dependency Inputs:** Task 19
- **Risk Class:** Medium
- **Mandatory Reviewer Role:** Compatibility Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `animation-engine batch-export-headers --manifest ./pack.json --output-dir out/`
  - **Expected Output:** `animation-engine batch-export-headers --manifest ./pack.json --output-dir out/` creates one `.hpp` file per clip in `ordered_files` and exits with code 0 on success.
  - **Artifact Path:** `./animation_engine/cli.py`
- **Acceptance Criteria:** `animation-engine batch-export-headers --manifest ./pack.json --output-dir out/` creates one `.hpp` file per clip in `ordered_files` and exits with code 0 on success.

### Task 30
- **Task Name:** Add blend tree state graph panel in editor
- **Narrative Logic:** Artists cannot see the current state machine structure from the clip list alone. A read-only node-graph panel shows BlendTree states and transitions visually, reducing confusion during animation state authoring.
- **Code Structure Need:** Add a `State Graph` tab inside the centre panel. Draw each `BlendTreeState` as a rounded rectangle labelled with state name. Draw directed arrows between states for each allowed transition. Clicking a node highlights it.
- **READ_FILE:** `./animation_engine/editor/main.py`
- **READ_LINES:** `338-392`
- **READ_FILE:** `./animation_engine/animation/blend_tree.py`
- **READ_LINES:** `1-60, 131-175`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** Add `_build_state_graph_panel` ~line `392`; add `_redraw_state_graph` after `_redraw_timeline` ~line `685`
- **Dependency Inputs:** Task 23
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Editor Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** State Graph panel renders one node per BlendTreeState; transitions appear as arrows; panel redraws when blend tree state count changes.
  - **Artifact Path:** `./animation_engine/editor/main.py`
- **Acceptance Criteria:** State Graph panel renders one node per BlendTreeState; transitions appear as arrows; panel redraws when blend tree state count changes.

### Task 31
- **Task Name:** Add animation retargeting utility
- **Narrative Logic:** GameRewritten needs the same animation clips applied to multiple character skeletons (hero, enemy, NPC variants). Retargeting preserves pose intent while adapting to different proportions.
- **Code Structure Need:** Add `retarget_clip(clip, source_skel, target_skel, bone_map)` at module level in `clip.py`. For each channel: (1) look up `bone_map[channel.bone_name]`; (2) scale TRANSLATION values by `target_bone.length / source_bone.length`; (3) copy ROTATION values unchanged; (4) skip unmapped bones.
- **READ_FILE:** `./animation_engine/animation/clip.py`
- **READ_LINES:** `1-50, 175-220`
- **READ_FILE:** `./animation_engine/model/skeleton.py`
- **READ_LINES:** `1-60`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** Add `retarget_clip` function after `from_dict` ~line `205`
- **Dependency Inputs:** Task 28
- **Risk Class:** Medium
- **Mandatory Reviewer Role:** Animation Systems Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** `retarget_clip` with a 2x longer target bone scales root translation channels by 2.0 and leaves rotation channels unchanged.
  - **Artifact Path:** `./animation_engine/animation/clip.py`
- **Acceptance Criteria:** `retarget_clip` with a 2x longer target bone scales root translation channels by 2.0 and leaves rotation channels unchanged.

### Task 32
- **Task Name:** Add skinning and IK solver unit tests
- **Narrative Logic:** `cpu_skin_mesh` and `IKSolver` both exist and are used by the editor and runtime but have no direct unit tests. These tests protect against regressions when upstream math utilities change.
- **Code Structure Need:** Add `test_cpu_skin_mesh_deforms_vertices` that applies a translation-only skin matrix and asserts output positions differ from input. Add `test_ik_solver_converges` that places two bones in a chain, sets a reachable goal, and asserts end-effector distance < 0.01 after `solve`.
- **READ_FILE:** `./tests/test_animation.py`
- **READ_LINES:** `549-588`
- **READ_FILE:** `./animation_engine/runtime/skinning.py`
- **READ_LINES:** `36-65`
- **READ_FILE:** `./animation_engine/animation/ik_solver.py`
- **READ_LINES:** `30-95`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `589-628` (append at EOF)
- **Dependency Inputs:** Task 23, Task 25
- **Risk Class:** Medium
- **Mandatory Reviewer Role:** Test Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest ./tests/test_animation.py -q`
  - **Expected Output:** Both new tests pass with `python -m pytest ./tests/test_animation.py -q`.
  - **Artifact Path:** `./tests/test_animation.py`
- **Acceptance Criteria:** Both new tests pass with `python -m pytest ./tests/test_animation.py -q`.

### Task 33
- **Task Name:** Add retargeting and pack migration unit tests
- **Narrative Logic:** Tasks 28 and 31 add new public functions with no test coverage. Tests lock in the migration and retargeting contracts before GameRewritten begins consuming these utilities.
- **Code Structure Need:** Add `test_migrate_anim_dict_v1_to_v2` asserting that a dict without `events` key gains it and that existing keys survive. Add `test_retarget_clip_scales_translation` asserting that a clip with 1-unit root translation retargeted to a 2x-length skeleton produces 2-unit translation.
- **READ_FILE:** `./tests/test_io.py`
- **READ_LINES:** `550-589`
- **READ_FILE:** `./animation_engine/io/anim_format.py`
- **READ_LINES:** `85-100`
- **READ_FILE:** `./animation_engine/animation/clip.py`
- **READ_LINES:** `205-230`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `590-629` (append at EOF)
- **Dependency Inputs:** Task 28, Task 31
- **Risk Class:** Medium
- **Mandatory Reviewer Role:** Test Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest ./tests/test_io.py -q`
  - **Expected Output:** Both new tests pass with `python -m pytest ./tests/test_io.py -q`.
  - **Artifact Path:** `./tests/test_io.py`
- **Acceptance Criteria:** Both new tests pass with `python -m pytest ./tests/test_io.py -q`.

### Task 34
- **Task Name:** Update program_assessment.md with final completion scores
- **Narrative Logic:** The assessment document was written before Tasks 1–34 were complete. Updating it gives new contributors and the GameRewritten team an accurate picture of what is production-ready.
- **Code Structure Need:** In section 3 mark all gaps A–F as resolved (with brief notes on which tasks resolved them). In section 5 update each score to reflect completed state (target: all categories ≥ 8/10). In section 6 replace the recommendation list with a completion summary.
- **READ_FILE:** `./program_assessment.md`
- **READ_LINES:** `FULL_FILE`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `19-64`
- **Dependency Inputs:** Task 23, Task 24, Task 25, Task 26, Task 27, Task 28, Task 29, Task 30, Task 31, Task 32, Task 33
- **Risk Class:** Low
- **Mandatory Reviewer Role:** Documentation Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `rg -n "Resolved — Task|/10" ./program_assessment.md`
  - **Expected Output:** All six readiness scores in section 5 are updated; all gap items in section 3 include a "(Resolved — Task N)" note.
  - **Artifact Path:** `./program_assessment.md`
- **Acceptance Criteria:** All six readiness scores in section 5 are updated; all gap items in section 3 include a "(Resolved — Task N)" note.

---

### Phase G Review Checkpoints
- **Design review:** Confirm every acceptance criterion in this phase is measurable, deterministic, and dependency-safe before implementation is marked ready for review.
- **Code review:** Verify the one-file-per-task rule still holds and that no hidden cross-file coupling was introduced outside the declared dependency inputs.
- **Test review:** Check that new or updated tests cover the changed behavior, preserve backward compatibility where required, and are scheduled immediately after the feature work they validate.
- **Release review:** Confirm the proof block for each task contains a command, expected result, and artifact path that a reviewer can independently replay.

## Phase H — Full Animation GUI Completion

Execute the final editor-heavy pass in strict order: state helpers, timeline controls, direct editing, history/recovery, workflow documentation, then regression tests.

### Task 35
- **Task Name:** Expand editor state helpers for timeline view and history
- **Narrative Logic:** The current editor state helpers cover playback and recent files, but a full animation GUI also needs deterministic state for timeline zoom, visible range, selection IDs, bookmarks, and undo snapshots. Keeping those rules in a pure helper module reduces Tkinter-only logic and stays friendly to weak local LLM workflows.
- **Code Structure Need:** Extend `animation_engine/editor/state.py` with dataclasses and helpers for timeline view state, playback in/out range, selected keyframe IDs, bookmark storage, and labeled undo/redo snapshot stacks.
- **READ_FILE:** `./animation_engine/editor/state.py`
- **READ_LINES:** `1-80`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `1-220`
- **Dependency Inputs:** Task 23, Task 24, Task 25, Task 30
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Editor Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Pure helper tests can create, clamp, and restore editor state without importing Tkinter.
  - **Artifact Path:** `./animation_engine/editor/state.py`
- **Acceptance Criteria:** Pure helper tests can create, clamp, and restore editor state without importing Tkinter.

### Task 36
- **Task Name:** Add timeline zoom, pan, and transport range controls
- **Narrative Logic:** A full animation GUI must let animators focus on a small timing window instead of always viewing a fixed 10-second strip. Dedicated controls for zoom, pan, and transport range are foundational before direct keyframe manipulation becomes usable.
- **Code Structure Need:** In `animation_engine/editor/main.py`, add toolbar and timeline controls backed by the new state helpers so the timeline can zoom, pan, and display only the active range while keeping playhead, scrubber, and ruler in sync.
- **READ_FILE:** `./animation_engine/editor/main.py`
- **READ_LINES:** `275-330, 1046-1090, 1378-1435`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `275-330, 1046-1194, 1378-1435`
- **Dependency Inputs:** Task 35
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Editor Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** User can zoom in/out, pan the visible time window, and see the ruler/playhead update without desynchronizing playback.
  - **Artifact Path:** `./animation_engine/editor/main.py`
- **Acceptance Criteria:** User can zoom in/out, pan the visible time window, and see the ruler/playhead update without desynchronizing playback.

### Task 37
- **Task Name:** Add direct keyframe selection, marquee, and drag editing
- **Narrative Logic:** The editor is not “full” while keyframes are only passive diamonds. Artists need direct mouse-driven keyframe selection, marquee selection, and drag retiming so the timeline behaves like an actual animation tool instead of a playback monitor.
- **Code Structure Need:** In `animation_engine/editor/main.py`, add timeline hit-testing, selected-keyframe highlighting, box selection, drag-to-retime, and redraw logic for one or many keyframes across visible rows.
- **READ_FILE:** `./animation_engine/editor/main.py`
- **READ_LINES:** `1046-1194, 1868-1890`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `1094-1194, 1868-1935`
- **Dependency Inputs:** Task 35, Task 36
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Editor Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Clicking selects a keyframe, dragging moves it in time, and marquee selection can select multiple keys without affecting unrelated rows.
  - **Artifact Path:** `./animation_engine/editor/main.py`
- **Acceptance Criteria:** Clicking selects a keyframe, dragging moves it in time, and marquee selection can select multiple keys without affecting unrelated rows.

### Task 38
- **Task Name:** Add duplicate, copy/paste, delete, and nudge for selected keys
- **Narrative Logic:** After keyframes become selectable, the next productivity gap is repetitive timing cleanup. Full animation GUI workflows need deterministic copy/paste, duplicate, delete, and frame nudge actions so loops, anticipation holds, and impact offsets can be authored quickly.
- **Code Structure Need:** In `animation_engine/editor/main.py`, add keyboard shortcuts and edit-menu actions for selected timeline keys, including clipboard serialization, duplicate-in-place, delete, and frame-accurate left/right nudging.
- **READ_FILE:** `./animation_engine/editor/main.py`
- **READ_LINES:** `143-181, 1439-1515, 1868-1935`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `163-181, 1439-1515, 1868-1985`
- **Dependency Inputs:** Task 37
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Editor Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** A selected keyframe set can be duplicated or pasted at the playhead, deleted, and nudged by frame steps with immediate timeline redraw.
  - **Artifact Path:** `./animation_engine/editor/main.py`
- **Acceptance Criteria:** A selected keyframe set can be duplicated or pasted at the playhead, deleted, and nudged by frame steps with immediate timeline redraw.

### Task 39
- **Task Name:** Upgrade event editing to full timeline and inspector workflows
- **Narrative Logic:** Event markers already exist, but a full animation GUI needs event authoring to feel equal to transform key authoring. Direct marker selection, drag retiming, rename, and payload editing are required for gameplay synchronization workflows like footsteps, hit windows, and cast release timing.
- **Code Structure Need:** In `animation_engine/editor/main.py`, expand the event panel into a richer inspector with editable payload text, selection sync with the timeline, marker dragging, and context actions for rename/duplicate/delete.
- **READ_FILE:** `./animation_engine/editor/main.py`
- **READ_LINES:** `580-643, 1170-1194, 1793-1838`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `580-643, 1170-1194, 1793-1867`
- **Dependency Inputs:** Task 37, Task 38
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Editor Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Event markers can be selected from either the list or timeline, edited in-place, dragged to a new time, and saved without losing payload data.
  - **Artifact Path:** `./animation_engine/editor/main.py`
- **Acceptance Criteria:** Event markers can be selected from either the list or timeline, edited in-place, dragged to a new time, and saved without losing payload data.

### Task 40
- **Task Name:** Add contact marker schema to animation clips
- **Narrative Logic:** Contact markers are the missing data contract between the current editor and a production-ready animation GUI. Foot plants, hand plants, weapon contact, and landing windows should live beside events in the clip itself so they round-trip through save/load and can drive later GUI overlays.
- **Code Structure Need:** Extend `animation_engine/animation/clip.py` with contact-marker add/remove/query helpers plus `to_dict()` / `from_dict()` support for named markers containing time, channel, side, and optional metadata.
- **READ_FILE:** `./animation_engine/animation/clip.py`
- **READ_LINES:** `33-87, 228-254`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `33-120, 228-254`
- **Dependency Inputs:** Task 39
- **Risk Class:** Medium
- **Mandatory Reviewer Role:** Animation Systems Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Contact markers serialize and deserialize in sorted order without changing existing clip event behavior.
  - **Artifact Path:** `./animation_engine/animation/clip.py`
- **Acceptance Criteria:** Contact markers serialize and deserialize in sorted order without changing existing clip event behavior.

### Task 41
- **Task Name:** Add contact marker lane, inspector, and viewport overlays
- **Narrative Logic:** Contact data is not useful unless animators can see and edit it directly. A dedicated lane and viewport overlay make it clear when feet, hands, or props should stick, which is essential for PS2-era readable motion polish.
- **Code Structure Need:** In `animation_engine/editor/main.py`, add a contact-marker lane below the ruler, a contact inspector beside the event tools, and viewport overlays that highlight active contacts at the current playhead.
- **READ_FILE:** `./animation_engine/editor/main.py`
- **READ_LINES:** `580-648, 1094-1194, 2051-2397`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `580-648, 1094-1194, 2087-2397`
- **Dependency Inputs:** Task 40
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Editor Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Adding a contact marker shows it on the timeline and viewport at the correct time, and saving/reopening preserves it.
  - **Artifact Path:** `./animation_engine/editor/main.py`
- **Acceptance Criteria:** Adding a contact marker shows it on the timeline and viewport at the correct time, and saving/reopening preserves it.

### Task 42
- **Task Name:** Add viewport bone picking and selected-bone highlighting
- **Narrative Logic:** A full animation GUI should let artists choose bones from the viewport, not only from the tree view. Bone picking, selection highlighting, and clear active-bone feedback make pose blocking much faster during combat and cinematic authoring.
- **Code Structure Need:** In `animation_engine/editor/main.py`, add projected-bone hit-testing, selected-bone outlines, status text updates, and selection sync between the viewport, bone tree, properties panel, and timeline rows.
- **READ_FILE:** `./animation_engine/editor/main.py`
- **READ_LINES:** `331-341, 437-497, 1856-2397`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `331-341, 437-497, 1856-2397`
- **Dependency Inputs:** Task 36, Task 37
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Editor Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Clicking a visible joint selects the same bone in all UI panels and highlights it until another bone is selected.
  - **Artifact Path:** `./animation_engine/editor/main.py`
- **Acceptance Criteria:** Clicking a visible joint selects the same bone in all UI panels and highlights it until another bone is selected.

### Task 43
- **Task Name:** Add pose mirror, reset, and selection-aware pose tools
- **Narrative Logic:** Full manual animation work involves repeated left/right pose transfer and recovery from bad experimental edits. Mirror-pose and reset helpers speed up blocking of symmetrical combat, locomotion, and idle motions while reducing accidental destructive edits.
- **Code Structure Need:** In `animation_engine/editor/main.py`, add Tools or Edit actions for mirroring selected-bone transforms, resetting selected channels to bind/default pose, and applying those operations at the current playhead or selected keyframe set.
- **READ_FILE:** `./animation_engine/editor/main.py`
- **READ_LINES:** `143-202, 1439-1776`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `163-202, 1439-1776`
- **Dependency Inputs:** Task 42
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Editor Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** User can mirror or reset the active pose for selected bones and immediately see the result in both viewport and timeline.
  - **Artifact Path:** `./animation_engine/editor/main.py`
- **Acceptance Criteria:** User can mirror or reset the active pose for selected bones and immediately see the result in both viewport and timeline.

### Task 44
- **Task Name:** Add clip bookmarks plus in/out playback preview range
- **Narrative Logic:** A full animation GUI must support quick iteration on a subsection of a clip rather than replaying the full clip every time. Bookmarks and in/out preview ranges let animators loop only the anticipation, impact, recovery, or contact window they are currently polishing.
- **Code Structure Need:** In `animation_engine/editor/main.py`, add bookmark commands, in/out markers on the timeline, playback clamping to preview range, and UI affordances for clearing or jumping between bookmarks.
- **READ_FILE:** `./animation_engine/editor/main.py`
- **READ_LINES:** `275-330, 1094-1194, 1378-1435`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `275-330, 1094-1194, 1378-1435`
- **Dependency Inputs:** Task 36, Task 37, Task 38
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Editor Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Playback can loop only the chosen in/out range, and bookmarks jump the playhead to saved timing landmarks.
  - **Artifact Path:** `./animation_engine/editor/main.py`
- **Acceptance Criteria:** Playback can loop only the chosen in/out range, and bookmarks jump the playhead to saved timing landmarks.

### Task 45
- **Task Name:** Add undo/redo history helpers with labeled snapshot coalescing
- **Narrative Logic:** Direct manipulation features become risky without deterministic rollback. Undo/redo should be driven by pure state helpers so future editor additions can reuse the same rules without duplicating Tkinter-specific history logic.
- **Code Structure Need:** Extend `animation_engine/editor/state.py` with undo/redo stack helpers, labeled snapshots, stack limits, and small-change coalescing rules for repeated drags or nudges.
- **READ_FILE:** `./animation_engine/editor/state.py`
- **READ_LINES:** `1-220`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `1-260`
- **Dependency Inputs:** Task 35, Task 37, Task 38, Task 39, Task 44
- **Risk Class:** Medium
- **Mandatory Reviewer Role:** Animation Editor Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Helper calls can push, undo, redo, and coalesce snapshots deterministically while honoring a fixed history limit.
  - **Artifact Path:** `./animation_engine/editor/state.py`
- **Acceptance Criteria:** Helper calls can push, undo, redo, and coalesce snapshots deterministically while honoring a fixed history limit.

### Task 46
- **Task Name:** Wire undo/redo, autosave recovery, and session restore into editor
- **Narrative Logic:** Once history helpers exist, the GUI should use them everywhere that matters. Autosave and crash recovery keep long authoring sessions safe, and session restore makes the editor feel complete enough for daily production use.
- **Code Structure Need:** In `animation_engine/editor/main.py`, integrate snapshot creation into key editing, event/contact editing, and pose tools; add autosave/recovery prompts; and restore timeline/bookmark/session state on reopen when recovery data exists.
- **READ_FILE:** `./animation_engine/editor/main.py`
- **READ_LINES:** `1199-1358, 1439-1985, 2087-2397`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `1199-1358, 1439-1985, 2087-2397`
- **Dependency Inputs:** Task 35, Task 37, Task 38, Task 39, Task 40, Task 41, Task 42, Task 43, Task 44, Task 45
- **Risk Class:** High
- **Mandatory Reviewer Role:** Animation Editor Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q`
  - **Expected Output:** Undo/redo works across timeline and viewport edits, and an autosaved recovery document can reopen with playhead, selection, and clip state intact.
  - **Artifact Path:** `./animation_engine/editor/main.py`
- **Acceptance Criteria:** Undo/redo works across timeline and viewport edits, and an autosaved recovery document can reopen with playhead, selection, and clip state intact.

### Task 47
- **Task Name:** Document the full animation GUI workflow in README
- **Narrative Logic:** Small local LLMs and human contributors both need a single copy-ready workflow for the completed animation GUI. The README should explain timeline editing, event/contact authoring, viewport posing, preview ranges, and recovery behavior so the editor can be used without guesswork.
- **Code Structure Need:** Update the README with a `Full Animation GUI Workflow` section covering launch commands, major panels, key editing actions, event/contact markers, viewport pose tools, undo/redo, autosave recovery, and a short production-authoring checklist.
- **READ_FILE:** `./README.md`
- **READ_LINES:** `148-167, 200-255`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `148-167, 227-310`
- **Dependency Inputs:** Task 46
- **Risk Class:** Low
- **Mandatory Reviewer Role:** Documentation Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `rg -n "generate-pack|validate-pack|workflow|editor" ./README.md`
  - **Expected Output:** README gives exact editor launch commands and a deterministic step-by-step workflow for authoring and reviewing a clip in the finished GUI.
  - **Artifact Path:** `./README.md`
- **Acceptance Criteria:** README gives exact editor launch commands and a deterministic step-by-step workflow for authoring and reviewing a clip in the finished GUI.

### Task 48
- **Task Name:** Add animation GUI workflow regression tests
- **Narrative Logic:** Full GUI completion adds dense editing logic that weak local LLMs could easily regress. Focused non-Tkinter regression tests should lock in timeline state, history behavior, bookmark handling, and clip contact-marker round trips.
- **Code Structure Need:** Create `tests/test_editor_gui_workflows.py` with tests for state-helper clamping, undo/redo stack behavior, bookmark persistence, and `AnimationClip` contact-marker serialization.
- **READ_FILE:** `./tests/test_editor_state.py`
- **READ_LINES:** `1-280`
- **READ_FILE:** `./animation_engine/editor/state.py`
- **READ_LINES:** `FULL_FILE`
- **READ_FILE:** `./animation_engine/animation/clip.py`
- **READ_LINES:** `33-120, 228-254`
- **File Edited or Created:** Create new file `./tests/test_editor_gui_workflows.py`
- **Lines Being Edited:** `1-260`
- **Dependency Inputs:** Task 35, Task 40, Task 45, Task 46, Task 47
- **Risk Class:** Medium
- **Mandatory Reviewer Role:** Animation Editor Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest ./tests/test_editor_gui_workflows.py -q`
  - **Expected Output:** `python -m pytest tests/test_editor_gui_workflows.py -q` passes and proves the new GUI state contracts are deterministic.
  - **Artifact Path:** `./tests/test_editor_gui_workflows.py`
- **Acceptance Criteria:** `python -m pytest tests/test_editor_gui_workflows.py -q` passes and proves the new GUI state contracts are deterministic.

---

### Phase H Review Checkpoints
- **Design review:** Confirm every acceptance criterion in this phase is measurable, deterministic, and dependency-safe before implementation is marked ready for review.
- **Code review:** Verify the one-file-per-task rule still holds and that no hidden cross-file coupling was introduced outside the declared dependency inputs.
- **Test review:** Check that new or updated tests cover the changed behavior, preserve backward compatibility where required, and are scheduled immediately after the feature work they validate.
- **Release review:** Confirm the proof block for each task contains a command, expected result, and artifact path that a reviewer can independently replay.

## Phase I — Final Release Readiness and Go/No-Go

Run the final acceptance gate only after every implementation, documentation, and regression step above is complete.

### Task 22
- **Task Name:** Final acceptance gate for retail-grade export
- **Narrative Logic:** Conclude with a measurable go/no-go standard for `Mikester9000/GameRewritten` handoff.
- **Code Structure Need:** Define required pass matrix: tests green, validators green, full pack generated, compat docs updated.
- **READ_FILE:** `./README.md`
- **READ_LINES:** `42-103,104-136`
- **File Edited or Created:** Edit this file only if criteria evolve
- **Lines Being Edited:** `267-286`
- **Dependency Inputs:** Task 10, Task 14, Task 15, Task 16, Task 17, Task 18, Task 19, Task 20, Task 21, Task 29, Task 34, Task 48
- **Risk Class:** High
- **Mandatory Reviewer Role:** Release Reviewer
- **Do Not Mark Complete Without Proof:**
  - **Command Run:** `python -m pytest -q && animation-engine generate-pack --help && animation-engine validate-pack --help`
  - **Expected Output:** All required gates pass before release tag.
  - **Artifact Path:** `./README.md`
- **Acceptance Criteria:** All required gates pass before release tag.

---

### Phase I Review Checkpoints
- **Design review:** Confirm every acceptance criterion in this phase is measurable, deterministic, and dependency-safe before implementation is marked ready for review.
- **Code review:** Verify the one-file-per-task rule still holds and that no hidden cross-file coupling was introduced outside the declared dependency inputs.
- **Test review:** Check that new or updated tests cover the changed behavior, preserve backward compatibility where required, and are scheduled immediately after the feature work they validate.
- **Release review:** Confirm the proof block for each task contains a command, expected result, and artifact path that a reviewer can independently replay.

---

## Authoritative Release Validation Gates

1. `python -m pytest -q`
2. Generate at least one full nostalgia profile pack through the CLI.
3. Run the CLI validation command against the generated pack.
4. Verify the pack manifest lists all required clips in order.
5. Verify the compatibility handoff path (`README.md`, `compat/README.md`, and header-export workflow) matches the generated artifacts.
6. Run the late-stage targeted validations required by Tasks 29, 32, 33, and 48 before Task 22 is marked complete.

---

## Final Traceability Matrix

| Handoff requirement | Task IDs | Primary proof/tests |
|---|---|---|
| `.anim` metadata compatibility and migration safety | 01, 16, 28, 33 | `./tests/test_io.py` |
| Style profiles, motion taxonomy, and deterministic generation inputs | 02, 03, 04, 05 | `./tests/test_backend_qa_integration.py` |
| Full-pack manifest generation, failure handling, and deterministic defaults | 06, 07, 08, 20 | `./tests/test_backend_qa_integration.py` |
| CLI generation, validation, and batch header export | 09, 10, 29 | `python -m pytest -q`, `animation-engine batch-export-headers --manifest <pack.json> --output-dir out/` |
| QA coverage, pack completeness, and backward-compatibility gates | 11, 12, 13, 14, 15, 16 | `./tests/test_backend_qa_integration.py`, `./tests/test_io.py` |
| README and compatibility handoff documentation | 17, 18, 19, 21 | `./README.md`, `./compat/README.md`, `./compat/anim_to_cpp_header.py` |
| Late-stage runtime/tooling/editor improvements | 23, 24, 25, 26, 27, 28, 29, 30, 31 | `python -m pytest -q`, targeted smoke checks listed in each proof block |
| Editor workflow depth, history/recovery, and GUI regression coverage | 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48 | `./tests/test_editor_state.py`, `./tests/test_editor_gui_workflows.py` |
| Final go/no-go release gate | 22 | `python -m pytest -q`, CLI smoke commands, documented artifact checks |

---

## Historical Validation Snapshot (Non-Authoritative Reference)

This snapshot is retained for context only. Treat every `PASS` line below as stale until the commands are rerun in the current repository state and their proof artifacts are re-collected.

## Legacy Release Readiness Snapshot (Task 22)
At the time this snapshot was captured, all gates below were verified and passed.

| Gate | Status | Details |
|------|--------|---------|
| `python -m pytest -q` | ✅ PASS | 225 tests pass (0 failures, 0 errors) |
| `generate-pack` (ff10_ps2 profile) | ✅ PASS | 57/57 clips generated; `pack_manifest.json` written with profile ID, visual_target, gameplay_target, reference_titles, ordered_files, seed, sample_rate, generation_version |
| `validate-pack` against generated manifest | ✅ PASS | Style report VALID; all required clips present in correct order; per-clip art-direction fields verified |
| Manifest lists all required clips in order | ✅ PASS | `ordered_files` entries match `required_clips` in profile definition |
| Byte-stable deterministic output | ✅ PASS | `test_pipeline_byte_stable_output_same_inputs` confirms identical MD5s across two identical runs |
| Compat docs — `compat/README.md` | ✅ PASS | Manifest ingestion, failure handling rules, `anim_to_cpp_header.py` batch workflow documented |
| Compat docs — `README.md` | ✅ PASS | Profile selection, CLI commands, expected pack tree, and smoke test sequence documented |
| Quality gates — manifest art-direction | ✅ PASS | `validate-pack` enforces `visual_target`, `gameplay_target`, `reference_titles` match selected profile |
| Quality gates — per-clip metadata | ✅ PASS | `validate-pack` enforces per-clip `style_profile`, `motion_type`, art-direction fields, duration, sample_rate |
| Deterministic defaults pinned | ✅ PASS | `PIPELINE_DEFAULT_BACKEND`, `PIPELINE_DEFAULT_SAMPLE_RATE`, `PIPELINE_DEFAULT_SEED`, `PIPELINE_DEFAULT_PROFILE_ID`, `PIPELINE_GENERATION_VERSION` exported from `asset_pipeline.py` |
| BlendTree `has_exit_time` enforcement (Task 13) | ✅ PASS | Exit-time deferred transitions, auto-condition transitions, and context merging fully implemented in `blend_tree.py`; 9 new tests added in `test_animation.py` |
| BlendTree `get_events_in_window` (Task 13) | ✅ PASS | `AnimationClip.get_events_in_window(start, end)` added to `clip.py`; event timing window tests passing |
| glTF extras — events + loop flag (Task 14) | ✅ PASS | `GltfExporter` writes `extras.loop` + `extras.events`; `GltfImporter` reads them back; 3 new tests added in `test_io.py` |
| `.anim` event serialization compat (Task 18) | ✅ PASS | Legacy (no events key) and forward-compat (unknown data keys) tests added in `test_io.py` |
| C++ header events + metadata (Task 15) | ✅ PASS | `anim_to_cpp_header.py` emits clip events and style-profile metadata; `GameEngineCompat.hpp` `AE_AnimClip::Event` struct and `AE_AnimPackage` metadata fields added |
| Editor event track UI (Task 21) | ✅ PASS | `AnimationEditor` right panel includes Add/Remove event controls; events rendered as markers on the timeline canvas |

---

## Output Contract for Mikester9000/GameRewritten Handoff

At completion of Phase I, the export package must include:
- Complete ordered `.anim` clip set per selected profile.
- Pack manifest JSON with profile ID, PS2-era visual target, modern gameplay target, reference titles, clip inventory, and metadata.
- Validation status report (pass/fail with reasons).
- Saved source `.anim` authoring file containing transform keys, events, gameplay tags, contact markers, and editor-authored timing metadata needed for continued polish.
- Optional review export (for example glTF or validation snapshots) produced from the completed animation GUI workflow for downstream visual review.
- Contact-marker and event timing mapping that keeps authored gameplay windows aligned with clip playback in `Mikester9000/GameRewritten`.
- Updated compatibility documentation for import in `Mikester9000/GameRewritten` repo.
