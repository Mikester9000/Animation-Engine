"""
Skeleton validator – detect hierarchy and bind pose errors.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

__all__ = ["SkeletonValidator", "SkeletonReport"]


@dataclass
class SkeletonReport:
    """Validation result for a skeleton.

    Attributes
    ----------
    skeleton_name:
        Name of the validated skeleton.
    is_valid:
        True if no errors were found.
    errors:
        List of error messages.
    warnings:
        List of warning messages.
    """

    skeleton_name: str
    is_valid: bool
    errors: list[str]
    warnings: list[str]

    def summary(self) -> str:
        """Return a human-readable one-line summary."""
        status = "VALID" if self.is_valid else "INVALID"
        return f"{status} – {len(self.errors)} errors, {len(self.warnings)} warnings"


class SkeletonValidator:
    """Validate skeleton hierarchies."""

    def validate_skeleton(self, skeleton: Any) -> SkeletonReport:
        """Validate a Skeleton instance.

        Parameters
        ----------
        skeleton:
            Skeleton to validate.

        Returns
        -------
        SkeletonReport
        """
        errors: list[str] = []
        warnings: list[str] = []

        # Check for duplicate bone names
        names = [b.name for b in skeleton.bones]
        if len(names) != len(set(names)):
            duplicates = [n for n in set(names) if names.count(n) > 1]
            errors.append(f"Duplicate bone names: {', '.join(sorted(duplicates))}")

        # Check parent indices are valid
        for idx, bone in enumerate(skeleton.bones):
            parent_index = bone.parent_index
            if parent_index is not None and parent_index != -1:
                if parent_index < 0 or parent_index >= len(skeleton.bones):
                    errors.append(
                        f"Bone '{bone.name}' (index {idx}): "
                        f"parent_index {parent_index} out of bounds "
                        f"[0, {len(skeleton.bones)})"
                    )
                elif parent_index >= idx:
                    errors.append(
                        f"Bone '{bone.name}' (index {idx}): "
                        f"parent_index {parent_index} must be < current index "
                        f"(DAG violation)"
                    )

        # Check that bone.index matches its position in the flat array
        seen_indices: set[int] = set()
        for idx, bone in enumerate(skeleton.bones):
            if bone.index != idx:
                errors.append(
                    f"Bone '{bone.name}': stored index {bone.index} does not match "
                    f"list position {idx}"
                )
            if bone.index in seen_indices:
                errors.append(f"Bone '{bone.name}': duplicate bone index {bone.index}")
            elif 0 <= bone.index < len(skeleton.bones):
                seen_indices.add(bone.index)
            else:
                errors.append(
                    f"Bone '{bone.name}': bone index {bone.index} out of range "
                    f"[0, {len(skeleton.bones)})"
                )

        # Warn if no root bone (parent_index = None/-1)
        root_count = sum(1 for b in skeleton.bones if b.parent_index in (None, -1))
        if root_count == 0:
            warnings.append("No root bone found (all bones have parents)")
        elif root_count > 1:
            root_names = [b.name for b in skeleton.bones if b.parent_index in (None, -1)]
            warnings.append(
                f"Multiple root bones found ({root_count}): {', '.join(root_names)}"
            )

        is_valid = len(errors) == 0
        return SkeletonReport(skeleton.name, is_valid, errors, warnings)
