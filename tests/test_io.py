"""
tests/test_io.py
==================
Unit tests for animation_engine.io (.anim format and glTF 2.0 export/import).
"""

import json
import os
import pytest

from animation_engine.model import Model, Mesh, Vertex, PBRMaterial, Skeleton
from animation_engine.math_utils import Vector2, Vector3
from animation_engine.animation import AnimationClip, MorphTrack
from animation_engine.animation.channel import ChannelTarget
from animation_engine.io import AnimExporter, AnimImporter, GltfExporter, GltfImporter
from compat.anim_to_cpp_header import convert_pack_manifest, main as anim_to_cpp_header_main

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

    def test_editor_state_metadata_roundtrip(self):
        model = _make_model()
        clip = _make_clip()
        metadata = {
            "editor_state": {
                "selected_clip": "run",
                "playback_time": 0.75,
                "viewer": {"lighting": "ps2_studio", "show_grid": True},
            }
        }
        exporter = AnimExporter()
        payload = exporter.export_string(model, [clip], metadata=metadata)
        importer = AnimImporter()
        _, _, _, imported_metadata = importer.import_string(payload, include_metadata=True)
        assert imported_metadata is not None
        assert imported_metadata["editor_state"]["selected_clip"] == "run"
        assert imported_metadata["editor_state"]["viewer"]["lighting"] == "ps2_studio"

    def test_wrong_format_raises(self):
        bad_json = json.dumps(
            {"format": "SomeOtherEngine", "version": "1.0", "model": {}, "clips": []}
        )
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

    def test_pack_manifest_batch_conversion_writes_headers(self, tmp_path):
        model = _make_model()
        exporter = AnimExporter()

        idle_path = tmp_path / "idle.anim"
        run_path = tmp_path / "run.anim"
        exporter.export(model, [_make_clip()], path=str(idle_path))
        exporter.export(model, [_make_clip()], path=str(run_path))

        manifest_path = tmp_path / "pack_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "ordered_files": [
                        {"motion_type": "idle", "path": str(idle_path)},
                        {"motion_type": "run", "path": str(run_path)},
                    ]
                }
            ),
            encoding="utf-8",
        )

        output_dir = tmp_path / "headers"
        written = convert_pack_manifest(manifest_path, output_dir)
        assert [path.name for path in written] == ["idle.hpp", "run.hpp"]
        assert all(path.exists() for path in written)

    def test_pack_manifest_ordered_files_must_not_be_empty_when_present(self, tmp_path):
        model = _make_model()
        exporter = AnimExporter()
        idle_path = tmp_path / "idle.anim"
        exporter.export(model, [_make_clip()], path=str(idle_path))

        manifest_path = tmp_path / "pack_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "ordered_files": [],
                    "files": {"idle": str(idle_path)},
                }
            ),
            encoding="utf-8",
        )

        with pytest.raises(ValueError, match="ordered_files must contain at least one entry"):
            convert_pack_manifest(manifest_path, tmp_path / "headers")

    def test_batch_manifest_cli_reports_invalid_json(self, tmp_path, monkeypatch, capsys):
        manifest_path = tmp_path / "pack_manifest.json"
        manifest_path.write_text("{", encoding="utf-8")
        output_dir = tmp_path / "headers"

        monkeypatch.setattr(
            "sys.argv",
            [
                "anim_to_cpp_header.py",
                "--manifest",
                str(manifest_path),
                "--output-dir",
                str(output_dir),
            ],
        )
        assert anim_to_cpp_header_main() == 1
        assert "Error: invalid JSON" in capsys.readouterr().err


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

    def test_gltf_animation_extras_preserved(self, tmp_path):
        """Animation extras (loop flag + event markers) survive glTF round-trip."""
        model = _make_model()
        clip = _make_clip()
        clip.loop = True
        clip.add_event("footstep_left", 0.25, {"foot": "left"})
        clip.add_event("hit_window_open", 0.45)

        gltf_path = str(tmp_path / "extras.gltf")
        GltfExporter().export(model, [clip], path=gltf_path)

        with open(gltf_path, "r") as fh:
            gltf = json.load(fh)
        extras = gltf["animations"][0].get("extras", {})
        assert extras.get("loop") is True
        assert len(extras.get("events", [])) == 2
        assert extras["events"][0]["name"] == "footstep_left"
        assert extras["events"][1]["name"] == "hit_window_open"

    def test_gltf_animation_events_import_roundtrip(self, tmp_path):
        """Events written to glTF extras are read back correctly by GltfImporter."""
        model = _make_model()
        clip = _make_clip()
        clip.loop = False
        clip.add_event("cast_release", 0.8, {"spell": "fire"})

        gltf_path = str(tmp_path / "events.gltf")
        GltfExporter().export(model, [clip], path=gltf_path)

        _, imported_clips = GltfImporter().import_file(gltf_path)
        assert len(imported_clips) >= 1
        imported = imported_clips[0]
        assert imported.loop is False
        events = imported.get_events()
        assert len(events) == 1
        assert events[0]["name"] == "cast_release"
        assert events[0]["time"] == pytest.approx(0.8)
        assert events[0]["data"]["spell"] == "fire"


# ---------------------------------------------------------------------------
# .anim event serialization compatibility
# ---------------------------------------------------------------------------


class TestAnimEventSerializationCompat:
    """Verify backward and forward compatibility of event markers in .anim files."""

    def _make_model(self) -> Model:
        return _make_model()

    def test_legacy_payload_without_events_imports_cleanly(self):
        """An .anim file with no events key loads without error and has no events."""
        model = _make_model()
        clip = AnimationClip("idle", fps=30.0, loop=True)
        exporter = AnimExporter()
        s = exporter.export_string(model, [clip])
        payload = json.loads(s)
        # Strip events from the clip dict to simulate a legacy file
        for c in payload.get("clips", []):
            c.pop("events", None)

        importer = AnimImporter()
        _, clips2, _ = importer.import_string(json.dumps(payload))
        assert len(clips2) == 1
        assert clips2[0].get_events() == []

    def test_events_round_trip_with_full_metadata(self):
        """Events + style metadata both survive a complete .anim round-trip."""
        model = _make_model()
        clip = AnimationClip("attack", fps=30.0, loop=False)
        clip.add_event("hit_window_open", 0.4, {"power": "heavy"})
        clip.add_event("hit_window_close", 0.6)
        metadata = {
            "style_profile": "ff10_ps2",
            "motion_type": "attack",
            "visual_target": "PS2",
            "gameplay_target": "Modern",
            "reference_titles": ["FF10"],
            "duration": 1.2,
            "sample_rate": 30.0,
        }
        s = AnimExporter().export_string(model, [clip], metadata=metadata)
        _, clips2, _, meta2 = AnimImporter().import_string(s, include_metadata=True)

        assert len(clips2) == 1
        events = clips2[0].get_events()
        assert len(events) == 2
        assert events[0]["name"] == "hit_window_open"
        assert events[0]["time"] == pytest.approx(0.4)
        assert events[0]["data"]["power"] == "heavy"
        assert events[1]["name"] == "hit_window_close"
        assert meta2 == metadata

    def test_forward_compat_unknown_event_data_keys_preserved(self):
        """Unknown keys in event data dict are carried through without loss."""
        model = _make_model()
        clip = AnimationClip("cast", fps=30.0, loop=False)
        clip.add_event("cast_release", 1.0, {"spell": "blizzard", "rank": 3, "aoe": True})
        s = AnimExporter().export_string(model, [clip])
        _, clips2, _ = AnimImporter().import_string(s)
        ev = clips2[0].get_events("cast_release")[0]
        assert ev["data"]["spell"] == "blizzard"
        assert ev["data"]["rank"] == 3
        assert ev["data"]["aoe"] is True

    def test_style_metadata_fields_preserved_across_roundtrip(self):
        """All style-profile art-direction fields survive the .anim roundtrip."""
        model = _make_model()
        clip = AnimationClip("idle")
        metadata = {
            "style_profile": "ff7_ps2",
            "motion_type": "idle",
            "visual_target": "PS2_visual",
            "gameplay_target": "modern_gameplay",
            "reference_titles": ["FF7", "FF8"],
            "duration": 3.0,
            "sample_rate": 30.0,
            "locomotion_category": "idle",
            "root_motion_policy": "none",
            "interaction_tags": [],
            "transition_intent": "entry_loop",
        }
        s = AnimExporter().export_string(model, [clip], metadata=metadata)
        _, _, _, meta2 = AnimImporter().import_string(s, include_metadata=True)
        for key, expected_val in metadata.items():
            assert meta2[key] == expected_val, f"Metadata field '{key}' mismatch"
