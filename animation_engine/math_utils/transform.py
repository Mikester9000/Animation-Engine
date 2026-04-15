"""
animation_engine.math_utils.transform
========================================
Composite TRS (Translation, Rotation, Scale) transform.

A Transform bundles a Vector3 position, Quaternion orientation and Vector3
scale into a single object that can be nested to form a hierarchy — exactly
how bone transforms are represented in skeletal animation rigs.
"""

from __future__ import annotations

from .vector import Vector3
from .quaternion import Quaternion
from .matrix import Matrix4x4


class Transform:
    """
    Represents a local-space transformation (position, rotation, scale).

    This mirrors what game engines like Unity/Unreal expose as a "Transform"
    component and is used as the per-bone local transform in the skeleton.
    """

    def __init__(
        self,
        position: Vector3 = None,
        rotation: Quaternion = None,
        scale: Vector3 = None,
    ) -> None:
        self.position: Vector3 = position if position is not None else Vector3.zero()
        self.rotation: Quaternion = rotation if rotation is not None else Quaternion.identity()
        self.scale: Vector3 = scale if scale is not None else Vector3.one()

    # -- factories -----------------------------------------------------------

    @classmethod
    def identity(cls) -> "Transform":
        """Return the identity transform (origin, no rotation, scale 1)."""
        return cls()

    # -- matrix conversion ---------------------------------------------------

    def to_matrix(self) -> Matrix4x4:
        """Compose position × rotation × scale into a 4×4 matrix."""
        return Matrix4x4.compose(self.position, self.rotation, self.scale)

    @classmethod
    def from_matrix(cls, m: Matrix4x4) -> "Transform":
        """Decompose a 4×4 matrix into a Transform."""
        pos, rot, scl = m.decompose()
        return cls(pos, rot, scl)

    # -- interpolation -------------------------------------------------------

    def lerp(self, other: "Transform", t: float) -> "Transform":
        """
        Linearly interpolate position and scale; SLERP rotation.

        This is the standard approach used in animation blending: two poses
        are blended by lerp-ing each channel independently.
        """
        return Transform(
            self.position.lerp(other.position, t),
            self.rotation.slerp(other.rotation, t),
            self.scale.lerp(other.scale, t),
        )

    # -- hierarchy -----------------------------------------------------------

    def combine(self, child: "Transform") -> "Transform":
        """
        Apply *child* in the local space of *self* and return the world-space
        result.  Equivalent to: world_matrix = parent_matrix * child_matrix.
        """
        parent_mat = self.to_matrix()
        child_mat = child.to_matrix()
        return Transform.from_matrix(parent_mat * child_mat)

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise to a plain Python dict (ready for JSON)."""
        return {
            "position": self.position.to_list(),
            "rotation": self.rotation.to_list(),
            "scale": self.scale.to_list(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Transform":
        """Reconstruct from a serialised dict."""
        return cls(
            Vector3.from_list(d["position"]),
            Quaternion.from_list(d["rotation"]),
            Vector3.from_list(d["scale"]),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Transform):
            return NotImplemented
        return (
            self.position == other.position
            and self.rotation == other.rotation
            and self.scale == other.scale
        )

    def __repr__(self) -> str:
        return (
            f"Transform(pos={self.position}, "
            f"rot={self.rotation}, "
            f"scale={self.scale})"
        )
