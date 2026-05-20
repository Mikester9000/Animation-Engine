"""
Animation clip validator – detect common animation errors.

Checks for:
- Denormalized quaternions
- Out-of-order keyframes
- Extreme translation/scale values
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

__all__ = ["ClipValidator", "ValidationReport"]


@dataclass
class ValidationReport:
    """Validation result for an animation clip.

    Attributes
    ----------
    clip_name:
        Name of the validated clip.
    is_valid:
        True if no errors were found.
    errors:
        List of error messages.
    warnings:
        List of warning messages.
    """

    clip_name: str
    is_valid: bool
    errors: list[str]
    warnings: list[str]

    def summary(self) -> str:
        """Return a human-readable one-line summary."""
        status = "VALID" if self.is_valid else "INVALID"
        return f"{status} – {len(self.errors)} errors, {len(self.warnings)} warnings"


class ClipValidator:
    """Validate animation clips for correctness.

    Parameters
    ----------
    epsilon:
        Tolerance for floating-point comparisons.
    """

    def __init__(self, epsilon: float = 1e-4) -> None:
        self.epsilon = epsilon

    def validate_clip(self, clip: Any) -> ValidationReport:
        """Validate an AnimationClip instance.

        Parameters
        ----------
        clip:
            AnimationClip to validate.

        Returns
        -------
        ValidationReport
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check each channel
        for channel in clip.channels:
            target_name = getattr(channel.target, "name", str(channel.target))

            # Validate keyframe time ordering
            times = [kf.time for kf in channel.keyframes]
            if times != sorted(times):
                errors.append(
                    f"Channel {channel.bone_name}/{target_name}: "
                    f"keyframes not time-sorted"
                )

            # Validate quaternion normalization (for rotation channels)
            if target_name == "ROTATION":
                for kf in channel.keyframes:
                    quat = kf.value
                    mag = math.sqrt(sum(x**2 for x in quat))
                    if abs(mag - 1.0) > self.epsilon:
                        errors.append(
                            f"Channel {channel.bone_name}/ROTATION time={kf.time:.3f}: "
                            f"quaternion not normalized (magnitude={mag:.6f})"
                        )

            # Check for extreme values
            if target_name == "TRANSLATION":
                for kf in channel.keyframes:
                    if any(abs(x) > 100.0 for x in kf.value[:3]):
                        warnings.append(
                            f"Channel {channel.bone_name}/TRANSLATION time={kf.time:.3f}: "
                            f"extreme position value {kf.value[:3]}"
                        )

            # Check for extreme scale
            if target_name == "SCALE":
                for kf in channel.keyframes:
                    if any(x < 0.01 or x > 100.0 for x in kf.value[:3]):
                        warnings.append(
                            f"Channel {channel.bone_name}/SCALE time={kf.time:.3f}: "
                            f"extreme scale value {kf.value[:3]}"
                        )

        is_valid = len(errors) == 0
        return ValidationReport(clip.name, is_valid, errors, warnings)
