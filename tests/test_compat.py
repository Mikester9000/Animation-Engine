"""
tests/test_compat.py
=====================
Validates the compatibility bridge between the Python Animation Engine and
the C++ Game Engine for Teaching.

These tests verify:
1. Exported .anim files contain all JSON fields required by GameEngineCompat.hpp.
2. The anim_to_cpp_header.py converter produces syntactically well-formed C++.
3. The .anim round-trip preserves every field that the C++ bridge reads.
4. Edge cases: missing optional fields, empty clips, zero-keyframe channels.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from typing import List

import pytest

from animation_engine.model import Model, Mesh, Vertex, PBRMaterial, Skeleton
from animation_engine.model.mesh import MorphTarget
from animation_engine.math_utils import Vector2, Vector3, Transform, Quaternion
from animation_engine.animation import AnimationClip, MorphTrack
from animation_engine.animation.channel import ChannelTarget
from animation_engine.animation.keyframe import KeyframeType
from animation_engine.io import AnimExporter, AnimImporter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

COMPAT_SCRIPT = os.path.join(
    os.path.dirname(__file__), "..", "compat", "anim_to_cpp_header.py"
)


def _make_full_model() -> Model:
    """Return a model with a skeleton, mesh, and material — like a character asset."""
    model = Model("Noctis")

    # PBR material (skin + cloth typical of FF15 characters)
    mat = PBRMaterial("body_skin")
    mat.metallic   = 0.0
    mat.roughness  = 0.6
    mat.base_color = [0.8, 0.7, 0.65, 1.0]
    model.add_material(mat)

    # Single mesh — a minimal quad to keep the test fast
    verts = [
        Vertex(
            position=Vector3(x, 0, 0),
            normal=Vector3(0, 1, 0),
            uv0=Vector2(float(x), 0.0),
            bone_indices=[0, 0, 0, 0],
            bone_weights=[1.0, 0.0, 0.0, 0.0],
        )
        for x in range(3)
    ]
    mesh = Mesh(name="body", vertices=verts, indices=[0, 1, 2],
                material_name="body_skin")
    model.add_mesh(mesh)

    # 3-bone skeleton (root → spine → head)
    skel = Skeleton("character_rig")
    root_idx  = skel.add_bone("root")
    spine_idx = skel.add_bone("spine_01", parent_index=root_idx)
    skel.add_bone("head", parent_index=spine_idx)
    skel.compute_bind_pose()
    model.skeleton = skel

    return model


def _make_full_clip(fps: float = 30.0) -> AnimationClip:
    """Return a clip with TRANSLATION + ROTATION + SCALE keyframes."""
    clip = AnimationClip("run_cycle", fps=fps, loop=True)

    # Root bone — translation driven by cubic spline (walk cycle root motion)
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 0.0, [0, 0, 0],
                      KeyframeType.CUBIC, in_tangent=[0, 0, 1], out_tangent=[0, 0, 1])
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 1.0, [0, 0, 2],
                      KeyframeType.CUBIC, in_tangent=[0, 0, 1], out_tangent=[0, 0, 1])

    # Spine — rotation (quaternion)
    clip.add_keyframe("spine_01", ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
    clip.add_keyframe("spine_01", ChannelTarget.ROTATION, 0.5, [0, 0.1, 0, 0.995])
    clip.add_keyframe("spine_01", ChannelTarget.ROTATION, 1.0, [0, 0, 0, 1])

    # Head — scale (breathing swell, optional)
    clip.add_keyframe("head", ChannelTarget.SCALE, 0.0, [1, 1, 1])
    clip.add_keyframe("head", ChannelTarget.SCALE, 0.5, [1.02, 1.02, 1.02])

    return clip


def _make_idle_clip() -> AnimationClip:
    clip = AnimationClip("idle", fps=24.0, loop=True)
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 2.0, [0, 0, 0])
    return clip


def _export_to_string(model: Model, clips: List[AnimationClip],
                      morph_tracks=None) -> str:
    return AnimExporter().export_string(model, clips, morph_tracks or [])


def _parse_json(s: str) -> dict:
    return json.loads(s)


# ===========================================================================
# Part 1 — Schema completeness tests
# ===========================================================================
# GameEngineCompat.hpp reads specific JSON fields.  These tests ensure every
# required field is present in the exported output.

class TestSchemaCompleteness:
    """Verify .anim JSON contains all fields consumed by the C++ bridge."""

    def test_top_level_fields(self):
        model = _make_full_model()
        payload = _parse_json(_export_to_string(model, []))
        # Header fields
        assert payload.get("format") == "AnimEngine", "Missing 'format'"
        assert payload.get("version", "").startswith("1"), "Missing/wrong version"
        assert "model" in payload, "Missing 'model'"
        assert "clips" in payload, "Missing 'clips'"
        assert "morph_tracks" in payload, "Missing 'morph_tracks'"

    def test_model_fields(self):
        model = _make_full_model()
        payload = _parse_json(_export_to_string(model, []))
        m = payload["model"]
        assert "name" in m, "model.name missing"
        assert isinstance(m["name"], str)

    def test_skeleton_fields(self):
        model = _make_full_model()
        payload = _parse_json(_export_to_string(model, []))
        skel = payload["model"]["skeleton"]
        assert skel is not None, "skeleton is null"
        assert "name" in skel, "skeleton.name missing"
        assert "bones" in skel, "skeleton.bones missing"
        assert len(skel["bones"]) == 3, "Expected 3 bones"

    def test_bone_fields(self):
        model = _make_full_model()
        payload = _parse_json(_export_to_string(model, []))
        for bone in payload["model"]["skeleton"]["bones"]:
            assert "name" in bone,         f"bone.name missing in {bone}"
            assert "index" in bone,        f"bone.index missing in {bone}"
            assert "parent_index" in bone, f"bone.parent_index missing in {bone}"
            assert "local_transform" in bone, "bone.local_transform missing"
            assert "inverse_bind" in bone, "bone.inverse_bind missing"
            lt = bone["local_transform"]
            # The Python Transform.to_dict() uses "position" as the key for the
            # translation; the C++ bridge reads both "position" and "translation".
            has_translation = "position" in lt or "translation" in lt
            assert has_translation, \
                f"local_transform must have 'position' or 'translation', got {list(lt.keys())}"
            assert "rotation" in lt, "local_transform.rotation missing"
            assert "scale"    in lt, "local_transform.scale missing"
            # inverse_bind must be 16 floats
            assert len(bone["inverse_bind"]) == 16, "inverse_bind must have 16 values"

    def test_clip_fields(self):
        model = _make_full_model()
        clip  = _make_full_clip()
        payload = _parse_json(_export_to_string(model, [clip]))
        assert len(payload["clips"]) == 1
        c = payload["clips"][0]
        assert "name" in c,     "clip.name missing"
        assert "fps"  in c,     "clip.fps missing"
        assert "loop" in c,     "clip.loop missing"
        assert "channels" in c, "clip.channels missing"
        assert isinstance(c["fps"], (int, float))
        assert isinstance(c["loop"], bool)

    def test_channel_fields(self):
        model = _make_full_model()
        clip  = _make_full_clip()
        payload = _parse_json(_export_to_string(model, [clip]))
        for ch in payload["clips"][0]["channels"]:
            assert "bone_name" in ch, "channel.bone_name missing"
            assert "target"    in ch, "channel.target missing"
            assert "keyframes" in ch, "channel.keyframes missing"
            assert ch["target"] in ("TRANSLATION", "ROTATION", "SCALE", "WEIGHT"), \
                f"Unknown target: {ch['target']}"

    def test_keyframe_fields(self):
        model = _make_full_model()
        clip  = _make_full_clip()
        payload = _parse_json(_export_to_string(model, [clip]))
        for ch in payload["clips"][0]["channels"]:
            for kf in ch["keyframes"]:
                assert "time"   in kf, "keyframe.time missing"
                assert "value"  in kf, "keyframe.value missing"
                assert "interp" in kf, "keyframe.interp missing"
                assert kf["interp"] in ("STEP", "LINEAR", "CUBIC"), \
                    f"Unknown interp: {kf['interp']}"

    def test_cubic_keyframe_has_tangents(self):
        model = _make_full_model()
        clip  = _make_full_clip()
        payload = _parse_json(_export_to_string(model, [clip]))
        cubic_kfs = [
            kf
            for ch in payload["clips"][0]["channels"]
            for kf in ch["keyframes"]
            if kf.get("interp") == "CUBIC"
        ]
        assert len(cubic_kfs) > 0, "Expected at least one CUBIC keyframe"
        for kf in cubic_kfs:
            assert "in_tangent"  in kf, "CUBIC keyframe missing in_tangent"
            assert "out_tangent" in kf, "CUBIC keyframe missing out_tangent"

    def test_morph_track_fields(self):
        model = _make_full_model()
        track = MorphTrack("smile")
        track.add_keyframe(0.0, 0.0)
        track.add_keyframe(0.5, 1.0)
        track.add_keyframe(1.0, 0.0)
        payload = _parse_json(_export_to_string(model, [], [track]))
        assert len(payload["morph_tracks"]) == 1
        mt = payload["morph_tracks"][0]
        assert "morph_name" in mt, "morph_track.morph_name missing"
        assert "keyframes"  in mt, "morph_track.keyframes missing"
        for kf in mt["keyframes"]:
            assert "time"  in kf, "morph keyframe.time missing"
            assert "value" in kf, "morph keyframe.value missing"


# ===========================================================================
# Part 2 — C++ bridge data-structure compatibility
# ===========================================================================
# These tests verify that the data values exported by Python will be correctly
# interpreted by the C++ structs in GameEngineCompat.hpp.

class TestDataCompatibility:
    """Verify value formats match what the C++ bridge expects."""

    def test_rotation_is_quaternion_xyzw(self):
        """Rotation keyframes must be [x, y, z, w] (not Euler)."""
        model = _make_full_model()
        q = Quaternion(0.0, 0.1, 0.0, 0.9950)  # small Y rotation
        clip = AnimationClip("test")
        clip.add_keyframe("spine_01", ChannelTarget.ROTATION, 0.0,
                          [q.x, q.y, q.z, q.w])
        payload = _parse_json(_export_to_string(model, [clip]))
        ch = next(c for c in payload["clips"][0]["channels"]
                  if c["target"] == "ROTATION")
        kf_val = ch["keyframes"][0]["value"]
        assert len(kf_val) == 4, "Rotation value must be [x, y, z, w] (4 components)"
        # The w component is last (glTF / Animation Engine convention)
        assert abs(kf_val[3]) > 0.9, "w component should be large for near-identity quat"

    def test_translation_is_xyz_list(self):
        """Translation keyframes must be [x, y, z]."""
        model = _make_full_model()
        clip = AnimationClip("test")
        clip.add_keyframe("root", ChannelTarget.TRANSLATION, 0.0, [1.5, 2.0, -0.5])
        payload = _parse_json(_export_to_string(model, [clip]))
        ch = next(c for c in payload["clips"][0]["channels"]
                  if c["target"] == "TRANSLATION")
        kf_val = ch["keyframes"][0]["value"]
        assert len(kf_val) == 3, "Translation must be [x, y, z] (3 components)"
        assert kf_val[0] == pytest.approx(1.5)
        assert kf_val[1] == pytest.approx(2.0)
        assert kf_val[2] == pytest.approx(-0.5)

    def test_inverse_bind_is_16_floats(self):
        """inverse_bind must be exactly 16 floats (4×4 matrix, row-major)."""
        model = _make_full_model()
        payload = _parse_json(_export_to_string(model, []))
        for bone in payload["model"]["skeleton"]["bones"]:
            ib = bone["inverse_bind"]
            assert len(ib) == 16, f"inverse_bind should have 16 values, got {len(ib)}"
            for v in ib:
                assert isinstance(v, (int, float)), "inverse_bind values must be numeric"

    def test_root_bone_parent_index_is_minus_one(self):
        """The root bone must have parent_index == -1."""
        model = _make_full_model()
        payload = _parse_json(_export_to_string(model, []))
        root_bone = payload["model"]["skeleton"]["bones"][0]
        assert root_bone["parent_index"] == -1, "Root bone parent_index must be -1"

    def test_keyframe_time_is_float(self):
        model = _make_full_model()
        clip = _make_full_clip()
        payload = _parse_json(_export_to_string(model, [clip]))
        for ch in payload["clips"][0]["channels"]:
            for kf in ch["keyframes"]:
                assert isinstance(kf["time"], (int, float)), \
                    "keyframe.time must be a number"
                assert kf["time"] >= 0.0, "keyframe.time must be non-negative"

    def test_multiple_clips_preserved(self):
        """Multiple clips must all appear in the exported file."""
        model = _make_full_model()
        run  = _make_full_clip()
        idle = _make_idle_clip()
        payload = _parse_json(_export_to_string(model, [run, idle]))
        names = [c["name"] for c in payload["clips"]]
        assert "run_cycle" in names
        assert "idle"      in names

    def test_model_name_preserved(self):
        model = _make_full_model()
        payload = _parse_json(_export_to_string(model, []))
        assert payload["model"]["name"] == "Noctis"

    def test_empty_clips_list(self):
        """Exporting with no clips must still produce a valid file."""
        model = _make_full_model()
        payload = _parse_json(_export_to_string(model, []))
        assert payload["clips"] == []
        assert "skeleton" in payload["model"]

    def test_no_skeleton_model(self):
        """Static models (no skeleton) should export with skeleton=null."""
        model = Model("StaticProp")
        mat   = PBRMaterial("wood")
        model.add_material(mat)
        # No skeleton assigned
        payload = _parse_json(_export_to_string(model, []))
        assert payload["model"]["skeleton"] is None


# ===========================================================================
# Part 3 — anim_to_cpp_header.py converter tests
# ===========================================================================

class TestCppHeaderConverter:
    """Verify the Python → C++ header converter produces valid output."""

    def _run_converter(self, anim_path: str, var_name: str = None) -> str:
        """Run the converter script and return the generated C++ source."""
        cmd = [sys.executable, COMPAT_SCRIPT, anim_path]
        if var_name:
            cmd += ["--var", var_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0, \
            f"Converter failed:\nstdout={result.stdout}\nstderr={result.stderr}"
        return result.stdout

    def _write_anim(self, model: Model, clips: List[AnimationClip],
                    morph_tracks=None, tmp_path=None) -> str:
        """Export a .anim file to a temp path and return the path."""
        path = str(tmp_path / "test.anim")
        AnimExporter().export(model, clips, morph_tracks or [], path=path)
        return path

    def test_converter_produces_pragma_once(self, tmp_path):
        model = _make_full_model()
        path  = self._write_anim(model, [_make_full_clip()], tmp_path=tmp_path)
        cpp   = self._run_converter(path, "TESTCHAR")
        assert "#pragma once" in cpp

    def test_converter_produces_correct_var_name(self, tmp_path):
        model = _make_full_model()
        path  = self._write_anim(model, [_make_full_clip()], tmp_path=tmp_path)
        cpp   = self._run_converter(path, "NOCTIS")
        # The var name should appear as a function definition and a reference
        assert "NOCTIS()" in cpp or "NOCTIS" in cpp

    def test_converter_includes_compat_header(self, tmp_path):
        model = _make_full_model()
        path  = self._write_anim(model, [], tmp_path=tmp_path)
        cpp   = self._run_converter(path, "FOO")
        assert '#include "compat/GameEngineCompat.hpp"' in cpp

    def test_converter_embeds_bone_names(self, tmp_path):
        model = _make_full_model()
        path  = self._write_anim(model, [], tmp_path=tmp_path)
        cpp   = self._run_converter(path, "FOO")
        assert '"root"' in cpp
        assert '"spine_01"' in cpp
        assert '"head"' in cpp

    def test_converter_embeds_clip_name(self, tmp_path):
        model = _make_full_model()
        clip  = _make_full_clip()
        path  = self._write_anim(model, [clip], tmp_path=tmp_path)
        cpp   = self._run_converter(path, "FOO")
        assert '"run_cycle"' in cpp

    def test_converter_embeds_morph_track(self, tmp_path):
        model = _make_full_model()
        track = MorphTrack("smile")
        track.add_keyframe(0.0, 0.0)
        track.add_keyframe(1.0, 1.0)
        path = self._write_anim(model, [], [track], tmp_path=tmp_path)
        cpp  = self._run_converter(path, "FOO")
        assert '"smile"' in cpp

    def test_converter_var_derived_from_filename(self, tmp_path):
        """If no --var is given, variable name should derive from the filename."""
        model = _make_full_model()
        # Write to a known filename
        path = str(tmp_path / "noctis_hero.anim")
        AnimExporter().export(model, [], path=path)
        cpp = self._run_converter(path)   # no --var
        # Filename stem = "noctis_hero" → upper = "NOCTIS_HERO"
        assert "NOCTIS_HERO" in cpp

    def test_converter_output_file_flag(self, tmp_path):
        """--output flag writes to a file instead of stdout."""
        model     = _make_full_model()
        anim_path = self._write_anim(model, [], tmp_path=tmp_path)
        out_path  = str(tmp_path / "out.hpp")
        cmd = [sys.executable, COMPAT_SCRIPT, anim_path,
               "--var", "BAR", "--output", out_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode == 0
        assert os.path.exists(out_path)
        with open(out_path) as fh:
            cpp = fh.read()
        assert "#pragma once" in cpp

    def test_converter_handles_missing_skeleton(self, tmp_path):
        """Converter should not crash for a model without a skeleton."""
        model = Model("StaticProp")
        model.add_material(PBRMaterial("wood"))
        path = self._write_anim(model, [], tmp_path=tmp_path)
        cpp  = self._run_converter(path, "PROP")
        assert "#pragma once" in cpp

    def test_converter_error_on_missing_file(self):
        cmd = [sys.executable, COMPAT_SCRIPT, "/nonexistent/path/x.anim"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        assert result.returncode != 0


# ===========================================================================
# Part 4 — Integration round-trip
# ===========================================================================

class TestRoundTrip:
    """Full export → import → re-export cycle to catch serialisation drift."""

    def test_full_roundtrip_preserves_clip_count(self):
        model  = _make_full_model()
        clips  = [_make_full_clip(), _make_idle_clip()]
        s      = AnimExporter().export_string(model, clips)
        model2, clips2, _ = AnimImporter().import_string(s)
        assert len(clips2) == 2

    def test_full_roundtrip_preserves_bone_hierarchy(self):
        model  = _make_full_model()
        s      = AnimExporter().export_string(model, [])
        model2, _, _ = AnimImporter().import_string(s)
        skel   = model2.skeleton
        assert skel is not None
        assert skel.bone_count == 3
        assert skel.bones[0].name == "root"
        assert skel.bones[1].name == "spine_01"
        assert skel.bones[2].name == "head"
        # Parent indices
        assert skel.bones[0].parent_index == -1
        assert skel.bones[1].parent_index == 0
        assert skel.bones[2].parent_index == 1

    def test_full_roundtrip_preserves_keyframe_interpolation(self):
        model = _make_full_model()
        clip  = _make_full_clip()
        s     = AnimExporter().export_string(model, [clip])
        _, clips2, _ = AnimImporter().import_string(s)
        ch = clips2[0].get_channel("root", ChannelTarget.TRANSLATION)
        assert ch is not None
        # First keyframe is CUBIC
        assert ch.keyframes[0].interp == KeyframeType.CUBIC

    def test_roundtrip_morph_weight_evaluation(self):
        model = _make_full_model()
        track = MorphTrack("blink")
        track.add_keyframe(0.0, 0.0)
        track.add_keyframe(0.1, 1.0)
        track.add_keyframe(0.2, 0.0)
        s = AnimExporter().export_string(model, [], [track])
        _, _, tracks2 = AnimImporter().import_string(s)
        assert len(tracks2) == 1
        # At t=0.1 weight should be ≈ 1.0
        assert tracks2[0].evaluate(0.1) == pytest.approx(1.0)
        # At t=0.0 and t=0.2 weight should be 0.0
        assert tracks2[0].evaluate(0.0) == pytest.approx(0.0)
        assert tracks2[0].evaluate(0.2) == pytest.approx(0.0)
