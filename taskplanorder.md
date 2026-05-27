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
- **READ_FILE:** `/home/runner/work/Animation-Engine/Animation-Engine/README.md`
- **READ_LINES:** `42-103,104-136`
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

## Phase I — Motion Quality, Editor Depth, and Production Tooling (Tasks 23–34)

### Task 23
- **Task Name:** Render skinned mesh wireframe in PS2 viewport
- **Narrative Logic:** The PS2-era preview viewport currently draws skeleton sticks only. Drawing projected triangle edges from a skinned mesh gives artists a true wireframe character preview without GPU dependencies.
- **Code Structure Need:** Call `cpu_skin_mesh(mesh, skin_matrices)` in `_redraw_viewport`; project each vertex with `_project_world_point`; draw triangle edges using `canvas.create_line`.
- **READ_FILE:** `animation_engine/editor/main.py`
- **READ_LINES:** `1488-1560, 1600-1640`
- **READ_FILE:** `animation_engine/runtime/skinning.py`
- **READ_LINES:** `36-65`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `1488-1560` (_redraw_viewport body); add helper `_draw_mesh_wireframe` after `_draw_skeleton_world` near line `1608`
- **Acceptance Criteria:** When a model with mesh is loaded, viewport draws wireframe triangle edges that move with the current pose.

### Task 24
- **Task Name:** Add F-curve editor panel for keyframe tangent visualisation
- **Narrative Logic:** Fine-tuning FF-style timing (anticipation hold, sharp impact, follow-through) requires seeing the value curve for each channel. A visual F-curve panel reduces manual trial-and-error.
- **Code Structure Need:** Add a `tk.Canvas`-based curve panel below the timeline. Read keyframe values from the selected `AnimationChannel`, plot Bezier segments, draw draggable tangent handles. Write edited tangent data back via `add_keyframe` with `KeyframeType.CUBIC`.
- **READ_FILE:** `animation_engine/editor/main.py`
- **READ_LINES:** `532-580, 685-760`
- **READ_FILE:** `animation_engine/animation/channel.py`
- **READ_LINES:** `1-60`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** Add `_build_curve_editor` after `_build_timeline` ~line `577`; add `_redraw_curve_editor` and tangent drag handlers after `_redraw_timeline` ~line `685`
- **Acceptance Criteria:** Selecting a channel on the timeline shows its value curve; dragging a tangent handle updates the channel keyframe and redraws the preview.

### Task 25
- **Task Name:** Expose IK posing mode in editor viewport
- **Narrative Logic:** IK goal-dragging lets animators block foot-plant and hand-contact poses far faster than manual FK entry. These contact poses are essential for FF PS2-era expressive body language.
- **Code Structure Need:** Add IK mode toggle button in toolbar. When active, click on a projected joint to select it as end-effector; drag calls `IKSolver(chain).solve(goal_pos)` and writes the result as a keyframe at `playback.time_seconds`.
- **READ_FILE:** `animation_engine/editor/main.py`
- **READ_LINES:** `243-299, 1452-1495`
- **READ_FILE:** `animation_engine/animation/ik_solver.py`
- **READ_LINES:** `30-95`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** Add IK toggle ~line `243` in `_build_toolbar`; add `_on_viewport_ik_drag` ~line `1480`; add `_apply_ik_pose` ~line `1490`
- **Acceptance Criteria:** Enabling IK mode and dragging a joint in the viewport updates that joint's rotation keyframe; disabling IK mode restores normal orbit behaviour.

### Task 26
- **Task Name:** Improve procedural walk and run cycle motion quality
- **Narrative Logic:** The current walk/run uses a single root-bob with two keyframes. A proper stride cycle with hip sway, pelvis rotation, counter-shoulder swing, and foot contact pairs produces character-appropriate FF-style locomotion.
- **Code Structure Need:** Replace the `walk` branch with an eight-keyframe root translation + pelvis lateral + shoulder counter-rotation loop. Replace `run` with a tighter four-count version with stronger amplitude. Use the skeleton bone name list to target the correct bones.
- **READ_FILE:** `animation_engine/backend.py`
- **READ_LINES:** `195-265`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `200-225` (walk branch), `265-310` (run branch)
- **Acceptance Criteria:** Generated walk clip has keyframes on at least three bone channels (root, pelvis/hip, left_shoulder) with values that produce a visible stride cycle when played back.

### Task 27
- **Task Name:** Improve procedural combat clip motion quality
- **Narrative Logic:** Current attack/cast/dodge branches produce one or two rotation keyframes with no anticipation or follow-through. FF-style combat requires five-phase staged motion: rest → anticipate → strike → impact → recover.
- **Code Structure Need:** For each combat branch, add keyframes at: `0` (rest), `duration*0.2` (anticipate), `duration*0.45` (strike), `duration*0.55` (impact), `duration*1.0` (recover). Use spine and arm bone channels. Amplitude values should be larger than locomotion.
- **READ_FILE:** `animation_engine/backend.py`
- **READ_LINES:** `430-670`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** attack `430-480`, heavy_attack `495-540`, cast `550-600`, dodge `615-660`
- **Acceptance Criteria:** Generated attack clip has at least five keyframes on spine and arm channels; keyframe values at the impact frame differ noticeably from rest and anticipation values.

### Task 28
- **Task Name:** Add pack format version migration utility
- **Narrative Logic:** Old `.anim` files (v1) lack `events`, `gameplay_tags`, and `version` keys. A migration utility lets `AnimImporter` load legacy assets cleanly without requiring re-export.
- **Code Structure Need:** Add `migrate_anim_dict(d: dict) -> dict` that: (1) checks for missing `"version"` key (v1 detection); (2) inserts `"version": 2`, `"events": []`, `"gameplay_tags": {}` if absent; (3) returns the dict unmodified if already v2. Call it at the top of `AnimImporter.load`.
- **READ_FILE:** `animation_engine/io/anim_format.py`
- **READ_LINES:** `85-120, 160-190`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** Add `migrate_anim_dict` ~line `95`; call it in `AnimImporter.load` ~line `165`
- **Acceptance Criteria:** Loading a v1 dict (no `events` key) via `AnimImporter` succeeds and returns a clip; loading the same dict twice is idempotent.

### Task 29
- **Task Name:** Add batch-export-headers CLI subcommand
- **Narrative Logic:** The GameRewritten release build needs all clip packs pre-converted to C++ headers. A single CLI command driven by the pack manifest avoids manual per-clip invocation.
- **Code Structure Need:** Add `_cmd_batch_export_headers(args)` that: reads manifest JSON from `--manifest`; iterates `ordered_files`; calls `AnimToHeaderConverter` on each `.anim` file; writes `<clip_name>.hpp` into `--output-dir`. Register as `batch-export-headers` subcommand in `build_parser`.
- **READ_FILE:** `animation_engine/cli.py`
- **READ_LINES:** `333-386, 540-566`
- **READ_FILE:** `compat/anim_to_cpp_header.py`
- **READ_LINES:** `12-30, 360-409`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** Add `_cmd_batch_export_headers` ~line `374`; add parser registration ~line `545`
- **Acceptance Criteria:** `animation-engine batch-export-headers --manifest pack.json --output-dir out/` creates one `.hpp` file per clip in `ordered_files` and exits with code 0 on success.

### Task 30
- **Task Name:** Add blend tree state graph panel in editor
- **Narrative Logic:** Artists cannot see the current state machine structure from the clip list alone. A read-only node-graph panel shows BlendTree states and transitions visually, reducing confusion during animation state authoring.
- **Code Structure Need:** Add a `State Graph` tab inside the centre panel. Draw each `BlendTreeState` as a rounded rectangle labelled with state name. Draw directed arrows between states for each allowed transition. Clicking a node highlights it.
- **READ_FILE:** `animation_engine/editor/main.py`
- **READ_LINES:** `338-392`
- **READ_FILE:** `animation_engine/animation/blend_tree.py`
- **READ_LINES:** `1-60, 131-175`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** Add `_build_state_graph_panel` ~line `392`; add `_redraw_state_graph` after `_redraw_timeline` ~line `685`
- **Acceptance Criteria:** State Graph panel renders one node per BlendTreeState; transitions appear as arrows; panel redraws when blend tree state count changes.

### Task 31
- **Task Name:** Add animation retargeting utility
- **Narrative Logic:** GameRewritten needs the same animation clips applied to multiple character skeletons (hero, enemy, NPC variants). Retargeting preserves pose intent while adapting to different proportions.
- **Code Structure Need:** Add `retarget_clip(clip, source_skel, target_skel, bone_map)` at module level in `clip.py`. For each channel: (1) look up `bone_map[channel.bone_name]`; (2) scale TRANSLATION values by `target_bone.length / source_bone.length`; (3) copy ROTATION values unchanged; (4) skip unmapped bones.
- **READ_FILE:** `animation_engine/animation/clip.py`
- **READ_LINES:** `1-50, 175-220`
- **READ_FILE:** `animation_engine/model/skeleton.py`
- **READ_LINES:** `1-60`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** Add `retarget_clip` function after `from_dict` ~line `205`
- **Acceptance Criteria:** `retarget_clip` with a 2x longer target bone scales root translation channels by 2.0 and leaves rotation channels unchanged.

### Task 32
- **Task Name:** Add skinning and IK solver unit tests
- **Narrative Logic:** `cpu_skin_mesh` and `IKSolver` both exist and are used by the editor and runtime but have no direct unit tests. These tests protect against regressions when upstream math utilities change.
- **Code Structure Need:** Add `test_cpu_skin_mesh_deforms_vertices` that applies a translation-only skin matrix and asserts output positions differ from input. Add `test_ik_solver_converges` that places two bones in a chain, sets a reachable goal, and asserts end-effector distance < 0.01 after `solve`.
- **READ_FILE:** `tests/test_animation.py`
- **READ_LINES:** `last 40 lines of file`
- **READ_FILE:** `animation_engine/runtime/skinning.py`
- **READ_LINES:** `36-65`
- **READ_FILE:** `animation_engine/animation/ik_solver.py`
- **READ_LINES:** `30-95`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** Append new tests at end of file
- **Acceptance Criteria:** Both new tests pass with `python -m pytest tests/test_animation.py -q`.

### Task 33
- **Task Name:** Add retargeting and pack migration unit tests
- **Narrative Logic:** Tasks 28 and 31 add new public functions with no test coverage. Tests lock in the migration and retargeting contracts before GameRewritten begins consuming these utilities.
- **Code Structure Need:** Add `test_migrate_anim_dict_v1_to_v2` asserting that a dict without `events` key gains it and that existing keys survive. Add `test_retarget_clip_scales_translation` asserting that a clip with 1-unit root translation retargeted to a 2x-length skeleton produces 2-unit translation.
- **READ_FILE:** `tests/test_io.py`
- **READ_LINES:** `last 40 lines of file`
- **READ_FILE:** `animation_engine/io/anim_format.py`
- **READ_LINES:** `85-100`
- **READ_FILE:** `animation_engine/animation/clip.py`
- **READ_LINES:** `205-230`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** Append new tests at end of file
- **Acceptance Criteria:** Both new tests pass with `python -m pytest tests/test_io.py -q`.

### Task 34
- **Task Name:** Update program_assessment.md with final completion scores
- **Narrative Logic:** The assessment document was written before Tasks 1–34 were complete. Updating it gives new contributors and the GameRewritten team an accurate picture of what is production-ready.
- **Code Structure Need:** In section 3 mark all gaps A–F as resolved (with brief notes on which tasks resolved them). In section 5 update each score to reflect completed state (target: all categories ≥ 8/10). In section 6 replace the recommendation list with a completion summary.
- **READ_FILE:** `program_assessment.md`
- **READ_LINES:** `FULL_FILE`
- **File Edited or Created:** Edit existing file
- **Lines Being Edited:** `19-64`
- **Acceptance Criteria:** All six readiness scores in section 5 are updated; all gap items in section 3 include a "(Resolved — Task N)" note.

---

## Phase I Required Validation Gates (Tasks 23–34)

1. `python -m pytest -q` — all tests pass including new Tasks 32 and 33 tests.
2. `animation-engine batch-export-headers --manifest <pack.json> --output-dir /tmp/headers/` — exits 0 and writes one `.hpp` per clip.
3. Load a v1 `.anim` dict through `AnimImporter` — no exception raised.
4. Editor launches and State Graph panel renders at least one node.
5. `program_assessment.md` section 5 shows all scores ≥ 8/10.

---

## Output Contract for Mikester9000/GameRewritten Handoff

At completion, export package must include:
- Complete ordered `.anim` clip set per selected profile.
- Pack manifest JSON with profile ID, PS2-era visual target, modern gameplay target, reference titles, clip inventory, and metadata.
- Validation status report (pass/fail with reasons).
- Updated compatibility documentation for import in `Mikester9000/GameRewritten` repo.
