"""Tests for editor session/playback helper logic."""

from copy import deepcopy

from animation_engine.animation.channel import ChannelTarget
from animation_engine.animation.clip import AnimationClip
from animation_engine.animation.morph_track import MorphTrack
from animation_engine.editor.state import (
    PlaybackState,
    is_rename_collision,
    merge_recent_files,
    normalize_path,
    select_clip_name,
    unique_duplicate_name,
)
from animation_engine.model.skeleton import Skeleton


def test_select_clip_name_prefers_requested() -> None:
    assert select_clip_name(["idle", "run"], "run") == "run"


def test_select_clip_name_falls_back_to_first() -> None:
    assert select_clip_name(["idle", "run"], "missing") == "idle"


def test_playback_step_loops_when_enabled() -> None:
    state = PlaybackState(time_seconds=0.95, speed=1.0, is_playing=True)
    state.step(0.1, duration_seconds=1.0, loop=True)
    assert 0.0 <= state.time_seconds < 0.1


def test_playback_step_clamps_and_stops_when_not_looping() -> None:
    state = PlaybackState(time_seconds=0.95, speed=1.0, is_playing=True)
    state.step(0.1, duration_seconds=1.0, loop=False)
    assert state.time_seconds == 1.0
    assert state.is_playing is False


def test_playback_step_noops_when_speed_non_positive() -> None:
    state = PlaybackState(time_seconds=0.5, speed=0.0, is_playing=True)
    state.step(0.25, duration_seconds=1.0, loop=True)
    assert state.time_seconds == 0.5
    assert state.is_playing is True


def test_playback_step_noops_when_delta_non_positive() -> None:
    state = PlaybackState(time_seconds=0.5, speed=1.0, is_playing=True)
    state.step(0.0, duration_seconds=1.0, loop=True)
    assert state.time_seconds == 0.5
    assert state.is_playing is True


def test_merge_recent_files_deduplicates_and_limits() -> None:
    recent = ["/a.anim", "/b.anim", "/c.anim"]
    merged = merge_recent_files(recent, "/b.anim", limit=3)
    assert merged[0].endswith("b.anim")
    assert len(merged) == 3
    assert len(set(merged)) == 3


def test_normalize_path_returns_absolute() -> None:
    assert normalize_path("tests/../README.md").endswith("README.md")


# ---------------------------------------------------------------------------
# Clip management logic (independent of Tkinter)
# ---------------------------------------------------------------------------


def _make_clips(*names: str) -> list:
    return [AnimationClip(n) for n in names]


def test_duplicate_clip_produces_unique_name() -> None:
    clips = _make_clips("idle", "run")
    source = clips[0]
    existing = {c.name for c in clips}
    candidate = unique_duplicate_name(source.name, existing)
    new_clip = AnimationClip.from_dict(deepcopy(source.to_dict()))
    new_clip.name = candidate
    assert new_clip.name == "idle_copy"
    assert new_clip.name not in {c.name for c in clips}


def test_duplicate_clip_increments_suffix_on_collision() -> None:
    clips = _make_clips("idle", "idle_copy")
    source = clips[0]
    existing = {c.name for c in clips}
    candidate = unique_duplicate_name(source.name, existing)
    assert candidate == "idle_copy2"


def test_delete_clip_removes_from_list() -> None:
    clips = _make_clips("idle", "run", "attack")
    active = clips[1]
    clips.remove(active)
    assert len(clips) == 2
    assert all(c.name != "run" for c in clips)


def test_rename_clip_detects_collision() -> None:
    clips = _make_clips("idle", "run")
    other_names = [c.name for c in clips if c.name != clips[0].name]
    assert is_rename_collision("run", other_names), "Should detect collision with existing name"


def test_rename_clip_accepts_unique_name() -> None:
    clips = _make_clips("idle", "run")
    other_names = [c.name for c in clips if c.name != clips[0].name]
    assert not is_rename_collision("walk", other_names), "Unique name should not collide"
    clips[0].name = "walk"
    assert clips[0].name == "walk"


# ---------------------------------------------------------------------------
# Morph track management
# ---------------------------------------------------------------------------


def _make_morph_tracks(*names: str) -> list:
    return [MorphTrack(n) for n in names]


def test_morph_track_add_and_evaluate() -> None:
    mt = MorphTrack("brow_raise")
    mt.add_keyframe(0.0, 0.0)
    mt.add_keyframe(0.5, 1.0)
    mt.add_keyframe(1.0, 0.0)
    assert mt.evaluate(0.5) == 1.0
    assert mt.evaluate(0.0) == 0.0
    assert 0.0 < mt.evaluate(0.25) < 1.0


def test_morph_track_name_uniqueness() -> None:
    tracks = _make_morph_tracks("smile", "frown")
    names = {mt.morph_name for mt in tracks}
    assert "smile" in names and "frown" in names
    assert len(names) == 2


def test_morph_track_remove() -> None:
    tracks = _make_morph_tracks("smile", "frown", "blink")
    target = tracks[1]
    tracks.remove(target)
    assert all(mt.morph_name != "frown" for mt in tracks)
    assert len(tracks) == 2


def test_morph_track_serialization_roundtrip() -> None:
    mt = MorphTrack("cheek_puff")
    mt.add_keyframe(0.0, 0.2)
    mt.add_keyframe(0.5, 0.9)
    d = mt.to_dict()
    restored = MorphTrack.from_dict(d)
    assert restored.morph_name == mt.morph_name
    assert len(restored.keyframes) == len(mt.keyframes)
    assert abs(restored.evaluate(0.5) - 0.9) < 1e-6


# ---------------------------------------------------------------------------
# Clip settings (FPS / motion_type / loop)
# ---------------------------------------------------------------------------


def test_clip_fps_assignment() -> None:
    clip = AnimationClip("run", fps=30.0)
    clip.fps = 24.0
    assert clip.fps == 24.0


def test_clip_motion_type_attribute() -> None:
    """motion_type is a formal attribute of AnimationClip."""
    clip = AnimationClip("strafe_left")
    clip.motion_type = "strafe_left"
    assert clip.motion_type == "strafe_left"


def test_clip_motion_type_default_is_empty() -> None:
    clip = AnimationClip("idle")
    assert clip.motion_type == ""


def test_clip_motion_type_serialization_roundtrip() -> None:
    clip = AnimationClip("idle")
    clip.motion_type = "locomotion"
    restored = AnimationClip.from_dict(clip.to_dict())
    assert restored.motion_type == "locomotion"


def test_clip_loop_toggle_via_settings() -> None:
    clip = AnimationClip("idle", loop=True)
    clip.loop = False
    assert not clip.loop
    clip.loop = True
    assert clip.loop


def test_clip_duration_reflects_keyframe_span() -> None:
    clip = AnimationClip("attack")
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 1.5, [0, 1, 0])
    assert abs(clip.duration - 1.5) < 1e-6


# ---------------------------------------------------------------------------
# Skeleton bone rename / delete (GUI completeness)
# ---------------------------------------------------------------------------


def _make_skeleton() -> Skeleton:
    skel = Skeleton("test_rig")
    root = skel.add_bone("root", parent_index=-1)
    spine = skel.add_bone("spine_01", parent_index=root)
    skel.add_bone("spine_02", parent_index=spine)
    skel.compute_bind_pose()
    return skel


def test_skeleton_rename_bone_updates_name_and_lookup() -> None:
    skel = _make_skeleton()
    assert skel.rename_bone("spine_01", "spine_a")
    assert skel.get_bone("spine_a") is not None
    assert skel.get_bone("spine_01") is None
    assert skel.get_bone_index("spine_a") >= 0
    assert skel.get_bone_index("spine_01") == -1


def test_skeleton_rename_bone_rejects_collision() -> None:
    skel = _make_skeleton()
    assert not skel.rename_bone("spine_01", "root"), "Should reject rename to existing name"


def test_skeleton_rename_bone_rejects_missing() -> None:
    skel = _make_skeleton()
    assert not skel.rename_bone("nonexistent", "new_name")


def test_skeleton_remove_leaf_bone() -> None:
    skel = _make_skeleton()
    initial_count = skel.bone_count
    assert skel.remove_bone("spine_02")
    assert skel.bone_count == initial_count - 1
    assert skel.get_bone("spine_02") is None


def test_skeleton_remove_bone_with_children_is_rejected() -> None:
    skel = _make_skeleton()
    # spine_01 has a child (spine_02), so removal should fail
    assert not skel.remove_bone("spine_01")
    assert skel.get_bone("spine_01") is not None


def test_skeleton_remove_bone_updates_parent_children_list() -> None:
    skel = _make_skeleton()
    spine01 = skel.get_bone("spine_01")
    assert skel.get_bone_index("spine_02") in spine01.children
    skel.remove_bone("spine_02")
    # spine_01's children list must not reference the deleted bone's old index
    assert skel.get_bone_index("spine_02") not in skel.get_bone("spine_01").children


def test_skeleton_remove_bone_indices_stay_contiguous() -> None:
    skel = _make_skeleton()
    skel.remove_bone("spine_02")
    for i, bone in enumerate(skel.bones):
        assert bone.index == i, f"Bone index out of sync after remove: {bone}"


def test_clip_rename_bone_channels() -> None:
    clip = AnimationClip("walk")
    clip.add_keyframe("spine_01", ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
    clip.add_keyframe("spine_01", ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
    updated = clip.rename_bone_channels("spine_01", "spine_a")
    assert updated == 2
    assert ("spine_a", ChannelTarget.TRANSLATION) in clip._channels
    assert ("spine_a", ChannelTarget.ROTATION) in clip._channels
    assert not any(k[0] == "spine_01" for k in clip._channels)


def test_clip_remove_bone_channels() -> None:
    clip = AnimationClip("walk")
    clip.add_keyframe("spine_01", ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
    removed = clip.remove_bone_channels("spine_01")
    assert removed == 1
    assert not any(k[0] == "spine_01" for k in clip._channels)
    assert any(k[0] == "root" for k in clip._channels)


def test_clip_rename_bone_channels_no_op_when_bone_absent() -> None:
    clip = AnimationClip("idle")
    clip.add_keyframe("root", ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
    updated = clip.rename_bone_channels("nonexistent", "new_name")
    assert updated == 0


def test_clip_rename_bone_channels_merges_when_destination_exists() -> None:
    clip = AnimationClip("walk")
    clip.add_keyframe("spine_01", ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
    clip.add_keyframe("spine_a", ChannelTarget.TRANSLATION, 1.0, [0, 1, 0])

    updated = clip.rename_bone_channels("spine_01", "spine_a")

    assert updated == 1
    ch = clip.get_channel("spine_a", ChannelTarget.TRANSLATION)
    assert ch is not None
    assert [kf.time for kf in ch.keyframes] == [0.0, 1.0]
    assert [kf.value for kf in ch.keyframes] == [[0, 0, 0], [0, 1, 0]]
