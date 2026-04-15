"""
animation_engine.animation.ik_solver
=======================================
Inverse Kinematics (IK) solver using the FABRIK algorithm.

FABRIK (Forward And Backward Reaching Inverse Kinematics) is used in FF15
and most AAA titles for:
  - Foot placement on uneven terrain (foot-IK)
  - Hand attachment to interactive objects (hand-IK)
  - Look-at / aim constraints for spine and head bones

FABRIK is iterative, fast, and produces natural-looking results that blend
well with keyframe animation.  The solver is applied on top of the FK pose
output from AnimationClip evaluation.

Reference: Aristidou & Lasenby (2011), "FABRIK: A fast, iterative solver for
the Inverse Kinematics problem."
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional

from ..math_utils import Vector3, Quaternion, Transform


@dataclass
class IKChain:
    """
    A chain of bones to be solved by the IK solver.

    Attributes
    ----------
    bone_names  : Ordered list of bone names from root to end-effector.
    target      : Desired world-space position for the end-effector.
    pole_target : Optional hint for controlling elbow/knee bending direction.
    weight      : Blend weight between FK pose (0) and IK pose (1).
    max_iterations : FABRIK iteration budget per frame.
    tolerance   : Stop iterating when end-effector is within this distance.
    """

    bone_names: List[str] = field(default_factory=list)
    target: Vector3 = field(default_factory=Vector3.zero)
    pole_target: Optional[Vector3] = None
    weight: float = 1.0
    max_iterations: int = 10
    tolerance: float = 0.001


class IKSolver:
    """
    FABRIK IK solver that modifies a per-bone pose dict in-place.

    Usage
    -----
    >>> chain = IKChain(
    ...     bone_names=["thigh_l", "shin_l", "foot_l"],
    ...     target=foot_target_position,
    ...     weight=0.8,
    ... )
    >>> solver = IKSolver()
    >>> solver.solve(chain, pose_transforms, skeleton)
    """

    def solve(
        self,
        chain: IKChain,
        pose_transforms: dict,       # bone_name → Transform (in world space)
        bone_lengths: List[float],   # segment lengths (len(bone_names) - 1 values)
    ) -> None:
        """
        Run FABRIK on *chain* and update *pose_transforms* in place.

        Parameters
        ----------
        chain           : The IK chain definition.
        pose_transforms : World-space Transform dict (modified in place).
        bone_lengths    : Pre-computed segment lengths for the chain.
        """
        names = chain.bone_names
        if len(names) < 2:
            return  # Need at least 2 bones

        # Extract current world-space positions
        positions = [
            pose_transforms[n].position if n in pose_transforms else Vector3.zero()
            for n in names
        ]

        target = chain.target
        root_pos = positions[0]

        # Total chain reach
        total_length = sum(bone_lengths)
        dist_to_target = root_pos.distance_to(target)

        if dist_to_target >= total_length:
            # Target is unreachable — stretch fully toward target
            dir_to_target = (target - root_pos).normalized()
            for i in range(1, len(positions)):
                positions[i] = positions[i - 1] + dir_to_target * bone_lengths[i - 1]
        else:
            # FABRIK iterations
            for _ in range(chain.max_iterations):
                # --- Forward pass (end-effector → root) ---
                positions[-1] = target
                for i in range(len(positions) - 2, -1, -1):
                    seg_dir = (positions[i] - positions[i + 1]).normalized()
                    positions[i] = positions[i + 1] + seg_dir * bone_lengths[i]

                # --- Backward pass (root → end-effector) ---
                positions[0] = root_pos
                for i in range(1, len(positions)):
                    seg_dir = (positions[i] - positions[i - 1]).normalized()
                    positions[i] = positions[i - 1] + seg_dir * bone_lengths[i - 1]

                # Convergence check
                if positions[-1].distance_to(target) < chain.tolerance:
                    break

        # Apply pole target heuristic (2-bone limb only)
        if chain.pole_target is not None and len(positions) == 3:
            positions = _apply_pole_target(
                positions, bone_lengths, chain.pole_target
            )

        # Write positions back and recompute rotations
        for i, name in enumerate(names):
            if name not in pose_transforms:
                continue
            old_t = pose_transforms[name]
            # Apply weight blend between FK and IK positions
            blended_pos = old_t.position.lerp(positions[i], chain.weight)
            # Compute rotation to point this bone at the next
            if i < len(names) - 1 and names[i + 1] in pose_transforms:
                local_dir = (positions[i + 1] - positions[i]).normalized()
                new_rot = _rotation_from_direction(local_dir)
                blended_rot = old_t.rotation.slerp(new_rot, chain.weight)
            else:
                blended_rot = old_t.rotation
            pose_transforms[name] = Transform(blended_pos, blended_rot, old_t.scale)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rotation_from_direction(direction: Vector3) -> Quaternion:
    """
    Return a quaternion that rotates the Y-axis to point along *direction*.
    Used to orient each IK bone segment.
    """
    y_axis = Vector3.up()
    cross = y_axis.cross(direction)
    mag = cross.length
    if mag < 1e-8:
        # Already aligned or exactly opposite
        if direction.dot(y_axis) > 0.0:
            return Quaternion.identity()
        return Quaternion.from_axis_angle(Vector3.right(), math.pi)
    axis = cross.normalized()
    angle = math.acos(max(-1.0, min(1.0, y_axis.dot(direction))))
    return Quaternion.from_axis_angle(axis, angle)


def _apply_pole_target(
    positions: List[Vector3],
    bone_lengths: List[float],
    pole: Vector3,
) -> List[Vector3]:
    """
    Rotate a 2-bone chain so the elbow/knee points toward *pole*.

    This keeps the limb from flipping while solving — a critical artifact
    prevention technique used in every AAA IK system.
    """
    root, mid, tip = positions
    # Project pole onto the plane perpendicular to (root → tip)
    root_to_tip = (tip - root).normalized()
    root_to_pole = pole - root
    # Gram-Schmidt: remove component along the bone axis
    projected_pole = (
        root_to_pole
        - root_to_tip * root_to_tip.dot(root_to_pole)
    ).normalized()

    # Current mid position projected into the same plane
    root_to_mid = mid - root
    projected_mid = (
        root_to_mid
        - root_to_tip * root_to_tip.dot(root_to_mid)
    )
    mid_mag = projected_mid.length
    if mid_mag < 1e-8:
        return positions
    projected_mid = projected_mid.normalized()

    # Compute angle from current mid to pole
    cos_angle = max(-1.0, min(1.0, projected_mid.dot(projected_pole)))
    angle = math.acos(cos_angle)
    cross = projected_mid.cross(projected_pole)
    if cross.dot(root_to_tip) < 0.0:
        angle = -angle

    # Rotate mid point around the root→tip axis
    from ..math_utils import Quaternion as Q
    rot = Q.from_axis_angle(root_to_tip, angle)
    new_mid = root + rot.rotate_vector(mid - root)
    return [root, new_mid, tip]
