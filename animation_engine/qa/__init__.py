"""
Quality assurance module for animation validation.

Provides validators for:
- Animation clips (keyframe correctness)
- Skeletons (hierarchy correctness)
- Loop seamlessness (boundary discontinuities)

Usage
-----
>>> from animation_engine.qa import ClipValidator, SkeletonValidator, LoopAnalyzer
>>> validator = ClipValidator()
>>> report = validator.validate_clip(my_clip)
>>> print(report.summary())
"""

from animation_engine.qa.clip_validator import ClipValidator, ValidationReport
from animation_engine.qa.skeleton_validator import SkeletonValidator, SkeletonReport
from animation_engine.qa.loop_analyzer import LoopAnalyzer, LoopReport

__all__ = [
    "ClipValidator",
    "ValidationReport",
    "SkeletonValidator",
    "SkeletonReport",
    "LoopAnalyzer",
    "LoopReport",
]
