# planv1 — Animation Engine to Retail-Grade Mikester9000/GameRewritten Export

This file is the single ordered master plan from current repository state to a retail-grade animation asset pipeline that exports cleanly into `Mikester9000/GameRewritten`.

---

## Execution Rules (for low-reasoning local LLMs)

1. Execute tasks strictly in numeric order.
2. Each task edits or creates one file only.
3. Do not skip validation gates.
4. Do not start the next task until current task acceptance criteria are met.
5. Keep every change deterministic and backward compatible unless the task explicitly says otherwise.
6. `READ_LINES` uses only two deterministic formats: numeric ranges (`start-end` comma-separated) or keyword `FULL_FILE` / `DIRECTORY`.

---

## Art Direction Baseline

All planned outputs must satisfy this visual target:

- Ship assets with a **high-end PS2-era JRPG look** that would still feel plausible on PlayStation 2-class hardware.
- Use *Final Fantasy VII*, *VIII*, *IX*, *X*, and *XII* as the primary visual readability references.
- Keep the motion library broad enough for modern gameplay/features comparable to *Final Fantasy VII Remake* and *Final Fantasy XV* even while preserving the PS2-era presentation target.
- Preserve this direction in generated metadata, manifests, and hand-off documentation so downstream tools can validate it.

---

## Phase A — Format + Profile Foundations

### Task 01
- **Task Name:** Add style metadata envelope to `.anim` payload
- **Narrative Logic:** Retail-ready assets need explicit style identity (FF7/FF8/FF10 nostalgia direction) embedded with animation data so `Mikester9000/GameRewritten` can consume and tag packs reliably.
- **Code Structure Need:** Extend serializer/deserializer schema with optional metadata block while preserving existing format compatibility.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/animation_engine/io/anim_format.py`
- **READ_LINES:** `33-38, 49-77, 90-103, 137-158`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `35-36, 96-102, 140-158`
- **Acceptance Criteria:** Existing imports still load old `.anim`; new metadata round-trips without loss.

### Task 02
- **Task Name:** Create nostalgia style profile registry
- **Narrative Logic:** Generation must be profile-driven so outputs stay inside the shared PS2-era art direction while still covering modern gameplay needs.
- **Code Structure Need:** Add centralized immutable style profile definitions for motion packs, clip timing, naming, cinematic mood, and explicit art-direction metadata.
- **READ_DIRECTORY:** `/home/runner/work/Animation-Engine/Animation-Engine/animation_engine/integration`
- **READ_LINES:** `DIRECTORY`
- **File Edited or Created:** Create new file `/home/runner/work/Animation-Engine/Animation-Engine/animation_engine/integration/style_profiles.py`
- **Lines Being Edited:** `1-260`
- **Acceptance Criteria:** Registry exposes stable profile IDs and ordered clip requirements.

### Task 03
- **Task Name:** Export style profiles in integration package API
- **Narrative Logic:** Downstream pipeline and CLI should import profiles from a stable public path.
- **Code Structure Need:** Re-export style profile registry via integration package init.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/animation_engine/integration/__init__.py`
- **READ_LINES:** `1-10`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `1-10`
- **Acceptance Criteria:** `from animation_engine.integration import ...` exposes profiles and pipeline cleanly.

---

## Phase B — Motion Generation Expansion

### Task 04
- **Task Name:** Expand backend supported motion taxonomy
- **Narrative Logic:** Retail-quality JRPG presentation requires a full move set beyond idle/walk/run/attack.
- **Code Structure Need:** Extend `supported_motion_types` and generation branches for core gameplay, combat, and cinematic loops.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/animation_engine/backend.py`
- **READ_LINES:** `72-75, 100-145, 192-200`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `72-75, 102-145`
- **Acceptance Criteria:** Backend advertises and can generate all required motion IDs for profile packs.

### Task 05
- **Task Name:** Add profile-aware generation parameters
- **Narrative Logic:** FF nostalgia variants need different cadence and amplitude tuning while sharing common pipeline code.
- **Code Structure Need:** Extend backend generation entry point to accept profile tuning data deterministically.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/animation_engine/backend.py`
- **READ_LINES:** `42-48, 89-96, 100-145`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `42-48, 89-96, 102-145`
- **Acceptance Criteria:** Generated clips differ predictably by profile inputs without randomness drift.

---

## Phase C — Asset Pipeline Orchestration

### Task 06
- **Task Name:** Replace fixed 4-clip list with profile manifest
- **Narrative Logic:** `Mikester9000/GameRewritten` needs complete pack generation in one pass, not demo-only motion output.
- **Code Structure Need:** Pipeline reads ordered clip manifest from profile registry and generates all required files.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/animation_engine/integration/asset_pipeline.py`
- **READ_LINES:** `15-16, 39-44, 64-86`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `39-44, 64-86`
- **Acceptance Criteria:** Manifest includes full ordered clip set; output count equals profile requirement count.

### Task 07
- **Task Name:** Emit pack-level manifest JSON beside `.anim` files
- **Narrative Logic:** `Mikester9000/GameRewritten` import stage requires machine-readable index of all generated assets and metadata.
- **Code Structure Need:** Add deterministic manifest writer with profile ID, clip list, file paths, and generation version.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/animation_engine/integration/asset_pipeline.py`
- **READ_LINES:** `39-44, 61-63, 83-86`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `61-63, 83-110`
- **Acceptance Criteria:** Pipeline returns and writes manifest with exact exported file inventory.

### Task 08
- **Task Name:** Add failure-safe generation checkpoints
- **Narrative Logic:** Retail pipeline must not silently ship partial packs.
- **Code Structure Need:** Add per-clip generation error collection and fail-fast summary status in pipeline output.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/animation_engine/integration/asset_pipeline.py`
- **READ_LINES:** `64-86`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `64-86`
- **Acceptance Criteria:** On any failed clip generation, pipeline marks status failed and reports exact failed motion IDs.

---

## Phase D — CLI Production Commands

### Task 09
- **Task Name:** Add CLI command for full nostalgia pack generation
- **Narrative Logic:** One command must produce all assets needed for `Mikester9000/GameRewritten` integration.
- **Code Structure Need:** Add subcommand for output dir, profile choice, skeleton source, and manifest path.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/animation_engine/cli.py`
- **READ_LINES:** `94-129, 132-140`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `94-129, 132-140`
- **Acceptance Criteria:** CLI command exits success and prints generated pack summary.

### Task 10
- **Task Name:** Add CLI command for pack validation gate
- **Narrative Logic:** Export to `Mikester9000/GameRewritten` should be blocked if quality gates fail.
- **Code Structure Need:** Add subcommand to run clip, loop, skeleton, and style validation over generated pack.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/animation_engine/cli.py`
- **READ_LINES:** `8-31, 58-77, 94-129`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `8-31, 58-77, 94-140`
- **Acceptance Criteria:** Non-zero exit when any required validator fails.

---

## Phase E — QA and Retail Quality Gates

### Task 11
- **Task Name:** Create style validator module
- **Narrative Logic:** Nostalgia target must be measurable, not subjective only.
- **Code Structure Need:** Add profile-aware validation rules for cadence, loop smoothness, and motion coverage.
- **READ_DIRECTORY:** `/home/runner/work/Animation-Engine/Animation-Engine/animation_engine/qa`
- **READ_LINES:** `DIRECTORY`
- **File Edited or Created:** Create new file `/home/runner/work/Animation-Engine/Animation-Engine/animation_engine/qa/style_validator.py`
- **Lines Being Edited:** `1-300`
- **Acceptance Criteria:** Validator returns structured report with pass/fail, warnings, and error reasons.

### Task 12
- **Task Name:** Export style validator in QA package API
- **Narrative Logic:** CLI and tests need stable import path for new validator.
- **Code Structure Need:** Update QA package exports.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/animation_engine/qa/__init__.py`
- **READ_LINES:** `1-29`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `1-29`
- **Acceptance Criteria:** Public QA API includes new style validator symbols.

### Task 13
- **Task Name:** Add pack completeness checker
- **Narrative Logic:** Retail delivery requires no missing motions in any profile pack.
- **Code Structure Need:** Add deterministic rule set that compares generated set vs required profile motion IDs.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/animation_engine/qa/style_validator.py`
- **READ_LINES:** `1-300`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `180-300`
- **Acceptance Criteria:** Missing, duplicate, or misnamed clips are reported as errors.

---

## Phase F — Tests for Stability and Backward Compatibility

### Task 14
- **Task Name:** Add integration test for full profile pack generation
- **Narrative Logic:** Prevent regressions where only partial packs are generated.
- **Code Structure Need:** Extend backend/pipeline integration tests with profile matrix checks and manifest assertions.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/tests/test_backend_qa_integration.py`
- **READ_LINES:** `15-20, 71-81, 83-92`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `93-170`
- **Acceptance Criteria:** Tests assert all required files exist and match profile order.

### Task 15
- **Task Name:** Add tests for style validator pass/fail behavior
- **Narrative Logic:** Retail quality gates must be deterministic and test-covered.
- **Code Structure Need:** Add QA tests validating both compliant and non-compliant clip sets.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/tests/test_backend_qa_integration.py`
- **READ_LINES:** `83-92`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `171-250`
- **Acceptance Criteria:** Controlled fixtures produce expected error/warning outputs.

### Task 16
- **Task Name:** Add `.anim` metadata round-trip tests
- **Narrative Logic:** New payload metadata must not break old import/export paths.
- **Code Structure Need:** Extend `TestAnimFormat` coverage for optional metadata persistence and backward compatibility.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/tests/test_io.py`
- **READ_LINES:** `83-164`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `110-164`
- **Acceptance Criteria:** Old payloads still import; new metadata fields survive export/import unchanged.

---

## Phase G — Mikester9000/GameRewritten Compatibility and Hand-off

### Task 17
- **Task Name:** Document profile-based pack export for engine users
- **Narrative Logic:** Teams need one deterministic hand-off recipe from generation to runtime load.
- **Code Structure Need:** Add README sections for profile selection, CLI commands, output directory contract, and manifest schema.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/README.md`
- **READ_LINES:** `10-24, 137-150`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `25-41, 137-150`
- **Acceptance Criteria:** README includes exact command flow and expected output tree.

### Task 18
- **Task Name:** Update compatibility bridge documentation
- **Narrative Logic:** `Mikester9000/GameRewritten` integration requires clear runtime vs pre-baked workflow for expanded pack output.
- **Code Structure Need:** Update compat guide with profile pack manifest usage and validation expectations before import.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/compat/README.md`
- **READ_LINES:** `18-44, 65-143, 192-215`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `18-44, 65-143, 192-235`
- **Acceptance Criteria:** Compat docs explicitly describe pack manifest ingestion and failure handling.

### Task 19
- **Task Name:** Add converter guidance for full pack batch conversion
- **Narrative Logic:** Retail export path must support generating multiple pre-baked headers from pack manifest.
- **Code Structure Need:** Document and/or script deterministic per-clip conversion workflow for `anim_to_cpp_header.py`.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/compat/anim_to_cpp_header.py`
- **READ_LINES:** `12-27, 360-409`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `12-27, 360-374`
- **Acceptance Criteria:** Batch conversion workflow is explicitly defined for `Mikester9000/GameRewritten` release builds.

---

## Phase H — Release Readiness, Deterministic Ops, and Final Verification

### Task 20
- **Task Name:** Add deterministic generation mode defaults
- **Narrative Logic:** Retail output must be reproducible for audits and patch pipelines.
- **Code Structure Need:** Ensure pipeline seed/profile/sample rate defaults are pinned and exposed in manifest.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/animation_engine/integration/asset_pipeline.py`
- **READ_LINES:** `28-38, 61-63, 83-86`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `28-38, 61-63, 83-110`
- **Acceptance Criteria:** Same inputs produce byte-stable pack outputs (excluding timestamps if any).

### Task 21
- **Task Name:** Add final smoke test command sequence to docs
- **Narrative Logic:** Small local LLMs need explicit no-ambiguity validation sequence before release.
- **Code Structure Need:** Add exact command list for install, tests, generation, and validation.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/README.md`
- **READ_LINES:** `42-103`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `104-136`
- **Acceptance Criteria:** Docs provide exact command order and expected success conditions.

### Task 22
- **Task Name:** Final acceptance gate for retail-grade export
- **Narrative Logic:** Conclude with a measurable go/no-go standard for `Mikester9000/GameRewritten` handoff.
- **Code Structure Need:** Define required pass matrix: tests green, validators green, full pack generated, compat docs updated.
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/planv1.md`
- **READ_LINES:** `FULL_FILE`
- **File Edited or Created:** Edit this file only if criteria evolve
- **Lines Being Edited:** `267-286`
- **Acceptance Criteria:** All required gates pass before release tag.

---

## Required Validation Gates After Implementation

1. `python -m pytest -v`
2. Generate at least one full nostalgia profile pack through CLI.
3. Run CLI validation command against generated pack.
4. Verify pack manifest lists all required clips in order.
5. Verify `Mikester9000/GameRewritten` compatibility path (runtime load and/or pre-baked header flow) with updated docs.

---

## Gate Results — Release Readiness (Task 22)

All gates below were verified and passed. Tag `Mikester9000/Animation-Engine` as ready for `GameRewritten` handoff.

| Gate | Status | Details |
|------|--------|---------|
| `python -m pytest -q` | ✅ PASS | 173 tests pass (0 failures, 0 errors) |
| `generate-pack` (ff10_ps2 profile) | ✅ PASS | 43/43 clips generated; `pack_manifest.json` written with profile ID, visual_target, gameplay_target, reference_titles, ordered_files, seed, sample_rate, generation_version |
| `validate-pack` against generated manifest | ✅ PASS | Style report VALID; all required clips present in correct order; per-clip art-direction fields verified |
| Manifest lists all required clips in order | ✅ PASS | `ordered_files` entries match `required_clips` in profile definition |
| Byte-stable deterministic output | ✅ PASS | `test_pipeline_byte_stable_output_same_inputs` confirms identical MD5s across two identical runs |
| Compat docs — `compat/README.md` | ✅ PASS | Manifest ingestion, failure handling rules, `anim_to_cpp_header.py` batch workflow documented |
| Compat docs — `README.md` | ✅ PASS | Profile selection, CLI commands, expected pack tree, and smoke test sequence documented |
| Quality gates — manifest art-direction | ✅ PASS | `validate-pack` enforces `visual_target`, `gameplay_target`, `reference_titles` match selected profile |
| Quality gates — per-clip metadata | ✅ PASS | `validate-pack` enforces per-clip `style_profile`, `motion_type`, art-direction fields, duration, sample_rate |
| Deterministic defaults pinned | ✅ PASS | `PIPELINE_DEFAULT_BACKEND`, `PIPELINE_DEFAULT_SAMPLE_RATE`, `PIPELINE_DEFAULT_SEED`, `PIPELINE_DEFAULT_PROFILE_ID`, `PIPELINE_GENERATION_VERSION` exported from `asset_pipeline.py` |

---

## Output Contract for Mikester9000/GameRewritten Handoff

At completion, export package must include:
- Complete ordered `.anim` clip set per selected profile.
- Pack manifest JSON with profile ID, PS2-era visual target, modern gameplay target, reference titles, clip inventory, and metadata.
- Validation status report (pass/fail with reasons).
- Updated compatibility documentation for import in `Mikester9000/GameRewritten` repo.
