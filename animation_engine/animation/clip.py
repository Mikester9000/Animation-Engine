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
    events      : Timeline event markers for gameplay synchronisation
                  (footstep, contact, hit, cancel, cast_release, etc.).
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
        self.motion_type: str = ""
        # Channels keyed by (bone_name, ChannelTarget)
        self._channels: Dict[Tuple[str, ChannelTarget], AnimationChannel] = {}
        # Event markers: list of {"name": str, "time": float, "data": dict}
        self._events: List[dict] = []

    # -- event management ----------------------------------------------------

    def add_event(self, name: str, time: float, data: dict | None = None) -> None:
        """Add a named timeline event at *time* seconds.

        Parameters
        ----------
        name:
            Event identifier (e.g. ``"footstep_left"``, ``"hit_window_open"``).
        time:
            Time in seconds at which the event fires.
        data:
            Optional dict of event-specific payload (e.g. ``{"foot": "left"}``).
        """
        self._events.append({"name": name, "time": float(time), "data": data or {}})

    def remove_event_at_index(self, index: int) -> None:
        """Remove the event at *index* (into the time-sorted event list)."""
        sorted_events = sorted(self._events, key=lambda e: e["time"])
        if 0 <= index < len(sorted_events):
            event_to_remove = sorted_events[index]
            for i, event in enumerate(self._events):
                if event is event_to_remove:
                    del self._events[i]
                    break

    def get_events(self, name: str | None = None) -> List[dict]:
        """Return all events, optionally filtered by *name*.

        Returns events sorted by time.
        """
        events = sorted(self._events, key=lambda e: e["time"])
        if name is not None:
            events = [e for e in events if e["name"] == name]
        return events

    def get_events_in_window(self, start: float, end: float) -> List[dict]:
        """Return events whose time satisfies start <= time < end, sorted by time."""
        return [e for e in self.get_events() if start <= e["time"] < end]

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

    def rename_bone_channels(self, old_bone_name: str, new_bone_name: str) -> int:
        """Rename all channels that reference *old_bone_name* to *new_bone_name*.

        Returns the number of channels updated.
        """
        if old_bone_name == new_bone_name:
            return 0
        keys_to_rename = [
            k for k in self._channels if k[0] == old_bone_name
        ]
        for key in keys_to_rename:
            new_key = (new_bone_name, key[1])
            if new_key in self._channels:
                existing = self._channels[new_key]
                source = self._channels[key]
                for kf in source.keyframes:
                    existing.add_keyframe(kf)
                del self._channels[key]
                continue
            ch = self._channels.pop(key)
            ch.bone_name = new_bone_name
            self._channels[new_key] = ch
        return len(keys_to_rename)

    def remove_bone_channels(self, bone_name: str) -> int:
        """Remove all animation channels for *bone_name*.

        Returns the number of channels removed.
        """
        keys_to_remove = [k for k in self._channels if k[0] == bone_name]
        for key in keys_to_remove:
            del self._channels[key]
        return len(keys_to_remove)

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "fps": self.fps,
            "loop": self.loop,
            "motion_type": self.motion_type,
            "channels": [ch.to_dict() for ch in self._channels.values()],
        }
        if self._events:
            d["events"] = list(self._events)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "AnimationClip":
        clip = cls(
            name=d.get("name", "Clip"),
            fps=d.get("fps", 30.0),
            loop=d.get("loop", True),
        )
        clip.motion_type = str(d.get("motion_type", "") or "")
        for ch_data in d.get("channels", []):
            ch = AnimationChannel.from_dict(ch_data)
            clip._channels[(ch.bone_name, ch.target)] = ch
        for ev in d.get("events", []):
            if isinstance(ev, dict) and "name" in ev and "time" in ev:
                clip.add_event(ev["name"], float(ev["time"]), ev.get("data") or {})
        return clip

    def __repr__(self) -> str:
        return (
            f"AnimationClip({self.name!r}, "
            f"duration={self.duration:.2f}s, "
            f"channels={len(self._channels)})"
        )


# ---------------------------------------------------------------------------
# Retargeting utility
# ---------------------------------------------------------------------------

def retarget_clip(
    clip: "AnimationClip",
    source_skel: object,
    target_skel: object,
    bone_map: Dict[str, str],
) -> "AnimationClip":
    """Return a new AnimationClip retargeted from *source_skel* to *target_skel*.

    Bone names are remapped using *bone_map* (``{source_name: target_name}``).
    Translation channels are scaled by the ratio of target-to-source bone
    chain lengths so proportions match the target skeleton.  Rotation channels
    are copied unchanged, preserving pose intent across skeleton variants.

    Parameters
    ----------
    clip:
        Source animation clip (authored for *source_skel*).
    source_skel:
        Source skeleton (``animation_engine.model.skeleton.Skeleton``).
    target_skel:
        Destination skeleton.  Must contain all bones referenced by the
        *bone_map* target values.
    bone_map:
        Dict mapping source bone names to target bone names.  Bones not
        present in *bone_map* are dropped from the output clip.

    Returns
    -------
    A new :class:`AnimationClip` with remapped channels.
    """
    from copy import deepcopy
    from .channel import AnimationChannel, ChannelTarget
    from .keyframe import Keyframe

    # Build a lookup dict once to avoid O(n) scan per channel.
    def _build_bone_lookup(skel) -> dict:
        if hasattr(skel, "get_bone"):
            return {}  # get_bone handles lookup directly.
        return {b.name: b for b in getattr(skel, "bones", [])}

    src_lookup = _build_bone_lookup(source_skel)
    tgt_lookup = _build_bone_lookup(target_skel)

    def _bone_length(skel, lookup: dict, name: str) -> float:
        """Return the bind-pose distance from a bone to its parent (its 'length')."""
        bone = skel.get_bone(name) if hasattr(skel, "get_bone") else lookup.get(name)
        if bone is None:
            return 1.0
        pos = bone.local_transform.position
        return max(1e-6, (pos.x ** 2 + pos.y ** 2 + pos.z ** 2) ** 0.5)

    new_clip = AnimationClip(
        name=f"{clip.name}_retargeted",
        fps=clip.fps,
        loop=clip.loop,
    )

    for (bone_name, target), ch in clip._channels.items():
        mapped_name = bone_map.get(bone_name)
        if mapped_name is None:
            continue

        new_ch = AnimationChannel(mapped_name, target)
        if target == ChannelTarget.TRANSLATION:
            src_len = _bone_length(source_skel, src_lookup, bone_name)
            tgt_len = _bone_length(target_skel, tgt_lookup, mapped_name)
            scale = tgt_len / src_len
            for kf in ch.keyframes:
                scaled_value = [v * scale for v in kf.value]
                scaled_in_tangent = (
                    [v * scale for v in kf.in_tangent]
                    if isinstance(kf.in_tangent, list)
                    else kf.in_tangent * scale
                )
                scaled_out_tangent = (
                    [v * scale for v in kf.out_tangent]
                    if isinstance(kf.out_tangent, list)
                    else kf.out_tangent * scale
                )
                new_ch.add_keyframe(
                    Keyframe(
                        time=kf.time,
                        value=scaled_value,
                        in_tangent=scaled_in_tangent,
                        out_tangent=scaled_out_tangent,
                        interp=kf.interp,
                    )
                )
        else:
            for kf in ch.keyframes:
                new_ch.add_keyframe(
                    Keyframe(
                        time=kf.time,
                        value=deepcopy(kf.value),
                        in_tangent=deepcopy(kf.in_tangent),
                        out_tangent=deepcopy(kf.out_tangent),
                        interp=kf.interp,
                    )
                )
        new_clip._channels[(mapped_name, target)] = new_ch

    for ev in clip._events:
        new_clip.add_event(ev["name"], ev["time"], dict(ev.get("data") or {}))

    return new_clip
