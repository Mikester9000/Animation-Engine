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

from typing import Dict, List, Optional

import numpy as np

from ..model.model import Model
from ..math_utils import Matrix4x4, Transform
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
        self.skin_matrices: List[Matrix4x4] = [
            Matrix4x4.identity() for _ in range(bone_count)
        ]
        self.morph_weights: Dict[str, float] = {}

        # Elapsed time in seconds (used for morph track evaluation)
        self._time: float = 0.0

    def update(self, delta: float, context: dict = None) -> None:
        """
        Advance the animation system by *delta* seconds.

        Call this once per game tick from Game Engine for Teaching's entity
        update loop.
        """
        self._time += delta

        # 1. Advance blend tree → per-bone FK pose
        pose: Dict[str, Transform] = self.blend_tree.update(delta, context)

        # 2. Apply IK overrides on top of the FK pose
        #    IK works in world space; we build world transforms first, then
        #    pass them to the solver which writes back corrected transforms.
        if self.ik_chains and self.model.skeleton:
            self._apply_ik(pose)

        # 3. Compute final skin matrices
        self._compute_skin_matrices(pose)

        # 4. Evaluate morph-target weights
        self._update_morph_weights()

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

        bone_transforms_list = [
            pose.get(b.name, b.local_transform) for b in skeleton.bones
        ]
        world_matrices = skeleton.get_world_matrices(bone_transforms_list)
        for i, bone in enumerate(skeleton.bones):
            self.skin_matrices[i] = world_matrices[i] * bone.inverse_bind

    # -- morph weights -------------------------------------------------------

    def _update_morph_weights(self) -> None:
        """Evaluate all morph tracks at the current animation time."""
        for track in self.morph_tracks:
            self.morph_weights[track.morph_name] = track.evaluate(self._time)

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
