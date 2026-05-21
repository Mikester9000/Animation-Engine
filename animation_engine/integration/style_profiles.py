"""Style profiles for PS2-era JRPG animation pack generation."""

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
    visual_target: str
    gameplay_target: str
    reference_titles: tuple[str, ...]
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


_PS2_VISUAL_TARGET = (
    "High-end PS2-era JRPG presentation with readable silhouettes, cinematic poses, "
    "and asset complexity suitable for PlayStation 2-class hardware."
)

_MODERN_GAMEPLAY_TARGET = (
    "Animation packs must support modern open-world JRPG gameplay beats similar to "
    "Final Fantasy VII Remake and Final Fantasy XV."
)

_REFERENCE_TITLES = (
    "Final Fantasy VII",
    "Final Fantasy VIII",
    "Final Fantasy IX",
    "Final Fantasy X",
    "Final Fantasy XII",
)

DEFAULT_STYLE_PROFILE_ID = "ff10_ps2"

_STYLE_PROFILES: dict[str, StyleProfile] = {
    "ff7_ps2": StyleProfile(
        profile_id="ff7_ps2",
        label="Final Fantasy VII inspired (PS2-era remake-friendly readability)",
        visual_target=_PS2_VISUAL_TARGET,
        gameplay_target=_MODERN_GAMEPLAY_TARGET,
        reference_titles=_REFERENCE_TITLES,
        cadence_scale=0.96,
        amplitude_scale=0.92,
        required_clips=_BASE_REQUIRED_CLIPS,
    ),
    "ff8_ps2": StyleProfile(
        profile_id="ff8_ps2",
        label="Final Fantasy VIII inspired (PS2-style cadence)",
        visual_target=_PS2_VISUAL_TARGET,
        gameplay_target=_MODERN_GAMEPLAY_TARGET,
        reference_titles=_REFERENCE_TITLES,
        cadence_scale=1.0,
        amplitude_scale=0.95,
        required_clips=_BASE_REQUIRED_CLIPS,
    ),
    "ff9_ps2": StyleProfile(
        profile_id="ff9_ps2",
        label="Final Fantasy IX inspired (PS2-era heroic exaggeration)",
        visual_target=_PS2_VISUAL_TARGET,
        gameplay_target=_MODERN_GAMEPLAY_TARGET,
        reference_titles=_REFERENCE_TITLES,
        cadence_scale=1.02,
        amplitude_scale=1.0,
        required_clips=_BASE_REQUIRED_CLIPS,
    ),
    "ff10_ps2": StyleProfile(
        profile_id="ff10_ps2",
        label="Final Fantasy X inspired (PS2-era cinematic pacing)",
        visual_target=_PS2_VISUAL_TARGET,
        gameplay_target=_MODERN_GAMEPLAY_TARGET,
        reference_titles=_REFERENCE_TITLES,
        cadence_scale=1.08,
        amplitude_scale=1.05,
        required_clips=_BASE_REQUIRED_CLIPS,
    ),
    "ff12_ps2": StyleProfile(
        profile_id="ff12_ps2",
        label="Final Fantasy XII inspired (PS2-era grounded travel/combat blend)",
        visual_target=_PS2_VISUAL_TARGET,
        gameplay_target=_MODERN_GAMEPLAY_TARGET,
        reference_titles=_REFERENCE_TITLES,
        cadence_scale=1.1,
        amplitude_scale=0.98,
        required_clips=_BASE_REQUIRED_CLIPS,
    ),
}

_STYLE_PROFILE_ALIASES = {
    "ff7_psx": "ff7_ps2",
}


def list_style_profiles() -> tuple[StyleProfile, ...]:
    """Return all style profiles in stable ID order."""
    return tuple(_STYLE_PROFILES[k] for k in sorted(_STYLE_PROFILES))


def get_style_profile(profile_id: str = DEFAULT_STYLE_PROFILE_ID) -> StyleProfile:
    """Return a style profile by ID."""
    resolved_profile_id = _STYLE_PROFILE_ALIASES.get(profile_id, profile_id)
    try:
        return _STYLE_PROFILES[resolved_profile_id]
    except KeyError as exc:
        aliases = ", ".join(f"{alias}->{target}" for alias, target in sorted(_STYLE_PROFILE_ALIASES.items()))
        available = ", ".join(sorted(_STYLE_PROFILES))
        if aliases:
            available = f"{available}; aliases: {aliases}"
        raise ValueError(f"Unknown profile '{profile_id}'. Available: {available}") from exc
