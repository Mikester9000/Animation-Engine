"""Tests for editor session/playback helper logic."""

from animation_engine.editor.state import (
    PlaybackState,
    merge_recent_files,
    normalize_path,
    select_clip_name,
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


def test_merge_recent_files_deduplicates_and_limits() -> None:
    recent = ["/a.anim", "/b.anim", "/c.anim"]
    merged = merge_recent_files(recent, "/b.anim", limit=3)
    assert merged[0].endswith("b.anim")
    assert len(merged) == 3
    assert len(set(merged)) == 3


def test_normalize_path_returns_absolute() -> None:
    assert normalize_path("tests/../README.md").endswith("README.md")
