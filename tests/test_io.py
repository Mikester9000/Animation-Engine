"""
tests/test_io.py
==================
Unit tests for animation_engine.io (.anim format and glTF 2.0 export/import).
"""

import json
import os
import tempfile
import pytest

from animation_engine.model import Model, Mesh, Vertex, PBRMaterial, Skeleton
from animation_engine.model.mesh import MorphTarget
from animation_engine.math_utils import Vector2, Vector3, Transform
from animation_engine.animation import AnimationClip, MorphTrack
from animation_engine.animation.channel import ChannelTarget
from animation_engine.animation.keyframe import KeyframeType
from animation_engine.io import AnimExporter, AnimImporter, GltfExporter, GltfImporter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_model() -> Model:
    """Return a minimal complete model suitable for export tests."""
    model = Model("TestModel")

    # Material
    mat = PBRMaterial("body")
    mat.metallic = 0.1
    mat.roughness = 0.6
    model.add_material(mat)

    # Mesh (single triangle)
    verts = [
        Vertex(
            position=Vector3(0, 0, 0),
            normal=Vector3(0, 0, 1),
            uv0=Vector2(0, 0),
            bone_indices=[0, 0, 0, 0],
            bone_weights=[1.0, 0.0, 0.0, 0.0],
        ),
        Vertex(
            position=Vector3(1, 0, 0),
            normal=Vector3(0, 0, 1),
            uv0=Vector2(1, 0),
            bone_indices=[0, 0, 0, 0],
            bone_weights=[1.0, 0.0, 0.0, 0.0],
        ),
        Vertex(
            position=Vector3(0, 1, 0),
            normal=Vector3(0, 0, 1),
            uv0=Vector2(0, 1),
            bone_indices=[0, 0, 0, 0],
            bone_weights=[1.0, 0.0, 0.0, 0.0],
        ),
    ]
    mesh = Mesh(name="body", vertices=verts, indices=[0, 1, 2], material_name="body")
    model.add_mesh(mesh)

    # Skeleton
    skel = Skeleton("TestSkel")
    skel.add_bone("root")
    skel.compute_bind_pose()
    model.skeleton = skel

    return model


def _make_clip() -> AnimationClip:
    clip = AnimationClip("run", fps=30.0, loop=True)
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 1.0, [1, 0, 0])
    clip.add_keyframe("root", ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
    return clip


# ---------------------------------------------------------------------------
# .anim format
# ---------------------------------------------------------------------------

class TestAnimFormat:
    def test_export_to_string(self):
        model = _make_model()
        clip = _make_clip()
        exporter = AnimExporter()
        s = exporter.export_string(model, [clip])
        payload = json.loads(s)
        assert payload["format"] == "AnimEngine"
        assert payload["version"] == "1.0"
        assert payload["model"]["name"] == "TestModel"
        assert len(payload["clips"]) == 1

    def test_import_from_string_roundtrip(self):
        model = _make_model()
        clip = _make_clip()
        exporter = AnimExporter()
        s = exporter.export_string(model, [clip])
        importer = AnimImporter()
        model2, clips2, _ = importer.import_string(s)
        assert model2.name == model.name
        assert len(model2.meshes) == 1
        assert len(model2.materials) == 1
        assert len(clips2) == 1
        assert clips2[0].name == "run"

    def test_export_import_file(self, tmp_path):
        model = _make_model()
        clip = _make_clip()
        path = str(tmp_path / "test.anim")
        exporter = AnimExporter()
        exporter.export(model, [clip], path=path)
        assert os.path.exists(path)
        importer = AnimImporter()
        model2, clips2, _ = importer.import_file(path)
        assert model2.name == "TestModel"
        assert len(clips2) == 1

    def test_skeleton_preserved_across_roundtrip(self):
        model = _make_model()
        exporter = AnimExporter()
        s = exporter.export_string(model, [])
        importer = AnimImporter()
        model2, _, _ = importer.import_string(s)
        assert model2.skeleton is not None
        assert model2.skeleton.bone_count == 1
        assert model2.skeleton.bones[0].name == "root"

    def test_morph_track_preserved(self):
        model = _make_model()
        track = MorphTrack("smile")
        track.add_keyframe(0.0, 0.0)
        track.add_keyframe(0.5, 1.0)
        exporter = AnimExporter()
        s = exporter.export_string(model, [], [track])
        importer = AnimImporter()
        _, _, tracks2 = importer.import_string(s)
        assert len(tracks2) == 1
        assert tracks2[0].morph_name == "smile"
        assert tracks2[0].evaluate(0.5) == pytest.approx(1.0)

    def test_metadata_roundtrip_when_requested(self):
        model = _make_model()
        clip = _make_clip()
        metadata = {
            "style_profile": "ff10_ps2",
            "motion_type": "run",
            "sample_rate": 30.0,
        }
        exporter = AnimExporter()
        s = exporter.export_string(model, [clip], metadata=metadata)
        importer = AnimImporter()
        _, clips2, _, imported_metadata = importer.import_string(s, include_metadata=True)
        assert len(clips2) == 1
        assert imported_metadata == metadata

    def test_metadata_defaults_to_none_for_legacy_payload(self):
        model = _make_model()
        clip = _make_clip()
        exporter = AnimExporter()
        s = exporter.export_string(model, [clip])
        importer = AnimImporter()
        _, _, _, metadata = importer.import_string(s, include_metadata=True)
        assert metadata is None

    def test_wrong_format_raises(self):
        bad_json = json.dumps({"format": "SomeOtherEngine", "version": "1.0",
                               "model": {}, "clips": []})
        importer = AnimImporter()
        with pytest.raises(ValueError, match="Unrecognised format"):
            importer.import_string(bad_json)

    def test_incompatible_version_raises(self):
        model = _make_model()
        exporter = AnimExporter()
        s = exporter.export_string(model)
        payload = json.loads(s)
        payload["version"] = "99.0"
        importer = AnimImporter()
        with pytest.raises(ValueError, match="Incompatible"):
            importer.import_string(json.dumps(payload))


# ---------------------------------------------------------------------------
# glTF 2.0
# ---------------------------------------------------------------------------

class TestGltfExporter:
    def test_export_creates_files(self, tmp_path):
        model = _make_model()
        clip = _make_clip()
        gltf_path = str(tmp_path / "character.gltf")
        exporter = GltfExporter()
        exporter.export(model, [clip], path=gltf_path)
        assert os.path.exists(gltf_path)
        bin_path = str(tmp_path / "character.bin")
        assert os.path.exists(bin_path)

    def test_gltf_json_structure(self, tmp_path):
        model = _make_model()
        gltf_path = str(tmp_path / "test.gltf")
        exporter = GltfExporter()
        exporter.export(model, [], path=gltf_path)
        with open(gltf_path, "r") as fh:
            gltf = json.load(fh)
        assert gltf["asset"]["version"] == "2.0"
        assert len(gltf["meshes"]) == 1
        assert len(gltf["materials"]) == 1

    def test_gltf_import_roundtrip(self, tmp_path):
        model = _make_model()
        gltf_path = str(tmp_path / "char.gltf")
        exporter = GltfExporter()
        exporter.export(model, [], path=gltf_path)
        importer = GltfImporter()
        model2, clips2 = importer.import_file(gltf_path)
        # Should have at least one mesh
        assert len(model2.meshes) >= 1
        # Triangle should have 3 vertices
        assert model2.meshes[0].vertex_count == 3

    def test_gltf_animation_export(self, tmp_path):
        model = _make_model()
        clip = _make_clip()
        gltf_path = str(tmp_path / "anim.gltf")
        exporter = GltfExporter()
        exporter.export(model, [clip], path=gltf_path)
        with open(gltf_path, "r") as fh:
            gltf = json.load(fh)
        assert len(gltf["animations"]) >= 1
