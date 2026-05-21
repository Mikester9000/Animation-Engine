"""Style profiles for nostalgia-focused animation pack generation."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "ClipSpec",
    "StyleProfile",
    "DEFAULT_STYLE_PROFILE_ID",
    "list_style_profiles",
    "get_style_profile",
]


@dataclass(frozen=True)
class ClipSpec:
    motion_type: str
    duration: float
    purpose: str = ""


@dataclass(frozen=True)
class StyleProfile:
    profile_id: str
    label: str
    cadence_scale: float
    amplitude_scale: float
    required_clips: tuple[ClipSpec, ...]


_BASE_REQUIRED_CLIPS: tuple[ClipSpec, ...] = (
    ClipSpec("idle", 3.0, "calm loop"),
    ClipSpec("walk", 2.0, "exploration gait"),
    ClipSpec("run", 1.5, "urgent traversal"),
    ClipSpec("attack", 1.2, "basic combat strike"),
    ClipSpec("defend", 1.1, "guard pose"),
    ClipSpec("cast", 1.4, "spell windup"),
    ClipSpec("hit_react", 0.9, "damage reaction"),
    ClipSpec("dodge", 0.8, "quick evade"),
    ClipSpec("jump_start", 0.4, "takeoff"),
    ClipSpec("jump_loop", 0.8, "airborne hold"),
    ClipSpec("jump_land", 0.5, "landing recovery"),
    ClipSpec("victory", 2.5, "post-combat celebration"),
)


DEFAULT_STYLE_PROFILE_ID = "ff10_ps2"

_STYLE_PROFILES: dict[str, StyleProfile] = {
    "ff8_ps2": StyleProfile(
        profile_id="ff8_ps2",
        label="Final Fantasy VIII inspired (PS2-style cadence)",
        cadence_scale=1.0,
        amplitude_scale=0.95,
        required_clips=_BASE_REQUIRED_CLIPS,
    ),
    "ff10_ps2": StyleProfile(
        profile_id="ff10_ps2",
        label="Final Fantasy X inspired (PS2-era cinematic pacing)",
        cadence_scale=1.08,
        amplitude_scale=1.05,
        required_clips=_BASE_REQUIRED_CLIPS,
    ),
    "ff7_psx": StyleProfile(
        profile_id="ff7_psx",
        label="Final Fantasy VII classic inspired (legacy stylization)",
        cadence_scale=0.92,
        amplitude_scale=0.85,
        required_clips=_BASE_REQUIRED_CLIPS,
    ),
}


def list_style_profiles() -> tuple[StyleProfile, ...]:
    """Return all style profiles in stable ID order."""
    return tuple(_STYLE_PROFILES[k] for k in sorted(_STYLE_PROFILES))


def get_style_profile(profile_id: str = DEFAULT_STYLE_PROFILE_ID) -> StyleProfile:
    """Return a style profile by ID."""
    try:
        return _STYLE_PROFILES[profile_id]
    except KeyError as exc:
        available = ", ".join(sorted(_STYLE_PROFILES))
        raise ValueError(f"Unknown profile '{profile_id}'. Available: {available}") from exc
