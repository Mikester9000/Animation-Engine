# Task List — Path to Completion for GameRewritten Animation Needs

## Task 01
- **Task Name:** Expand required clip taxonomy to full gameplay coverage
- **Coding logic of task and narrative design required:** Define a much larger required clip set for exploration, traversal, combat, damage states, interactions, and celebration/idle variants while preserving FF-style readability and dramatic pose language.
- **Logic of how it functions in the program and design it must follow:** `StyleProfile.required_clips` drives generation and validation, so expanding it upgrades the whole pipeline contract automatically.
- **Check to adhere to Final Fantasy aesthetics:** Ensure each clip purpose preserves PS2-era silhouette clarity while enabling modern FF15/FF7R gameplay pacing.
- **Name of the file to be edited or create:** `animation_engine/integration/style_profiles.py`
- **Line where code is to be edited or create:** Edit around `35-48`, `71-122`.

## Task 02
- **Task Name:** Add profile-level motion style variants by gameplay class
- **Coding logic of task and narrative design required:** Add profile tuning fields per gameplay class (locomotion, melee, magic, reaction, traversal) so style remains coherent while behavior differs by context.
- **Logic of how it functions in the program and design it must follow:** Pipeline reads profile values and passes them to backend generation for deterministic motion shaping.
- **Check to adhere to Final Fantasy aesthetics:** Keep heroic, readable arcs and cinematic cadence aligned with FF references.
- **Name of the file to be edited or create:** `animation_engine/integration/style_profiles.py`
- **Line where code is to be edited or create:** Edit around `23-33`, `71-122`, `134-144`.

## Task 03
- **Task Name:** Implement procedural generation branches for expanded motion set
- **Coding logic of task and narrative design required:** Add generation logic for newly required motion IDs (strafe, sprint variants, traversal entries/exits, combo phases, stagger/knockdown/recover, contextual interactions).
- **Logic of how it functions in the program and design it must follow:** `ProceduralBackend.generate_clip` must return valid clips for every required motion to avoid manifest failures.
- **Check to adhere to Final Fantasy aesthetics:** Motion timing must remain readable and characterful, avoiding overly realistic noise that breaks FF-style clarity.
- **Name of the file to be edited or create:** `animation_engine/backend.py`
- **Line where code is to be edited or create:** Edit around `73-91`, `106-321`.

## Task 04
- **Task Name:** Add gameplay semantic metadata per generated clip
- **Coding logic of task and narrative design required:** Embed fields like locomotion/combat category, root-motion policy, interaction tags, and transition intent in per-clip metadata.
- **Logic of how it functions in the program and design it must follow:** Metadata becomes runtime contract for state selection in GameRewritten and for stricter validation.
- **Check to adhere to Final Fantasy aesthetics:** Tags must support cinematic transitions and iconic JRPG combat readability.
- **Name of the file to be edited or create:** `animation_engine/integration/asset_pipeline.py`
- **Line where code is to be edited or create:** Edit around `105-139`, `144-162`.

## Task 05
- **Task Name:** Introduce manifest schema version bump and migration-safe fields
- **Coding logic of task and narrative design required:** Extend manifest with explicit schema/version and gameplay-semantic sections for future-proof pack loading.
- **Logic of how it functions in the program and design it must follow:** GameRewritten can reject incompatible packs early and route migration logic cleanly.
- **Check to adhere to Final Fantasy aesthetics:** Preserve existing visual/gameplay target fields and ensure new fields reinforce FF-directed output validation.
- **Name of the file to be edited or create:** `animation_engine/integration/asset_pipeline.py`
- **Line where code is to be edited or create:** Edit around `28-33`, `143-166`.

## Task 06
- **Task Name:** Expand style validator with gameplay-category coverage gates
- **Coding logic of task and narrative design required:** Validate required coverage by gameplay category (exploration/combat/traversal/reaction) and enforce metadata semantics.
- **Logic of how it functions in the program and design it must follow:** `validate-pack` should fail when category coverage or semantic metadata is incomplete even if files exist.
- **Check to adhere to Final Fantasy aesthetics:** Require category-level quality rules that keep FF pose readability and cinematic pacing.
- **Name of the file to be edited or create:** `animation_engine/qa/style_validator.py`
- **Line where code is to be edited or create:** Edit around `75-160`, `187-240`.

## Task 07
- **Task Name:** Add validator rules for transition continuity expectations
- **Coding logic of task and narrative design required:** Add checks for transition-critical clips (start/loop/stop sets, combo links, hit-to-recover continuity) to reduce runtime snapping.
- **Logic of how it functions in the program and design it must follow:** QA should encode transition contract before assets reach game runtime.
- **Check to adhere to Final Fantasy aesthetics:** Preserve smooth cinematic transition feel characteristic of modern FF combat flow.
- **Name of the file to be edited or create:** `animation_engine/qa/style_validator.py`
- **Line where code is to be edited or create:** Edit around `167-186`, `226-240`.

## Task 08
- **Task Name:** Extend CLI to expose advanced pack generation controls
- **Coding logic of task and narrative design required:** Add arguments for profile variants, category subsets, manifest schema selection, and strict mode.
- **Logic of how it functions in the program and design it must follow:** CLI becomes deterministic orchestration point for production-ready batch outputs.
- **Check to adhere to Final Fantasy aesthetics:** Defaults should continue to enforce FF PS2-era profile alignment.
- **Name of the file to be edited or create:** `animation_engine/cli.py`
- **Line where code is to be edited or create:** Edit around `116-154`, `282-375`.

## Task 09
- **Task Name:** Add CLI validation reporting output suitable for build pipelines
- **Coding logic of task and narrative design required:** Emit machine-readable validation summaries for CI/release gates.
- **Logic of how it functions in the program and design it must follow:** GameRewritten build scripts can fail fast using structured validator output.
- **Check to adhere to Final Fantasy aesthetics:** Report must include art-direction compliance status from manifest and clip metadata.
- **Name of the file to be edited or create:** `animation_engine/cli.py`
- **Line where code is to be edited or create:** Edit around `157-279`.

## Task 10
- **Task Name:** Add animation event marker support in clip model
- **Coding logic of task and narrative design required:** Add timeline events (footstep/contact/hit/cancel/cast release) for gameplay synchronization.
- **Logic of how it functions in the program and design it must follow:** Runtime and export layers consume events for deterministic combat/exploration behavior.
- **Check to adhere to Final Fantasy aesthetics:** Event timing should reinforce staged, readable, cinematic combat beats.
- **Name of the file to be edited or create:** `animation_engine/animation/clip.py`
- **Line where code is to be edited or create:** Edit around `31-42`, `145-163`.

## Task 11
- **Task Name:** Persist clip events and gameplay tags in .anim format
- **Coding logic of task and narrative design required:** Extend serializer/importer payload to include new event and semantic metadata with backward compatibility.
- **Logic of how it functions in the program and design it must follow:** Guarantees exported packs retain gameplay-authoring intent across tooling boundaries.
- **Check to adhere to Final Fantasy aesthetics:** Preserve existing style-profile metadata and link event semantics to FF-style motion pacing.
- **Name of the file to be edited or create:** `animation_engine/io/anim_format.py`
- **Line where code is to be edited or create:** Edit around `95-110`, `165-190`.

## Task 12
- **Task Name:** Add runtime animation event dispatch and root-motion output channel
- **Coding logic of task and narrative design required:** Emit event callbacks and root-motion deltas during `Animator.update` for gameplay systems.
- **Logic of how it functions in the program and design it must follow:** Runtime systems in GameRewritten can trigger FX/combat logic from animation timing.
- **Check to adhere to Final Fantasy aesthetics:** Root motion and events must support smooth cinematic locomotion/combat presentation.
- **Name of the file to be edited or create:** `animation_engine/runtime/animator.py`
- **Line where code is to be edited or create:** Edit around `72-95`, `156-204`.

## Task 13
- **Task Name:** Upgrade blend tree for parameter-driven transition logic
- **Coding logic of task and narrative design required:** Add richer condition handling and transition policies for locomotion speed/direction/combat state parameters.
- **Logic of how it functions in the program and design it must follow:** Prevent brittle one-trigger transitions and improve gameplay responsiveness.
- **Check to adhere to Final Fantasy aesthetics:** Blend behavior should preserve readable pose silhouettes and dramatic anticipation/recovery.
- **Name of the file to be edited or create:** `animation_engine/animation/blend_tree.py`
- **Line where code is to be edited or create:** Edit around `97-125`, `176-264`.

## Task 14
- **Task Name:** Expand glTF export/import handling for richer animation semantics
- **Coding logic of task and narrative design required:** Carry expanded animation channels/metadata linkage and ensure import symmetry for production round trips.
- **Logic of how it functions in the program and design it must follow:** Preserves interoperability with DCC and external pipelines without semantic loss.
- **Check to adhere to Final Fantasy aesthetics:** Ensure exported animation data preserves timing and arcs needed for FF-style readability.
- **Name of the file to be edited or create:** `animation_engine/io/gltf.py`
- **Line where code is to be edited or create:** Edit around `281-359`, `429-520`.

## Task 15
- **Task Name:** Extend compat converter for expanded metadata contract
- **Coding logic of task and narrative design required:** Add generated C++ output support for new semantic/event metadata used by GameRewritten runtime.
- **Logic of how it functions in the program and design it must follow:** Keeps pre-baked header route equivalent to runtime JSON load route.
- **Check to adhere to Final Fantasy aesthetics:** Exported metadata must include style constraints so runtime can enforce FF presentation goals.
- **Name of the file to be edited or create:** `compat/anim_to_cpp_header.py`
- **Line where code is to be edited or create:** Edit around `207-315`, `396-477`.

## Task 16
- **Task Name:** Update compatibility guide for expanded production pack contract
- **Coding logic of task and narrative design required:** Document new schema fields, validation gates, and runtime integration sequence for GameRewritten.
- **Logic of how it functions in the program and design it must follow:** Prevents integration drift and ensures deterministic import behavior.
- **Check to adhere to Final Fantasy aesthetics:** Include explicit style compliance checks as mandatory pre-import gate.
- **Name of the file to be edited or create:** `compat/README.md`
- **Line where code is to be edited or create:** Edit around `40-47`, `94-106`, `265-292`.

## Task 17
- **Task Name:** Expand backend/QA integration test matrix for new motion taxonomy
- **Coding logic of task and narrative design required:** Add tests for expanded required clip set, semantic metadata presence, and deterministic manifest behavior.
- **Logic of how it functions in the program and design it must follow:** Protects production contract from regressions as scope increases.
- **Check to adhere to Final Fantasy aesthetics:** Test fixtures must verify FF target metadata stays intact across generated outputs.
- **Name of the file to be edited or create:** `tests/test_backend_qa_integration.py`
- **Line where code is to be edited or create:** Edit around `101-130`, `347-456`.

## Task 18
- **Task Name:** Add clip/event serialization compatibility tests
- **Coding logic of task and narrative design required:** Validate backward compatibility for legacy `.anim` plus forward compatibility for new event/semantic payloads.
- **Logic of how it functions in the program and design it must follow:** Ensures migration-safe asset loading across versions.
- **Check to adhere to Final Fantasy aesthetics:** Include asserts for preservation of style_profile/visual/gameplay/reference metadata.
- **Name of the file to be edited or create:** `tests/test_io.py`
- **Line where code is to be edited or create:** Edit around `84-167`, `185-230`.

## Task 19
- **Task Name:** Add runtime transition/event behavior tests
- **Coding logic of task and narrative design required:** Add tests for event timing, transition continuity, and parameter-driven state behavior.
- **Logic of how it functions in the program and design it must follow:** Locks gameplay-runtime behavior to deterministic expectations.
- **Check to adhere to Final Fantasy aesthetics:** Tests should enforce smooth cinematic transition behavior and readable movement timing.
- **Name of the file to be edited or create:** `tests/test_animation.py`
- **Line where code is to be edited or create:** Edit around `171-229`, add new tests near file end.

## Task 20
- **Task Name:** Update main README with production completion workflow
- **Coding logic of task and narrative design required:** Document expanded animation target, required categories, generation/validation commands, and release checklist.
- **Logic of how it functions in the program and design it must follow:** Provides one authoritative workflow for contributors and GameRewritten integration.
- **Check to adhere to Final Fantasy aesthetics:** Include explicit rule that all packs must pass FF art-direction metadata and quality gates.
- **Name of the file to be edited or create:** `README.md`
- **Line where code is to be edited or create:** Edit around `44-54`, `176-217`.

## Task 21
- **Task Name:** Add editor support for event track and semantic metadata editing
- **Coding logic of task and narrative design required:** Extend UI for adding/removing event markers and clip gameplay tags.
- **Logic of how it functions in the program and design it must follow:** Authoring tool must produce complete runtime-ready animation data, not only transform keys.
- **Check to adhere to Final Fantasy aesthetics:** Authoring controls should guide designers toward readable pose timing and cinematic rhythm.
- **Name of the file to be edited or create:** `animation_engine/editor/main.py`
- **Line where code is to be edited or create:** Edit around `242-260`, plus corresponding UI handlers later in file.

## Task 22
- **Task Name:** Final full-pack acceptance and regression gate update
- **Coding logic of task and narrative design required:** Update release gating tests/checklist to require expanded taxonomy generation + validation + compatibility conversion success.
- **Logic of how it functions in the program and design it must follow:** Establishes commercial-ready go/no-go criteria before handoff to GameRewritten.
- **Check to adhere to Final Fantasy aesthetics:** Acceptance gate must explicitly fail if FF visual/gameplay/reference metadata compliance is broken.
- **Name of the file to be edited or create:** `planv1.md`
- **Line where code is to be edited or create:** Edit around `281-317`.

## Task 23
- **Task Name:** Render skinned mesh wireframe in PS2 viewport
- **Coding logic of task and narrative design required:** Call `cpu_skin_mesh` with current-frame world matrices to deform bound mesh vertices, then project and draw triangle edges on the viewport canvas for a wire-mesh preview of the actual character geometry.
- **Logic of how it functions in the program and design it must follow:** Viewport currently draws skeleton sticks only. After skinning, triangle edge lines (projected the same way as joint points) give PS2-era wireframe preview without GPU dependencies.
- **Check to adhere to Final Fantasy aesthetics:** Wireframe colour should honour the active `PS2_LIGHTING_PRESETS` palette so the preview matches the intended PS2 rendering mood.
- **Name of the file to be edited or create:** `animation_engine/editor/main.py`
- **Line where code is to be edited or create:** Edit `_redraw_viewport` around `1488-1560`; add helper `_draw_mesh_wireframe` after `_draw_skeleton_world` around line `1608`.

## Task 24
- **Task Name:** Add F-curve editor panel for keyframe tangent visualisation
- **Coding logic of task and narrative design required:** Add a collapsible canvas panel below the timeline that plots the selected channel's keyframe values over time, with draggable tangent handles for cubic-spline control.
- **Logic of how it functions in the program and design it must follow:** `AnimationChannel` already stores cubic-spline keyframes. The curve panel reads channel data, draws a Bezier preview, and writes tangent overrides back via `add_keyframe`/`KeyframeType`.
- **Check to adhere to Final Fantasy aesthetics:** Curve editor should make it easy to achieve the characteristic FF style: held anticipation, sharp impact, and smooth follow-through timing.
- **Name of the file to be edited or create:** `animation_engine/editor/main.py`
- **Line where code is to be edited or create:** Add `_build_curve_editor` after `_build_timeline` around line `577`; add `_redraw_curve_editor` and tangent drag handlers after line `685`.

## Task 25
- **Task Name:** Expose IK posing mode in editor viewport
- **Coding logic of task and narrative design required:** Add an IK mode toggle button in the toolbar. When active, clicking a joint in the viewport sets it as the end-effector goal, and dragging solves the chain with `IKSolver` from `animation_engine/animation/ik_solver.py`, writing the result as a keyframe at the current playhead time.
- **Logic of how it functions in the program and design it must follow:** `IKSolver.solve` exists but is not wired to the editor. IK mode bypasses FK property entry for faster pose blocking, especially for foot-planting and hand-contact poses common in FF-style combat animation.
- **Check to adhere to Final Fantasy aesthetics:** IK should enable efficient blocking of held contact poses that are characteristic of PS2-era expressive body language.
- **Name of the file to be edited or create:** `animation_engine/editor/main.py`
- **Line where code is to be edited or create:** Add IK toggle around `_build_toolbar` at line `243`; add `_on_viewport_ik_drag` handler around line `1480`; add `_apply_ik_pose` after line `1490`.

## Task 26
- **Task Name:** Improve procedural walk and run cycle motion quality
- **Coding logic of task and narrative design required:** Replace the existing simple root-bob walk with a proper stride-based cycle: alternating foot placements via hip lateral sway, forward root translation, counter-rotating pelvis and shoulders, and arm swing on separate channels.
- **Logic of how it functions in the program and design it must follow:** `ProceduralBackend.generate_clip` dispatches on `motion_type`; the `walk` and `run` branches should be replaced with multi-bone keyframe sequences that produce a believable eight-count stride loop when played at their respective `duration` values.
- **Check to adhere to Final Fantasy aesthetics:** Walk should feel heroic and readable at PS2 resolution: deliberate foot placement, slight hip rotation, controlled arm swing. Run should be fast but retain silhouette clarity.
- **Name of the file to be edited or create:** `animation_engine/backend.py`
- **Line where code is to be edited or create:** Edit walk branch around lines `200-225` and run branch around lines `265-310`.

## Task 27
- **Task Name:** Improve procedural combat clip motion quality
- **Coding logic of task and narrative design required:** Rewrite attack, heavy attack, cast, and dodge branches to include anticipation wind-up, sharp impact peak, and follow-through/recovery phases using multi-keyframe sequences on spine, shoulders, and arm bones.
- **Logic of how it functions in the program and design it must follow:** Current combat branches set only one or two rotation keyframes. New logic should use at least five keyframes per clip (rest, anticipate, attack, impact, recover) to produce the staged FF-style combat readability.
- **Check to adhere to Final Fantasy aesthetics:** Each combat clip must have a readable silhouette change at every phase; impact frames should be visually distinct and held for at least one frame's worth of duration.
- **Name of the file to be edited or create:** `animation_engine/backend.py`
- **Line where code is to be edited or create:** Edit attack around lines `430-480`, heavy_attack around `495-540`, cast around `550-600`, dodge around `615-660`.

## Task 28
- **Task Name:** Add pack format version migration utility
- **Coding logic of task and narrative design required:** Add a `migrate_anim_dict(d: dict) -> dict` function that detects schema version from the `"version"` key (or its absence) and upgrades v1 dicts (no events, no gameplay_tags) to v2 format by inserting empty defaults.
- **Logic of how it functions in the program and design it must follow:** `AnimImporter.load` currently raises on unknown keys. Migration runs before `from_dict` so old assets load cleanly. `AnimExporter` always writes v2. Migration is idempotent: running twice returns same result.
- **Check to adhere to Final Fantasy aesthetics:** Migrated clips must preserve all existing style_profile and art-direction metadata fields without modification.
- **Name of the file to be edited or create:** `animation_engine/io/anim_format.py`
- **Line where code is to be edited or create:** Add `migrate_anim_dict` around line `95`; call it at top of `AnimImporter.load` around line `165`.

## Task 29
- **Task Name:** Add batch-export-headers CLI subcommand
- **Coding logic of task and narrative design required:** Add a `batch-export-headers` subcommand that reads a pack manifest JSON, iterates every entry in `ordered_files`, loads each `.anim` file, and calls `anim_to_cpp_header.py`-equivalent logic to write per-clip C++ header files into an `--output-dir`.
- **Logic of how it functions in the program and design it must follow:** `compat/anim_to_cpp_header.py` already has `AnimToHeaderConverter`; the CLI subcommand wraps it in a loop driven by the manifest. Exit code is non-zero if any clip fails.
- **Check to adhere to Final Fantasy aesthetics:** Emitted headers must include style-profile metadata fields so GameRewritten runtime can enforce FF art-direction compliance at load time.
- **Name of the file to be edited or create:** `animation_engine/cli.py`
- **Line where code is to be edited or create:** Add `_cmd_batch_export_headers` around line `374`; add `batch_export_headers_parser` in `build_parser` around line `545`.

## Task 30
- **Task Name:** Add blend tree state graph panel in editor
- **Coding logic of task and narrative design required:** Add a "State Graph" tab or side panel that renders each `BlendTreeState` as a rounded rectangle and each allowed transition as a directed arrow between them, drawn on a Tkinter canvas. Clicking a node selects it and shows its parameters in the Properties panel.
- **Logic of how it functions in the program and design it must follow:** `BlendTree` holds a `states` dict and `transitions` list accessible from the editor's `animator.blend_tree`. The panel redraws whenever the clip list changes. No interactive editing required in this task—read-only visualisation only.
- **Check to adhere to Final Fantasy aesthetics:** State graph colours should follow the dark editor palette (`BG_COLOR`, `ACCENT_COLOR`) and communicate clean separation between locomotion, combat, and reaction state clusters.
- **Name of the file to be edited or create:** `animation_engine/editor/main.py`
- **Line where code is to be edited or create:** Add `_build_state_graph_panel` after `_build_centre_panel` around line `392`; add `_redraw_state_graph` after `_redraw_timeline` around line `685`.

## Task 31
- **Task Name:** Add animation retargeting utility
- **Coding logic of task and narrative design required:** Add a `retarget_clip(clip, source_skel, target_skel, bone_map)` function that takes a clip authored for `source_skel` and returns a new clip with channels remapped to `target_skel` bone names, scaling translations proportionally using the ratio of bone chain lengths.
- **Logic of how it functions in the program and design it must follow:** Retargeting reads each channel's bone name, looks it up in `bone_map` (dict of source→target names), scales any TRANSLATION channel by `target_bone.length / source_bone.length`, and copies ROTATION channels unchanged.
- **Check to adhere to Final Fantasy aesthetics:** Retargeted clips must preserve the characteristic pose silhouettes and timing of the source animation even when skeleton proportions differ between FF-style character variants.
- **Name of the file to be edited or create:** `animation_engine/animation/clip.py`
- **Line where code is to be edited or create:** Add `retarget_clip` function after `from_dict` around line `205`.

## Task 32
- **Task Name:** Add skinning and IK solver unit tests
- **Coding logic of task and narrative design required:** Add tests that (a) verify `cpu_skin_mesh` returns a mesh with the same vertex count but different positions when a non-identity skin matrix is applied, and (b) verify `IKSolver.solve` converges the end-effector within 1 cm of a reachable target within the iteration limit.
- **Logic of how it functions in the program and design it must follow:** Tests import `cpu_skin_mesh` from `animation_engine.runtime.skinning` and `IKSolver` from `animation_engine.animation.ik_solver`, construct minimal fixtures, and assert correctness without needing a real skeleton.
- **Check to adhere to Final Fantasy aesthetics:** IK convergence test target positions should be foot-contact and hand-grip locations typical of FF PS2-era pose blocking (e.g. foot flat on ground at y=0).
- **Name of the file to be edited or create:** `tests/test_animation.py`
- **Line where code is to be edited or create:** Add new tests at end of file.

## Task 33
- **Task Name:** Add retargeting and pack migration unit tests
- **Coding logic of task and narrative design required:** Add tests that (a) verify `retarget_clip` remaps bone names and scales translations correctly for a two-bone source/target pair, and (b) verify `migrate_anim_dict` upgrades a v1 dict (missing `events`, `gameplay_tags`) to a valid v2 dict without data loss.
- **Logic of how it functions in the program and design it must follow:** Retargeting test builds a minimal clip with known keyframes and bone_map, asserts channel bone names change and translation magnitudes scale. Migration test asserts default keys are inserted and existing keys are preserved.
- **Check to adhere to Final Fantasy aesthetics:** Migration test must assert that `style_profile`, `visual_target`, and `gameplay_target` fields are preserved untouched from the original v1 payload.
- **Name of the file to be edited or create:** `tests/test_io.py`
- **Line where code is to be edited or create:** Add new tests at end of file.

## Task 34
- **Task Name:** Update program_assessment.md with final completion scores
- **Coding logic of task and narrative design required:** Rewrite the gap sections and readiness scores in `program_assessment.md` to reflect all implemented features (Tasks 1–34), marking gaps as resolved and updating each category score to its post-completion value.
- **Logic of how it functions in the program and design it must follow:** Assessment drives onboarding clarity; an accurate final score communicates project completion status to future contributors and the GameRewritten integration team.
- **Check to adhere to Final Fantasy aesthetics:** Confirm in the assessment that PS2-era viewport, motion quality improvements, and FF art-direction metadata compliance are all marked as production-ready.
- **Name of the file to be edited or create:** `program_assessment.md`
- **Line where code is to be edited or create:** Edit sections 3, 5, and 6 throughout the file.
