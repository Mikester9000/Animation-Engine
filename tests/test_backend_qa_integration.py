from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from animation_engine.animation import AnimationClip
from animation_engine.animation.channel import ChannelTarget
from animation_engine.backend import AnimationBackend, BackendRegistry, ProceduralBackend
from animation_engine.cli import (
    _cmd_build_production_pack,
    build_parser,
    _cmd_generate_pack,
    _cmd_list_backends,
    _cmd_validate_pack,
)
from animation_engine.integration import (
    AnimationPipeline,
    DEFAULT_STYLE_PROFILE_ID,
    get_style_profile,
    list_style_profiles,
)
from animation_engine.integration.asset_pipeline import PIPELINE_GENERATION_VERSION
from animation_engine.io import AnimExporter, AnimImporter
from animation_engine.model import Model, Skeleton
from animation_engine.qa import ClipValidator, LoopAnalyzer, SkeletonValidator, StyleValidator


def _make_skeleton() -> Skeleton:
    skel = Skeleton("HeroRig")
    root = skel.add_bone("root")
    skel.add_bone("spine_01", parent_index=root)
    skel.compute_bind_pose()
    return skel


def test_backend_registry_default_and_custom_backend_registration():
    class DemoBackend(AnimationBackend):
        def generate_clip(self, skeleton, motion_type, duration, **kwargs):
            return AnimationClip("demo")

    backend = BackendRegistry.get("procedural")
    assert isinstance(backend, ProceduralBackend)

    BackendRegistry.register("demo", DemoBackend)
    demo = BackendRegistry.get("demo", sample_rate=60.0)
    assert isinstance(demo, DemoBackend)
    assert demo.sample_rate == 60.0


def test_procedural_backend_generates_named_clip():
    backend = ProceduralBackend()
    clip = backend.generate_clip(_make_skeleton(), "walk", 1.5)
    assert clip.name == "walk"
    assert len(clip.channels) >= 1


def test_pipeline_manifest_backend_name_uses_registry_id(tmp_path):
    class DemoBackend(AnimationBackend):
        def generate_clip(self, skeleton, motion_type, duration, **kwargs):
            return AnimationClip(motion_type)

    BackendRegistry.register("demo_registry", DemoBackend)
    manifest = AnimationPipeline(backend="demo_registry").generate_all(tmp_path, _make_skeleton())
    assert manifest["backend_name"] == "demo_registry"


def test_procedural_backend_walk_and_run_keep_requested_duration():
    backend = ProceduralBackend()
    walk = backend.generate_clip(_make_skeleton(), "walk", 2.0, cadence_scale=1.08)
    run = backend.generate_clip(_make_skeleton(), "run", 1.5, cadence_scale=1.08)
    assert walk.duration == 2.0
    assert run.duration == 1.5


def test_clip_validator_and_loop_analyzer_reports():
    clip = AnimationClip("bad_clip")
    clip.add_keyframe("root", ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1.5])
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 0.0, [200, 0, 0])
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 1.0, [0, 0, 0])

    clip_report = ClipValidator().validate_clip(clip)
    assert not clip_report.is_valid
    assert any("quaternion not normalized" in err for err in clip_report.errors)
    assert any("extreme position value" in warn for warn in clip_report.warnings)

    loop_report = LoopAnalyzer(position_threshold=0.1).analyze_clip(clip)
    assert not loop_report.is_seamless
    assert loop_report.max_position_jump > 0.1


def test_skeleton_validator_detects_dag_violation():
    skel = Skeleton("broken")
    skel.add_bone("root")
    skel.add_bone("child", parent_index=0)
    skel.bones[0].parent_index = 1

    report = SkeletonValidator().validate_skeleton(skel)
    assert not report.is_valid
    assert any("DAG violation" in err for err in report.errors)


def test_pipeline_generates_anim_files(tmp_path):
    profile = get_style_profile("ff10_ps2")
    pipeline = AnimationPipeline(profile_id=profile.profile_id)
    manifest = pipeline.generate_all(tmp_path, _make_skeleton())
    assert manifest["status"] == "ok"
    assert manifest["profile_id"] == profile.profile_id
    assert manifest["visual_target"] == profile.visual_target
    assert manifest["gameplay_target"] == profile.gameplay_target
    assert manifest["reference_titles"] == list(profile.reference_titles)
    assert manifest["expected"] == len(profile.required_clips)
    assert manifest["generated"] == len(profile.required_clips)
    assert manifest["backend_name"] == "procedural"
    assert manifest["seed"] is None
    assert manifest["generation_version"] == PIPELINE_GENERATION_VERSION
    assert set(manifest["files"]) == {clip.motion_type for clip in profile.required_clips}
    assert [entry["motion_type"] for entry in manifest["ordered_files"]] == [
        clip.motion_type for clip in profile.required_clips
    ]
    assert Path(manifest["manifest_path"]).exists()
    for path in manifest["files"].values():
        assert Path(path).exists()
        model, clips, _, metadata = AnimImporter().import_file(path, include_metadata=True)
        assert model.skeleton is not None
        assert len(clips) == 1
        assert metadata is not None
        assert metadata["style_profile"] == profile.profile_id
        assert metadata["style_profile_label"] == profile.label
        assert metadata["visual_target"] == profile.visual_target
        assert metadata["gameplay_target"] == profile.gameplay_target
        assert metadata["reference_titles"] == list(profile.reference_titles)


def test_style_profiles_registry_exposes_expected_profiles():
    profiles = list_style_profiles()
    profile_ids = [p.profile_id for p in profiles]
    assert DEFAULT_STYLE_PROFILE_ID == "ff10_ps2"
    assert "ff7_ps2" in profile_ids
    assert "ff8_ps2" in profile_ids
    assert "ff9_ps2" in profile_ids
    assert "ff10_ps2" in profile_ids
    assert "ff12_ps2" in profile_ids


def test_style_profiles_registry_supports_legacy_ff7_alias():
    profile = get_style_profile("ff7_psx")
    assert profile.profile_id == "ff7_ps2"


def test_style_validator_detects_missing_required_clips():
    profile = get_style_profile("ff10_ps2")
    manifest = {
        "profile_id": "ff10_ps2",
        "status": "ok",
        "visual_target": profile.visual_target,
        "gameplay_target": profile.gameplay_target,
        "reference_titles": list(profile.reference_titles),
        "files": {"idle": "/tmp/idle.anim"},
    }
    report = StyleValidator().validate_pack(manifest)
    assert not report.is_valid
    assert "walk" in report.missing_clips
    assert any("Missing required clips" in err for err in report.errors)


def test_style_validator_handles_invalid_manifest_files_type():
    profile = get_style_profile("ff10_ps2")
    manifest = {
        "profile_id": "ff10_ps2",
        "status": "ok",
        "visual_target": profile.visual_target,
        "gameplay_target": profile.gameplay_target,
        "reference_titles": list(profile.reference_titles),
        "files": [],
    }
    report = StyleValidator().validate_pack(manifest)
    assert not report.is_valid
    assert "Manifest files must be an object" in report.errors


def test_style_validator_detects_wrong_clip_order_and_duplicates(monkeypatch):
    fake_profile = SimpleNamespace(
        profile_id="ff10_ps2",
        label="fake",
        visual_target="fake",
        gameplay_target="fake",
        reference_titles=("fake",),
        required_clips=(
            SimpleNamespace(motion_type="idle"),
            SimpleNamespace(motion_type="walk"),
            SimpleNamespace(motion_type="run"),
        ),
    )
    monkeypatch.setattr(
        "animation_engine.qa.style_validator.get_style_profile",
        lambda profile_id="ff10_ps2": fake_profile,
    )
    manifest = {
        "profile_id": "ff10_ps2",
        "status": "ok",
        "visual_target": "fake",
        "gameplay_target": "fake",
        "reference_titles": ["fake"],
        "ordered_files": [
            {"motion_type": "walk", "path": "/tmp/walk.anim"},
            {"motion_type": "idle", "path": "/tmp/idle.anim"},
            {"motion_type": "idle", "path": "/tmp/idle2.anim"},
        ],
        "required_clips": ["idle", "walk", "run"],
    }
    report = StyleValidator().validate_pack(manifest)
    assert not report.is_valid
    assert any("Duplicate clip ids" in err for err in report.errors)
    assert any("Clip order mismatch" in err for err in report.errors)


def test_style_validator_duplicate_clip_ids_are_deduplicated_in_error(monkeypatch):
    fake_profile = SimpleNamespace(
        profile_id="ff10_ps2",
        label="fake",
        visual_target="fake",
        gameplay_target="fake",
        reference_titles=("fake",),
        required_clips=(SimpleNamespace(motion_type="idle"),),
    )
    monkeypatch.setattr(
        "animation_engine.qa.style_validator.get_style_profile",
        lambda profile_id="ff10_ps2": fake_profile,
    )
    manifest = {
        "profile_id": "ff10_ps2",
        "status": "ok",
        "visual_target": "fake",
        "gameplay_target": "fake",
        "reference_titles": ["fake"],
        "ordered_files": [
            {"motion_type": "idle", "path": "/tmp/idle.anim"},
            {"motion_type": "idle", "path": "/tmp/idle2.anim"},
            {"motion_type": "idle", "path": "/tmp/idle3.anim"},
        ],
    }
    report = StyleValidator().validate_pack(manifest)
    duplicate_error = next(err for err in report.errors if err.startswith("Duplicate clip ids:"))
    assert duplicate_error == "Duplicate clip ids: idle"


def test_cli_parser_and_list_backends_command(capsys):
    parser = build_parser()
    args = parser.parse_args(["list-backends"])
    assert args.command == "list-backends"

    exit_code = _cmd_list_backends(args)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "procedural" in out


def test_cli_generate_pack_and_validate_pack_commands(tmp_path, capsys):
    source_anim = tmp_path / "source.anim"
    model = Model("source")
    model.skeleton = _make_skeleton()
    AnimExporter().export(model, [], path=str(source_anim))

    output_dir = tmp_path / "pack"
    parser = build_parser()
    generate_args = parser.parse_args(
        [
            "generate-pack",
            "--skeleton-anim",
            str(source_anim),
            "--output-dir",
            str(output_dir),
            "--profile",
            "ff10_ps2",
        ]
    )
    assert _cmd_generate_pack(generate_args) == 0
    manifest_path = output_dir / "pack_manifest.json"
    assert manifest_path.exists()

    validate_args = parser.parse_args(["validate-pack", "--manifest", str(manifest_path)])
    assert _cmd_validate_pack(validate_args) == 0
    out = capsys.readouterr().out
    assert "Style report:" in out


def test_cli_build_production_pack_command(tmp_path, capsys):
    source_anim = tmp_path / "source.anim"
    model = Model("source")
    model.skeleton = _make_skeleton()
    AnimExporter().export(model, [], path=str(source_anim))

    output_dir = tmp_path / "pack"
    report_path = output_dir / "validation_report.json"
    parser = build_parser()
    args = parser.parse_args(
        [
            "build-production-pack",
            "--skeleton-anim",
            str(source_anim),
            "--output-dir",
            str(output_dir),
            "--profile",
            "ff10_ps2",
            "--strict",
            "--json-report",
            str(report_path),
        ]
    )
    assert _cmd_build_production_pack(args) == 0
    assert (output_dir / "pack_manifest.json").exists()
    assert report_path.exists()
    out = capsys.readouterr().out
    assert "Pack generation summary:" in out
    assert "Style report:" in out


def test_cli_validate_pack_accepts_ordered_files_only_and_resolves_relative_paths(
    tmp_path, monkeypatch
):
    fake_profile = SimpleNamespace(
        profile_id="ff10_ps2",
        label="fake",
        visual_target="fake",
        gameplay_target="fake",
        reference_titles=("fake",),
        required_clips=(SimpleNamespace(motion_type="idle", duration=1.0),),
    )
    monkeypatch.setattr(
        "animation_engine.qa.style_validator.get_style_profile",
        lambda profile_id="ff10_ps2": fake_profile,
    )

    model = Model("source")
    model.skeleton = _make_skeleton()
    clip = AnimationClip("idle", fps=30.0, loop=True)
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 1.0, [0, 0, 0])
    anim_path = tmp_path / "idle.anim"
    AnimExporter().export(
        model,
        [clip],
        metadata={
            "style_profile": "ff10_ps2",
            "motion_type": "idle",
            "visual_target": "fake",
            "gameplay_target": "fake",
            "reference_titles": ["fake"],
            "duration": 1.0,
            "sample_rate": 30.0,
        },
        path=str(anim_path),
    )

    manifest_path = tmp_path / "pack_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "status": "ok",
                "profile_id": "ff10_ps2",
                "visual_target": "fake",
                "gameplay_target": "fake",
                "reference_titles": ["fake"],
                "expected": 1,
                "generated": 1,
                "required_clips": ["idle"],
                "ordered_files": [{"motion_type": "idle", "path": "idle.anim"}],
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.chdir(tmp_path.parent)
    parser = build_parser()
    validate_args = parser.parse_args(["validate-pack", "--manifest", str(manifest_path)])
    assert _cmd_validate_pack(validate_args) == 0


def test_style_validator_detects_manifest_art_direction_mismatch():
    profile = get_style_profile("ff10_ps2")
    manifest = {
        "profile_id": "ff10_ps2",
        "status": "ok",
        "visual_target": "wrong",
        "gameplay_target": profile.gameplay_target,
        "reference_titles": list(profile.reference_titles),
        "files": {
            clip.motion_type: f"/tmp/{clip.motion_type}.anim" for clip in profile.required_clips
        },
    }
    report = StyleValidator().validate_pack(manifest)
    assert not report.is_valid
    assert "Manifest visual_target does not match selected profile" in report.errors


def test_style_validator_detects_clip_metadata_mismatch():
    profile = get_style_profile("ff10_ps2")
    manifest = {
        "profile_id": "ff10_ps2",
        "status": "ok",
        "visual_target": profile.visual_target,
        "gameplay_target": profile.gameplay_target,
        "reference_titles": list(profile.reference_titles),
        "required_clips": [clip.motion_type for clip in profile.required_clips],
        "expected": len(profile.required_clips),
        "generated": len(profile.required_clips),
        "files": {
            clip.motion_type: f"/tmp/{clip.motion_type}.anim" for clip in profile.required_clips
        },
    }
    clip_metadata = {
        clip.motion_type: {
            "style_profile": profile.profile_id,
            "motion_type": clip.motion_type,
            "visual_target": profile.visual_target,
            "gameplay_target": profile.gameplay_target,
            "reference_titles": list(profile.reference_titles),
            "duration": clip.duration,
            "sample_rate": 30.0,
        }
        for clip in profile.required_clips
    }
    clip_metadata["idle"] = {
        **clip_metadata["idle"],
        "sample_rate": 0.0,
    }
    report = StyleValidator().validate_pack(manifest, clip_metadata=clip_metadata)
    assert not report.is_valid
    assert any("idle: metadata sample_rate" in e for e in report.errors)


def test_cli_generate_pack_manifest_out_has_updated_manifest_path(tmp_path):
    source_anim = tmp_path / "source.anim"
    model = Model("source")
    model.skeleton = _make_skeleton()
    AnimExporter().export(model, [], path=str(source_anim))

    output_dir = tmp_path / "pack"
    external_manifest = tmp_path / "custom_manifest.json"
    parser = build_parser()
    generate_args = parser.parse_args(
        [
            "generate-pack",
            "--skeleton-anim",
            str(source_anim),
            "--output-dir",
            str(output_dir),
            "--manifest-out",
            str(external_manifest),
        ]
    )
    assert _cmd_generate_pack(generate_args) == 0
    with open(external_manifest, "r", encoding="utf-8") as fh:
        copied_manifest = json.load(fh)
    assert copied_manifest["manifest_path"] == str(external_manifest)


def test_pipeline_byte_stable_output_same_inputs(tmp_path):
    """Same skeleton + default settings must produce identical .anim bytes."""
    import hashlib

    from animation_engine.integration.asset_pipeline import (
        PIPELINE_DEFAULT_BACKEND,
        PIPELINE_DEFAULT_PROFILE_ID,
        PIPELINE_DEFAULT_SAMPLE_RATE,
        PIPELINE_DEFAULT_SEED,
        PIPELINE_GENERATION_VERSION,
    )

    skel = _make_skeleton()

    def _run(out_dir: Path) -> dict[str, str]:
        pipeline = AnimationPipeline(
            backend=PIPELINE_DEFAULT_BACKEND,
            sample_rate=PIPELINE_DEFAULT_SAMPLE_RATE,
            seed=PIPELINE_DEFAULT_SEED,
            profile_id=PIPELINE_DEFAULT_PROFILE_ID,
        )
        manifest = pipeline.generate_all(str(out_dir), skel)
        assert manifest["generation_version"] == PIPELINE_GENERATION_VERSION
        return {
            entry["motion_type"]: hashlib.md5(Path(entry["path"]).read_bytes()).hexdigest()
            for entry in manifest["ordered_files"]
        }

    hashes_a = _run(tmp_path / "run_a")
    hashes_b = _run(tmp_path / "run_b")
    # MD5 is used here for byte-content comparison only, not for security.
    assert hashes_a == hashes_b, "Same inputs must produce byte-identical .anim files"


# ===========================================================================
# Task 11 – Animation event markers: clip serialisation round-trip
# ===========================================================================


def test_animation_clip_event_add_and_get():
    """Events can be added and retrieved sorted by time."""
    clip = AnimationClip("test")
    clip.add_event("footstep_left", 0.5, {"foot": "left"})
    clip.add_event("hit_window_open", 0.2)
    clip.add_event("footstep_right", 0.9, {"foot": "right"})

    all_events = clip.get_events()
    assert len(all_events) == 3
    assert [e["time"] for e in all_events] == [0.2, 0.5, 0.9]

    footsteps = clip.get_events("footstep_left")
    assert len(footsteps) == 1
    assert footsteps[0]["data"] == {"foot": "left"}


def test_animation_clip_events_round_trip_via_dict():
    """Events survive to_dict / from_dict serialisation."""
    clip = AnimationClip("evented")
    clip.add_event("cast_release", 1.2, {"spell_id": 7})
    clip.add_event("footstep_left", 0.4)

    restored = AnimationClip.from_dict(clip.to_dict())

    events = restored.get_events()
    assert len(events) == 2
    assert events[0]["name"] == "footstep_left"
    assert events[1]["name"] == "cast_release"
    assert events[1]["data"] == {"spell_id": 7}


def test_animation_clip_events_round_trip_via_anim_format(tmp_path):
    """Events survive export / import through the .anim file format."""
    clip = AnimationClip("evented_anim")
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 1.0, [0, 0, 0])
    clip.add_event("footstep_left", 0.25, {"foot": "left"})
    clip.add_event("hit_window_open", 0.5)

    model = Model("evented_model")
    model.skeleton = _make_skeleton()
    path = tmp_path / "evented.anim"
    AnimExporter().export(model, clips=[clip], metadata={"motion_type": "walk"}, path=str(path))
    _, loaded_clips, _ = AnimImporter().import_file(str(path))
    assert loaded_clips, "No clips loaded from .anim file"
    events = loaded_clips[0].get_events()
    assert len(events) == 2
    assert events[0]["name"] == "footstep_left"
    assert events[0]["data"] == {"foot": "left"}
    assert events[1]["name"] == "hit_window_open"


def test_animation_clip_no_events_omitted_from_dict():
    """to_dict omits 'events' key when there are no events."""
    clip = AnimationClip("no_events")
    d = clip.to_dict()
    assert "events" not in d


# ===========================================================================
# Task 12 – Runtime event dispatch and root-motion channel
# ===========================================================================


def _make_animator_with_events():
    """Return an Animator whose active clip contains two footstep events."""
    from animation_engine.runtime.animator import Animator
    from animation_engine.animation.blend_tree import BlendTree, BlendState

    clip = AnimationClip("run_cycle", fps=30.0, loop=True)
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 1.0, [0, 0, 0])
    clip.add_event("footstep_left", 0.25)
    clip.add_event("footstep_right", 0.75)

    bone_names = ["root", "spine_01"]
    bt = BlendTree(bone_names)
    bt.add_state(BlendState("run", clip))
    bt.set_initial_state("run")

    model = Model("animator_model")
    model.skeleton = _make_skeleton()
    return Animator(model, bt)


def test_animator_event_callback_fires():
    """Callback fires when animation advances past the event time."""
    animator = _make_animator_with_events()

    fired = []
    animator.register_event_callback("footstep_left", lambda ev: fired.append(ev))

    animator.update(0.3)  # past 0.25
    assert len(fired) == 1
    assert fired[0]["name"] == "footstep_left"


def test_animator_event_callback_does_not_fire_before_time():
    """Callback does not fire when animation has not yet reached the event."""
    animator = _make_animator_with_events()

    fired = []
    animator.register_event_callback("footstep_left", lambda ev: fired.append(ev))

    animator.update(0.1)  # before 0.25
    assert len(fired) == 0


def test_animator_event_callback_fires_exactly_on_time():
    """Callback fires when current_time equals the event time exactly."""
    animator = _make_animator_with_events()

    fired = []
    animator.register_event_callback("footstep_right", lambda ev: fired.append(ev))

    animator.update(0.75)
    assert len(fired) == 1


def test_animator_event_callback_repeats_on_loop_cycles():
    """Looping clip events continue firing on subsequent cycles."""
    animator = _make_animator_with_events()

    fired = []
    animator.register_event_callback("footstep_left", lambda ev: fired.append(ev))

    animator.update(0.3)  # first cycle crosses 0.25
    animator.update(1.0)  # second cycle crosses 0.25 again
    assert len(fired) == 2


def test_animator_root_motion_delta_is_vector3():
    """root_motion_delta attribute is a Vector3 after each update."""
    from animation_engine.math_utils import Vector3

    animator = _make_animator_with_events()
    animator.update(0.1)
    assert isinstance(animator.root_motion_delta, Vector3)


def test_animator_root_motion_delta_is_per_frame_delta():
    """root_motion_delta reports frame-to-frame movement, not absolute position."""
    from animation_engine.animation.blend_tree import BlendTree, BlendState
    from animation_engine.math_utils import Vector3
    from animation_engine.runtime.animator import Animator

    clip = AnimationClip("root_motion", fps=30.0, loop=False)
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 1.0, [2, 0, 0])

    bt = BlendTree(["root", "spine_01"])
    bt.add_state(BlendState("move", clip))
    bt.set_initial_state("move")

    model = Model("root_motion_model")
    model.skeleton = _make_skeleton()
    animator = Animator(model, bt)

    animator.update(0.25)
    assert animator.root_motion_delta == Vector3(0.5, 0.0, 0.0)

    animator.update(0.25)
    assert animator.root_motion_delta == Vector3(0.5, 0.0, 0.0)


# ===========================================================================
# Task 17 – Expanded clip set, semantic metadata, coverage / continuity gates
# ===========================================================================

_ALL_PROFILE_IDS = ["ff7_ps2", "ff8_ps2", "ff9_ps2", "ff10_ps2", "ff12_ps2"]


def test_expanded_clip_taxonomy_covers_minimum_motions():
    """Legacy minimum-coverage guard: every built-in profile requires at least 43 clip types."""
    for pid in _ALL_PROFILE_IDS:
        profile = get_style_profile(pid)
        assert (
            len(profile.required_clips) >= 43
        ), f"Profile {pid} has {len(profile.required_clips)} clips, expected >= 43"


def test_procedural_backend_supports_all_required_motions():
    """ProceduralBackend.supported_motion_types() covers every clip in every profile."""
    from animation_engine.backend import ProceduralBackend

    supported = set(ProceduralBackend().supported_motion_types())
    for pid in _ALL_PROFILE_IDS:
        profile = get_style_profile(pid)
        for clip_def in profile.required_clips:
            assert (
                clip_def.motion_type in supported
            ), f"Profile {pid}: motion '{clip_def.motion_type}' not in ProceduralBackend"


def test_pipeline_manifest_includes_schema_version(tmp_path):
    """Generated manifest contains schema_version matching MANIFEST_SCHEMA_VERSION."""
    from animation_engine.integration.asset_pipeline import MANIFEST_SCHEMA_VERSION

    skel = _make_skeleton()
    pipeline = AnimationPipeline(profile_id="ff10_ps2")
    manifest = pipeline.generate_all(tmp_path, skel)
    assert manifest.get("schema_version") == MANIFEST_SCHEMA_VERSION


def test_pipeline_manifest_includes_gameplay_semantic(tmp_path):
    """Generated manifest includes gameplay_semantic with adequate category coverage."""
    skel = _make_skeleton()
    pipeline = AnimationPipeline(profile_id="ff10_ps2")
    manifest = pipeline.generate_all(tmp_path, skel)

    assert "gameplay_semantic" in manifest
    cov = manifest["gameplay_semantic"].get("category_coverage", {})
    # Values are lists of motion type names.
    assert len(cov.get("exploration", [])) >= 3
    assert len(cov.get("combat", [])) >= 3
    assert len(cov.get("traversal", [])) >= 2
    assert len(cov.get("reaction", [])) >= 2


def test_pipeline_clip_metadata_includes_semantic_fields(tmp_path):
    """Each generated .anim file carries the new semantic metadata fields."""
    skel = _make_skeleton()
    pipeline = AnimationPipeline(profile_id="ff10_ps2")
    manifest = pipeline.generate_all(tmp_path, skel)

    for entry in manifest["ordered_files"]:
        _, _, _, meta = AnimImporter().import_file(entry["path"], include_metadata=True)
        assert meta is not None, f"{entry['motion_type']} has no metadata"
        assert "locomotion_category" in meta, f"{entry['motion_type']} missing locomotion_category"
        assert "root_motion_policy" in meta, f"{entry['motion_type']} missing root_motion_policy"
        assert "interaction_tags" in meta, f"{entry['motion_type']} missing interaction_tags"
        assert "transition_intent" in meta, f"{entry['motion_type']} missing transition_intent"


def test_style_validator_category_coverage_pass(tmp_path):
    """StyleValidator passes category coverage for a fully generated pack."""
    skel = _make_skeleton()
    pipeline = AnimationPipeline(profile_id="ff10_ps2")
    manifest = pipeline.generate_all(tmp_path, skel)

    report = StyleValidator().validate_pack(manifest)
    coverage_errors = [e for e in report.errors if "insufficient coverage" in e]
    assert not coverage_errors, f"Unexpected coverage errors: {coverage_errors}"


def test_style_validator_category_coverage_fail():
    """StyleValidator raises coverage errors when key categories are absent."""
    profile = get_style_profile("ff10_ps2")
    # Only idle/interaction/exploration motions — no combat or reaction
    thin_clips = [
        "idle",
        "idle_alt",
        "idle_combat",
        "interact",
        "pickup",
        "victory",
        "walk",
        "run",
        "sprint",
        "turn_left",
        "turn_right",
    ]
    manifest = {
        "profile_id": "ff10_ps2",
        "status": "ok",
        "visual_target": profile.visual_target,
        "gameplay_target": profile.gameplay_target,
        "reference_titles": list(profile.reference_titles),
        "files": {m: f"/tmp/{m}.anim" for m in thin_clips},
    }
    report = StyleValidator().validate_pack(manifest)
    coverage_errors = [e for e in report.errors if "insufficient coverage" in e]
    assert coverage_errors, "Expected coverage errors but got none"
    categories_reported = {e.split("'")[1] for e in coverage_errors}
    assert "combat" in categories_reported


def test_style_validator_transition_continuity_fail():
    """StyleValidator errors when a transition group is only partially present."""
    profile = get_style_profile("ff10_ps2")
    all_motion_types = [clip.motion_type for clip in profile.required_clips]
    # Remove attack_combo_2 and attack_combo_3 to break the combo group
    partial = [m for m in all_motion_types if m not in ("attack_combo_2", "attack_combo_3")]
    manifest = {
        "profile_id": "ff10_ps2",
        "status": "ok",
        "visual_target": profile.visual_target,
        "gameplay_target": profile.gameplay_target,
        "reference_titles": list(profile.reference_titles),
        "files": {m: f"/tmp/{m}.anim" for m in partial},
    }
    report = StyleValidator().validate_pack(manifest)
    continuity_errors = [e for e in report.errors if "Transition continuity" in e]
    assert continuity_errors, "Expected transition continuity error but got none"


def test_cli_validate_pack_json_report(tmp_path):
    """--json-report writes a machine-readable JSON file."""
    skel = _make_skeleton()
    pipeline = AnimationPipeline(profile_id="ff10_ps2")
    manifest = pipeline.generate_all(tmp_path / "pack", skel)

    parser = build_parser()
    report_path = tmp_path / "report.json"
    validate_args = parser.parse_args(
        [
            "validate-pack",
            "--manifest",
            manifest["manifest_path"],
            "--json-report",
            str(report_path),
        ]
    )
    ret = _cmd_validate_pack(validate_args)
    assert ret == 0
    assert report_path.exists()
    data = json.loads(report_path.read_text())
    assert "overall_valid" in data
    assert "style_report" in data
    assert "errors" in data["style_report"]
    assert "clips" in data


def test_cli_generate_pack_strict_succeeds_for_valid_profile(tmp_path):
    """--strict exits 0 when all clips generate successfully."""
    source_anim = tmp_path / "source.anim"
    model = Model("source")
    model.skeleton = _make_skeleton()
    AnimExporter().export(model, [], path=str(source_anim))

    parser = build_parser()
    args = parser.parse_args(
        [
            "generate-pack",
            "--skeleton-anim",
            str(source_anim),
            "--output-dir",
            str(tmp_path / "pack"),
            "--profile",
            "ff10_ps2",
            "--strict",
        ]
    )
    assert _cmd_generate_pack(args) == 0


def test_motion_style_variants_exported_on_all_profiles():
    """Every built-in profile exposes MotionStyleVariants with positive cadence values."""
    from animation_engine.integration import MotionStyleVariants

    cadence_fields = ("locomotion", "melee", "magic", "reaction", "traversal")
    for pid in _ALL_PROFILE_IDS:
        profile = get_style_profile(pid)
        variants = profile.motion_style_variants
        assert isinstance(variants, MotionStyleVariants), f"{pid} missing MotionStyleVariants"
        for field in cadence_fields:
            val = getattr(variants, field)
            assert val > 0, f"{pid}.{field} = {val} (must be > 0)"


# ---------------------------------------------------------------------------
# Tests for expanded clip taxonomy (57 clips)
# ---------------------------------------------------------------------------

_NEW_MOTION_TYPES = [
    "backstep",
    "block_break",
    "emote_cheer",
    "guard_walk",
    "knockdown_air",
    "ladder_down",
    "ladder_up",
    "land_hard",
    "land_roll",
    "sprint_start",
    "sprint_stop",
    "swim_forward",
    "swim_idle",
    "swim_surface",
]


def test_expanded_taxonomy_has_57_clips():
    """All profiles now include the expanded 57-clip set."""
    for pid in _ALL_PROFILE_IDS:
        profile = get_style_profile(pid)
        assert len(profile.required_clips) == 57, (
            f"Profile {pid} has {len(profile.required_clips)} clips, expected 57"
        )


def test_new_motion_types_present_in_all_profiles():
    """Every new motion type is present in every built-in profile's required_clips."""
    for pid in _ALL_PROFILE_IDS:
        profile = get_style_profile(pid)
        motion_types = {spec.motion_type for spec in profile.required_clips}
        for mt in _NEW_MOTION_TYPES:
            assert mt in motion_types, f"Profile {pid} is missing new motion type '{mt}'"


def test_procedural_backend_generates_all_new_motion_types():
    """ProceduralBackend generates a non-empty clip for each new motion type."""
    backend = ProceduralBackend()
    skel = _make_skeleton()
    for mt in _NEW_MOTION_TYPES:
        clip = backend.generate_clip(skel, mt, 1.0)
        assert clip.name == mt, f"Clip name mismatch for '{mt}'"
        assert len(clip.channels) >= 1, f"No channels generated for '{mt}'"


def test_procedural_backend_supported_types_covers_new_motions():
    """supported_motion_types() explicitly lists all new motion types."""
    supported = set(ProceduralBackend().supported_motion_types())
    for mt in _NEW_MOTION_TYPES:
        assert mt in supported, f"'{mt}' not in supported_motion_types()"


def test_full_pipeline_generates_expanded_pack(tmp_path):
    """Pipeline generates a complete pack for the expanded 57-clip taxonomy."""
    skel = _make_skeleton()
    pipeline = AnimationPipeline(profile_id="ff10_ps2")
    manifest = pipeline.generate_all(tmp_path, skel)
    generated = {e["motion_type"] for e in manifest["ordered_files"]}
    for mt in _NEW_MOTION_TYPES:
        assert mt in generated, f"Pipeline did not generate clip for '{mt}'"
