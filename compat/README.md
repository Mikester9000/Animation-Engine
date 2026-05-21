# Animation Engine ↔ Game Engine for Teaching — Compatibility Guide

This folder contains the bridge between the Python **Animation Engine** tool
and the C++ **Game Engine for Teaching** (repo: `Mikester9000/Game-Engine-for-Teaching-`).

---

## Contents

| File | Purpose |
|------|---------|
| `GameEngineCompat.hpp` | Header-only C++17 bridge library |
| `anim_to_cpp_header.py` | Python converter: `.anim` → C++ pre-baked header |
| `README.md` | This file |

---

## Overview

The Animation Engine exports **`.anim` files** — JSON packages that contain:

```
.anim (JSON)
├── format: "AnimEngine"
├── version: "1.0"
├── model
│   ├── name
│   ├── meshes  [...]
│   ├── materials {...}
│   └── skeleton
│       └── bones [name, parent_index, local_transform, inverse_bind]
├── clips
│   └── [] { name, fps, loop, channels [ {bone_name, target, keyframes} ] }
├── morph_tracks
│   └── [] { morph_name, keyframes }
└── metadata
    └── style_profile, visual_target, gameplay_target, reference_titles, ...
```

Generated profile packs also include `pack_manifest.json`, which is the
downstream hand-off contract for `Mikester9000/GameRewritten`. It records the
selected style profile, the PS2-era visual target, the modern gameplay target,
the reference titles, and the ordered clip inventory.

The C++ bridge provides:

1. **`AnimLoader`** — runtime JSON parser → `AE_AnimPackage`
2. **ECS components** — `AnimationComponent`, `SkinnedSpriteComponent`, `MorphWeightComponent`
3. **`AnimationSystem`** — advances playback, writes to `TransformComponent` / `RenderComponent`
4. **`anim_to_cpp_header.py`** — pre-bake the `.anim` data into a C++ header (zero runtime I/O)

---

## Step 1 — Export from Animation Engine

Prefer the profile-based pack flow for production content so every exported clip
inherits the same visual/gameplay direction metadata:

```bash
animation-engine generate-pack \
    --skeleton-anim assets/hero_source.anim \
    --output-dir assets/hero_pack \
    --profile ff10_ps2
```

This generates `pack_manifest.json` plus one `.anim` file per required clip.
Import/build tooling should validate the manifest first, then load or convert
the listed clips in order.

```python
from animation_engine.model import Model, Mesh, Vertex, Skeleton
from animation_engine.animation import AnimationClip
from animation_engine.io import AnimExporter

# Build or load your model + clips …
model = Model("Noctis")
# … (add meshes, skeleton, materials)

clips = [idle_clip, run_clip, attack_clip]
exporter = AnimExporter()
exporter.export(model, clips, path="assets/noctis.anim")
```

---

## Step 2 — Integrate into the Game Engine

### Option A — Runtime loading (recommended for development)

The `.anim` file ships alongside the game binary.  `AnimLoader` parses it
at startup using the built-in JSON parser (no external libraries needed).

**CMakeLists.txt**

```cmake
# Add the compat/ folder to the include path
target_include_directories(game PRIVATE
    src/
    path/to/Animation-Engine   # so #include "compat/GameEngineCompat.hpp" works
    ${CURSES_INCLUDE_DIRS}
    ${LUA_INCLUDE_DIRS}
)
```

**C++ usage**

```cpp
#include "compat/GameEngineCompat.hpp"

// ── Startup ──────────────────────────────────────────────────────────────
// Register new components (call AFTER the existing RegisterAllComponents)
RegisterAnimationComponents(world);

// Register AnimationSystem (requires AnimationComponent + TransformComponent)
auto& animSys = SetupAnimationSystem(world);
animSys.SetWorld(world);

// Load the .anim file once and share the package.
// For generated packs, resolve the selected clip path from pack_manifest.json.
AE_AnimPackage noctisAnim = AnimLoader::Load("assets/noctis.anim");

// ── Per-entity setup ──────────────────────────────────────────────────────
EntityID hero = world.CreateEntity();
world.AddComponent(hero, TransformComponent{});
world.AddComponent(hero, RenderComponent{});

AnimationComponent ac;
ac.package  = &noctisAnim;
ac.clipName = "idle";
ac.loop     = true;
world.AddComponent(hero, ac);

// ── Per-frame ─────────────────────────────────────────────────────────────
world.Update(deltaTime);   // drives AnimationSystem automatically
```

---

### Option B — Pre-baked C++ header (recommended for release / students)

Convert the `.anim` file into a C++ header **at build time**.  The animation
data is compiled directly into the executable — no file I/O at runtime, no
JSON parsing overhead.

For a generated pack, iterate the ordered file list from `pack_manifest.json`
and convert each clip deterministically so release builds preserve the same
PS2-era art-direction contract used during generation and validation.

**Convert the file**

```bash
# From the Animation-Engine repo root:
python compat/anim_to_cpp_header.py assets/noctis.anim --var NOCTIS \
    --output path/to/Game-Engine/src/game/data/noctis_anim.hpp
```

**C++ usage**

```cpp
#include "compat/GameEngineCompat.hpp"
#include "game/data/noctis_anim.hpp"   // defines: AE_AnimPackage& NOCTIS

// NOCTIS is a static reference — use it directly
AnimationComponent ac;
ac.package  = &NOCTIS;
ac.clipName = "run_cycle";
world.AddComponent(hero, ac);
```

---

## Step 3 — Skinned Sprite (ASCII terminal animation)

The Game Engine renders ASCII characters via ncurses.  Use
`SkinnedSpriteComponent` to map bone rotations to ASCII symbols so your
animation affects how the character looks in the terminal.

```cpp
SkinnedSpriteComponent ssc;

// Watch the root bone — change symbol based on yaw angle
SkinnedSpriteComponent::BoneRegion region;
region.boneName    = "root";
region.regionLabel = "character";

// Facing right (+Y yaw ≈ 0°)
SkinnedSpriteComponent::BoneRegion::Frame faceRight;
faceRight.symbol    = '>';
faceRight.colorPair = CP_HERO;
faceRight.minYawDeg = -45.0f;
faceRight.maxYawDeg =  45.0f;
region.frames.push_back(faceRight);

// Facing left (yaw ≈ 180°)
SkinnedSpriteComponent::BoneRegion::Frame faceLeft;
faceLeft.symbol    = '<';
faceLeft.colorPair = CP_HERO;
faceLeft.minYawDeg =  135.0f;
faceLeft.maxYawDeg =  180.0f;
region.frames.push_back(faceLeft);

ssc.regions.push_back(region);
world.AddComponent(hero, ssc);
```

---

## Step 4 — Clip transitions (crossfade)

```cpp
// Smoothly blend from "idle" → "run" over 0.3 seconds
auto& ac = world.GetComponent<AnimationComponent>(hero);
ac.transitionTo("run_cycle", 0.3f);
```

---

## Supported .anim Schema Fields

The C++ bridge reads all fields defined in `Animation Engine 1.0`:

| JSON field | C++ struct | Notes |
|------------|-----------|-------|
| `model.name` | `AE_AnimPackage.name` | |
| `model.skeleton.bones[].name` | `AE_Bone.name` | |
| `model.skeleton.bones[].parent_index` | `AE_Bone.parentIndex` | |
| `model.skeleton.bones[].local_transform` | `AE_Bone.localBind` | TRS |
| `model.skeleton.bones[].inverse_bind` | `AE_Bone.inverseBind[16]` | row-major |
| `clips[].name` | `AE_AnimClip.name` | |
| `clips[].fps` | `AE_AnimClip.fps` | informational |
| `clips[].loop` | `AE_AnimClip.loop` | |
| `clips[].channels[].bone_name` | `AE_Channel.boneName` | |
| `clips[].channels[].target` | `AE_Channel.target` | TRANSLATION/ROTATION/SCALE/WEIGHT |
| `clips[].channels[].keyframes[].time` | `AE_Keyframe.time` | |
| `clips[].channels[].keyframes[].value` | `AE_Keyframe.value[4]` | |
| `clips[].channels[].keyframes[].in_tangent` | `AE_Keyframe.inTangent[4]` | CUBIC only |
| `clips[].channels[].keyframes[].out_tangent` | `AE_Keyframe.outTangent[4]` | CUBIC only |
| `clips[].channels[].keyframes[].interp` | `AE_Keyframe.interp` | STEP/LINEAR/CUBIC |
| `morph_tracks[].morph_name` | `AE_MorphTrack.morphName` | |
| `morph_tracks[].keyframes` | `AE_MorphTrack.keyframes` | |
| `metadata.style_profile` | external pack selection | Profile ID used during generation |
| `metadata.visual_target` | external art-direction check | PS2-era visual target string |
| `metadata.gameplay_target` | external gameplay check | Modern gameplay support string |
| `metadata.reference_titles[]` | external review/import check | Final Fantasy art-direction references |

---

## TEACHING NOTES

### Why a header-only bridge?

Header-only libraries are easy to add to any project — just add the include
path to CMakeLists.txt.  No `.cpp` files to compile, no static libraries to
link.  The trade-off is slightly longer build times when the header changes.

### Quaternion → Euler conversion

The Animation Engine stores rotations as quaternions (x, y, z, w) — the
industry standard for smooth rotation interpolation.  The Game Engine for
Teaching uses Euler angles (degrees) in `TransformComponent`.

`AE_Quat::toEulerDeg()` performs this conversion via the standard atan2
formulas, matching the ZYX (yaw-pitch-roll) convention used by the engine.
Note: Euler angles suffer from gimbal lock near ±90° pitch; a future version
of the Game Engine may store quaternions natively.

### SLERP (Spherical Linear Interpolation)

`AE_Quat::slerp(b, t)` interpolates between two rotations along the shortest
arc on the 4D unit hypersphere.  This is what AA games use for smooth
crossfades between animation clips.
