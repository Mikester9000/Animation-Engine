"""
animation_engine.animation.clip
==================================
AnimationClip — a named, time-bounded collection of AnimationChannels.

A clip corresponds to one "animation" in the artist tool: "walk_cycle",
"run_forward", "idle_breathe", etc.  It is the unit of asset that is exported,
imported, and referenced by the BlendTree.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ..math_utils import Transform, Vector3, Quaternion
from .channel import AnimationChannel, ChannelTarget
from .keyframe import Keyframe, KeyframeType


class AnimationClip:
    """
    A named collection of animation channels forming one complete animation.

    Attributes
    ----------
    name        : Human-readable name (e.g. "run_cycle").
    fps         : Original authoring frame rate (informational only).
    loop        : Whether the clip should loop seamlessly.
    """

    def __init__(
        self,
        name: str = "Clip",
        fps: float = 30.0,
        loop: bool = True,
    ) -> None:
        self.name: str = name
        self.fps: float = fps
        self.loop: bool = loop
        # Channels keyed by (bone_name, ChannelTarget)
        self._channels: Dict[Tuple[str, ChannelTarget], AnimationChannel] = {}

    # -- channel management --------------------------------------------------

    def get_channel(
        self, bone_name: str, target: ChannelTarget
    ) -> Optional[AnimationChannel]:
        """Return the channel for a bone/target pair, or None."""
        return self._channels.get((bone_name, target))

    def get_or_create_channel(
        self, bone_name: str, target: ChannelTarget
    ) -> AnimationChannel:
        """Return the channel, creating it if it does not yet exist."""
        key = (bone_name, target)
        if key not in self._channels:
            self._channels[key] = AnimationChannel(bone_name, target)
        return self._channels[key]

    def add_keyframe(
        self,
        bone_name: str,
        target: ChannelTarget,
        time: float,
        value,
        interp: KeyframeType = KeyframeType.LINEAR,
        in_tangent=0.0,
        out_tangent=0.0,
    ) -> None:
        """
        Convenience method: add a single keyframe to a channel.

        Example
        -------
        >>> clip.add_keyframe("spine_01", ChannelTarget.ROTATION, 0.0,
        ...                   [0, 0, 0, 1], KeyframeType.CUBIC)
        """
        channel = self.get_or_create_channel(bone_name, target)
        channel.add_keyframe(
            Keyframe(
                time=time,
                value=value,
                in_tangent=in_tangent,
                out_tangent=out_tangent,
                interp=interp,
            )
        )

    @property
    def channels(self) -> List[AnimationChannel]:
        return list(self._channels.values())

    # -- evaluation ----------------------------------------------------------

    @property
    def duration(self) -> float:
        """Duration of the clip in seconds (longest channel)."""
        if not self._channels:
            return 0.0
        return max(ch.duration for ch in self._channels.values())

    def evaluate_bone(self, bone_name: str, time: float) -> Transform:
        """
        Evaluate all channels for *bone_name* at *time* and return the
        resulting local Transform.

        Channels that are not present fall back to the identity transform so
        a partial animation clip can safely override only a subset of bones.
        """
        t_ch = self.get_channel(bone_name, ChannelTarget.TRANSLATION)
        r_ch = self.get_channel(bone_name, ChannelTarget.ROTATION)
        s_ch = self.get_channel(bone_name, ChannelTarget.SCALE)

        # Apply loop wrapping when clip is marked looping
        sample_time = time
        dur = self.duration
        if self.loop and dur > 1e-6:
            sample_time = time % dur

        translation = (
            Vector3.from_list(t_ch.evaluate(sample_time))
            if t_ch
            else Vector3.zero()
        )
        rotation = (
            Quaternion.from_list(r_ch.evaluate(sample_time))
            if r_ch
            else Quaternion.identity()
        )
        scale = (
            Vector3.from_list(s_ch.evaluate(sample_time))
            if s_ch
            else Vector3.one()
        )
        return Transform(translation, rotation, scale)

    def evaluate_all_bones(
        self, bone_names: List[str], time: float
    ) -> Dict[str, Transform]:
        """Return a dict of per-bone Transforms for all bones in *bone_names*."""
        return {name: self.evaluate_bone(name, time) for name in bone_names}

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "fps": self.fps,
            "loop": self.loop,
            "channels": [ch.to_dict() for ch in self._channels.values()],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "AnimationClip":
        clip = cls(
            name=d.get("name", "Clip"),
            fps=d.get("fps", 30.0),
            loop=d.get("loop", True),
        )
        for ch_data in d.get("channels", []):
            ch = AnimationChannel.from_dict(ch_data)
            clip._channels[(ch.bone_name, ch.target)] = ch
        return clip

    def __repr__(self) -> str:
        return (
            f"AnimationClip({self.name!r}, "
            f"duration={self.duration:.2f}s, "
            f"channels={len(self._channels)})"
        )
