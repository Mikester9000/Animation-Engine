"""
animation_engine.model.model
================================
Top-level Model container.

A Model aggregates all data that makes up a complete 3-D asset:
  - One or more named Meshes
  - A Skeleton (optional — static meshes have no skeleton)
  - A dict of PBRMaterials keyed by name

This is the primary unit that is exported and imported by the IO layer.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from .mesh import Mesh
from .material import PBRMaterial
from .skeleton import Skeleton


class Model:
    """
    A complete 3-D model ready for the animation pipeline.

    Typical usage
    -------------
    >>> model = Model("Noctis")
    >>> model.skeleton = build_character_skeleton()
    >>> model.add_mesh(body_mesh)
    >>> model.add_mesh(face_mesh)
    >>> model.add_material(skin_material)
    """

    def __init__(self, name: str = "Model") -> None:
        self.name: str = name
        self.meshes: List[Mesh] = []
        self.materials: Dict[str, PBRMaterial] = {}
        self.skeleton: Optional[Skeleton] = None
        # Metadata tags — useful for Game Engine for Teaching asset browser
        self.tags: List[str] = []

    # -- mesh management -----------------------------------------------------

    def add_mesh(self, mesh: Mesh) -> None:
        """Append a mesh to the model."""
        self.meshes.append(mesh)

    def get_mesh(self, name: str) -> Optional[Mesh]:
        """Return the first mesh with the given name, or None."""
        for mesh in self.meshes:
            if mesh.name == name:
                return mesh
        return None

    # -- material management -------------------------------------------------

    def add_material(self, material: PBRMaterial) -> None:
        """Register a material by its name."""
        self.materials[material.name] = material

    def get_material(self, name: str) -> Optional[PBRMaterial]:
        """Return the material with the given name, or None."""
        return self.materials.get(name)

    # -- statistics ----------------------------------------------------------

    @property
    def total_vertex_count(self) -> int:
        return sum(m.vertex_count for m in self.meshes)

    @property
    def total_triangle_count(self) -> int:
        return sum(m.triangle_count for m in self.meshes)

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the entire model to a JSON-compatible dict."""
        return {
            "name": self.name,
            "tags": self.tags,
            "meshes": [m.to_dict() for m in self.meshes],
            "materials": {
                name: mat.to_dict() for name, mat in self.materials.items()
            },
            "skeleton": self.skeleton.to_dict() if self.skeleton else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Model":
        """Reconstruct a Model from a serialised dict."""
        model = cls(name=d.get("name", "Model"))
        model.tags = d.get("tags", [])
        for md in d.get("meshes", []):
            model.meshes.append(Mesh.from_dict(md))
        for mat_name, mat_data in d.get("materials", {}).items():
            model.materials[mat_name] = PBRMaterial.from_dict(mat_data)
        skel_data = d.get("skeleton")
        if skel_data is not None:
            model.skeleton = Skeleton.from_dict(skel_data)
        return model

    def __repr__(self) -> str:
        return (
            f"Model({self.name!r}, "
            f"meshes={len(self.meshes)}, "
            f"materials={len(self.materials)}, "
            f"skeleton={self.skeleton})"
        )
