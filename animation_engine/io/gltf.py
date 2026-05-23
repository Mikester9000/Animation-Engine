"""
animation_engine.io.gltf
==========================
glTF 2.0 export and import.

glTF (GL Transmission Format) 2.0 is the industry-standard interchange format
for 3-D assets used by Unreal Engine, Unity, Godot, Blender, and Game Engine
for Teaching.  Every major AAA studio supports it as an import pipeline.

This module converts between the engine's native objects and the glTF 2.0 JSON
structure.  Binary buffer data (.bin / GLB) is written alongside the .gltf file.

Spec reference: https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
"""

from __future__ import annotations

import json
import os
import struct
from typing import Dict, List, Optional, Tuple

import numpy as np

from ..model.model import Model
from ..model.mesh import Mesh, Vertex
from ..model.material import PBRMaterial, TextureRef
from ..model.skeleton import Skeleton, Bone
from ..animation.clip import AnimationClip
from ..animation.channel import ChannelTarget
from ..math_utils import Vector3, Vector4, Quaternion


# ---------------------------------------------------------------------------
# Exporter
# ---------------------------------------------------------------------------

class GltfExporter:
    """
    Export a Model and AnimationClips to a .gltf + .bin file pair.

    Usage
    -----
    >>> exporter = GltfExporter()
    >>> exporter.export(model, clips, "output/character.gltf")
    """

    def export(
        self,
        model: Model,
        clips: List[AnimationClip] = None,
        path: str = "output.gltf",
    ) -> str:
        """
        Write a .gltf JSON file and a companion .bin buffer.

        Parameters
        ----------
        model : Model to export.
        clips : Animation clips to embed in the glTF.
        path  : Output .gltf path; the .bin file is placed in the same directory.

        Returns
        -------
        Absolute path of the .gltf file.
        """
        clips = clips or []
        self._buffer_data = bytearray()
        self._accessors: list = []
        self._buffer_views: list = []

        gltf = {
            "asset": {"version": "2.0", "generator": "Animation Engine 1.0"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [],
            "meshes": [],
            "materials": [],
            "skins": [],
            "accessors": [],
            "bufferViews": [],
            "buffers": [],
            "animations": [],
        }

        # Materials
        mat_index_map: Dict[str, int] = {}
        for mat_name, mat in model.materials.items():
            mat_index_map[mat_name] = len(gltf["materials"])
            gltf["materials"].append(self._export_material(mat))

        # Skeleton / skin
        skin_index: Optional[int] = None
        bone_node_offset = 1  # Node 0 = root mesh node
        if model.skeleton:
            skel_nodes, skin_def = self._export_skeleton(
                model.skeleton, bone_node_offset
            )
            skin_index = len(gltf["skins"])
            gltf["skins"].append(skin_def)
            gltf["nodes"].extend(skel_nodes)

        # Meshes
        mesh_node_children = []
        for mesh in model.meshes:
            mesh_gltf, mesh_idx = self._export_mesh(
                mesh,
                mat_index_map,
                gltf,
                skin_index,
            )
            gltf["meshes"].append(mesh_gltf)
            node = {"name": mesh.name, "mesh": mesh_idx}
            if skin_index is not None:
                node["skin"] = skin_index
            child_idx = len(gltf["nodes"])
            gltf["nodes"].append(node)
            mesh_node_children.append(child_idx)

        # Root node
        root_node = {"name": model.name, "children": mesh_node_children}
        gltf["nodes"].insert(0, root_node)

        # Animations
        for clip in clips:
            anim_def = self._export_animation(clip, model, gltf)
            if anim_def:
                gltf["animations"].append(anim_def)

        # Write binary buffer
        bin_name = os.path.splitext(os.path.basename(path))[0] + ".bin"
        bin_path = os.path.join(os.path.dirname(os.path.abspath(path)), bin_name)
        os.makedirs(os.path.dirname(bin_path), exist_ok=True) \
            if os.path.dirname(bin_path) else None
        with open(bin_path, "wb") as fh:
            fh.write(self._buffer_data)

        # Finalise accessors / buffer views
        gltf["accessors"] = self._accessors
        gltf["bufferViews"] = self._buffer_views
        gltf["buffers"] = [
            {"uri": bin_name, "byteLength": len(self._buffer_data)}
        ]

        # Write .gltf
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(gltf, fh, indent=2)

        return os.path.abspath(path)

    # -- material ------------------------------------------------------------

    def _export_material(self, mat: PBRMaterial) -> dict:
        """Convert a PBRMaterial to a glTF 2.0 material definition."""
        pbr = {
            "baseColorFactor": mat.albedo_color,
            "metallicFactor": mat.metallic,
            "roughnessFactor": mat.roughness,
        }
        if mat.albedo_texture:
            pbr["baseColorTexture"] = {"index": 0, "texCoord": mat.albedo_texture.uv_set}
        gltf_mat: dict = {
            "name": mat.name,
            "pbrMetallicRoughness": pbr,
            "emissiveFactor": mat.emissive_color,
            "alphaMode": mat.alpha_mode.upper(),
            "doubleSided": mat.double_sided,
        }
        if mat.alpha_mode.lower() == "mask":
            gltf_mat["alphaCutoff"] = mat.alpha_cutoff
        if mat.normal_texture:
            gltf_mat["normalTexture"] = {
                "index": 0,
                "texCoord": mat.normal_texture.uv_set,
                "scale": mat.normal_scale,
            }
        if mat.occlusion_texture:
            gltf_mat["occlusionTexture"] = {
                "index": 0,
                "texCoord": mat.occlusion_texture.uv_set,
                "strength": mat.occlusion_strength,
            }
        return gltf_mat

    # -- skeleton ------------------------------------------------------------

    def _export_skeleton(
        self, skeleton: Skeleton, node_offset: int
    ) -> Tuple[list, dict]:
        """
        Convert a Skeleton to a list of glTF nodes and a skin definition.
        """
        nodes = []
        joint_indices = []
        for bone in skeleton.bones:
            t, r, s = bone.local_transform.to_matrix().decompose()
            node = {
                "name": bone.name,
                "translation": [t.x, t.y, t.z],
                "rotation": [r.x, r.y, r.z, r.w],
                "scale": [s.x, s.y, s.z],
            }
            # Link children (indices are relative to the node array offset)
            if bone.children:
                node["children"] = [
                    c + node_offset for c in bone.children
                ]
            nodes.append(node)
            joint_indices.append(bone.index + node_offset)

        # Write inverse bind matrices to binary buffer
        ibm_data = bytearray()
        for bone in skeleton.bones:
            for val in bone.inverse_bind.to_list():  # column-major
                ibm_data += struct.pack("<f", val)
        ibm_acc = self._add_accessor(
            ibm_data,
            component_type=5126,  # FLOAT
            gltf_type="MAT4",
            count=len(skeleton.bones),
        )
        skin = {
            "name": skeleton.name,
            "joints": joint_indices,
            "inverseBindMatrices": ibm_acc,
        }
        return nodes, skin

    # -- mesh ----------------------------------------------------------------

    def _export_mesh(
        self,
        mesh: Mesh,
        mat_index_map: Dict[str, int],
        gltf: dict,
        skin_index: Optional[int],
    ) -> Tuple[dict, int]:
        """Convert a Mesh to a glTF mesh definition and return (mesh_def, index)."""
        verts = mesh.vertices
        indices = mesh.indices

        # Build flat arrays
        positions = np.array([[v.position.x, v.position.y, v.position.z] for v in verts], dtype=np.float32)
        normals = np.array([[v.normal.x, v.normal.y, v.normal.z] for v in verts], dtype=np.float32)
        uvs = np.array([[v.uv0.x, v.uv0.y] for v in verts], dtype=np.float32)
        joints = np.array([v.bone_indices[:4] for v in verts], dtype=np.uint16)
        weights = np.array([v.bone_weights[:4] for v in verts], dtype=np.float32)
        idx_arr = np.array(indices, dtype=np.uint32)

        pos_acc = self._add_accessor(
            positions.tobytes(), 5126, "VEC3", len(verts),
            min_val=positions.min(axis=0).tolist(),
            max_val=positions.max(axis=0).tolist(),
        )
        nor_acc = self._add_accessor(normals.tobytes(), 5126, "VEC3", len(verts))
        uv_acc = self._add_accessor(uvs.tobytes(), 5126, "VEC2", len(verts))
        jnt_acc = self._add_accessor(joints.tobytes(), 5123, "VEC4", len(verts))
        wgt_acc = self._add_accessor(weights.tobytes(), 5126, "VEC4", len(verts))
        idx_acc = self._add_accessor(
            idx_arr.tobytes(), 5125, "SCALAR", len(indices),
            target=34963,  # ELEMENT_ARRAY_BUFFER
        )

        attrs: dict = {
            "POSITION": pos_acc,
            "NORMAL": nor_acc,
            "TEXCOORD_0": uv_acc,
        }
        if skin_index is not None:
            attrs["JOINTS_0"] = jnt_acc
            attrs["WEIGHTS_0"] = wgt_acc

        mat_idx = mat_index_map.get(mesh.material_name, 0)
        prim = {"attributes": attrs, "indices": idx_acc, "material": mat_idx}
        mesh_def = {"name": mesh.name, "primitives": [prim]}
        mesh_idx = len(gltf["meshes"])
        return mesh_def, mesh_idx

    # -- animation -----------------------------------------------------------

    def _export_animation(
        self, clip: AnimationClip, model: Model, gltf: dict
    ) -> Optional[dict]:
        """Convert an AnimationClip to a glTF animation definition."""
        if not clip.channels:
            return None

        # Build bone-name → glTF-node-index mapping
        bone_node_map: Dict[str, int] = {}
        if model.skeleton:
            node_offset = 1 + len(model.meshes)
            for bone in model.skeleton.bones:
                bone_node_map[bone.name] = bone.index + node_offset

        samplers = []
        channels = []

        for ch in clip.channels:
            if not ch.keyframes:
                continue
            target_node = bone_node_map.get(ch.bone_name)
            if target_node is None:
                continue

            # Time input accessor
            times = np.array([kf.time for kf in ch.keyframes], dtype=np.float32)
            time_acc = self._add_accessor(
                times.tobytes(), 5126, "SCALAR", len(times),
                min_val=[float(times.min())],
                max_val=[float(times.max())],
            )

            # Value output accessor
            values_raw = [kf.value for kf in ch.keyframes]
            if ch.target == ChannelTarget.ROTATION:
                val_arr = np.array(values_raw, dtype=np.float32).reshape(-1, 4)
                gltf_type = "VEC4"
            elif ch.target in (ChannelTarget.TRANSLATION, ChannelTarget.SCALE):
                val_arr = np.array(values_raw, dtype=np.float32).reshape(-1, 3)
                gltf_type = "VEC3"
            else:
                val_arr = np.array(values_raw, dtype=np.float32).reshape(-1, 1)
                gltf_type = "SCALAR"

            val_acc = self._add_accessor(
                val_arr.tobytes(), 5126, gltf_type, len(ch.keyframes)
            )

            interp_map = {
                "STEP": "STEP",
                "LINEAR": "LINEAR",
                "CUBIC": "CUBICSPLINE",
            }
            interp = interp_map.get(ch.keyframes[0].interp.name, "LINEAR")

            sampler_idx = len(samplers)
            samplers.append(
                {"input": time_acc, "interpolation": interp, "output": val_acc}
            )

            path_map = {
                ChannelTarget.TRANSLATION: "translation",
                ChannelTarget.ROTATION: "rotation",
                ChannelTarget.SCALE: "scale",
                ChannelTarget.WEIGHT: "weights",
            }
            channels.append(
                {
                    "sampler": sampler_idx,
                    "target": {
                        "node": target_node,
                        "path": path_map[ch.target],
                    },
                }
            )

        if not samplers:
            return None
        anim_def: dict = {"name": clip.name, "samplers": samplers, "channels": channels}
        # Embed animation event markers and loop flag in glTF extras for import symmetry.
        extras: dict = {"loop": clip.loop}
        events = clip.get_events()
        if events:
            extras["events"] = [
                {"name": e["name"], "time": e["time"], "data": e.get("data", {})}
                for e in events
            ]
        anim_def["extras"] = extras
        return anim_def

    # -- binary buffer helpers -----------------------------------------------

    def _add_accessor(
        self,
        data: bytes,
        component_type: int,
        gltf_type: str,
        count: int,
        target: int = 34962,  # ARRAY_BUFFER
        min_val=None,
        max_val=None,
    ) -> int:
        """
        Append *data* to the binary buffer and register an accessor.

        Returns the accessor index.
        """
        # Align to 4 bytes
        padding = (4 - len(self._buffer_data) % 4) % 4
        self._buffer_data += b"\x00" * padding

        byte_offset = len(self._buffer_data)
        self._buffer_data += data

        bv_idx = len(self._buffer_views)
        self._buffer_views.append(
            {
                "buffer": 0,
                "byteOffset": byte_offset,
                "byteLength": len(data),
                "target": target,
            }
        )
        acc: dict = {
            "bufferView": bv_idx,
            "byteOffset": 0,
            "componentType": component_type,
            "count": count,
            "type": gltf_type,
        }
        if min_val is not None:
            acc["min"] = min_val
        if max_val is not None:
            acc["max"] = max_val

        acc_idx = len(self._accessors)
        self._accessors.append(acc)
        return acc_idx


# ---------------------------------------------------------------------------
# Importer
# ---------------------------------------------------------------------------

class GltfImporter:
    """
    Import a .gltf / .glb file into engine objects.

    This is a *best-effort* importer that handles the subset of the glTF 2.0
    spec produced by the GltfExporter above.  Full spec coverage is outside
    the scope of this tool; for production pipelines use DCC tool exporters.

    Usage
    -----
    >>> importer = GltfImporter()
    >>> model, clips = importer.import_file("character.gltf")
    """

    def import_file(
        self, path: str
    ) -> Tuple[Model, List[AnimationClip]]:
        """
        Read a .gltf file and return a (Model, clips) tuple.
        """
        with open(path, "r", encoding="utf-8") as fh:
            gltf = json.load(fh)

        # Load binary buffer(s)
        buffers = []
        base_dir = os.path.dirname(os.path.abspath(path))
        for buf_def in gltf.get("buffers", []):
            uri = buf_def.get("uri", "")
            buf_path = os.path.join(base_dir, uri)
            with open(buf_path, "rb") as fh:
                buffers.append(fh.read())

        model = self._import_model(gltf, buffers)
        clips = self._import_animations(gltf, buffers, model)
        return model, clips

    # -- model ---------------------------------------------------------------

    def _import_model(self, gltf: dict, buffers: list) -> Model:
        model = Model(name=gltf.get("asset", {}).get("generator", "Model"))

        # Materials
        mat_list = []
        for mat_def in gltf.get("materials", []):
            mat = PBRMaterial(name=mat_def.get("name", "material"))
            pbr = mat_def.get("pbrMetallicRoughness", {})
            mat.albedo_color = pbr.get("baseColorFactor", [1, 1, 1, 1])
            mat.metallic = pbr.get("metallicFactor", 0.0)
            mat.roughness = pbr.get("roughnessFactor", 0.5)
            mat.emissive_color = mat_def.get("emissiveFactor", [0, 0, 0])
            mat.double_sided = mat_def.get("doubleSided", False)
            mat.alpha_mode = mat_def.get("alphaMode", "OPAQUE").lower()
            mat.alpha_cutoff = mat_def.get("alphaCutoff", 0.5)
            mat_list.append(mat)
            model.add_material(mat)

        # Meshes
        for mesh_def in gltf.get("meshes", []):
            for prim in mesh_def.get("primitives", []):
                mesh = self._import_primitive(
                    mesh_def.get("name", "mesh"),
                    prim,
                    gltf,
                    buffers,
                    mat_list,
                )
                model.add_mesh(mesh)

        return model

    def _import_primitive(
        self,
        name: str,
        prim: dict,
        gltf: dict,
        buffers: list,
        mat_list: list,
    ) -> Mesh:
        """Convert a glTF primitive to a Mesh."""
        attrs = prim.get("attributes", {})
        positions = self._read_accessor(gltf, buffers, attrs.get("POSITION"))
        normals = self._read_accessor(gltf, buffers, attrs.get("NORMAL"))
        uvs = self._read_accessor(gltf, buffers, attrs.get("TEXCOORD_0"))
        joints = self._read_accessor(gltf, buffers, attrs.get("JOINTS_0"))
        weights = self._read_accessor(gltf, buffers, attrs.get("WEIGHTS_0"))
        indices_raw = self._read_accessor(gltf, buffers, prim.get("indices"))

        vertex_count = len(positions) if positions is not None else 0
        vertices = []
        for i in range(vertex_count):
            v = Vertex()
            if positions is not None:
                v.position = Vector3(*positions[i])
            if normals is not None:
                v.normal = Vector3(*normals[i])
            if uvs is not None:
                v.uv0 = __import__("animation_engine.math_utils", fromlist=["Vector2"]).Vector2(*uvs[i])
            if joints is not None:
                v.bone_indices = [int(x) for x in joints[i]]
            if weights is not None:
                v.bone_weights = [float(x) for x in weights[i]]
            vertices.append(v)

        mat_name = "default"
        mat_idx = prim.get("material")
        if mat_idx is not None and mat_idx < len(mat_list):
            mat_name = mat_list[mat_idx].name

        indices = indices_raw.flatten().tolist() if indices_raw is not None else []
        return Mesh(name=name, vertices=vertices, indices=indices, material_name=mat_name)

    # -- animation -----------------------------------------------------------

    def _import_animations(
        self, gltf: dict, buffers: list, model: Model
    ) -> List[AnimationClip]:
        """Convert glTF animations to AnimationClips."""
        clips = []
        # Build node → bone name mapping
        node_to_bone: Dict[int, str] = {}
        if model.skeleton:
            # Nodes for bones start after the mesh nodes
            for bone in model.skeleton.bones:
                # Find node index by name
                for i, node in enumerate(gltf.get("nodes", [])):
                    if node.get("name") == bone.name:
                        node_to_bone[i] = bone.name

        for anim_def in gltf.get("animations", []):
            clip = AnimationClip(name=anim_def.get("name", "animation"))
            samplers = anim_def.get("samplers", [])
            for ch_def in anim_def.get("channels", []):
                sampler = samplers[ch_def["sampler"]]
                target = ch_def.get("target", {})
                node_idx = target.get("node")
                path = target.get("path", "")
                bone_name = node_to_bone.get(node_idx, f"node_{node_idx}")

                times_raw = self._read_accessor(gltf, buffers, sampler.get("input"))
                values_raw = self._read_accessor(gltf, buffers, sampler.get("output"))
                if times_raw is None or values_raw is None:
                    continue

                path_to_target = {
                    "translation": ChannelTarget.TRANSLATION,
                    "rotation": ChannelTarget.ROTATION,
                    "scale": ChannelTarget.SCALE,
                    "weights": ChannelTarget.WEIGHT,
                }
                ch_target = path_to_target.get(path, ChannelTarget.TRANSLATION)

                from ..animation.keyframe import KeyframeType
                interp_map = {
                    "STEP": KeyframeType.STEP,
                    "LINEAR": KeyframeType.LINEAR,
                    "CUBICSPLINE": KeyframeType.CUBIC,
                }
                interp = interp_map.get(sampler.get("interpolation", "LINEAR"), KeyframeType.LINEAR)

                for j, t in enumerate(times_raw.flatten()):
                    val = values_raw[j].tolist()
                    clip.add_keyframe(bone_name, ch_target, float(t), val, interp)

            # Restore extras written by GltfExporter (loop flag + event markers).
            extras = anim_def.get("extras") or {}
            if "loop" in extras:
                clip.loop = bool(extras["loop"])
            for ev in extras.get("events", []):
                if isinstance(ev, dict) and "name" in ev and "time" in ev:
                    clip.add_event(ev["name"], float(ev["time"]), ev.get("data") or {})

            clips.append(clip)
        return clips

    # -- buffer helpers ------------------------------------------------------

    def _read_accessor(
        self, gltf: dict, buffers: list, accessor_idx
    ):
        """
        Read and decode a glTF accessor, returning a NumPy array or None.
        """
        if accessor_idx is None:
            return None
        accessors = gltf.get("accessors", [])
        if accessor_idx >= len(accessors):
            return None
        acc = accessors[accessor_idx]
        bv_idx = acc.get("bufferView")
        bv = gltf["bufferViews"][bv_idx]
        buf = buffers[bv.get("buffer", 0)]

        byte_offset = bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
        count = acc["count"]
        comp_type = acc["componentType"]
        gltf_type = acc["type"]

        type_map = {
            "SCALAR": 1,
            "VEC2": 2,
            "VEC3": 3,
            "VEC4": 4,
            "MAT4": 16,
        }
        dtype_map = {
            5120: np.int8,
            5121: np.uint8,
            5122: np.int16,
            5123: np.uint16,
            5125: np.uint32,
            5126: np.float32,
        }
        num_components = type_map.get(gltf_type, 1)
        dtype = dtype_map.get(comp_type, np.float32)
        byte_length = count * num_components * np.dtype(dtype).itemsize
        raw = buf[byte_offset : byte_offset + byte_length]
        arr = np.frombuffer(raw, dtype=dtype).reshape(count, num_components)
        return arr
