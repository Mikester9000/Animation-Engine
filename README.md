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

### Smoke test sequence

```bash
python -m pytest -q
animation-engine generate-pack --skeleton-anim assets/hero_source.anim --output-dir assets/hero_pack --profile ff10_ps2
animation-engine validate-pack --manifest assets/hero_pack/pack_manifest.json
```
