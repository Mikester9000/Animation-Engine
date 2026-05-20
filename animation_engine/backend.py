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
        return (
            "idle",
            "walk",
            "run",
            "attack",
            "defend",
            "cast",
            "hit_react",
            "dodge",
            "jump_start",
            "jump_loop",
            "jump_land",
            "victory",
            "turn_left",
            "turn_right",
            "crouch",
        )


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
        # Clamp to avoid divide-by-zero / near-zero step durations.
        cadence_scale = max(float(kwargs.get("cadence_scale", 1.0)), 1e-3)
        amplitude_scale = float(kwargs.get("amplitude_scale", 1.0))

        # Generate simple procedural keyframes based on motion type
        if motion_type == "idle":
            # Slight breathing motion on spine
            if skeleton and len(skeleton.bones) > 1:
                spine_name = skeleton.bones[1].name
                breathe_rotation = [0, 0.02 * amplitude_scale, 0, 0.9998]
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(
                    spine_name,
                    ChannelTarget.ROTATION,
                    duration / (2 * cadence_scale),
                    breathe_rotation,
                )
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])

        elif motion_type == "walk":
            # Simple walk cycle on root
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                step_duration = duration / (4 * cadence_scale)
                for i in range(5):
                    t = i * step_duration
                    y_offset = (0.1 if i % 2 == 0 else -0.1) * amplitude_scale
                    clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, t, [0, y_offset, 0])

        elif motion_type == "run":
            # Faster cycle
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                step_duration = duration / (6 * cadence_scale)
                for i in range(7):
                    t = i * step_duration
                    y_offset = (0.15 if i % 2 == 0 else -0.15) * amplitude_scale
                    clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, t, [0, y_offset, 0])

        elif motion_type == "attack":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.4,
                    [0, 0, 0.25 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "defend":
            if skeleton and len(skeleton.bones) > 1:
                spine_name = skeleton.bones[1].name
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(
                    spine_name,
                    ChannelTarget.ROTATION,
                    duration * 0.35,
                    [0.03 * amplitude_scale, 0, 0, 0.9995],
                )
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])

        elif motion_type == "cast":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.5,
                    [0, 0.05 * amplitude_scale, -0.08 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "hit_react":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.2,
                    [0, 0, -0.12 * amplitude_scale],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "dodge":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.3,
                    [0.2 * amplitude_scale, 0, 0],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "jump_start":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration,
                    [0, 0.25 * amplitude_scale, 0.08 * amplitude_scale],
                )

        elif motion_type == "jump_loop":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                peak = 0.3 * amplitude_scale
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, peak, 0])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration * 0.5, [0, peak, 0])
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, peak, 0])

        elif motion_type == "jump_land":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    0.0,
                    [0, 0.2 * amplitude_scale, 0],
                )
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.4,
                    [0, -0.08 * amplitude_scale, 0],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        elif motion_type == "victory":
            if skeleton and len(skeleton.bones) > 1:
                spine_name = skeleton.bones[1].name
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(
                    spine_name,
                    ChannelTarget.ROTATION,
                    duration * 0.5,
                    [0, 0.08 * amplitude_scale, 0, 0.9968],
                )
                clip.add_keyframe(spine_name, ChannelTarget.ROTATION, duration, [0, 0, 0, 1])

        elif motion_type in {"turn_left", "turn_right"}:
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                direction = 1.0 if motion_type == "turn_left" else -1.0
                clip.add_keyframe(root_name, ChannelTarget.ROTATION, 0.0, [0, 0, 0, 1])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.ROTATION,
                    duration,
                    [0, direction * 0.15 * amplitude_scale, 0, 0.9887],
                )

        elif motion_type == "crouch":
            if skeleton and len(skeleton.bones) > 0:
                root_name = skeleton.bones[0].name
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
                clip.add_keyframe(
                    root_name,
                    ChannelTarget.TRANSLATION,
                    duration * 0.5,
                    [0, -0.12 * amplitude_scale, 0],
                )
                clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, duration, [0, 0, 0])

        # keep deterministic fallback for unknown motion identifiers
        if not clip.channels and skeleton and len(skeleton.bones) > 0:
            root_name = skeleton.bones[0].name
            clip.add_keyframe(root_name, ChannelTarget.TRANSLATION, 0.0, [0, 0, 0])
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
        if not (isinstance(backend_class, type) and issubclass(backend_class, AnimationBackend)):
            raise TypeError(
                f"backend_class must be a subclass of AnimationBackend, got {backend_class!r}"
            )
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
