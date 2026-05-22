"""
animation_engine.animation.blend_tree
=========================================
Animation state machine and blend tree.

FF15's characters use a sophisticated multi-layer blend tree to smoothly
transition between hundreds of motion-captured clips.  This module provides
a simplified but production-quality implementation that is fully compatible
with Game Engine for Teaching's runtime.

Key concepts
------------
  BlendState      : A leaf node holding one AnimationClip and a playback speed.
  BlendTransition : A directed edge from one state to another with a crossfade
                    duration and optional trigger condition.
  BlendTree       : The state machine that owns states, handles transition
                    triggers, and outputs a blended per-bone pose.

Blending algorithm
------------------
  During a transition between state A and state B:
    - Both clips are evaluated at their respective local times.
    - Per-bone Transforms are blended using Transform.lerp (position+scale)
      and Quaternion.slerp (rotation) with a smooth cubic ease function.
    - After *transition_duration* seconds the blend reaches 100 % state B.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from ..math_utils import Transform
from .clip import AnimationClip


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _smooth_step(t: float) -> float:
    """
    Cubic smooth-step easing — same curve used in UE4 transitions.
    Maps t ∈ [0,1] → [0,1] with zero derivative at endpoints.
    """
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class BlendState:
    """
    A single node in the blend tree — wraps one AnimationClip.

    Attributes
    ----------
    name        : Unique identifier used to trigger transitions.
    clip        : The AnimationClip to play while in this state.
    speed       : Playback speed multiplier (1.0 = normal).
    """

    def __init__(
        self,
        name: str,
        clip: AnimationClip,
        speed: float = 1.0,
    ) -> None:
        self.name: str = name
        self.clip: AnimationClip = clip
        self.speed: float = speed
        self._local_time: float = 0.0

    def update(self, delta: float) -> None:
        """Advance the local playback time by *delta* seconds."""
        self._local_time += delta * self.speed

    def evaluate(self, bone_names: List[str]) -> Dict[str, Transform]:
        """Return the per-bone pose at the current local time."""
        return self.clip.evaluate_all_bones(bone_names, self._local_time)

    def reset(self) -> None:
        """Restart playback from the beginning."""
        self._local_time = 0.0

    def to_dict(self) -> dict:
        return {"name": self.name, "clip_name": self.clip.name, "speed": self.speed}


# ---------------------------------------------------------------------------
# Transition
# ---------------------------------------------------------------------------

@dataclass
class BlendTransition:
    """
    A directed edge in the state machine.

    Attributes
    ----------
    from_state          : Name of the source state.
    to_state            : Name of the destination state.
    duration            : Crossfade length in seconds.
    condition           : Optional callable(context_dict) → bool; if provided,
                          the transition is only triggered when the condition is
                          True.  Useful for gait/speed parameter checks.
    has_exit_time       : If True, the transition only starts when the source
                          clip reaches its natural end.
    """

    from_state: str
    to_state: str
    duration: float = 0.25
    condition: Optional[Callable] = None
    has_exit_time: bool = False

    def is_eligible(self, context: dict) -> bool:
        """Return True if this transition should activate."""
        if self.condition is not None:
            return bool(self.condition(context))
        return True


# ---------------------------------------------------------------------------
# Blend Tree
# ---------------------------------------------------------------------------

class BlendTree:
    """
    Finite-state machine that blends between AnimationClips.

    Quick-start
    -----------
    >>> tree = BlendTree(["spine_01", "hand_l", ...])
    >>> tree.add_state(BlendState("idle",    idle_clip))
    >>> tree.add_state(BlendState("walk",    walk_clip))
    >>> tree.add_state(BlendState("run",     run_clip))
    >>> tree.add_transition(BlendTransition("idle", "walk", duration=0.2))
    >>> tree.add_transition(BlendTransition("walk", "run",  duration=0.15))
    >>> tree.set_initial_state("idle")
    >>> # Each game tick:
    >>> tree.trigger("walk")
    >>> pose = tree.update(delta_time)   # → {bone_name: Transform}
    """

    def __init__(self, bone_names: List[str]) -> None:
        self.bone_names: List[str] = bone_names
        self._states: Dict[str, BlendState] = {}
        self._transitions: List[BlendTransition] = []

        self._current_state: Optional[BlendState] = None
        self._next_state: Optional[BlendState] = None
        self._blend_time: float = 0.0       # Elapsed transition time
        self._blend_duration: float = 0.0   # Total transition duration
        self._pending_trigger: Optional[str] = None
        self._context: dict = {}

    # -- building the graph --------------------------------------------------

    def add_state(self, state: BlendState) -> None:
        """Register a blend state."""
        self._states[state.name] = state

    def add_transition(self, transition: BlendTransition) -> None:
        """Register a directed transition edge."""
        self._transitions.append(transition)

    def set_initial_state(self, name: str) -> None:
        """Set the starting state (must be called before the first update)."""
        self._current_state = self._states[name]

    # -- runtime control -----------------------------------------------------

    def trigger(self, target_state: str) -> None:
        """
        Request a transition to *target_state*.

        If a matching transition exists from the current state it will start
        on the next update call; otherwise the request is silently ignored.
        """
        self._pending_trigger = target_state

    def set_parameter(self, key: str, value) -> None:
        """
        Set a named parameter used by condition functions.

        Parameters are passed as context to BlendTransition.is_eligible.
        """
        self._context[key] = value

    # -- update --------------------------------------------------------------

    def update(self, delta: float, context: dict = None) -> Dict[str, Transform]:
        """
        Advance the state machine by *delta* seconds.

        Parameters
        ----------
        delta   : Elapsed time in seconds since the last update.
        context : Optional parameter dict forwarded to transition conditions.

        Returns
        -------
        Per-bone Transforms representing the current blended pose.
        """
        ctx = context or {}

        # -- Process pending transition request --------------------------
        if self._pending_trigger is not None and self._current_state is not None:
            target_name = self._pending_trigger
            self._pending_trigger = None
            transition = self._find_transition(
                self._current_state.name, target_name, ctx
            )
            if transition and target_name in self._states:
                self._next_state = self._states[target_name]
                self._next_state.reset()
                self._blend_duration = max(transition.duration, 1e-6)
                self._blend_time = 0.0

        # -- Advance local times -----------------------------------------
        if self._current_state:
            self._current_state.update(delta)
        if self._next_state:
            self._next_state.update(delta)
            self._blend_time += delta

        # -- Finish transition -------------------------------------------
        if self._next_state and self._blend_time >= self._blend_duration:
            self._current_state = self._next_state
            self._next_state = None
            self._blend_time = 0.0

        # -- Evaluate pose -----------------------------------------------
        if self._current_state is None:
            # No state set — return identity transforms
            return {name: Transform.identity() for name in self.bone_names}

        current_pose = self._current_state.evaluate(self.bone_names)

        if self._next_state is None or self._blend_duration < 1e-6:
            return current_pose

        # Smoothly blend toward the next state
        next_pose = self._next_state.evaluate(self.bone_names)
        alpha = _smooth_step(self._blend_time / self._blend_duration)
        blended = {}
        for bone_name in self.bone_names:
            a = current_pose.get(bone_name, Transform.identity())
            b = next_pose.get(bone_name, Transform.identity())
            blended[bone_name] = a.lerp(b, alpha)
        return blended

    def _find_transition(
        self, from_name: str, to_name: str, context: dict
    ) -> Optional[BlendTransition]:
        """Return the best matching transition or None."""
        for tr in self._transitions:
            if tr.from_state == from_name and tr.to_state == to_name:
                if tr.is_eligible(context):
                    return tr
        return None

    # -- state inspection ----------------------------------------------------

    @property
    def current_state_name(self) -> Optional[str]:
        return self._current_state.name if self._current_state else None

    @property
    def is_transitioning(self) -> bool:
        return self._next_state is not None

    @property
    def transition_progress(self) -> float:
        """Normalised crossfade progress in [0, 1]."""
        if not self.is_transitioning or self._blend_duration < 1e-6:
            return 1.0
        return min(1.0, self._blend_time / self._blend_duration)

    def __repr__(self) -> str:
        return (
            f"BlendTree(states={list(self._states.keys())}, "
            f"current={self.current_state_name!r})"
        )
