"""
GameRewritten integration layer.

Provides asset pipeline for generating all character animations
compatible with GameRewritten engine.
"""

from animation_engine.integration.asset_pipeline import AnimationPipeline
from animation_engine.integration.style_profiles import (
    ClipSpec,
    StyleProfile,
    get_style_profile,
    list_style_profiles,
)

__all__ = [
    "AnimationPipeline",
    "ClipSpec",
    "StyleProfile",
    "get_style_profile",
    "list_style_profiles",
]
