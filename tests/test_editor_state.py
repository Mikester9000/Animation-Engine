"""Tests for editor session/playback helper logic."""

from copy import deepcopy

from animation_engine.animation.clip import AnimationClip
from animation_engine.editor.state import (
    PlaybackState,
    is_rename_collision,
    merge_recent_files,
    normalize_path,
    select_clip_name,
    unique_duplicate_name,
)


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
