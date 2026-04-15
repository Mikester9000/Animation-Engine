"""
animation_engine.animation.morph_track
=========================================
MorphTrack — animates the weight of a MorphTarget over time.

Used for lip-sync, facial expressions, and secondary deformations.
FF15 uses dense morph-target animations exported from dedicated face-capture
tools; this module stores those animated weights in the standard keyframe format.
"""

from __future__ import annotations

import bisect
from typing import List

from .keyframe import Keyframe, KeyframeType, interpolate_keyframes


class MorphTrack:
    """
    A time-series of float weights driving one named MorphTarget.

    Attributes
    ----------
    morph_name  : Must match the MorphTarget.name on the target Mesh.
    keyframes   : Time-sorted Keyframe list (float values in [0, 1]).
    """

    def __init__(self, morph_name: str) -> None:
        self.morph_name: str = morph_name
        self.keyframes: List[Keyframe] = []

    def add_keyframe(self, time: float, weight: float,
                     interp: KeyframeType = KeyframeType.LINEAR) -> None:
        """Insert a weight keyframe, maintaining time order."""
        kf = Keyframe(time=time, value=float(weight), interp=interp)
        times = [k.time for k in self.keyframes]
        idx = bisect.bisect_left(times, time)
        if idx < len(self.keyframes) and abs(self.keyframes[idx].time - time) < 1e-7:
            self.keyframes[idx] = kf
        else:
            self.keyframes.insert(idx, kf)

    def evaluate(self, time: float) -> float:
        """Return the interpolated weight at *time*."""
        if not self.keyframes:
            return 0.0
        if time <= self.keyframes[0].time:
            return float(self.keyframes[0].value)
        if time >= self.keyframes[-1].time:
            return float(self.keyframes[-1].value)
        times = [k.time for k in self.keyframes]
        idx = bisect.bisect_right(times, time) - 1
        kf0 = self.keyframes[idx]
        kf1 = self.keyframes[idx + 1]
        return float(interpolate_keyframes(kf0, kf1, time))

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "morph_name": self.morph_name,
            "keyframes": [kf.to_dict() for kf in self.keyframes],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MorphTrack":
        track = cls(morph_name=d["morph_name"])
        for kf_data in d.get("keyframes", []):
            track.keyframes.append(Keyframe.from_dict(kf_data))
        return track

    def __repr__(self) -> str:
        return f"MorphTrack({self.morph_name!r}, {len(self.keyframes)} keyframes)"
