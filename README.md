# Animation Engine

A professional animation tool for creating **3-D models and animated assets**
compatible with **Game Engine for Teaching** and `Mikester9000/GameRewritten`.
The target output is a **high-end PS2-era JRPG presentation** inspired by
*Final Fantasy VII*, *VIII*, *IX*, *X*, and *XII*, while still supporting
the broader gameplay and feature demands of modern open-world combat/exploration
games such as *Final Fantasy VII Remake* and *Final Fantasy XV*.

---

## Features

| Feature | Details |
|---------|---------|
| **Skeletal Animation** | Hierarchical bone rigs (50+ bones), local-space keyframes, world-space skin matrices |
| **Cubic-Spline Interpolation** | STEP / LINEAR / CUBICSPLINE modes matching glTF 2.0 for cinematic-but-readable motion timing |
| **Animation Blending** | State-machine driven BlendTree with smooth cubic ease-in/out crossfades |
| **Inverse Kinematics** | FABRIK solver for foot-placement, hand-IK, and look-at constraints |
| **Morph Targets** | Blend-shape / morph-target animation for facial expressions and lip-sync |
| **PBR Materials** | Full metalness/roughness workflow — albedo, normal, occlusion, emissive maps |
| **Export: `.anim`** | Native JSON format for Game Engine for Teaching (single-file: model + clips + morph tracks) |
| **Export: glTF 2.0** | Industry-standard interchange for Unreal, Unity, Godot, Blender, and more |
| **Import** | Re-import `.anim` and `.gltf` / `.glb` files back into the engine |
| **Timeline Editor** | Tkinter-based GUI with timeline, bone hierarchy, and properties panel |
| **57-Clip Taxonomy** | Complete motion library covering idle, locomotion, traversal, combat, reactions, and interactions |
| **Animation Events** | Named timeline markers (footstep, hit-window, cast-release, etc.) fire runtime callbacks |
| **Root-Motion Channel** | `Animator.root_motion_delta` exposes per-frame root translation for physics handoff |
| **Style Profiles** | Five built-in PS2-era JRPG profiles (FF7–FF12) with per-motion cadence and amplitude tuning |
| **Pack Generation** | `animation-engine generate-pack` produces a full 57-clip library in one command |
| **Quality Gating** | `animation-engine validate-pack` enforces category coverage, transition continuity, and loop seamlessness |

---

## Package Layout

```
animation_engine/
├── math_utils/      Vector2/3/4, Quaternion, Matrix4x4, Transform
├── model/           Vertex, Mesh, MorphTarget, PBRMaterial, Bone, Skeleton, Model
├── animation/       Keyframe, Channel, Clip (+ events), BlendTree, IKSolver, MorphTrack
├── io/              AnimExporter/Importer (.anim), GltfExporter/Importer (.gltf)
├── runtime/         Animator (event dispatch, root-motion, per-frame update), cpu_skin_mesh
├── integration/     AnimationPipeline, StyleProfile, MotionStyleVariants
├── qa/              ClipValidator, LoopAnalyzer, SkeletonValidator, StyleValidator
└── editor/          Tkinter timeline + bone editor (AnimationEditor)
tests/               pytest test suite (197 tests)
```

---

## Art Direction Contract

All generated content follows these output rules:

- **Visual target:** Aim for the highest-quality JRPG animation presentation that still feels believable on **PlayStation 2-class hardware**.
- **Reference mix:** Silhouettes, posing clarity, and animation readability aligned with *Final Fantasy VII*, *VIII*, *IX*, *X*, and *XII* era goals.
- **Gameplay coverage:** The 57-clip motion library supports modern gameplay — seamless traversal, reactive combat, dodges, spell casting, hit reactions, combo attacks, climb cycles, and celebratory states.
- **Profile metadata:** Generated packs embed visual target, gameplay target, reference titles, semantic metadata, and schema version in manifests and per-clip `.anim` files.
- **Category gates:** `validate-pack` rejects packs missing minimum coverage for exploration (≥3 clips), combat (≥3 clips), traversal (≥2 clips), and reaction (≥2 clips) categories.
- **Transition continuity:** Packs with partial combo/climb/cast/jump groups are rejected to prevent broken animation chains at runtime.

Use the built-in style profiles when generating packs; they are the repository's source of truth for this art direction.

---

## Clip Taxonomy (57 Motions)

| Category | Motions |
|----------|---------|
| **Idle** | `idle`, `idle_alt`, `idle_combat` |
| **Exploration** | `walk`, `run`, `run_start`, `run_stop`, `sprint`, `sprint_start`, `sprint_stop`, `strafe_left`, `strafe_right`, `backstep`, `crouch`, `crouch_walk`, `guard_walk`, `turn_left`, `turn_right` |
| **Traversal** | `jump_start`, `jump_loop`, `jump_land`, `land_hard`, `land_roll`, `roll`, `vault`, `climb_start`, `climb_loop`, `climb_stop`, `ladder_up`, `ladder_down`, `swim_idle`, `swim_forward` |
| **Combat / Offense** | `attack`, `attack_combo_1`, `attack_combo_2`, `attack_combo_3`, `heavy_attack`, `aerial_attack`, `cast`, `cast_channel`, `cast_release` |
| **Combat / Defense** | `defend`, `block`, `block_break`, `parry`, `dodge` |
| **Reactions** | `hit_react`, `stagger`, `knockdown`, `knockdown_air`, `get_up`, `death` |
| **Interactions** | `interact`, `pickup`, `victory`, `emote_cheer` |

---

## Style Profiles

| Profile ID | Inspired by | Cadence | Amplitude |
|------------|-------------|---------|-----------|
| `ff7_ps2` | Final Fantasy VII | 0.96 | 0.92 |
| `ff8_ps2` | Final Fantasy VIII | 1.00 | 0.95 |
| `ff9_ps2` | Final Fantasy IX | 1.02 | 1.00 |
| `ff10_ps2` | Final Fantasy X | 1.08 | 1.05 |
| `ff12_ps2` | Final Fantasy XII | 1.10 | 0.98 |

Each profile also exposes per-motion-class `MotionStyleVariants` for fine-grained cadence tuning across locomotion, melee, magic, reaction, and traversal categories.

---

## Quick Start

### Install

```bash
pip install -e '.[dev]'
```

### Create and export a model

```python
from animation_engine.model import Model, Mesh, Vertex, PBRMaterial, Skeleton
from animation_engine.math_utils import Vector2, Vector3, Transform
from animation_engine.animation import AnimationClip
from animation_engine.animation.channel import ChannelTarget
from animation_engine.io import AnimExporter

# 1. Build a model
model = Model("character")

# 2. Add a PBR material
skin = PBRMaterial("skin")
skin.albedo_color = [0.8, 0.65, 0.5, 1.0]
skin.roughness = 0.7
model.add_material(skin)

# 3. Add a mesh (geometry omitted for brevity)
mesh = Mesh("body", vertices=[...], indices=[...], material_name="skin")
model.add_mesh(mesh)

# 4. Build a skeleton
skel = Skeleton("rig")
root  = skel.add_bone("root")
spine = skel.add_bone("spine_01", parent_index=root,
                      local_transform=Transform(position=Vector3(0, 0.9, 0)))
skel.compute_bind_pose()
model.skeleton = skel

# 5. Author an animation clip with event markers
clip = AnimationClip("walk", fps=30.0, loop=True)
clip.add_keyframe("spine_01", ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
clip.add_keyframe("spine_01", ChannelTarget.ROTATION, 1.5, [0, 0.05, 0, 0.9987])
clip.add_keyframe("spine_01", ChannelTarget.ROTATION, 3.0, [0, 0, 0, 1])
clip.add_event("footstep_left",  0.25, {"foot": "left"})
clip.add_event("footstep_right", 0.75, {"foot": "right"})

# 6. Export to .anim (Game Engine for Teaching) and glTF 2.0
AnimExporter().export(model, [clip], path="character.anim")

from animation_engine.io import GltfExporter
GltfExporter().export(model, [clip], "character.gltf")
```

### Run the editor

```bash
python -m animation_engine.editor.main
```

Editor workflow (PS2-style preview target for GameRewritten import):

1. Create or open a `.anim` file.
2. Select a clip in the clip browser/selector.
3. Use play/stop/frame-step/scrub to inspect timing.
4. Preview in the center viewport (PS2 lighting presets + grid/compare options).
5. Adjust keys/events/properties and verify motion in the live viewport.
6. Save `.anim` once preview matches expected in-game PS2-era look.

### Run the tests

```bash
python -m pytest -q
```

---

## Animation Events

Animation clips carry named timeline markers that fire registered callbacks during runtime playback:

```python
from animation_engine.animation import AnimationClip
from animation_engine.runtime.animator import Animator

# Add events when authoring a clip
clip.add_event("footstep_left",   0.25, {"foot": "left"})
clip.add_event("hit_window_open", 0.45)
clip.add_event("hit_window_close",0.65)

# Register callbacks in the game loop
animator.register_event_callback("footstep_left",   lambda ev: play_footstep_sfx(ev))
animator.register_event_callback("hit_window_open",  lambda ev: enable_hitbox())
animator.register_event_callback("hit_window_close", lambda ev: disable_hitbox())

# Per-frame update dispatches events automatically
animator.update(delta_time)

# Root-motion delta is also available after each update
position += animator.root_motion_delta
```

Events are serialised inside the `.anim` file and survive round-trips through `AnimExporter` / `AnimImporter`.

---

## Production Pack Workflow

```bash
# 1. Generate a complete 57-clip pack for the ff10_ps2 profile
animation-engine generate-pack \
    --skeleton-anim assets/hero_source.anim \
    --output-dir    assets/hero_pack \
    --profile       ff10_ps2 \
    --strict

# 2. Validate the pack (category coverage, transition continuity, loop seamlessness)
animation-engine validate-pack \
    --manifest   assets/hero_pack/pack_manifest.json \
    --json-report assets/hero_pack/validation_report.json
```

### One-command production build (generate + validate)

```bash
animation-engine build-production-pack \
    --skeleton-anim assets/hero_source.anim \
    --output-dir assets/hero_pack \
    --profile ff10_ps2 \
    --strict \
    --json-report assets/hero_pack/validation_report.json
```

### Production GUI

```bash
animation-engine launch-production-gui
```

The production GUI runs full-pack generation and validation together, writes a
pack manifest, and can optionally write a JSON validation report.

### Windows standalone launcher (.bat)

Run this file from the repository root on Windows:

```bat
run_animation_engine_windows.bat
```

Launch editor directly with PS2 preview:

```bat
run_animation_engine_windows.bat --editor
```

The batch launcher creates `.venv` (if needed), installs dependencies with
`pip install -e ".[dev]"`, and opens the selected GUI mode.

The `--strict` flag causes `generate-pack` to exit non-zero if any clip fails to generate.

The `--json-report` flag writes a machine-readable JSON containing per-clip reports, style errors, and an `overall_valid` field suitable for CI integration.

### Expected pack tree

```text
assets/hero_pack/
├── aerial_attack.anim
├── attack.anim
├── attack_combo_1.anim
├── attack_combo_2.anim
├── attack_combo_3.anim
├── block.anim
├── cast.anim
├── cast_channel.anim
├── cast_release.anim
├── climb_loop.anim
├── climb_start.anim
├── climb_stop.anim
├── crouch.anim
├── crouch_walk.anim
├── death.anim
├── defend.anim
├── dodge.anim
├── get_up.anim
├── heavy_attack.anim
├── hit_react.anim
├── idle.anim
├── idle_alt.anim
├── idle_combat.anim
├── interact.anim
├── jump_land.anim
├── jump_loop.anim
├── jump_start.anim
├── knockdown.anim
├── parry.anim
├── pickup.anim
├── roll.anim
├── run.anim
├── run_start.anim
├── run_stop.anim
├── sprint.anim
├── stagger.anim
├── strafe_left.anim
├── strafe_right.anim
├── turn_left.anim
├── turn_right.anim
├── vault.anim
├── victory.anim
├── walk.anim
└── pack_manifest.json
```

The `pack_manifest.json` encodes `schema_version`, `generation_version`, the selected profile's art-direction fields, and `gameplay_semantic.category_coverage` so CI and downstream import tools can validate pack completeness without re-running the generator.

---

## Architecture

### Math layer (`math_utils`)
Column-vector convention (OpenGL / glTF).  All transforms use `M @ v` where `v`
is a 4-D column vector.  `Quaternion.slerp` produces smooth constant-angular-
velocity blending — the same algorithm used in FF15.

### Animation layer (`animation`)
- **Keyframe** — stores value + in/out tangents for CUBICSPLINE interpolation.
- **AnimationChannel** — time-sorted keyframe list for one bone × one property.
- **AnimationClip** — named collection of channels; evaluates a complete pose. Carries named timeline **events** for gameplay synchronisation.
- **BlendTree** — state-machine with smooth crossfades between clips.
- **IKSolver** — FABRIK algorithm; modifies FK poses in-place with optional pole-vector hinting.
- **MorphTrack** — float-valued keyframes for morph-target weights.

### Integration layer (`integration`)
- **StyleProfile** — frozen dataclass encoding art direction, required clip list, and `MotionStyleVariants`.
- **MotionStyleVariants** — per-motion-class cadence multipliers (locomotion, melee, magic, reaction, traversal).
- **AnimationPipeline** — generates all 57 clips for a profile, writes `.anim` files, and produces `pack_manifest.json`.

### QA layer (`qa`)
- **ClipValidator** — per-clip quaternion normalisation, position-range, and seam checks.
- **LoopAnalyzer** — detects position/rotation discontinuities at clip boundaries.
- **StyleValidator** — pack-level checks: required clips, art-direction fields, category coverage (≥ minimums per category), transition-group continuity, and duration tolerances.

### IO layer (`io`)
| Format | Read | Write |
|--------|------|-------|
| `.anim` (JSON) | ✅ `AnimImporter` | ✅ `AnimExporter` |
| `.gltf` + `.bin` | ✅ `GltfImporter` | ✅ `GltfExporter` |

### Runtime layer (`runtime`)
`Animator.update(delta)` advances the blend tree, runs IK, computes skin
matrices, dispatches animation events to registered callbacks, and extracts
`root_motion_delta` — all in one call from the game loop.
`get_skin_matrices_flat()` returns a flat `float32` array ready for upload
to a GPU uniform buffer via Game Engine for Teaching's rendering API.

---

## Compatibility with Game Engine for Teaching

The `.anim` format is the primary native format.  Import it with:

```python
from animation_engine.io import AnimImporter

# Basic import
model, clips, morph_tracks = AnimImporter().import_file("character.anim")

# Include per-clip metadata (art direction, semantic fields)
model, clips, morph_tracks, metadata = AnimImporter().import_file(
    "character.anim", include_metadata=True
)
```

Pass `animator.get_skin_matrices_flat()` to your shader's bone-matrix UBO,
and `animator.morph_weights` to blend-shape weight uniforms.

glTF 2.0 export ensures compatibility with any renderer that supports the
standard — every modern game engine and DCC tool does.

For profile-based pack generation, treat the generated `pack_manifest.json` as
the hand-off contract. It records the selected profile, PS2-era visual
target, modern gameplay target, reference titles, ordered clip inventory,
semantic category coverage, and schema version expected by downstream tools.

### Smoke test sequence

```bash
pip install -e '.[dev]'
python -m pytest -q
animation-engine generate-pack --skeleton-anim assets/hero_source.anim --output-dir assets/hero_pack --profile ff10_ps2 --strict
animation-engine validate-pack --manifest assets/hero_pack/pack_manifest.json --json-report assets/hero_pack/validation_report.json
```

Expected success conditions:

- `pip install -e '.[dev]'` completes without dependency errors.
- `python -m pytest -q` finishes green (171+ tests).
- `generate-pack` prints `status: ok`, reports `generated` equal to `expected` (43), and writes `pack_manifest.json`.
- `validate-pack` exits `0` and prints `Style report: VALID` with no blocking errors.

---

## Package Layout

```
animation_engine/
├── math_utils/      Vector2/3/4, Quaternion, Matrix4x4, Transform
├── model/           Vertex, Mesh, MorphTarget, PBRMaterial, Bone, Skeleton, Model
├── animation/       Keyframe, Channel, Clip, BlendTree, IKSolver, MorphTrack
├── io/              AnimExporter/Importer (.anim), GltfExporter/Importer (.gltf)
├── runtime/         Animator (per-frame update loop), cpu_skin_mesh
└── editor/          Tkinter timeline + bone editor (AnimationEditor)
tests/               pytest test suite
```

---

## Art Direction Contract

All future generated content should follow these output rules:

- **Visual target:** Aim for the highest-quality JRPG animation presentation that still feels believable on **PlayStation 2-class hardware**.
- **Reference mix:** Keep silhouettes, posing clarity, and animation readability aligned with *Final Fantasy VII*, *VIII*, *IX*, *X*, and *XII* era presentation goals.
- **Gameplay coverage:** Even with the PS2-era visual target, the motion library must support more modern gameplay beats such as seamless traversal, reactive combat, dodges, spell casting, hit reactions, and celebratory states.
- **Profile metadata:** Generated packs now embed the visual target, gameplay target, and reference titles in pack manifests and per-clip `.anim` metadata so downstream tools can enforce the direction.

Use the built-in style profiles when generating packs; they are the repository's source of truth for this art direction.

---

## Quick Start

### Install

```bash
pip install -r requirements.txt
```

### Create and export a model

```python
from animation_engine.model import Model, Mesh, Vertex, PBRMaterial, Skeleton
from animation_engine.math_utils import Vector2, Vector3, Transform
from animation_engine.animation import AnimationClip
from animation_engine.animation.channel import ChannelTarget
from animation_engine.io import AnimExporter

# 1. Build a model
model = Model("character")

# 2. Add a PBR material
skin = PBRMaterial("skin")
skin.albedo_color = [0.8, 0.65, 0.5, 1.0]
skin.roughness = 0.7
model.add_material(skin)

# 3. Add a mesh (geometry omitted for brevity)
mesh = Mesh("body", vertices=[...], indices=[...], material_name="skin")
model.add_mesh(mesh)

# 4. Build a skeleton
skel = Skeleton("rig")
root  = skel.add_bone("root")
spine = skel.add_bone("spine_01", parent_index=root,
                      local_transform=Transform(position=Vector3(0, 0.9, 0)))
skel.compute_bind_pose()
model.skeleton = skel

# 5. Author an animation clip
clip = AnimationClip("idle", fps=30.0, loop=True)
clip.add_keyframe("spine_01", ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
clip.add_keyframe("spine_01", ChannelTarget.ROTATION, 1.5, [0, 0.05, 0, 0.9987])
clip.add_keyframe("spine_01", ChannelTarget.ROTATION, 3.0, [0, 0, 0, 1])

# 6. Export to .anim (Game Engine for Teaching) and glTF 2.0
AnimExporter().export(model, [clip], "character.anim")

from animation_engine.io import GltfExporter
GltfExporter().export(model, [clip], "character.gltf")
```

### Run the editor

```bash
python -m animation_engine.editor.main
```

### Run the tests

```bash
python -m pytest -q
```

---

## Architecture

### Math layer (`math_utils`)
Column-vector convention (OpenGL / glTF).  All transforms use `M @ v` where `v`
is a 4-D column vector.  `Quaternion.slerp` produces smooth constant-angular-
velocity blending — the same algorithm used in FF15.

### Animation layer (`animation`)
- **Keyframe** — stores value + in/out tangents for CUBICSPLINE interpolation.
- **AnimationChannel** — time-sorted keyframe list for one bone × one property.
- **AnimationClip** — named collection of channels; evaluates a complete pose.
- **BlendTree** — state-machine with smooth crossfades between clips.
- **IKSolver** — FABRIK algorithm; modifies FK poses in-place with optional
  pole-vector hinting.
- **MorphTrack** — float-valued keyframes for morph-target weights.

### IO layer (`io`)
| Format | Read | Write |
|--------|------|-------|
| `.anim` (JSON) | ✅ `AnimImporter` | ✅ `AnimExporter` |
| `.gltf` + `.bin` | ✅ `GltfImporter` | ✅ `GltfExporter` |

### Runtime layer (`runtime`)
`Animator.update(delta)` advances the blend tree, runs IK, computes skin
matrices, and evaluates morph weights — all in one call from the game loop.
`get_skin_matrices_flat()` returns a flat `float32` array ready for upload
to a GPU uniform buffer via Game Engine for Teaching's rendering API.

---

## Compatibility with Game Engine for Teaching

The `.anim` format is the primary native format.  Import it with:

```python
from animation_engine.io import AnimImporter
model, clips, morph_tracks = AnimImporter().import_file("character.anim")
```

Pass `animator.get_skin_matrices_flat()` to your shader's bone-matrix UBO,
and `animator.morph_weights` to blend-shape weight uniforms.

glTF 2.0 export ensures compatibility with any renderer that supports the
standard — every modern game engine and DCC tool does.

For profile-based pack generation, treat the generated `pack_manifest.json` as
the hand-off contract. It now records the selected profile, PS2-era visual
target, modern gameplay target, reference titles, and the ordered clip inventory
expected by downstream runtime/import tools.

The manifest also includes `ordered_files`, `backend_name`, `seed`, and
`generation_version` so release builds can reproduce and validate packs without
guesswork.

### Expected generated pack tree

```text
assets/hero_pack/
├── attack.anim
├── cast.anim
├── defend.anim
├── dodge.anim
├── hit_react.anim
├── idle.anim
├── jump_land.anim
├── jump_loop.anim
├── jump_start.anim
├── pack_manifest.json
├── run.anim
├── victory.anim
└── walk.anim
```

The exact `.anim` filenames and order are defined by the selected style
profile's `ordered_files` manifest entries. Downstream import or conversion
tools should consume clips in that order instead of guessing from directory
listing order.

### Smoke test sequence

```bash
pip install -e '.[dev]'
python -m pytest -q
animation-engine generate-pack --skeleton-anim assets/hero_source.anim --output-dir assets/hero_pack --profile ff10_ps2
animation-engine validate-pack --manifest assets/hero_pack/pack_manifest.json
```

Expected success conditions:

- `pip install -e '.[dev]'` completes without dependency errors.
- `python -m pytest -q` finishes green.
- `generate-pack` prints `status: ok`, reports `generated` equal to `expected`,
  and writes `assets/hero_pack/pack_manifest.json`.
- `validate-pack` exits `0` and prints a `Style report: VALID` summary with no
  blocking errors.
