"""
Loop analyzer – detect animation loop boundary discontinuities.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

__all__ = ["LoopAnalyzer", "LoopReport"]


@dataclass
class LoopReport:
    """Loop analysis result.

    Attributes
    ----------
    clip_name:
        Name of the analyzed clip.
    is_seamless:
        True if loop is seamless within thresholds.
    max_position_jump:
        Maximum position discontinuity in world units.
    max_rotation_jump_deg:
        Maximum rotation discontinuity in degrees.
    """

    clip_name: str
    is_seamless: bool
    max_position_jump: float
    max_rotation_jump_deg: float

    def summary(self) -> str:
        """Return a human-readable one-line summary."""
        status = "SEAMLESS" if self.is_seamless else "DISCONTINUOUS"
        return (
            f"{status} – pos_jump={self.max_position_jump:.4f}, "
            f"rot_jump={self.max_rotation_jump_deg:.2f}°"
        )


class LoopAnalyzer:
    """Analyze animation clips for loop discontinuities.

    Parameters
    ----------
    position_threshold:
        Maximum acceptable position jump in world units.
    rotation_threshold_deg:
        Maximum acceptable rotation jump in degrees.
    """

    def __init__(
        self,
        position_threshold: float = 0.01,
        rotation_threshold_deg: float = 5.0,
    ) -> None:
        self.position_threshold = position_threshold
        self.rotation_threshold_deg = rotation_threshold_deg

    def analyze_clip(self, clip: Any) -> LoopReport:
        """Analyze an AnimationClip for loop quality.

        Parameters
        ----------
        clip:
            AnimationClip to analyze.

        Returns
        -------
        LoopReport
        """
        max_pos_jump = 0.0
        max_rot_jump_deg = 0.0

        for channel in clip.channels:
            if len(channel.keyframes) < 2:
                continue

            first_kf = channel.keyframes[0]
            last_kf = channel.keyframes[-1]
            target_name = getattr(channel.target, "name", str(channel.target))

            if target_name == "TRANSLATION":
                # Check position jump
                position_diff = [
                    (last_val - first_val)
                    for first_val, last_val in zip(first_kf.value[:3], last_kf.value[:3])
                ]
                jump = math.sqrt(sum(delta**2 for delta in position_diff))
                max_pos_jump = max(max_pos_jump, jump)

            elif target_name == "ROTATION":
                # Check quaternion angular difference
                q1 = first_kf.value
                q2 = last_kf.value
                dot = sum(
                    q1_component * q2_component
                    for q1_component, q2_component in zip(q1, q2)
                )
                # Handle quaternion double-cover: q and -q represent same rotation
                dot = abs(dot)
                # Clamp to avoid numerical errors in acos
                dot = max(-1.0, min(1.0, dot))
                angle_rad = 2 * math.acos(dot)
                angle_deg = math.degrees(angle_rad)
                max_rot_jump_deg = max(max_rot_jump_deg, angle_deg)

        is_seamless = (
            max_pos_jump <= self.position_threshold
            and max_rot_jump_deg <= self.rotation_threshold_deg
        )

        return LoopReport(clip.name, is_seamless, max_pos_jump, max_rot_jump_deg)
