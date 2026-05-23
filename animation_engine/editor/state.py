"""State helpers for editor playback/session behavior."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable


def normalize_path(path: str) -> str:
    """Normalize and absolutize a filesystem path."""
    return os.path.normpath(os.path.abspath(path))


def merge_recent_files(recent_files: list[str], new_path: str, limit: int = 8) -> list[str]:
    """Insert a path at top of recent-files list, keeping unique entries."""
    path = normalize_path(new_path)
    merged = [path]
    merged.extend(item for item in recent_files if normalize_path(item) != path)
    return merged[: max(1, limit)]


def select_clip_name(clip_names: Iterable[str], requested: str | None, fallback: str = "") -> str:
    """Return the selected clip name if valid, else first available, else fallback."""
    names = list(clip_names)
    if requested and requested in names:
        return requested
    if names:
        return names[0]
    return fallback


def unique_duplicate_name(base: str, existing_names: set[str]) -> str:
    """Return a unique '_copy' name derived from *base* not present in *existing_names*."""
    candidate = f"{base}_copy"
    counter = 2
    while candidate in existing_names:
        candidate = f"{base}_copy{counter}"
        counter += 1
    return candidate


def is_rename_collision(new_name: str, other_names: Iterable[str]) -> bool:
    """Return True if *new_name* collides with any name in *other_names*."""
    return new_name in other_names


@dataclass(slots=True)
class PlaybackState:
    """Playback state and stepping utility."""

    time_seconds: float = 0.0
    speed: float = 1.0
    is_playing: bool = False

    def step(self, dt_seconds: float, duration_seconds: float, loop: bool = True) -> float:
        """Advance playback and return updated time."""
        if not self.is_playing:
            return self.time_seconds
        if dt_seconds <= 0.0 or self.speed <= 0.0:
            return self.time_seconds
        scaled_dt = dt_seconds * self.speed
        next_time = self.time_seconds + scaled_dt
        if duration_seconds > 0.0:
            if loop:
                next_time = next_time % duration_seconds
            elif next_time > duration_seconds:
                next_time = duration_seconds
                self.is_playing = False
        self.time_seconds = max(0.0, next_time)
        return self.time_seconds

    def scrub(self, value: float, duration_seconds: float | None = None) -> float:
        """Set playhead to requested time, optionally clamped by duration."""
        t = max(0.0, float(value))
        if duration_seconds is not None and duration_seconds > 0.0:
            t = min(t, duration_seconds)
        self.time_seconds = t
        return self.time_seconds
