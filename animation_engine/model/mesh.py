"""
animation_engine.model.mesh
==============================
Mesh data structures: Vertex, MorphTarget, and Mesh.

A Mesh stores geometry in a format ready for GPU upload:
  - interleaved vertex attributes (position, normal, tangent, UVs, skin data)
  - a flat index buffer (triangle list)
  - optional per-mesh morph targets (blend shapes)

Morph targets (blend shapes) are used in FF15-style characters to drive
facial expressions, lip-sync and secondary deformations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np

from ..math_utils import Vector2, Vector3, Vector4


# Maximum number of bones that may influence a single vertex.
# 4 is the industry standard and fits in a vec4 uniform.
MAX_BONE_INFLUENCES: int = 4


@dataclass
class Vertex:
    """
    A single GPU vertex containing all attributes needed for skeletal animation.

    Attributes
    ----------
    position    : World-space or object-space position.
    normal      : Surface normal (unit vector).
    tangent     : Tangent vector (used for normal mapping), .w stores handedness.
    uv0         : Primary UV coordinate set (albedo / roughness / metallic maps).
    uv1         : Secondary UV coordinate set (lightmap / detail maps).
    color       : Per-vertex RGBA colour (e.g., ambient occlusion bake, team colour).
    bone_indices: Indices into the skeleton's bone array (up to MAX_BONE_INFLUENCES).
    bone_weights: Blend weights for each bone (must sum to 1 for correct skinning).
    """

    position: Vector3 = field(default_factory=Vector3.zero)
    normal: Vector3 = field(default_factory=Vector3.up)
    tangent: Vector4 = field(default_factory=Vector4.zero)
    uv0: Vector2 = field(default_factory=Vector2.zero)
    uv1: Vector2 = field(default_factory=Vector2.zero)
    color: Vector4 = field(default_factory=Vector4.one)
    # Bone influence data (for skeletal animation)
    bone_indices: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    bone_weights: List[float] = field(default_factory=lambda: [1.0, 0.0, 0.0, 0.0])

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dict."""
        return {
            "position": self.position.to_list(),
            "normal": self.normal.to_list(),
            "tangent": self.tangent.to_list(),
            "uv0": self.uv0.to_list(),
            "uv1": self.uv1.to_list(),
            "color": self.color.to_list(),
            "bone_indices": list(self.bone_indices),
            "bone_weights": list(self.bone_weights),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Vertex":
        """Reconstruct from a serialised dict."""
        return cls(
            position=Vector3.from_list(d["position"]),
            normal=Vector3.from_list(d["normal"]),
            tangent=Vector4.from_list(d["tangent"]),
            uv0=Vector2.from_list(d["uv0"]),
            uv1=Vector2.from_list(d["uv1"]),
            color=Vector4.from_list(d["color"]),
            bone_indices=d["bone_indices"],
            bone_weights=d["bone_weights"],
        )


@dataclass
class MorphTarget:
    """
    A blend-shape (morph target) stores delta positions, normals, and tangents.

    When an animator sets the weight of this target to a non-zero value the
    runtime adds the deltas to the base mesh — enabling facial expressions,
    secondary muscle deformations, and cloth pre-simulation offsets used in
    FF15-style characters.
    """

    name: str = ""
    weight: float = 0.0  # Current blend weight in [0, 1]
    # Sparse per-vertex deltas (index → delta vector)
    position_deltas: dict = field(default_factory=dict)  # {vertex_idx: Vector3}
    normal_deltas: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "weight": self.weight,
            "position_deltas": {
                str(k): v.to_list() for k, v in self.position_deltas.items()
            },
            "normal_deltas": {
                str(k): v.to_list() for k, v in self.normal_deltas.items()
            },
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MorphTarget":
        return cls(
            name=d.get("name", ""),
            weight=d.get("weight", 0.0),
            position_deltas={
                int(k): Vector3.from_list(v)
                for k, v in d.get("position_deltas", {}).items()
            },
            normal_deltas={
                int(k): Vector3.from_list(v)
                for k, v in d.get("normal_deltas", {}).items()
            },
        )


class Mesh:
    """
    Triangle-list mesh with optional morph targets and a material reference.

    The mesh stores:
      - vertices  : list of Vertex (interleaved attributes)
      - indices   : list of int (triangle list, 3 indices per face)
      - morph_targets : list of MorphTarget (blend shapes)
      - material_name : string key into the Model's material dict
    """

    def __init__(
        self,
        name: str = "Mesh",
        vertices: List[Vertex] = None,
        indices: List[int] = None,
        material_name: str = "default",
    ) -> None:
        self.name: str = name
        self.vertices: List[Vertex] = vertices if vertices is not None else []
        self.indices: List[int] = indices if indices is not None else []
        self.material_name: str = material_name
        self.morph_targets: List[MorphTarget] = []

    # -- geometry helpers ----------------------------------------------------

    @property
    def vertex_count(self) -> int:
        return len(self.vertices)

    @property
    def triangle_count(self) -> int:
        return len(self.indices) // 3

    def add_morph_target(self, target: MorphTarget) -> None:
        """Register a morph target on this mesh."""
        self.morph_targets.append(target)

    def compute_normals(self) -> None:
        """
        Recompute smooth per-vertex normals by averaging face normals.

        Called after geometry edits; FF15 uses pre-computed tangent-space
        normals baked into normal maps, but this is useful for tool previews.
        """
        # Accumulate face normals
        accumulated = [np.zeros(3, dtype=np.float64) for _ in self.vertices]
        for i in range(0, len(self.indices), 3):
            i0, i1, i2 = self.indices[i], self.indices[i + 1], self.indices[i + 2]
            v0 = self.vertices[i0].position
            v1 = self.vertices[i1].position
            v2 = self.vertices[i2].position
            edge1 = np.array([v1.x - v0.x, v1.y - v0.y, v1.z - v0.z])
            edge2 = np.array([v2.x - v0.x, v2.y - v0.y, v2.z - v0.z])
            face_normal = np.cross(edge1, edge2)
            for idx in (i0, i1, i2):
                accumulated[idx] += face_normal

        # Normalise and write back
        for idx, acc in enumerate(accumulated):
            mag = float(np.linalg.norm(acc))
            if mag > 1e-10:
                acc /= mag
            self.vertices[idx].normal = Vector3(
                float(acc[0]), float(acc[1]), float(acc[2])
            )

    def compute_tangents(self) -> None:
        """
        Compute tangent vectors using Lengyel's method (Mikktspace-compatible).

        Tangents are required for normal-map rendering and PBR shading —
        essential for AAA-quality visuals.
        """
        tan1 = [np.zeros(3, dtype=np.float64) for _ in self.vertices]
        tan2 = [np.zeros(3, dtype=np.float64) for _ in self.vertices]

        for i in range(0, len(self.indices), 3):
            i0, i1, i2 = self.indices[i], self.indices[i + 1], self.indices[i + 2]
            v0, v1, v2 = self.vertices[i0], self.vertices[i1], self.vertices[i2]

            p0 = np.array([v0.position.x, v0.position.y, v0.position.z])
            p1 = np.array([v1.position.x, v1.position.y, v1.position.z])
            p2 = np.array([v2.position.x, v2.position.y, v2.position.z])
            uv0_ = np.array([v0.uv0.x, v0.uv0.y])
            uv1_ = np.array([v1.uv0.x, v1.uv0.y])
            uv2_ = np.array([v2.uv0.x, v2.uv0.y])

            dp1, dp2 = p1 - p0, p2 - p0
            duv1, duv2 = uv1_ - uv0_, uv2_ - uv0_

            det = duv1[0] * duv2[1] - duv1[1] * duv2[0]
            if abs(det) < 1e-10:
                continue
            r = 1.0 / det
            sdir = (duv2[1] * dp1 - duv1[1] * dp2) * r
            tdir = (duv1[0] * dp2 - duv2[0] * dp1) * r

            for idx in (i0, i1, i2):
                tan1[idx] += sdir
                tan2[idx] += tdir

        for idx, vert in enumerate(self.vertices):
            n = np.array([vert.normal.x, vert.normal.y, vert.normal.z])
            t = tan1[idx]
            # Gram-Schmidt orthogonalise
            tng = t - n * np.dot(n, t)
            mag = float(np.linalg.norm(tng))
            if mag > 1e-10:
                tng /= mag
            # Calculate handedness
            w = -1.0 if np.dot(np.cross(n, t), tan2[idx]) < 0.0 else 1.0
            vert.tangent = Vector4(
                float(tng[0]), float(tng[1]), float(tng[2]), w
            )

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "material_name": self.material_name,
            "vertices": [v.to_dict() for v in self.vertices],
            "indices": self.indices,
            "morph_targets": [mt.to_dict() for mt in self.morph_targets],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Mesh":
        mesh = cls(
            name=d.get("name", "Mesh"),
            vertices=[Vertex.from_dict(v) for v in d.get("vertices", [])],
            indices=d.get("indices", []),
            material_name=d.get("material_name", "default"),
        )
        for mt_data in d.get("morph_targets", []):
            mesh.morph_targets.append(MorphTarget.from_dict(mt_data))
        return mesh

    def __repr__(self) -> str:
        return (
            f"Mesh(name={self.name!r}, "
            f"vertices={self.vertex_count}, "
            f"triangles={self.triangle_count})"
        )
