"""
Animation asset pipeline for GameRewritten engine.

Generates complete character animation library in batch.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from animation_engine.integration.style_profiles import DEFAULT_STYLE_PROFILE_ID

__all__ = [
    "AnimationPipeline",
    "PIPELINE_DEFAULT_BACKEND",
    "PIPELINE_DEFAULT_SAMPLE_RATE",
    "PIPELINE_DEFAULT_SEED",
    "PIPELINE_DEFAULT_PROFILE_ID",
    "PIPELINE_GENERATION_VERSION",
    "MANIFEST_SCHEMA_VERSION",
]

# ---------------------------------------------------------------------------
# Pinned generation defaults — edit here to change the entire pipeline's
# baseline without hunting through call-sites.
# ---------------------------------------------------------------------------
PIPELINE_DEFAULT_BACKEND: str = "procedural"
PIPELINE_DEFAULT_SAMPLE_RATE: float = 30.0
PIPELINE_DEFAULT_SEED: int | None = None  # seed is forwarded to backends; the built-in procedural backend is deterministic and does not use RNG
PIPELINE_DEFAULT_PROFILE_ID: str = DEFAULT_STYLE_PROFILE_ID
PIPELINE_GENERATION_VERSION: int = 2  # v2: added semantic metadata and animation event markers
MANIFEST_SCHEMA_VERSION: str = "2.0"

# ---------------------------------------------------------------------------
# Per-clip gameplay semantic metadata tables
# ---------------------------------------------------------------------------

# Gameplay category each motion belongs to.
_CLIP_CATEGORY: dict[str, str] = {
    "idle": "idle",
    "idle_alt": "idle",
    "idle_combat": "idle",
    "walk": "exploration",
    "run": "exploration",
    "run_start": "exploration",
    "run_stop": "exploration",
    "sprint": "exploration",
    "sprint_start": "exploration",
    "sprint_stop": "exploration",
    "backstep": "exploration",
    "strafe_left": "exploration",
    "strafe_right": "exploration",
    "crouch": "exploration",
    "crouch_walk": "exploration",
    "guard_walk": "exploration",
    "turn_left": "exploration",
    "turn_right": "exploration",
    "jump_start": "traversal",
    "jump_loop": "traversal",
    "jump_land": "traversal",
    "land_hard": "traversal",
    "land_roll": "traversal",
    "roll": "traversal",
    "vault": "traversal",
    "climb_start": "traversal",
    "climb_loop": "traversal",
    "climb_stop": "traversal",
    "ladder_up": "traversal",
    "ladder_down": "traversal",
    "swim_idle": "traversal",
    "swim_forward": "traversal",
    "swim_surface": "traversal",
    "attack": "combat",
    "attack_combo_1": "combat",
    "attack_combo_2": "combat",
    "attack_combo_3": "combat",
    "heavy_attack": "combat",
    "aerial_attack": "combat",
    "cast": "combat",
    "cast_channel": "combat",
    "cast_release": "combat",
    "defend": "combat",
    "block": "combat",
    "parry": "combat",
    "dodge": "combat",
    "hit_react": "reaction",
    "stagger": "reaction",
    "knockdown": "reaction",
    "knockdown_air": "reaction",
    "block_break": "reaction",
    "get_up": "reaction",
    "death": "reaction",
    "interact": "interaction",
    "pickup": "interaction",
    "victory": "idle",
    "emote_cheer": "idle",
}

# Root-motion policy expected for this clip at runtime.
_CLIP_ROOT_MOTION_POLICY: dict[str, str] = {
    "walk": "xy_only",
    "run": "xy_only",
    "run_start": "xy_only",
    "run_stop": "xy_only",
    "sprint": "xy_only",
    "sprint_start": "xy_only",
    "sprint_stop": "xy_only",
    "backstep": "xy_only",
    "strafe_left": "xy_only",
    "strafe_right": "xy_only",
    "crouch_walk": "xy_only",
    "guard_walk": "xy_only",
    "roll": "xy_only",
    "land_roll": "xy_only",
    "vault": "full",
    "climb_start": "full",
    "climb_loop": "full",
    "climb_stop": "full",
    "ladder_up": "full",
    "ladder_down": "full",
    "swim_forward": "full",
    "swim_surface": "full",
    "jump_start": "full",
    "jump_loop": "full",
    "jump_land": "full",
    "land_hard": "full",
    "knockdown_air": "full",
}

# Semantic interaction/gameplay tags per motion.
_CLIP_INTERACTION_TAGS: dict[str, list[str]] = {
    "attack": ["hit_window", "cancel_window"],
    "attack_combo_1": ["combo_link", "cancel_window"],
    "attack_combo_2": ["combo_link", "cancel_window"],
    "attack_combo_3": ["combo_finisher"],
    "heavy_attack": ["hit_window", "unbreakable"],
    "aerial_attack": ["hit_window", "airborne"],
    "cast": ["cast_window"],
    "cast_channel": ["cast_lock"],
    "cast_release": ["spell_release"],
    "parry": ["parry_window"],
    "dodge": ["invincibility_window"],
    "roll": ["invincibility_window"],
    "hit_react": ["interruptible"],
    "stagger": ["interruptible"],
    "knockdown": ["grounded"],
    "get_up": ["invincibility_window"],
    "death": ["terminal"],
    "interact": ["context_action"],
    "pickup": ["context_action"],
    "jump_start": ["leave_ground"],
    "jump_land": ["land_impact"],
    "vault": ["parkour"],
    "climb_start": ["climb_enter"],
    "climb_loop": ["climb_cycle"],
    "climb_stop": ["climb_exit"],
    "walk": ["footstep_even"],
    "run": ["footstep_even"],
    "sprint": ["footstep_even"],
    "sprint_start": ["burst_start"],
    "sprint_stop": ["decelerate"],
    "backstep": ["invincibility_window"],
    "crouch_walk": ["footstep_quiet"],
    "guard_walk": ["guard_up"],
    "land_hard": ["land_impact_heavy"],
    "land_roll": ["recovery_roll"],
    "ladder_up": ["ladder_cycle"],
    "ladder_down": ["ladder_cycle"],
    "swim_idle": ["aquatic_idle"],
    "swim_forward": ["aquatic_stroke"],
    "swim_surface": ["aquatic_surface"],
    "knockdown_air": ["airborne"],
    "block_break": ["guard_break"],
    "emote_cheer": ["emote"],
}

# Transition intent — what state this clip is expected to lead into.
_CLIP_TRANSITION_INTENT: dict[str, str] = {
    "idle": "entry_loop",
    "idle_alt": "entry_loop",
    "idle_combat": "entry_loop",
    "walk": "locomotion_loop",
    "run": "locomotion_loop",
    "sprint": "locomotion_loop",
    "sprint_start": "locomotion_enter",
    "sprint_stop": "locomotion_exit",
    "backstep": "dodge_action",
    "run_start": "locomotion_enter",
    "run_stop": "locomotion_exit",
    "strafe_left": "locomotion_loop",
    "strafe_right": "locomotion_loop",
    "crouch": "stance_enter",
    "crouch_walk": "locomotion_loop",
    "turn_left": "locomotion_pivot",
    "turn_right": "locomotion_pivot",
    "jump_start": "airborne_enter",
    "jump_loop": "airborne_loop",
    "jump_land": "airborne_exit",
    "land_hard": "airborne_exit",
    "land_roll": "airborne_exit",
    "roll": "dodge_action",
    "vault": "traversal_action",
    "climb_start": "climb_enter",
    "climb_loop": "climb_loop",
    "climb_stop": "climb_exit",
    "ladder_up": "climb_loop",
    "ladder_down": "climb_loop",
    "swim_idle": "locomotion_loop",
    "swim_forward": "locomotion_loop",
    "swim_surface": "traversal_action",
    "attack": "attack_oneshot",
    "attack_combo_1": "combo_step",
    "attack_combo_2": "combo_step",
    "attack_combo_3": "combo_finisher",
    "heavy_attack": "attack_oneshot",
    "aerial_attack": "attack_oneshot",
    "cast": "spell_action",
    "cast_channel": "spell_hold",
    "cast_release": "spell_fire",
    "defend": "defensive_loop",
    "block": "defensive_loop",
    "parry": "defensive_action",
    "dodge": "dodge_action",
    "hit_react": "reaction_oneshot",
    "stagger": "reaction_oneshot",
    "knockdown": "reaction_fall",
    "knockdown_air": "reaction_fall",
    "block_break": "reaction_oneshot",
    "get_up": "recovery_action",
    "death": "terminal_action",
    "interact": "context_action",
    "pickup": "context_action",
    "victory": "celebration_loop",
    "emote_cheer": "celebration_loop",
}


def _clip_semantic_metadata(motion: str) -> dict[str, Any]:
    """Return gameplay semantic metadata fields for a motion identifier."""
    return {
        "locomotion_category": _CLIP_CATEGORY.get(motion, "unknown"),
        "root_motion_policy": _CLIP_ROOT_MOTION_POLICY.get(motion, "none"),
        "interaction_tags": _CLIP_INTERACTION_TAGS.get(motion, []),
        "transition_intent": _CLIP_TRANSITION_INTENT.get(motion, "oneshot"),
    }


class AnimationPipeline:
    """Generate all animations for GameRewritten.

    Parameters
    ----------
    backend:
        Animation backend to use (default: ``PIPELINE_DEFAULT_BACKEND``).
    sample_rate:
        Animation FPS (default: ``PIPELINE_DEFAULT_SAMPLE_RATE``).
    seed:
        Optional seed forwarded to the backend.  The built-in ``procedural``
        backend is fully deterministic and never calls into any RNG, so the
        same inputs always produce byte-stable outputs regardless of this value.
    profile_id:
        Style profile for the generated pack (default: ``PIPELINE_DEFAULT_PROFILE_ID``).
    """

    def __init__(
        self,
        backend: str = PIPELINE_DEFAULT_BACKEND,
        sample_rate: float = PIPELINE_DEFAULT_SAMPLE_RATE,
        seed: int | None = PIPELINE_DEFAULT_SEED,
        profile_id: str = PIPELINE_DEFAULT_PROFILE_ID,
    ) -> None:
        from animation_engine.backend import BackendRegistry

        self.backend_id = backend
        self.backend = BackendRegistry.get(backend, sample_rate=sample_rate, seed=seed)
        self.sample_rate = sample_rate
        self.profile_id = profile_id

    def generate_all(
        self,
        output_dir: str | Path,
        skeleton: Any,
        profile_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate complete animation library.

        Parameters
        ----------
        output_dir:
            Output directory for .anim files.
        skeleton:
            Character skeleton to animate.

        Returns
        -------
        dict
            Manifest of generated files.
        """
        from animation_engine.io import AnimExporter
        from animation_engine.integration.style_profiles import get_style_profile
        from animation_engine.model import Model

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        active_profile_id = profile_id or self.profile_id
        profile = get_style_profile(active_profile_id)

        generated: dict[str, str] = {}
        failed: dict[str, str] = {}
        ordered_files: list[dict[str, Any]] = []

        exporter = AnimExporter()

        model = Model("generated_animation_model")
        model.skeleton = skeleton

        for clip_spec in profile.required_clips:
            motion = clip_spec.motion_type
            try:
                clip = self.backend.generate_clip(
                    skeleton=skeleton,
                    motion_type=motion,
                    duration=clip_spec.duration,
                    cadence_scale=profile.cadence_scale,
                    amplitude_scale=profile.amplitude_scale,
                    profile_id=profile.profile_id,
                )
                output_path = output_dir / f"{motion}.anim"
                exporter.export(
                    model,
                    [clip],
                    metadata={
                        "style_profile": profile.profile_id,
                        "style_profile_label": profile.label,
                        "visual_target": profile.visual_target,
                        "gameplay_target": profile.gameplay_target,
                        "reference_titles": list(profile.reference_titles),
                        "motion_type": motion,
                        "duration": clip_spec.duration,
                        "sample_rate": self.sample_rate,
                        **_clip_semantic_metadata(motion),
                    },
                    path=str(output_path),
                )
                generated[motion] = str(output_path)
                ordered_files.append(
                    {
                        "motion_type": motion,
                        "path": str(output_path),
                        "duration": clip_spec.duration,
                    }
                )
            except (ValueError, RuntimeError, OSError, TypeError) as exc:
                failed[motion] = str(exc)

        manifest_path = output_dir / "pack_manifest.json"
        # Build category coverage summary for the manifest.
        category_coverage: dict[str, list[str]] = {}
        for entry in ordered_files:
            m = entry["motion_type"]
            cat = _CLIP_CATEGORY.get(m, "unknown")
            category_coverage.setdefault(cat, []).append(m)

        manifest = {
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "status": "failed" if failed else "ok",
            "profile_id": profile.profile_id,
            "profile_label": profile.label,
            "visual_target": profile.visual_target,
            "gameplay_target": profile.gameplay_target,
            "reference_titles": list(profile.reference_titles),
            "required_clips": [clip.motion_type for clip in profile.required_clips],
            "ordered_files": ordered_files,
            "expected": len(profile.required_clips),
            "generated": len(generated),
            "files": generated,
            "failed": failed,
            "backend_name": self.backend_id,
            "seed": getattr(self.backend, "seed", None),
            "sample_rate": self.sample_rate,
            "generation_version": PIPELINE_GENERATION_VERSION,
            "gameplay_semantic": {
                "category_coverage": category_coverage,
            },
            "manifest_path": str(manifest_path),
        }
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)

        return manifest
