from __future__ import annotations

from pathlib import Path

from animation_engine.animation import AnimationClip
from animation_engine.animation.channel import ChannelTarget
from animation_engine.backend import AnimationBackend, BackendRegistry, ProceduralBackend
from animation_engine.cli import build_parser, _cmd_list_backends
from animation_engine.integration import AnimationPipeline
from animation_engine.io import AnimImporter
from animation_engine.model import Skeleton
from animation_engine.qa import ClipValidator, LoopAnalyzer, SkeletonValidator


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
    pipeline = AnimationPipeline()
    manifest = pipeline.generate_all(tmp_path, _make_skeleton())
    assert manifest["generated"] == 4
    assert set(manifest["files"]) == {"idle", "walk", "run", "attack"}
    for path in manifest["files"].values():
        assert Path(path).exists()
        model, clips, _ = AnimImporter().import_file(path)
        assert model.skeleton is not None
        assert len(clips) == 1


def test_cli_parser_and_list_backends_command(capsys):
    parser = build_parser()
    args = parser.parse_args(["list-backends"])
    assert args.command == "list-backends"

    exit_code = _cmd_list_backends(args)
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "procedural" in out
