"""
tests/test_model.py
====================
Unit tests for animation_engine.model (Vertex, Mesh, PBRMaterial, Bone, Skeleton, Model).
"""

import math
import pytest

from animation_engine.math_utils import Vector2, Vector3, Vector4, Transform
from animation_engine.model import Vertex, Mesh, PBRMaterial, Bone, Skeleton, Model
from animation_engine.model.mesh import MorphTarget
from animation_engine.model.material import TextureRef


# ---------------------------------------------------------------------------
# Vertex
# ---------------------------------------------------------------------------

class TestVertex:
    def test_defaults(self):
        v = Vertex()
        assert v.position == Vector3.zero()
        assert len(v.bone_indices) == 4
        assert sum(v.bone_weights) == pytest.approx(1.0)

    def test_serialise_roundtrip(self):
        v = Vertex(
            position=Vector3(1, 2, 3),
            normal=Vector3(0, 1, 0),
            uv0=Vector2(0.5, 0.5),
            bone_indices=[0, 1, 0, 0],
            bone_weights=[0.7, 0.3, 0.0, 0.0],
        )
        d = v.to_dict()
        v2 = Vertex.from_dict(d)
        assert v2.position == v.position
        assert v2.normal == v.normal
        assert v2.uv0 == v.uv0
        assert v2.bone_indices == v.bone_indices
        assert v2.bone_weights == pytest.approx(v.bone_weights)


# ---------------------------------------------------------------------------
# MorphTarget
# ---------------------------------------------------------------------------

class TestMorphTarget:
    def test_serialise(self):
        mt = MorphTarget(
            name="smile",
            weight=0.5,
            position_deltas={0: Vector3(0.1, 0.0, 0.0)},
        )
        d = mt.to_dict()
        mt2 = MorphTarget.from_dict(d)
        assert mt2.name == "smile"
        assert mt2.weight == pytest.approx(0.5)
        assert 0 in mt2.position_deltas
        assert mt2.position_deltas[0].x == pytest.approx(0.1)


# ---------------------------------------------------------------------------
# Mesh
# ---------------------------------------------------------------------------

class TestMesh:
    def _make_triangle_mesh(self) -> Mesh:
        """Create a single triangle mesh for tests."""
        verts = [
            Vertex(position=Vector3(0, 0, 0), normal=Vector3(0, 0, 1), uv0=Vector2(0, 0)),
            Vertex(position=Vector3(1, 0, 0), normal=Vector3(0, 0, 1), uv0=Vector2(1, 0)),
            Vertex(position=Vector3(0, 1, 0), normal=Vector3(0, 0, 1), uv0=Vector2(0, 1)),
        ]
        return Mesh(name="tri", vertices=verts, indices=[0, 1, 2])

    def test_counts(self):
        mesh = self._make_triangle_mesh()
        assert mesh.vertex_count == 3
        assert mesh.triangle_count == 1

    def test_compute_normals(self):
        """After computing normals, every vertex should have a unit normal."""
        mesh = self._make_triangle_mesh()
        # Scramble normals first
        for v in mesh.vertices:
            v.normal = Vector3.zero()
        mesh.compute_normals()
        for v in mesh.vertices:
            assert v.normal.length == pytest.approx(1.0, abs=1e-5)

    def test_compute_tangents(self):
        mesh = self._make_triangle_mesh()
        mesh.compute_tangents()
        for v in mesh.vertices:
            # W component should be ±1
            assert abs(v.tangent.w) == pytest.approx(1.0, abs=1e-5)

    def test_serialise_roundtrip(self):
        mesh = self._make_triangle_mesh()
        d = mesh.to_dict()
        mesh2 = Mesh.from_dict(d)
        assert mesh2.name == "tri"
        assert mesh2.vertex_count == 3
        assert mesh2.triangle_count == 1
        assert mesh2.vertices[0].position == mesh.vertices[0].position

    def test_morph_target(self):
        mesh = self._make_triangle_mesh()
        mt = MorphTarget(name="open_mouth", weight=0.0,
                         position_deltas={0: Vector3(0, 0.05, 0)})
        mesh.add_morph_target(mt)
        assert len(mesh.morph_targets) == 1


# ---------------------------------------------------------------------------
# PBRMaterial
# ---------------------------------------------------------------------------

class TestPBRMaterial:
    def test_defaults(self):
        mat = PBRMaterial("skin")
        assert mat.metallic == pytest.approx(0.0)
        assert mat.roughness == pytest.approx(0.5)
        assert mat.alpha_mode == "opaque"

    def test_serialise_roundtrip(self):
        mat = PBRMaterial("chrome")
        mat.metallic = 1.0
        mat.roughness = 0.1
        mat.albedo_color = [0.9, 0.9, 0.9, 1.0]
        mat.emissive_color = [0.5, 0.0, 0.0]
        d = mat.to_dict()
        mat2 = PBRMaterial.from_dict(d)
        assert mat2.name == "chrome"
        assert mat2.metallic == pytest.approx(1.0)
        assert mat2.roughness == pytest.approx(0.1)
        assert mat2.emissive_color == pytest.approx([0.5, 0.0, 0.0])


# ---------------------------------------------------------------------------
# Skeleton
# ---------------------------------------------------------------------------

class TestSkeleton:
    def _make_simple_skeleton(self) -> Skeleton:
        skel = Skeleton("test_skel")
        root_idx = skel.add_bone("root")
        spine_idx = skel.add_bone(
            "spine",
            parent_index=root_idx,
            local_transform=Transform(position=Vector3(0, 1, 0)),
        )
        skel.add_bone(
            "head",
            parent_index=spine_idx,
            local_transform=Transform(position=Vector3(0, 1, 0)),
        )
        skel.compute_bind_pose()
        return skel

    def test_bone_count(self):
        skel = self._make_simple_skeleton()
        assert skel.bone_count == 3

    def test_get_bone(self):
        skel = self._make_simple_skeleton()
        bone = skel.get_bone("spine")
        assert bone is not None
        assert bone.name == "spine"
        assert bone.parent_index == 0

    def test_get_bone_missing(self):
        skel = self._make_simple_skeleton()
        assert skel.get_bone("nonexistent") is None

    def test_inverse_bind_identity_for_root(self):
        """Root bone at origin should have an identity-ish inverse bind."""
        skel = Skeleton("s")
        skel.add_bone("root")
        skel.compute_bind_pose()
        ib = skel.bones[0].inverse_bind
        import numpy as np
        np.testing.assert_allclose(ib.to_numpy(), np.eye(4), atol=1e-5)

    def test_children_populated(self):
        skel = self._make_simple_skeleton()
        root = skel.get_bone("root")
        assert 1 in root.children  # spine is child of root

    def test_serialise_roundtrip(self):
        skel = self._make_simple_skeleton()
        d = skel.to_dict()
        skel2 = Skeleton.from_dict(d)
        assert skel2.bone_count == 3
        assert skel2.get_bone("head") is not None
        assert skel2.get_bone("head").parent_index == 1


# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------

class TestModel:
    def test_add_and_get_mesh(self):
        model = Model("hero")
        mesh = Mesh("body", vertices=[], indices=[])
        model.add_mesh(mesh)
        assert model.get_mesh("body") is mesh

    def test_add_and_get_material(self):
        model = Model("hero")
        mat = PBRMaterial("skin")
        model.add_material(mat)
        assert model.get_material("skin") is mat

    def test_total_vertex_count(self):
        model = Model("hero")
        v = Vertex()
        model.add_mesh(Mesh("a", vertices=[v, v], indices=[0, 1, 0]))
        model.add_mesh(Mesh("b", vertices=[v, v, v], indices=[0, 1, 2]))
        assert model.total_vertex_count == 5

    def test_serialise_roundtrip(self):
        model = Model("Noctis")
        model.add_material(PBRMaterial("skin"))
        model.add_mesh(Mesh("body", vertices=[Vertex()], indices=[]))
        d = model.to_dict()
        model2 = Model.from_dict(d)
        assert model2.name == "Noctis"
        assert len(model2.meshes) == 1
        assert len(model2.materials) == 1
