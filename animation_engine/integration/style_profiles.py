"""Style profiles for PS2-era JRPG animation pack generation."""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "ClipSpec",
    "MotionStyleVariants",
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
class MotionStyleVariants:
    """Per-gameplay-class cadence and amplitude modifiers applied on top of the
    profile-level ``cadence_scale`` / ``amplitude_scale`` values.

    Each value is a multiplier (1.0 = no additional adjustment).  Classes:

    * **locomotion** – walk, run, sprint, strafing, crouch cycles
    * **melee** – attack combos, heavy strike, aerial attack
    * **magic** – cast windup, channeling, release
    * **reaction** – hit-react, stagger, knockdown, get-up, death
    * **traversal** – jump, roll, vault, climb sequences
    """

    locomotion: float = 1.0
    melee: float = 1.0
    magic: float = 1.0
    reaction: float = 1.0
    traversal: float = 1.0


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
    motion_style_variants: MotionStyleVariants = field(default_factory=MotionStyleVariants)


_BASE_REQUIRED_CLIPS: tuple[ClipSpec, ...] = (
    # --- Idle / ambient ---
    ClipSpec("idle", 3.0, "calm loop"),
    ClipSpec("idle_alt", 3.5, "secondary idle variant"),
    ClipSpec("idle_combat", 2.0, "combat ready idle"),
    # --- Exploration / locomotion ---
    ClipSpec("walk", 2.0, "exploration gait"),
    ClipSpec("run", 1.5, "urgent traversal"),
    ClipSpec("run_start", 0.4, "run enter"),
    ClipSpec("run_stop", 0.5, "run exit"),
    ClipSpec("sprint", 1.2, "full-speed dash"),
    ClipSpec("sprint_start", 0.35, "sprint enter burst"),
    ClipSpec("sprint_stop", 0.45, "sprint decelerate and plant"),
    ClipSpec("backstep", 0.5, "defensive retreat step"),
    ClipSpec("strafe_left", 0.9, "lateral walk left"),
    ClipSpec("strafe_right", 0.9, "lateral walk right"),
    ClipSpec("crouch", 0.6, "crouch transition"),
    ClipSpec("crouch_walk", 1.6, "crouch gait"),
    ClipSpec("guard_walk", 1.8, "guarded locomotion while blocking"),
    ClipSpec("turn_left", 0.6, "pivot left"),
    ClipSpec("turn_right", 0.6, "pivot right"),
    # --- Traversal ---
    ClipSpec("jump_start", 0.4, "takeoff"),
    ClipSpec("jump_loop", 0.8, "airborne hold"),
    ClipSpec("jump_land", 0.5, "landing recovery"),
    ClipSpec("land_hard", 0.6, "heavy landing from height"),
    ClipSpec("land_roll", 0.7, "landing absorbed into evasive roll"),
    ClipSpec("roll", 0.6, "evasive roll"),
    ClipSpec("vault", 0.5, "obstacle vault"),
    ClipSpec("climb_start", 0.5, "climb initiate"),
    ClipSpec("climb_loop", 1.2, "climb cycle"),
    ClipSpec("climb_stop", 0.5, "dismount"),
    ClipSpec("ladder_up", 1.0, "ascending ladder loop"),
    ClipSpec("ladder_down", 1.0, "descending ladder loop"),
    # --- Aquatic traversal ---
    ClipSpec("swim_idle", 2.0, "treading water"),
    ClipSpec("swim_forward", 1.4, "swimming stroke cycle"),
    ClipSpec("swim_surface", 0.8, "surfacing from underwater"),
    # --- Combat / offense ---
    ClipSpec("attack", 1.2, "basic combat strike"),
    ClipSpec("attack_combo_1", 1.0, "combo chain step 1"),
    ClipSpec("attack_combo_2", 1.0, "combo chain step 2"),
    ClipSpec("attack_combo_3", 1.1, "combo chain step 3 finisher"),
    ClipSpec("heavy_attack", 1.4, "charged heavy strike"),
    ClipSpec("aerial_attack", 0.9, "airborne strike"),
    ClipSpec("cast", 1.4, "spell windup"),
    ClipSpec("cast_channel", 1.2, "spell channeling hold"),
    ClipSpec("cast_release", 0.8, "spell release burst"),
    # --- Combat / defense ---
    ClipSpec("defend", 1.1, "guard pose"),
    ClipSpec("block", 1.0, "sustained block pose"),
    ClipSpec("parry", 0.6, "timed parry"),
    ClipSpec("dodge", 0.8, "quick evade"),
    # --- Reactions ---
    ClipSpec("hit_react", 0.9, "damage reaction"),
    ClipSpec("stagger", 0.7, "hit stagger"),
    ClipSpec("knockdown", 1.0, "knockdown fall"),
    ClipSpec("knockdown_air", 1.2, "aerial knockback fall"),
    ClipSpec("block_break", 0.7, "guard shattered reaction"),
    ClipSpec("get_up", 0.9, "recover from knockdown"),
    ClipSpec("death", 1.8, "defeat animation"),
    # --- Interactions ---
    ClipSpec("interact", 0.8, "environment interaction"),
    ClipSpec("pickup", 0.7, "pick up item"),
    # --- Celebration / emotes ---
    ClipSpec("victory", 2.5, "post-combat celebration"),
    ClipSpec("emote_cheer", 2.0, "cheer gesture for cutscenes and dialogue"),
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
        motion_style_variants=MotionStyleVariants(
            locomotion=0.94,
            melee=0.98,
            magic=1.02,
            reaction=0.96,
            traversal=0.95,
        ),
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
        motion_style_variants=MotionStyleVariants(
            locomotion=1.0,
            melee=1.02,
            magic=1.05,
            reaction=0.98,
            traversal=1.0,
        ),
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
        motion_style_variants=MotionStyleVariants(
            locomotion=1.0,
            melee=1.05,
            magic=1.08,
            reaction=1.02,
            traversal=1.04,
        ),
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
        motion_style_variants=MotionStyleVariants(
            locomotion=1.06,
            melee=1.08,
            magic=1.12,
            reaction=1.04,
            traversal=1.06,
        ),
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
        motion_style_variants=MotionStyleVariants(
            locomotion=1.08,
            melee=1.0,
            magic=1.02,
            reaction=1.0,
            traversal=1.05,
        ),
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
