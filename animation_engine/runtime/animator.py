"""
animation_engine.runtime.animator
=====================================
The Animator ties together a Model, a BlendTree, and an IKSolver into a
single per-character update loop compatible with Game Engine for Teaching.

Each frame the game engine calls ``Animator.update(delta_time)`` which:
  1. Advances the BlendTree state machine.
  2. Evaluates the blended per-bone pose.
  3. Applies IK overrides (foot placement, look-at, etc.).
  4. Computes final world-space skin matrices for GPU upload.
  5. Applies active morph-target weights.

The resulting ``skin_matrices`` list and ``morph_weights`` dict are
consumed directly by the rendering system.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

import numpy as np

from ..model.model import Model
from ..math_utils import Matrix4x4, Transform, Vector3
from ..animation.blend_tree import BlendTree
from ..animation.ik_solver import IKSolver, IKChain
from ..animation.morph_track import MorphTrack


class Animator:
    """
    Runtime animation controller for a single character / prop.

    Attributes
    ----------
    model           : The Model being animated.
    blend_tree      : State machine controlling clip selection and blending.
    ik_solver       : Optional IK solver for foot/hand placement overrides.
    morph_tracks    : List of MorphTracks driving morph-target weights.
    skin_matrices   : (Output) Per-bone final skin matrix list, ready for GPU.
    morph_weights   : (Output) Dict of morph-target name → current weight.
    root_motion_delta : (Output) Root-motion translation delta for the last
                        ``update()`` call (world-space XYZ).  Consumed by the
                        character controller each frame.
    event_callbacks : Dict mapping event name → list of callables.  Each
                      callable receives the event dict when the event fires.
    """

    def __init__(
        self,
        model: Model,
        blend_tree: BlendTree,
        ik_solver: Optional[IKSolver] = None,
        morph_tracks: Optional[List[MorphTrack]] = None,
    ) -> None:
        self.model = model
        self.blend_tree = blend_tree
        self.ik_solver = ik_solver or IKSolver()
        self.morph_tracks: List[MorphTrack] = morph_tracks or []

        # IK chains applied each frame (can be populated after construction)
        self.ik_chains: List[IKChain] = []

        # --- Outputs updated each frame -----------------------------------
        skeleton = model.skeleton
        bone_count = skeleton.bone_count if skeleton else 0
        # Each skin matrix = world_matrix * inverse_bind
        self.skin_matrices: List[Matrix4x4] = [Matrix4x4.identity() for _ in range(bone_count)]
        self.morph_weights: Dict[str, float] = {}

        # Root-motion output — accumulated XYZ delta since last update().
        self.root_motion_delta: Vector3 = Vector3.zero()
        self._prev_root_position: Optional[Vector3] = self._sample_active_root_position()

        # Event dispatch table: event_name -> [callback, ...]
        self.event_callbacks: Dict[str, List[Callable[[dict], None]]] = {}

        # Elapsed time in seconds (used for morph track evaluation)
        self._time: float = 0.0
        # Track previous time to detect event crossings each frame.
        self._prev_time: float = 0.0

    def register_event_callback(self, event_name: str, callback: Callable[[dict], None]) -> None:
        """Register *callback* to be called whenever *event_name* fires.

        Parameters
        ----------
        event_name:
            The animation event name to listen for (e.g. ``"footstep_left"``).
        callback:
            Callable receiving the event dict ``{"name", "time", "data"}``.
        """
        self.event_callbacks.setdefault(event_name, []).append(callback)

    def update(self, delta: float, context: dict = None) -> None:
        """
        Advance the animation system by *delta* seconds.

        Call this once per game tick from Game Engine for Teaching's entity
        update loop.
        """
        self._prev_time = self._time
        self._time += delta

        current_state_before = getattr(self.blend_tree, "_current_state", None)
        next_state_before = getattr(self.blend_tree, "_next_state", None)
        previous_local_times = {}
        for state in (current_state_before, next_state_before):
            if state is not None:
                previous_local_times[state] = getattr(state, "_local_time", 0.0)

        # 1. Advance blend tree → per-bone FK pose
        pose: Dict[str, Transform] = self.blend_tree.update(delta, context)

        # 2. Apply IK overrides on top of the FK pose
        if self.ik_chains and self.model.skeleton:
            self._apply_ik(pose)

        # 3. Compute final skin matrices
        self._compute_skin_matrices(pose)

        # 4. Evaluate morph-target weights
        self._update_morph_weights()

        # 5. Extract root-motion delta from pose (XZ translation from root bone)
        self._extract_root_motion(pose)

        # 6. Dispatch animation events that crossed this state's local timeline.
        current_state = getattr(self.blend_tree, "_current_state", None)
        current_local_time = getattr(current_state, "_local_time", 0.0) if current_state else 0.0
        previous_local_time = previous_local_times.get(current_state, current_local_time)
        self._dispatch_events(current_state, previous_local_time, current_local_time)

    # -- IK ------------------------------------------------------------------

    def _apply_ik(self, pose: Dict[str, Transform]) -> None:
        """Apply all registered IK chains to *pose* in-place."""
        skeleton = self.model.skeleton
        if skeleton is None:
            return
        # Build world-space transforms (needed by the FABRIK solver)
        world_transforms = self._build_world_transforms(pose, skeleton)

        for chain in self.ik_chains:
            # Pre-compute bone lengths from the bind pose
            bone_lengths = []
            for i in range(len(chain.bone_names) - 1):
                b0 = skeleton.get_bone(chain.bone_names[i])
                b1 = skeleton.get_bone(chain.bone_names[i + 1])
                if b0 and b1:
                    p0 = b0.local_transform.position
                    p1 = b1.local_transform.position
                    bone_lengths.append(p0.distance_to(p1))
                else:
                    bone_lengths.append(0.5)  # fallback length

            self.ik_solver.solve(chain, world_transforms, bone_lengths)

        # Write IK-corrected world transforms back to the local-space pose
        for name, world_t in world_transforms.items():
            bone = skeleton.get_bone(name)
            if bone is None:
                continue
            if bone.parent_index < 0:
                pose[name] = world_t
            else:
                parent_name = skeleton.bones[bone.parent_index].name
                parent_world = world_transforms.get(parent_name)
                if parent_world:
                    # local = inverse(parent_world) * world
                    parent_inv = parent_world.to_matrix().inverse()
                    local_mat = parent_inv * world_t.to_matrix()
                    pose[name] = Transform.from_matrix(local_mat)

    def _build_world_transforms(
        self,
        pose: Dict[str, Transform],
        skeleton,
    ) -> Dict[str, Transform]:
        """Compute world-space Transform for every bone from the local pose."""
        world: Dict[str, Transform] = {}
        for bone in skeleton.bones:
            local_t = pose.get(bone.name, bone.local_transform)
            if bone.parent_index < 0:
                world[bone.name] = local_t
            else:
                parent_name = skeleton.bones[bone.parent_index].name
                parent_world = world.get(parent_name, Transform.identity())
                world[bone.name] = parent_world.combine(local_t)
        return world

    # -- skin matrices -------------------------------------------------------

    def _compute_skin_matrices(self, pose: Dict[str, Transform]) -> None:
        """
        Compute skin_matrices[i] = world_matrix[i] * inverse_bind[i].

        These 4×4 matrices are uploaded to the GPU and applied in the
        vertex shader to deform the mesh.
        """
        skeleton = self.model.skeleton
        if skeleton is None:
            return

        bone_transforms_list = [pose.get(b.name, b.local_transform) for b in skeleton.bones]
        world_matrices = skeleton.get_world_matrices(bone_transforms_list)
        for i, bone in enumerate(skeleton.bones):
            self.skin_matrices[i] = world_matrices[i] * bone.inverse_bind

    # -- morph weights -------------------------------------------------------

    def _update_morph_weights(self) -> None:
        """Evaluate all morph tracks at the current animation time."""
        for track in self.morph_tracks:
            self.morph_weights[track.morph_name] = track.evaluate(self._time)

    # -- root motion ---------------------------------------------------------

    def _sample_active_root_position(self) -> Optional[Vector3]:
        """Return the active state's current root-bone position, if available."""
        skeleton = self.model.skeleton
        if skeleton is None or not skeleton.bones:
            return None
        state = getattr(self.blend_tree, "_current_state", None)
        if state is None:
            return None
        clip = getattr(state, "clip", None)
        if clip is None:
            return None
        root_name = skeleton.bones[0].name
        local_time = getattr(state, "_local_time", 0.0)
        return clip.evaluate_bone(root_name, local_time).position

    def _extract_root_motion(self, pose: Dict[str, Transform]) -> None:
        """Compute XYZ root-motion delta from the current pose.

        The delta is derived from the root bone's translation channel.  The
        caller (character controller) is responsible for consuming and zeroing
        this value each frame.
        """
        skeleton = self.model.skeleton
        if skeleton is None or not skeleton.bones:
            self.root_motion_delta = Vector3.zero()
            return
        root_name = skeleton.bones[0].name
        root_transform = pose.get(root_name)
        if root_transform is not None:
            current_root_position = root_transform.position
            if self._prev_root_position is None:
                self.root_motion_delta = Vector3.zero()
            else:
                self.root_motion_delta = current_root_position - self._prev_root_position
            self._prev_root_position = current_root_position
        else:
            self.root_motion_delta = Vector3.zero()
            self._prev_root_position = None

    # -- event dispatch -------------------------------------------------------

    def _dispatch_events(
        self,
        current_state,
        previous_local_time: float,
        current_local_time: float,
    ) -> None:
        """Fire callbacks for any animation events in the current frame window.

        Checks the active clip's event list (if accessible) for events whose
        clip-local ``time`` falls in the half-open interval
        ``(previous_local_time, current_local_time]`` with loop-wrap handling.
        """
        if not self.event_callbacks:
            return

        active_clip = getattr(current_state, "clip", None) if current_state else None
        if active_clip is None:
            return

        clip_duration = active_clip.duration
        is_looping = bool(getattr(active_clip, "loop", False))
        for event in active_clip.get_events():
            t = event["time"]
            if self._did_event_fire_this_update(
                t, previous_local_time, current_local_time, clip_duration, is_looping
            ):
                callbacks = self.event_callbacks.get(event["name"], [])
                for cb in callbacks:
                    cb(event)

    @staticmethod
    def _did_event_fire_this_update(
        event_time: float,
        previous_local_time: float,
        current_local_time: float,
        clip_duration: float,
        is_looping: bool,
    ) -> bool:
        """Return True when an event time is crossed in this update window."""
        if not is_looping or clip_duration <= 1e-6:
            return previous_local_time < event_time <= current_local_time

        delta = current_local_time - previous_local_time
        if delta >= clip_duration:
            return True

        prev_mod = previous_local_time % clip_duration
        curr_mod = current_local_time % clip_duration
        if prev_mod < curr_mod:
            return prev_mod < event_time <= curr_mod
        return event_time > prev_mod or event_time <= curr_mod

    # -- convenience ---------------------------------------------------------

    def trigger(self, state_name: str) -> None:
        """Request a state transition in the blend tree."""
        self.blend_tree.trigger(state_name)

    def add_ik_chain(self, chain: IKChain) -> None:
        """Register an IK chain to be solved every frame."""
        self.ik_chains.append(chain)

    def get_skin_matrices_flat(self) -> np.ndarray:
        """
        Return all skin matrices as a flat (N * 16,) float32 array.

        Suitable for direct upload to a GPU uniform buffer via Game Engine
        for Teaching's rendering API.
        """
        if not self.skin_matrices:
            return np.zeros((0,), dtype=np.float32)
        result = np.zeros((len(self.skin_matrices), 4, 4), dtype=np.float32)
        for i, mat in enumerate(self.skin_matrices):
            result[i] = mat.to_numpy().astype(np.float32)
        return result.flatten()
