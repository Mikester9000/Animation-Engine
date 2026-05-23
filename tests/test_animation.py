"""
tests/test_animation.py
========================
Unit tests for animation_engine.animation (Keyframe, Channel, Clip,
BlendTree, IKSolver, MorphTrack).
"""

import math
import pytest

from animation_engine.math_utils import Vector3, Quaternion, Transform
from animation_engine.animation import (
    KeyframeType, Keyframe,
    AnimationChannel, ChannelTarget,
    AnimationClip,
    BlendState, BlendTransition, BlendTree,
    IKChain, IKSolver,
    MorphTrack,
)
from animation_engine.animation.keyframe import interpolate_keyframes


# ---------------------------------------------------------------------------
# Keyframe interpolation
# ---------------------------------------------------------------------------

class TestKeyframeInterpolation:
    def test_step_returns_start_value(self):
        kf0 = Keyframe(0.0, 1.0, interp=KeyframeType.STEP)
        kf1 = Keyframe(1.0, 5.0, interp=KeyframeType.STEP)
        result = interpolate_keyframes(kf0, kf1, 0.5)
        assert result == pytest.approx(1.0)

    def test_linear_midpoint(self):
        kf0 = Keyframe(0.0, 0.0, interp=KeyframeType.LINEAR)
        kf1 = Keyframe(1.0, 10.0, interp=KeyframeType.LINEAR)
        result = interpolate_keyframes(kf0, kf1, 0.5)
        assert result == pytest.approx(5.0)

    def test_linear_vector(self):
        kf0 = Keyframe(0.0, [0.0, 0.0, 0.0], interp=KeyframeType.LINEAR)
        kf1 = Keyframe(1.0, [1.0, 2.0, 3.0], interp=KeyframeType.LINEAR)
        result = interpolate_keyframes(kf0, kf1, 0.5)
        assert result == pytest.approx([0.5, 1.0, 1.5])

    def test_cubic_endpoints(self):
        """Cubic spline should match the keyframe values at t=0 and t=1."""
        kf0 = Keyframe(0.0, 0.0, in_tangent=0.0, out_tangent=0.0, interp=KeyframeType.CUBIC)
        kf1 = Keyframe(1.0, 1.0, in_tangent=0.0, out_tangent=0.0, interp=KeyframeType.CUBIC)
        assert interpolate_keyframes(kf0, kf1, 0.0) == pytest.approx(0.0, abs=1e-5)
        assert interpolate_keyframes(kf0, kf1, 1.0) == pytest.approx(1.0, abs=1e-5)

    def test_serialise_roundtrip(self):
        kf = Keyframe(1.5, [0.1, 0.2, 0.3], interp=KeyframeType.CUBIC)
        d = kf.to_dict()
        kf2 = Keyframe.from_dict(d)
        assert kf2.time == pytest.approx(1.5)
        assert kf2.interp == KeyframeType.CUBIC


# ---------------------------------------------------------------------------
# AnimationChannel
# ---------------------------------------------------------------------------

class TestAnimationChannel:
    def _make_channel(self) -> AnimationChannel:
        ch = AnimationChannel("bone_a", ChannelTarget.TRANSLATION)
        ch.add_keyframe(Keyframe(0.0, [0.0, 0.0, 0.0]))
        ch.add_keyframe(Keyframe(1.0, [1.0, 0.0, 0.0]))
        ch.add_keyframe(Keyframe(2.0, [2.0, 0.0, 0.0]))
        return ch

    def test_evaluate_at_keyframe(self):
        ch = self._make_channel()
        result = ch.evaluate(1.0)
        assert result == pytest.approx([1.0, 0.0, 0.0])

    def test_evaluate_between_keyframes(self):
        ch = self._make_channel()
        result = ch.evaluate(0.5)
        assert result == pytest.approx([0.5, 0.0, 0.0])

    def test_evaluate_clamp_start(self):
        ch = self._make_channel()
        result = ch.evaluate(-5.0)
        assert result == pytest.approx([0.0, 0.0, 0.0])

    def test_evaluate_clamp_end(self):
        ch = self._make_channel()
        result = ch.evaluate(100.0)
        assert result == pytest.approx([2.0, 0.0, 0.0])

    def test_sorted_insertion(self):
        ch = AnimationChannel("b", ChannelTarget.SCALE)
        ch.add_keyframe(Keyframe(2.0, [2, 2, 2]))
        ch.add_keyframe(Keyframe(0.0, [0, 0, 0]))
        ch.add_keyframe(Keyframe(1.0, [1, 1, 1]))
        times = [kf.time for kf in ch.keyframes]
        assert times == sorted(times)

    def test_remove_keyframe(self):
        ch = self._make_channel()
        removed = ch.remove_keyframe(1.0)
        assert removed is True
        assert len(ch.keyframes) == 2

    def test_duration(self):
        ch = self._make_channel()
        assert ch.duration == pytest.approx(2.0)

    def test_serialise_roundtrip(self):
        ch = self._make_channel()
        d = ch.to_dict()
        ch2 = AnimationChannel.from_dict(d)
        assert ch2.bone_name == "bone_a"
        assert len(ch2.keyframes) == 3


# ---------------------------------------------------------------------------
# AnimationClip
# ---------------------------------------------------------------------------

class TestAnimationClip:
    def _make_clip(self) -> AnimationClip:
        clip = AnimationClip("walk", fps=30.0, loop=False)
        clip.add_keyframe("hip", ChannelTarget.TRANSLATION, 0.0, [0, 0.9, 0])
        clip.add_keyframe("hip", ChannelTarget.TRANSLATION, 1.0, [0.1, 0.9, 0])
        clip.add_keyframe("hip", ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
        return clip

    def test_duration(self):
        clip = self._make_clip()
        assert clip.duration == pytest.approx(1.0)

    def test_evaluate_bone(self):
        clip = self._make_clip()
        pose = clip.evaluate_bone("hip", 0.5)
        assert pose.position.x == pytest.approx(0.05, abs=1e-4)

    def test_evaluate_bone_rotation_identity(self):
        clip = self._make_clip()
        pose = clip.evaluate_bone("hip", 0.0)
        assert pose.rotation == Quaternion.identity()

    def test_looping(self):
        clip = AnimationClip("idle", loop=True)
        clip.add_keyframe("root", ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
        clip.add_keyframe("root", ChannelTarget.TRANSLATION, 2.0, [1, 0, 0])
        # At t=3 with loop, it should wrap to t=1 → midpoint value
        pose = clip.evaluate_bone("root", 3.0)
        assert pose.position.x == pytest.approx(0.5, abs=1e-3)

    def test_get_or_create_channel(self):
        clip = AnimationClip("test")
        ch1 = clip.get_or_create_channel("spine", ChannelTarget.ROTATION)
        ch2 = clip.get_or_create_channel("spine", ChannelTarget.ROTATION)
        assert ch1 is ch2  # Same object returned

    def test_serialise_roundtrip(self):
        clip = self._make_clip()
        d = clip.to_dict()
        clip2 = AnimationClip.from_dict(d)
        assert clip2.name == "walk"
        assert len(clip2.channels) == 2  # translation + rotation channels

    def test_remove_event_at_index_uses_sorted_identity(self):
        clip = AnimationClip("events")
        clip.add_event("dup", 1.0, {"v": 1})
        first = clip._events[-1]
        clip.add_event("dup", 1.0, {"v": 1})
        clip.remove_event_at_index(1)
        assert len(clip._events) == 1
        assert clip._events[0] is first


# ---------------------------------------------------------------------------
# BlendTree
# ---------------------------------------------------------------------------

class TestBlendTree:
    def _make_tree(self) -> BlendTree:
        """Build a simple idle→walk→run blend tree."""
        from animation_engine.animation.clip import AnimationClip
        from animation_engine.animation.channel import ChannelTarget

        bone_names = ["hip", "spine"]

        def make_clip(name, dx):
            c = AnimationClip(name, loop=True)
            c.add_keyframe("hip", ChannelTarget.TRANSLATION, 0.0, [0, 1, 0])
            c.add_keyframe("hip", ChannelTarget.TRANSLATION, 1.0, [dx, 1, 0])
            c.add_keyframe("spine", ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
            return c

        idle_clip = make_clip("idle", 0.0)
        walk_clip = make_clip("walk", 0.1)

        tree = BlendTree(bone_names)
        tree.add_state(BlendState("idle", idle_clip))
        tree.add_state(BlendState("walk", walk_clip))
        tree.add_transition(BlendTransition("idle", "walk", duration=0.2))
        tree.add_transition(BlendTransition("walk", "idle", duration=0.2))
        tree.set_initial_state("idle")
        return tree

    def test_initial_state(self):
        tree = self._make_tree()
        assert tree.current_state_name == "idle"

    def test_update_returns_pose(self):
        tree = self._make_tree()
        pose = tree.update(0.016)
        assert "hip" in pose
        assert isinstance(pose["hip"], Transform)

    def test_transition(self):
        tree = self._make_tree()
        tree.trigger("walk")
        tree.update(0.1)  # Partially through transition
        assert tree.is_transitioning

    def test_transition_completes(self):
        tree = self._make_tree()
        tree.trigger("walk")
        # Advance past transition duration
        for _ in range(30):
            tree.update(0.016)
        assert tree.current_state_name == "walk"
        assert not tree.is_transitioning

    def test_invalid_trigger_ignored(self):
        """Triggering a non-existent state should not crash."""
        tree = self._make_tree()
        tree.trigger("nonexistent")
        pose = tree.update(0.016)
        assert pose is not None

    def test_set_parameter_stores_value(self):
        """set_parameter should store a value retrievable from _context."""
        tree = self._make_tree()
        tree.set_parameter("speed", 1.5)
        assert tree._context["speed"] == 1.5

    def test_set_parameter_multiple_values(self):
        """set_parameter supports multiple independent keys."""
        tree = self._make_tree()
        tree.set_parameter("speed", 2.0)
        tree.set_parameter("combat_mode", True)
        assert tree._context["speed"] == 2.0
        assert tree._context["combat_mode"] is True

    def test_set_parameter_does_not_crash_after_update(self):
        """set_parameter should not raise even after update is called."""
        tree = self._make_tree()
        tree.update(0.016)
        tree.set_parameter("speed", 0.5)
        pose = tree.update(0.016)
        assert pose is not None


# ---------------------------------------------------------------------------
# IKSolver (FABRIK)
# ---------------------------------------------------------------------------

class TestIKSolver:
    def _make_straight_chain(self):
        """Two-bone chain (thigh→shin→foot), each segment 1 unit long."""
        bone_names = ["thigh", "shin", "foot"]
        # Chain points upward from origin: foot at (0,2,0)
        pose = {
            "thigh": Transform(position=Vector3(0, 0, 0)),
            "shin":  Transform(position=Vector3(0, 1, 0)),
            "foot":  Transform(position=Vector3(0, 2, 0)),
        }
        bone_lengths = [1.0, 1.0]
        return bone_names, pose, bone_lengths

    def test_reach_reachable_target(self):
        """Solver should move end-effector close to a reachable target."""
        bone_names, pose, bone_lengths = self._make_straight_chain()
        # Root at (0,0,0), chain length=2.  Target at (1.5, 0.5, 0):
        # distance from root = sqrt(2.25+0.25) ≈ 1.58 → reachable.
        # Target is off-axis, so FABRIK has a unique non-degenerate solution.
        chain = IKChain(
            bone_names=bone_names,
            target=Vector3(1.5, 0.5, 0),
            weight=1.0,
            max_iterations=30,
            tolerance=0.005,
        )
        solver = IKSolver()
        solver.solve(chain, pose, bone_lengths)
        # Foot should be near the target
        foot_pos = pose["foot"].position
        assert foot_pos.distance_to(Vector3(1.5, 0.5, 0)) < 0.05

    def test_unreachable_target_stretches_chain(self):
        """For targets beyond reach, the chain stretches fully."""
        bone_names, pose, bone_lengths = self._make_straight_chain()
        chain = IKChain(
            bone_names=bone_names,
            target=Vector3(100, 0, 0),  # Way beyond reach
            weight=1.0,
        )
        solver = IKSolver()
        solver.solve(chain, pose, bone_lengths)
        # All bones should be pointing toward the target (+X direction),
        # so each bone should have a larger X component than its predecessor.
        thigh_x = pose["thigh"].position.x
        shin_x = pose["shin"].position.x
        foot_x = pose["foot"].position.x
        assert shin_x > thigh_x
        assert foot_x > shin_x


# ---------------------------------------------------------------------------
# MorphTrack
# ---------------------------------------------------------------------------

class TestMorphTrack:
    def test_evaluate_empty(self):
        track = MorphTrack("blink")
        assert track.evaluate(0.5) == pytest.approx(0.0)

    def test_evaluate_single_keyframe(self):
        track = MorphTrack("smile")
        track.add_keyframe(0.0, 1.0)
        assert track.evaluate(0.5) == pytest.approx(1.0)

    def test_linear_interpolation(self):
        track = MorphTrack("frown")
        track.add_keyframe(0.0, 0.0)
        track.add_keyframe(1.0, 1.0)
        assert track.evaluate(0.25) == pytest.approx(0.25)
        assert track.evaluate(0.75) == pytest.approx(0.75)

    def test_serialise_roundtrip(self):
        track = MorphTrack("open_mouth")
        track.add_keyframe(0.0, 0.0)
        track.add_keyframe(0.5, 1.0)
        d = track.to_dict()
        track2 = MorphTrack.from_dict(d)
        assert track2.morph_name == "open_mouth"
        assert track2.evaluate(0.5) == pytest.approx(1.0)
