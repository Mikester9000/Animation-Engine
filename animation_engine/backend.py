"""
Pluggable animation generation backend interface.

Defines :class:`AnimationBackend` abstract base class. Ships with
:class:`ProceduralBackend` for keyframe-based animation.

Future backends could wrap:
- Motion capture ML models (RNN/Transformer-based)
- Physics-based procedural animation
- Style-transfer motion synthesis
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

__all__ = ["AnimationBackend", "ProceduralBackend", "BackendRegistry"]


class AnimationBackend(ABC):
    """Abstract base class for animation generation backends.

    Parameters
    ----------
    sample_rate:
        Animation sample rate in FPS (frames per second).
    seed:
        Random seed for reproducibility.
    """

    def __init__(self, sample_rate: float = 30.0, seed: int | None = None) -> None:
        self.sample_rate = sample_rate
        self.seed = seed

    @property
    def name(self) -> str:
        """Human-readable backend name."""
        return self.__class__.__name__

    @abstractmethod
    def generate_clip(
        self,
        skeleton: Any,
        motion_type: str,
        duration: float,
        **kwargs: Any,
    ) -> Any:
        """Generate an animation clip.

        Parameters
        ----------
        skeleton:
            Skeleton instance defining bone hierarchy.
        motion_type:
            Type of motion: "idle", "walk", "run", "attack", etc.
        duration:
            Clip duration in seconds.
        **kwargs:
            Backend-specific parameters.

        Returns
        -------
        AnimationClip
            Generated animation clip.
        """

    def is_available(self) -> bool:
        """Return True if backend dependencies are installed."""
        return True

    def supported_motion_types(self) -> tuple[str, ...]:
        """Return supported motion types."""
        return ("idle", "walk", "run", "attack")


class ProceduralBackend(AnimationBackend):
    """Keyframe-based procedural animation backend.

    Uses existing AnimationClip keyframe system to generate simple
    procedural animations. This is the default fallback with zero
    external dependencies.
    """

    @property
    def name(self) -> str:
        return "procedural"

    def generate_clip(
        self,
        skeleton: Any,
        motion_type: str,
        duration: float,
        **kwargs: Any,
    ) -> Any:
        """Generate clip using keyframe interpolation."""
        from animation_engine.animation import AnimationClip
        from animation_engine.animation.channel import ChannelTarget

        clip = AnimationClip(motion_type, fps=self.sample_rate, loop=True)

        # Generate simple procedural keyframes based on motion type
        if motion_type == "idle":
            # Slight breathing motion on spine
            if skeleton and len(skeleton.bones) > 1:
                spine_name = skeleton.bones[1].name if len(skeleton.bones) > 1 else "root"
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(
                    spine_name,
                    ChannelTarget.ROTATION,
                    duration / 2,
                    [0, 0.02, 0, 0.9998],
                )
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])

        elif motion_type == "walk":
            # Simple walk cycle on root
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                step_duration = duration / 4  # 4 steps in duration
                for i in range(5):
                    t = i * step_duration
                    y_offset = 0.1 if i % 2 == 0 else -0.1
                    clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, t, [0, y_offset, 0])

        elif motion_type == "run":
            # Faster cycle
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                step_duration = duration / 6  # 6 steps in duration
                for i in range(7):
                    t = i * step_duration
                    y_offset = 0.15 if i % 2 == 0 else -0.15
                    clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, t, [0, y_offset, 0])

        elif motion_type == "attack":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.4, [0, 0, 0.25])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        return clip


class BackendRegistry:
    """Registry of available :class:`AnimationBackend` implementations.

    Example
    -------
    >>> BackendRegistry.register("ml_motion", MLMotionBackend)
    >>> backend = BackendRegistry.get("ml_motion", sample_rate=30.0)
    """

    _registry: dict[str, type[AnimationBackend]] = {
        "procedural": ProceduralBackend,
    }

    @classmethod
    def register(cls, name: str, backend_class: type[AnimationBackend]) -> None:
        """Register a new backend implementation.

        Parameters
        ----------
        name:
            Backend identifier (e.g. "ml_motion").
        backend_class:
            Class implementing AnimationBackend.
        """
        cls._registry[name] = backend_class

    @classmethod
    def get(cls, name: str = "procedural", **kwargs: Any) -> AnimationBackend:
        """Instantiate a backend by name.

        Parameters
        ----------
        name:
            Backend identifier.
        **kwargs:
            Passed to backend constructor.

        Returns
        -------
        AnimationBackend
        """
        if name not in cls._registry:
            available = ", ".join(sorted(cls._registry))
            raise ValueError(f"Unknown backend '{name}'. Available: {available}")
        return cls._registry[name](**kwargs)

    @classmethod
    def available_backends(cls) -> list[str]:
        """Return sorted list of registered backend names."""
        return sorted(cls._registry)
