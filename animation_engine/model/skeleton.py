"""
animation_engine.model.skeleton
==================================
Bone and Skeleton classes.

A Skeleton is a hierarchical tree of Bones.  Each bone stores:
  - A *local* transform (relative to its parent bone)
  - An *inverse bind-pose matrix* (the world-space transform of the bone in
    the reference T-pose, inverted).  The GPU uses this to un-deform the
    mesh before re-applying the animated pose.

This design mirrors the "joint" model in glTF 2.0 and is directly compatible
with the GPU skinning shader used by Game Engine for Teaching.

FF15 characters typically have ~50–80 bones covering the full body hierarchy:
spine, shoulders, arms, fingers, face rig, etc.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from ..math_utils import Matrix4x4, Transform, Vector3, Quaternion


class Bone:
    """
    A single joint in the skeleton hierarchy.

    Attributes
    ----------
    name            : Unique bone name (e.g. "spine_01", "hand_l").
    index           : Position of this bone in the skeleton's flat bone array.
    parent_index    : Index of the parent bone, or -1 for the root.
    local_transform : Bind-pose local transform (relative to parent).
    inverse_bind    : Inverse of the world-space bind pose matrix.
    """

    def __init__(
        self,
        name: str,
        index: int = 0,
        parent_index: int = -1,
        local_transform: Transform = None,
    ) -> None:
        self.name: str = name
        self.index: int = index
        self.parent_index: int = parent_index
        self.local_transform: Transform = (
            local_transform if local_transform is not None else Transform.identity()
        )
        # Computed and stored during Skeleton.compute_bind_pose()
        self.inverse_bind: Matrix4x4 = Matrix4x4.identity()
        # Children (populated by the Skeleton)
        self.children: List[int] = []

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "index": self.index,
            "parent_index": self.parent_index,
            "local_transform": self.local_transform.to_dict(),
            "inverse_bind": self.inverse_bind.to_list(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Bone":
        bone = cls(
            name=d["name"],
            index=d["index"],
            parent_index=d.get("parent_index", -1),
            local_transform=Transform.from_dict(d["local_transform"]),
        )
        bone.inverse_bind = Matrix4x4.from_list(d.get("inverse_bind", [
            1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1
        ]))
        return bone

    def __repr__(self) -> str:
        return (
            f"Bone(name={self.name!r}, index={self.index}, "
            f"parent={self.parent_index})"
        )


class Skeleton:
    """
    Hierarchical collection of Bones representing a character rig.

    Usage
    -----
    >>> skel = Skeleton("character")
    >>> root = skel.add_bone("root", parent_index=-1)
    >>> spine = skel.add_bone("spine_01", parent_index=root)
    >>> skel.compute_bind_pose()
    """

    def __init__(self, name: str = "Skeleton") -> None:
        self.name: str = name
        self.bones: List[Bone] = []
        # Fast lookup by name
        self._name_to_index: Dict[str, int] = {}

    # -- bone management -----------------------------------------------------

    def add_bone(
        self,
        name: str,
        parent_index: int = -1,
        local_transform: Transform = None,
    ) -> int:
        """
        Add a bone to the skeleton and return its index.

        Parameters
        ----------
        name            : Unique name for the new bone.
        parent_index    : Index of the parent bone (-1 for root).
        local_transform : Bind-pose local transform.
        """
        idx = len(self.bones)
        bone = Bone(
            name=name,
            index=idx,
            parent_index=parent_index,
            local_transform=local_transform or Transform.identity(),
        )
        self.bones.append(bone)
        self._name_to_index[name] = idx
        # Register this bone as a child of its parent
        if parent_index >= 0:
            self.bones[parent_index].children.append(idx)
        return idx

    def get_bone(self, name: str) -> Optional[Bone]:
        """Return the Bone with the given name, or None."""
        idx = self._name_to_index.get(name)
        return self.bones[idx] if idx is not None else None

    def get_bone_index(self, name: str) -> int:
        """Return the index of the bone with the given name, or -1."""
        return self._name_to_index.get(name, -1)

    # -- bind pose -----------------------------------------------------------

    def compute_bind_pose(self) -> None:
        """
        Compute and cache the inverse bind-pose matrices for all bones.

        Must be called once after the skeleton hierarchy is fully built.
        The bind pose is the reference T-pose stored in the mesh vertex data;
        each bone's inverse-bind matrix "undoes" the bind pose so the
        skinning shader can apply only the delta from the current pose.
        """
        world_matrices = [Matrix4x4.identity()] * len(self.bones)

        # Traverse in bone-index order (parents are added before children)
        for bone in self.bones:
            local_mat = bone.local_transform.to_matrix()
            if bone.parent_index < 0:
                # Root bone — local transform IS the world transform
                world_matrices[bone.index] = local_mat
            else:
                world_matrices[bone.index] = (
                    world_matrices[bone.parent_index] * local_mat
                )
            # Inverse bind = inverse of world matrix in bind pose
            bone.inverse_bind = world_matrices[bone.index].inverse()

    def get_world_matrices(self, pose_transforms: List[Transform]) -> List[Matrix4x4]:
        """
        Compute world-space matrices for every bone given per-bone pose transforms.

        Parameters
        ----------
        pose_transforms : Per-bone local transforms for the current animation pose.

        Returns
        -------
        world_matrices : World-space matrix for every bone.

        The caller combines these with inverse_bind to get final skin matrices:
            skin_matrix[i] = world_matrices[i] * bones[i].inverse_bind
        """
        world = [Matrix4x4.identity()] * len(self.bones)
        for bone in self.bones:
            local_mat = pose_transforms[bone.index].to_matrix()
            if bone.parent_index < 0:
                world[bone.index] = local_mat
            else:
                world[bone.index] = world[bone.parent_index] * local_mat
        return world

    @property
    def bone_count(self) -> int:
        return len(self.bones)

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "bones": [b.to_dict() for b in self.bones],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Skeleton":
        skel = cls(name=d.get("name", "Skeleton"))
        for bd in d.get("bones", []):
            bone = Bone.from_dict(bd)
            skel.bones.append(bone)
            skel._name_to_index[bone.name] = bone.index
        # Rebuild children lists
        for bone in skel.bones:
            if bone.parent_index >= 0:
                skel.bones[bone.parent_index].children.append(bone.index)
        return skel

    def __repr__(self) -> str:
        return f"Skeleton({self.name!r}, {self.bone_count} bones)"
