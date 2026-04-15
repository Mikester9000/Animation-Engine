"""
animation_engine.animation.channel
=====================================
AnimationChannel — a time-sorted list of keyframes for one animated property.

Each channel targets exactly one bone and one transform component
(translation, rotation, or scale).  This matches the glTF 2.0 animation
sampler / target layout and is the standard approach in AAA animation pipelines.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional

from .keyframe import Keyframe, KeyframeType, interpolate_keyframes


class ChannelTarget(Enum):
    """Which component of the bone transform this channel drives."""

    TRANSLATION = auto()  # Vector3 (x, y, z)
    ROTATION = auto()     # Quaternion (x, y, z, w)
    SCALE = auto()        # Vector3 (x, y, z)
    WEIGHT = auto()       # float  (morph-target weight)


class AnimationChannel:
    """
    A single animated curve (one bone × one transform component).

    Attributes
    ----------
    bone_name   : Name of the target bone in the Skeleton.
    target      : Which transform component is driven.
    keyframes   : Time-sorted list of Keyframe samples.
    """

    def __init__(
        self,
        bone_name: str,
        target: ChannelTarget = ChannelTarget.TRANSLATION,
    ) -> None:
        self.bone_name: str = bone_name
        self.target: ChannelTarget = target
        self.keyframes: List[Keyframe] = []

    # -- keyframe management -------------------------------------------------

    def add_keyframe(self, kf: Keyframe) -> None:
        """
        Insert a keyframe, maintaining time-sorted order.

        Using bisect keeps insertion O(log n) for typical clip lengths.
        """
        times = [k.time for k in self.keyframes]
        idx = bisect.bisect_left(times, kf.time)
        # Replace if a keyframe already exists at this exact time
        if idx < len(self.keyframes) and abs(self.keyframes[idx].time - kf.time) < 1e-7:
            self.keyframes[idx] = kf
        else:
            self.keyframes.insert(idx, kf)

    def remove_keyframe(self, time: float) -> bool:
        """Remove the keyframe closest to *time*. Return True if removed."""
        for i, kf in enumerate(self.keyframes):
            if abs(kf.time - time) < 1e-7:
                self.keyframes.pop(i)
                return True
        return False

    # -- evaluation ----------------------------------------------------------

    def evaluate(self, time: float):
        """
        Evaluate the channel at *time* and return the interpolated value.

        Returns the default bind-pose value if there are no keyframes.
        The returned type matches the channel target:
          TRANSLATION / SCALE → [x, y, z]
          ROTATION            → [x, y, z, w]
          WEIGHT              → float
        """
        if not self.keyframes:
            return _default_value(self.target)

        # Clamp to first / last keyframe
        if time <= self.keyframes[0].time:
            return self.keyframes[0].value
        if time >= self.keyframes[-1].time:
            return self.keyframes[-1].value

        # Binary search for surrounding keyframes
        times = [k.time for k in self.keyframes]
        idx = bisect.bisect_right(times, time) - 1
        kf0 = self.keyframes[idx]
        kf1 = self.keyframes[idx + 1]
        return interpolate_keyframes(kf0, kf1, time)

    @property
    def duration(self) -> float:
        """Duration of this channel in seconds."""
        if not self.keyframes:
            return 0.0
        return self.keyframes[-1].time - self.keyframes[0].time

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "bone_name": self.bone_name,
            "target": self.target.name,
            "keyframes": [kf.to_dict() for kf in self.keyframes],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AnimationChannel":
        ch = cls(
            bone_name=d["bone_name"],
            target=ChannelTarget[d["target"]],
        )
        for kf_data in d.get("keyframes", []):
            ch.keyframes.append(Keyframe.from_dict(kf_data))
        return ch

    def __repr__(self) -> str:
        return (
            f"AnimationChannel({self.bone_name!r}, "
            f"{self.target.name}, {len(self.keyframes)} keyframes)"
        )


def _default_value(target: ChannelTarget):
    """Return the identity value for a channel target (bind pose defaults)."""
    if target == ChannelTarget.TRANSLATION:
        return [0.0, 0.0, 0.0]
    if target == ChannelTarget.ROTATION:
        return [0.0, 0.0, 0.0, 1.0]
    if target == ChannelTarget.SCALE:
        return [1.0, 1.0, 1.0]
    return 0.0  # WEIGHT
