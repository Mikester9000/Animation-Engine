"""
Pluggable animation generation backend interface.

Defines :class:`AnimationBackend` abstract base class. Ships with
:class:`ProceduralBackend` for keyframe-based animation.

Future backends could wrap:
- Motion capture ML models (RNN/Transformer-based)
- Physics-based procedural animation
- Style-transfer motion synthesis
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import math
from typing import Any

__all__ = ["AnimationBackend", "ProceduralBackend", "BackendRegistry"]


class AnimationBackend(ABC):
    """Abstract base class for animation generation backends.

    Parameters
    ----------
    sample_rate:
        Animation sample rate in FPS (frames per second).
    seed:
        Random seed for reproducibility.
    """

    def __init__(self, sample_rate: float = 30.0, seed: int | None = None) -> None:
        self.sample_rate = sample_rate
        self.seed = seed

    @property
    def name(self) -> str:
        """Human-readable backend name."""
        return self.__class__.__name__

    @abstractmethod
    def generate_clip(
        self,
        skeleton: Any,
        motion_type: str,
        duration: float,
        **kwargs: Any,
    ) -> Any:
        """Generate an animation clip.

        Parameters
        ----------
        skeleton:
            Skeleton instance defining bone hierarchy.
        motion_type:
            Type of motion: "idle", "walk", "run", "attack", etc.
        duration:
            Clip duration in seconds.
        **kwargs:
            Backend-specific parameters.

        Returns
        -------
        AnimationClip
            Generated animation clip.
        """

    def is_available(self) -> bool:
        """Return True if backend dependencies are installed."""
        return True

    def supported_motion_types(self) -> tuple[str, ...]:
        """Return supported motion types."""
        return (
            "aerial_attack",
            "attack",
            "attack_combo_1",
            "attack_combo_2",
            "attack_combo_3",
            "backstep",
            "block",
            "block_break",
            "cast",
            "cast_channel",
            "cast_release",
            "climb_loop",
            "climb_start",
            "climb_stop",
            "crouch",
            "crouch_walk",
            "death",
            "defend",
            "dodge",
            "emote_cheer",
            "get_up",
            "guard_walk",
            "heavy_attack",
            "hit_react",
            "idle",
            "idle_alt",
            "idle_combat",
            "interact",
            "jump_land",
            "jump_loop",
            "jump_start",
            "knockdown",
            "knockdown_air",
            "ladder_down",
            "ladder_up",
            "land_hard",
            "land_roll",
            "parry",
            "pickup",
            "roll",
            "run",
            "run_start",
            "run_stop",
            "sprint",
            "sprint_start",
            "sprint_stop",
            "stagger",
            "strafe_left",
            "strafe_right",
            "swim_forward",
            "swim_idle",
            "swim_surface",
            "turn_left",
            "turn_right",
            "vault",
            "victory",
            "walk",
        )


class ProceduralBackend(AnimationBackend):
    """Keyframe-based procedural animation backend.

    Uses existing AnimationClip keyframe system to generate simple
    procedural animations. This is the default fallback with zero
    external dependencies.
    """

    @property
    def name(self) -> str:
        return "procedural"

    def generate_clip(
        self,
        skeleton: Any,
        motion_type: str,
        duration: float,
        **kwargs: Any,
    ) -> Any:
        """Generate clip using keyframe interpolation."""
        from animation_engine.animation import AnimationClip
        from animation_engine.animation.channel import ChannelTarget

        def _unit_axis_quat(axis_value: float, axis: str) -> list[float]:
            """Return a unit quaternion in engine [x, y, z, w] storage order."""
            # Engine convention is [x, y, z, w] (same as Quaternion.to_list/from_list).
            value = max(min(axis_value, 0.999999), -0.999999)
            w = math.sqrt(max(0.0, 1.0 - (value * value)))
            if axis == "x":
                return [value, 0.0, 0.0, w]
            if axis == "z":
                return [0.0, 0.0, value, w]
            return [0.0, value, 0.0, w]

        def _find_bone_name(*candidates: str) -> str | None:
            if not skeleton or not getattr(skeleton, "bones", None):
                return None
            by_name = {bone.name for bone in skeleton.bones}
            by_name_lower = {bone.name.lower(): bone.name for bone in skeleton.bones}
            for name in candidates:
                if name in by_name:
                    return name
            for name in candidates:
                found = by_name_lower.get(name.lower())
                if found is not None:
                    return found
            return None

        def _apply_sword_attack_pose(
            *,
            swing_direction: float = 1.0,
            overhead: bool = False,
            impact_hold: bool = True,
        ) -> None:
            weapon_name = _find_bone_name(
                "sword_r",
                "weapon_r",
                "blade_r",
                "hand_weapon_r",
                "sword",
                "weapon",
            )
            if weapon_name is None:
                return
            hand_name = _find_bone_name("hand_r", "r_hand", "right_hand")
            a = amplitude_scale
            clip.add_keyframe(weapon_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
            if overhead:
                clip.add_keyframe(
                    weapon_name,
                    ChannelTarget.ROTATION,
                    duration * 0.2,
                    _unit_axis_quat(-0.34 * a, axis="x"),
                )
                clip.add_keyframe(
                    weapon_name,
                    ChannelTarget.ROTATION,
                    duration * 0.45,
                    _unit_axis_quat(0.36 * a, axis="x"),
                )
            else:
                clip.add_keyframe(
                    weapon_name,
                    ChannelTarget.ROTATION,
                    duration * 0.2,
                    _unit_axis_quat(-0.30 * a * swing_direction, axis="y"),
                )
                clip.add_keyframe(
                    weapon_name,
                    ChannelTarget.ROTATION,
                    duration * 0.45,
                    _unit_axis_quat(0.33 * a * swing_direction, axis="y"),
                )
            if impact_hold:
                if overhead:
                    clip.add_keyframe(
                        weapon_name,
                        ChannelTarget.ROTATION,
                        duration * 0.55,
                        _unit_axis_quat(0.32 * a, axis="x"),
                    )
                else:
                    clip.add_keyframe(
                        weapon_name,
                        ChannelTarget.ROTATION,
                        duration * 0.55,
                        _unit_axis_quat(0.30 * a * swing_direction, axis="y"),
                    )
            clip.add_keyframe(weapon_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])

            if hand_name is not None:
                clip.add_keyframe(hand_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(
                    hand_name,
                    ChannelTarget.ROTATION,
                    duration * 0.2,
                    _unit_axis_quat(-0.12 * a * swing_direction, axis="y"),
                )
                clip.add_keyframe(
                    hand_name,
                    ChannelTarget.ROTATION,
                    duration * 0.45,
                    _unit_axis_quat(0.14 * a * swing_direction, axis="y"),
                )
                clip.add_keyframe(hand_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])

        clip = AnimationClip(motion_type, fps=self.sample_rate, loop=True)
        # Clamp to avoid divide-by-zero / near-zero step durations.
        cadence_scale = max(float(kwargs.get("cadence_scale", 1.0)), 1e-3)
        amplitude_scale = float(kwargs.get("amplitude_scale", 1.0))

        # Generate simple procedural keyframes based on motion type
        if motion_type == "idle":
            # Slight breathing motion on spine
            if skeleton and len(skeleton.bones) > 1:
                spine_name = skeleton.bones[1].name
                breathe_rotation = _unit_axis_quat(0.02 * amplitude_scale, axis="y")
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(
                    spine_name,
                    ChannelTarget.ROTATION,
                    duration / (2 * cadence_scale),
                    breathe_rotation,
                )
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])

        elif motion_type == "walk":
            # Eight-count stride cycle: hip sway, forward root translation,
            # counter-rotating shoulders for FF-style characterful locomotion.
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                spine_name = skeleton.bones[1].name if len(skeleton.bones) > 1 else root_name
                shoulder_name = skeleton.bones[2].name if len(skeleton.bones) > 2 else spine_name
                half = duration / (2 * cadence_scale)
                # Root: vertical bob (heel-strike compression) over full cycle.
                for i in range(5):
                    t = min(i * half * 0.5, duration)
                    y_bob = (0.04 if i % 2 == 0 else -0.04) * amplitude_scale
                    clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, t, [0.0, y_bob, 0.0])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0.0, 0.04 * amplitude_scale, 0.0])
                # Spine: lateral sway — rocks left/right opposite to foot contact.
                sway = 0.06 * amplitude_scale
                clip.add_keyframe(spine_name, ChannelTarget.TRANSLATION, 0.0, [-sway, 0.0, 0.0])
                clip.add_keyframe(spine_name, ChannelTarget.TRANSLATION, half, [sway, 0.0, 0.0])
                clip.add_keyframe(spine_name, ChannelTarget.TRANSLATION, duration, [-sway, 0.0, 0.0])
                # Shoulders: counter-rotate against pelvis sway (FF-style arm swing).
                arm_rot = 0.08 * amplitude_scale
                clip.add_keyframe(shoulder_name, ChannelTarget.ROTATION, 0.0, _unit_axis_quat(-arm_rot, axis="z"))
                clip.add_keyframe(shoulder_name, ChannelTarget.ROTATION, half, _unit_axis_quat(arm_rot, axis="z"))
                clip.add_keyframe(shoulder_name, ChannelTarget.ROTATION, duration, _unit_axis_quat(-arm_rot, axis="z"))

        elif motion_type == "run":
            # Tighter four-count stride with stronger vertical drive and
            # exaggerated arm swing for readable PS2-era run silhouette.
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                spine_name = skeleton.bones[1].name if len(skeleton.bones) > 1 else root_name
                shoulder_name = skeleton.bones[2].name if len(skeleton.bones) > 2 else spine_name
                quarter = duration / (4 * cadence_scale)
                # Root: strong vertical drive on each stride.
                for i in range(5):
                    t = min(i * quarter, duration)
                    y_drive = (0.10 if i % 2 == 0 else -0.05) * amplitude_scale
                    clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, t, [0.0, y_drive, 0.0])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0.0, 0.10 * amplitude_scale, 0.0])
                # Spine: forward lean during run.
                lean = 0.12 * amplitude_scale
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, _unit_axis_quat(lean, axis="x"))
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, _unit_axis_quat(lean, axis="x"))
                # Shoulders: exaggerated counter-swing.
                arm_rot = 0.15 * amplitude_scale
                half = duration * 0.5
                clip.add_keyframe(shoulder_name, ChannelTarget.ROTATION, 0.0, _unit_axis_quat(-arm_rot, axis="z"))
                clip.add_keyframe(shoulder_name, ChannelTarget.ROTATION, half, _unit_axis_quat(arm_rot, axis="z"))
                clip.add_keyframe(shoulder_name, ChannelTarget.ROTATION, duration, _unit_axis_quat(-arm_rot, axis="z"))

        elif motion_type == "attack":
            # Five-phase staged combat: rest → anticipate → strike → impact → recover.
            # Spine and root channels give a clear silhouette change at each phase.
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                spine_name = skeleton.bones[1].name if len(skeleton.bones) > 1 else root_name
                a = amplitude_scale
                # Root: weight-shift into strike then snap back.
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0.0, 0.0, 0.0])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.2, [0.0, 0.0, -0.05 * a])   # anticipate
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.45, [0.0, 0.0, 0.30 * a])   # strike
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.55, [0.0, 0.0, 0.28 * a])   # impact held
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0.0, 0.0, 0.0])               # recover
                # Spine: rotation arc through swing.
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration * 0.2, _unit_axis_quat(-0.08 * a, axis="y"))  # coil
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration * 0.45, _unit_axis_quat(0.18 * a, axis="y"))  # uncoil
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration * 0.55, _unit_axis_quat(0.15 * a, axis="y"))  # held
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])
                _apply_sword_attack_pose(swing_direction=1.0)

        elif motion_type == "defend":
            if skeleton and len(skeleton.bones) > 1:
                spine_name = skeleton.bones[1].name
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(
                    spine_name,
                    ChannelTarget.ROTATION,
                    duration * 0.35,
                    _unit_axis_quat(0.03 * amplitude_scale, axis="x"),
                )
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])

        elif motion_type == "cast":
            # Five-phase cast: rest → raise arms → channel → release → settle.
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                spine_name = skeleton.bones[1].name if len(skeleton.bones) > 1 else root_name
                a = amplitude_scale
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0.0, 0.0, 0.0])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.25, [0.0, 0.04 * a, -0.04 * a])  # arms raise
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.55, [0.0, 0.06 * a, -0.08 * a])  # channel held
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.65, [0.0, 0.02 * a, 0.05 * a])   # release lurch
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0.0, 0.0, 0.0])
                # Spine arches back during channel, then snaps forward on release.
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration * 0.25, _unit_axis_quat(-0.06 * a, axis="x"))
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration * 0.55, _unit_axis_quat(-0.09 * a, axis="x"))
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration * 0.65, _unit_axis_quat(0.08 * a, axis="x"))
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])

        elif motion_type == "hit_react":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.2,
                    [0, 0, -0.12 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "dodge":
            # Five-phase dodge: brace → crouch dip → burst → air → land.
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                spine_name = skeleton.bones[1].name if len(skeleton.bones) > 1 else root_name
                a = amplitude_scale
                # Root: quick lateral displacement burst then recovery.
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0.0, 0.0, 0.0])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.1, [0.02 * a, -0.04 * a, 0.0])  # brace dip
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.35, [0.30 * a, 0.02 * a, 0.0])  # burst peak
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.75, [0.35 * a, 0.0, 0.0])        # glide
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0.30 * a, 0.0, 0.0])               # land settle
                # Spine: lean into dodge direction.
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration * 0.35, _unit_axis_quat(0.12 * a, axis="z"))
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])

        elif motion_type == "jump_start":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [0, 0.25 * amplitude_scale, 0.08 * amplitude_scale],
                )

        elif motion_type == "jump_loop":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                peak = 0.3 * amplitude_scale
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, peak, 0])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.5, [0, peak, 0])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, peak, 0])

        elif motion_type == "jump_land":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    0.0,
                    [0, 0.2 * amplitude_scale, 0],
                )
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.4,
                    [0, -0.08 * amplitude_scale, 0],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "victory":
            if skeleton and len(skeleton.bones) > 1:
                spine_name = skeleton.bones[1].name
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(
                    spine_name,
                    ChannelTarget.ROTATION,
                    duration * 0.5,
                    _unit_axis_quat(0.08 * amplitude_scale, axis="y"),
                )
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])

        elif motion_type in {"turn_left", "turn_right"}:
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                direction = 1.0 if motion_type == "turn_left" else -1.0
                clip.add_keyframe(root_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.ROTATION,
                    duration,
                    _unit_axis_quat(direction * 0.15 * amplitude_scale, axis="y"),
                )

        elif motion_type == "crouch":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.5,
                    [0, -0.12 * amplitude_scale, 0],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        # --- New motions added in expanded taxonomy ---

        elif motion_type == "idle_alt":
            # Alternate idle with a subtle weight-shift
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.4,
                    [0.04 * amplitude_scale, 0, 0],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "idle_combat":
            # Combat-ready idle — slight forward lean
            if skeleton and len(skeleton.bones) > 1:
                spine_name = skeleton.bones[1].name
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(
                    spine_name,
                    ChannelTarget.ROTATION,
                    duration * 0.5,
                    _unit_axis_quat(0.04 * amplitude_scale, axis="x"),
                )
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])

        elif motion_type == "run_start":
            # Lean into run
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [0, 0, 0.12 * amplitude_scale],
                )

        elif motion_type == "run_stop":
            # Deceleration skid
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    0.0,
                    [0, 0, 0.1 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "sprint":
            # High-frequency run cycle
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                step_duration = duration / (8 * cadence_scale)
                for i in range(9):
                    t = i * step_duration
                    if t >= duration:
                        break
                    y_offset = (0.18 if i % 2 == 0 else -0.18) * amplitude_scale
                    clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, t, [0, y_offset, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [0, 0.18 * amplitude_scale, 0],
                )

        elif motion_type == "strafe_left":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                step_duration = duration / (4 * cadence_scale)
                for i in range(5):
                    t = i * step_duration
                    if t >= duration:
                        break
                    z_offset = (0.08 if i % 2 == 0 else -0.08) * amplitude_scale
                    clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, t, [-0.1, z_offset, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [-0.1, 0.08 * amplitude_scale, 0],
                )

        elif motion_type == "strafe_right":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                step_duration = duration / (4 * cadence_scale)
                for i in range(5):
                    t = i * step_duration
                    if t >= duration:
                        break
                    z_offset = (0.08 if i % 2 == 0 else -0.08) * amplitude_scale
                    clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, t, [0.1, z_offset, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [0.1, 0.08 * amplitude_scale, 0],
                )

        elif motion_type == "crouch_walk":
            # Low gait — seamless loop in crouched position
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                base_y = -0.1 * amplitude_scale
                sway = 0.04 * amplitude_scale
                step_duration = duration / (4 * cadence_scale)
                for i in range(5):
                    t = i * step_duration
                    if t >= duration:
                        break
                    y_offset = base_y + (sway if i % 2 == 0 else -sway)
                    clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, t, [0, y_offset, 0])
                # Return to the same value as frame 0 to guarantee a seamless loop.
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [0, base_y + sway, 0],
                )

        elif motion_type == "roll":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.5,
                    [0.15 * amplitude_scale, -0.05 * amplitude_scale, 0.15 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "vault":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.5,
                    [0, 0.3 * amplitude_scale, 0.2 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "climb_start":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [0, 0.18 * amplitude_scale, -0.05 * amplitude_scale],
                )

        elif motion_type == "climb_loop":
            # Arm-reach cycle while climbing — seamless positional loop.
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                base_y = 0.15 * amplitude_scale
                sway = 0.04 * amplitude_scale
                step_duration = duration / (4 * cadence_scale)
                for i in range(5):
                    t = i * step_duration
                    if t >= duration:
                        break
                    y_offset = base_y + (sway if i % 2 == 0 else -sway)
                    clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, t, [0, y_offset, 0])
                # Return to start value to guarantee a seamless loop.
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [0, base_y + sway, 0],
                )

        elif motion_type == "climb_stop":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    0.0,
                    [0, 0.15 * amplitude_scale, 0],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "attack_combo_1":
            # Combo step 1: left-to-right horizontal swing with spine coil.
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                spine_name = skeleton.bones[1].name if len(skeleton.bones) > 1 else root_name
                a = amplitude_scale
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0.0, 0.0, 0.0])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.2, [-0.05 * a, 0.0, -0.04 * a])  # wind-up
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.45, [-0.10 * a, 0.0, 0.22 * a]) # strike
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.55, [-0.10 * a, 0.0, 0.20 * a]) # impact held
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0.0, 0.0, 0.0])
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration * 0.2, _unit_axis_quat(-0.12 * a, axis="y"))
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration * 0.45, _unit_axis_quat(0.14 * a, axis="y"))
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])
                _apply_sword_attack_pose(swing_direction=1.0)

        elif motion_type == "attack_combo_2":
            # Combo step 2: right-to-left counter-swing continuation.
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                spine_name = skeleton.bones[1].name if len(skeleton.bones) > 1 else root_name
                a = amplitude_scale
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0.0, 0.0, 0.0])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.2, [0.05 * a, 0.0, -0.04 * a])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.45, [0.10 * a, 0.0, 0.22 * a])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.55, [0.10 * a, 0.0, 0.20 * a])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0.0, 0.0, 0.0])
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration * 0.2, _unit_axis_quat(0.12 * a, axis="y"))
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration * 0.45, _unit_axis_quat(-0.14 * a, axis="y"))
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])
                _apply_sword_attack_pose(swing_direction=-1.0)

        elif motion_type == "attack_combo_3":
            # Finisher — overhead lunge with dramatic follow-through.
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                spine_name = skeleton.bones[1].name if len(skeleton.bones) > 1 else root_name
                a = amplitude_scale
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0.0, 0.0, 0.0])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.15, [0.0, 0.08 * a, -0.06 * a])   # raise
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.45, [0.0, -0.02 * a, 0.38 * a])   # slam
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.55, [0.0, -0.04 * a, 0.36 * a])   # impact held
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0.0, 0.0, 0.0])
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration * 0.15, _unit_axis_quat(-0.18 * a, axis="x"))
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration * 0.45, _unit_axis_quat(0.20 * a, axis="x"))
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])
                _apply_sword_attack_pose(overhead=True)

        elif motion_type == "heavy_attack":
            # Slow powerful two-handed strike: coil → raise → slam → recovery.
            if skeleton and len(skeleton.bones) > 1:
                root_name = skeleton.bones[0].name
                spine_name = skeleton.bones[1].name
                a = amplitude_scale
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0.0, 0.0, 0.0])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.25, [0.0, 0.06 * a, -0.08 * a])   # coil back
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.5, [0.0, 0.02 * a, 0.40 * a])     # slam
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.6, [0.0, -0.06 * a, 0.38 * a])    # impact
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0.0, 0.0, 0.0])
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration * 0.25, _unit_axis_quat(-0.22 * a, axis="x"))  # raise
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration * 0.5, _unit_axis_quat(0.25 * a, axis="x"))   # slam
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration * 0.6, _unit_axis_quat(0.22 * a, axis="x"))   # held
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])
                _apply_sword_attack_pose(overhead=True)

        elif motion_type == "aerial_attack":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    0.0,
                    [0, 0.2 * amplitude_scale, 0],
                )
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.4,
                    [0, 0.1 * amplitude_scale, 0.25 * amplitude_scale],
                )
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [0, 0.2 * amplitude_scale, 0],
                )
                _apply_sword_attack_pose(swing_direction=1.0, impact_hold=False)

        elif motion_type == "cast_channel":
            if skeleton and len(skeleton.bones) > 1:
                spine_name = skeleton.bones[1].name
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(
                    spine_name,
                    ChannelTarget.ROTATION,
                    duration * 0.5,
                    _unit_axis_quat(0.06 * amplitude_scale, axis="z"),
                )
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])

        elif motion_type == "cast_release":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.3,
                    [0, 0.1 * amplitude_scale, -0.15 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "block":
            if skeleton and len(skeleton.bones) > 1:
                spine_name = skeleton.bones[1].name
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(
                    spine_name,
                    ChannelTarget.ROTATION,
                    duration * 0.4,
                    _unit_axis_quat(0.05 * amplitude_scale, axis="x"),
                )
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])

        elif motion_type == "parry":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.25,
                    [0, 0, -0.08 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "stagger":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.15,
                    [0.06 * amplitude_scale, 0, -0.08 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "knockdown":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.6,
                    [0, -0.35 * amplitude_scale, -0.1 * amplitude_scale],
                )
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [0, -0.35 * amplitude_scale, -0.1 * amplitude_scale],
                )

        elif motion_type == "get_up":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    0.0,
                    [0, -0.35 * amplitude_scale, -0.1 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "death":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.7,
                    [0, -0.4 * amplitude_scale, 0.05 * amplitude_scale],
                )
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [0, -0.4 * amplitude_scale, 0.05 * amplitude_scale],
                )

        elif motion_type == "interact":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.5,
                    [0, 0, 0.15 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "pickup":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.5,
                    [0, -0.18 * amplitude_scale, 0.08 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        # --- New motions for expanded taxonomy ---

        elif motion_type == "sprint_start":
            # Quick weight-shift lunge into sprint
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [0, 0.05 * amplitude_scale, 0.18 * amplitude_scale],
                )

        elif motion_type == "sprint_stop":
            # Foot-plant deceleration
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    0.0,
                    [0, 0.05 * amplitude_scale, 0.18 * amplitude_scale],
                )
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.5,
                    [0, -0.04 * amplitude_scale, 0.06 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "backstep":
            # Quick defensive step backward
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.4,
                    [0, 0.03 * amplitude_scale, -0.2 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "guard_walk":
            # Slow walking gait while maintaining block pose
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                step_duration = duration / (4 * cadence_scale)
                for i in range(5):
                    t = i * step_duration
                    if t >= duration:
                        break
                    y_offset = (0.06 if i % 2 == 0 else -0.06) * amplitude_scale
                    clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, t, [0, y_offset, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [0, 0.06 * amplitude_scale, 0],
                )

        elif motion_type == "land_hard":
            # Heavy impact landing with compression
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    0.0,
                    [0, 0.15 * amplitude_scale, 0],
                )
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.2,
                    [0, -0.14 * amplitude_scale, 0],
                )
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.5,
                    [0, -0.06 * amplitude_scale, 0],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "land_roll":
            # Momentum absorbed into a forward roll
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    0.0,
                    [0, 0.12 * amplitude_scale, 0],
                )
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.35,
                    [0, -0.05 * amplitude_scale, 0.2 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "ladder_up":
            # Repeating reach-and-step cycle for ascending a ladder
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                step_h = 0.15 * amplitude_scale
                step_duration = duration / (4 * cadence_scale)
                for i in range(5):
                    t = i * step_duration
                    if t >= duration:
                        break
                    sway = (0.04 if i % 2 == 0 else -0.04) * amplitude_scale
                    clip.add_keyframe(
                        root_name, ChannelTarget.TRANSLATION, t, [sway, i * step_h, 0]
                    )
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [0.04 * amplitude_scale, 4 * step_h, 0],
                )

        elif motion_type == "ladder_down":
            # Descending ladder loop
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                step_h = 0.15 * amplitude_scale
                step_duration = duration / (4 * cadence_scale)
                for i in range(5):
                    t = i * step_duration
                    if t >= duration:
                        break
                    sway = (0.04 if i % 2 == 0 else -0.04) * amplitude_scale
                    drop = i * step_h
                    clip.add_keyframe(
                        root_name, ChannelTarget.TRANSLATION, t, [sway, -drop, 0]
                    )
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [0.04 * amplitude_scale, -4 * step_h, 0],
                )

        elif motion_type == "swim_idle":
            # Buoyant treading-water loop
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                bob = 0.04 * amplitude_scale
                step_duration = duration / (2 * cadence_scale)
                for i in range(3):
                    t = i * step_duration
                    if t >= duration:
                        break
                    y = bob if i % 2 == 0 else -bob
                    clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, t, [0, y, 0])
                clip.add_keyframe(
                    root_name, ChannelTarget.TRANSLATION, duration, [0, bob, 0]
                )

        elif motion_type == "swim_forward":
            # Swimming stroke cycle with forward propulsion bob
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                step_duration = duration / (4 * cadence_scale)
                for i in range(5):
                    t = i * step_duration
                    if t >= duration:
                        break
                    y = (0.05 if i % 2 == 0 else -0.05) * amplitude_scale
                    clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, t, [0, y, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [0, 0.05 * amplitude_scale, 0],
                )

        elif motion_type == "swim_surface":
            # Breaking surface after underwater segment
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    0.0,
                    [0, -0.15 * amplitude_scale, 0],
                )
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.4,
                    [0, 0.1 * amplitude_scale, 0.08 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "knockdown_air":
            # Character launched airborne and falls
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.3,
                    [0.1 * amplitude_scale, 0.3 * amplitude_scale, -0.15 * amplitude_scale],
                )
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [0.1 * amplitude_scale, -0.35 * amplitude_scale, -0.1 * amplitude_scale],
                )

        elif motion_type == "block_break":
            # Guard shattered — recoil then recover
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.15,
                    [-0.1 * amplitude_scale, -0.05 * amplitude_scale, -0.12 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "emote_cheer":
            # Arms-up cheer gesture for cutscenes
            if skeleton and len(skeleton.bones) > 1:
                spine_name = skeleton.bones[1].name
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(
                    spine_name,
                    ChannelTarget.ROTATION,
                    duration * 0.35,
                    _unit_axis_quat(-0.05 * amplitude_scale, axis="x"),
                )
                clip.add_keyframe(
                    spine_name,
                    ChannelTarget.ROTATION,
                    duration * 0.65,
                    _unit_axis_quat(-0.05 * amplitude_scale, axis="x"),
                )
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])

        # keep deterministic fallback for unknown motion identifiers
        if not clip.channels and skeleton and len(skeleton.bones) > 0:
            root_name = skeleton.bones[0].name
            clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
            clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        return clip


class BackendRegistry:
    """Registry of available :class:`AnimationBackend` implementations.

    Example
    -------
    >>> BackendRegistry.register("ml_motion", MLMotionBackend)
    >>> backend = BackendRegistry.get("ml_motion", sample_rate=30.0)
    """

    _registry: dict[str, type[AnimationBackend]] = {
        "procedural": ProceduralBackend,
    }

    @classmethod
    def register(cls, name: str, backend_class: type[AnimationBackend]) -> None:
        """Register a new backend implementation.

        Parameters
        ----------
        name:
            Backend identifier (e.g. "ml_motion").
        backend_class:
            Class implementing AnimationBackend.
        """
        if not (isinstance(backend_class, type) and issubclass(backend_class, AnimationBackend)):
            raise TypeError(
                f"backend_class must be a subclass of AnimationBackend, got {backend_class!r}"
            )
        cls._registry[name] = backend_class

    @classmethod
    def get(cls, name: str = "procedural", **kwargs: Any) -> AnimationBackend:
        """Instantiate a backend by name.

        Parameters
        ----------
        name:
            Backend identifier.
        **kwargs:
            Passed to backend constructor.

        Returns
        -------
        AnimationBackend
        """
        if name not in cls._registry:
            available = ", ".join(sorted(cls._registry))
            raise ValueError(f"Unknown backend '{name}'. Available: {available}")
        return cls._registry[name](**kwargs)

    @classmethod
    def available_backends(cls) -> list[str]:
        """Return sorted list of registered backend names."""
        return sorted(cls._registry)
