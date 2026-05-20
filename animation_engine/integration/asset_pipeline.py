"""
Animation asset pipeline for GameRewritten engine.

Generates complete character animation library in batch.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["AnimationPipeline"]


class AnimationPipeline:
    """Generate all animations for GameRewritten.

    Parameters
    ----------
    backend:
        Animation backend to use (default: "procedural").
    sample_rate:
        Animation FPS (default: 30.0).
    seed:
        Random seed for reproducibility.
    """

    def __init__(
        self,
        backend: str = "procedural",
        sample_rate: float = 30.0,
        seed: int | None = None,
    ) -> None:
        from animation_engine.backend import BackendRegistry

        self.backend = BackendRegistry.get(backend, sample_rate=sample_rate, seed=seed)
        self.sample_rate = sample_rate

    def generate_all(
        self,
        output_dir: str | Path,
        skeleton: Any,
    ) -> dict[str, Any]:
        """Generate complete animation library.

        Parameters
        ----------
        output_dir:
            Output directory for .anim files.
        skeleton:
            Character skeleton to animate.

        Returns
        -------
        dict
            Manifest of generated files.
        """
        from animation_engine.io import AnimExporter
        from animation_engine.model import Model

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        motion_types = ["idle", "walk", "run", "attack"]
        generated: dict[str, str] = {}

        exporter = AnimExporter()

        model = Model("generated_animation_model")
        model.skeleton = skeleton

        for motion in motion_types:
            clip = self.backend.generate_clip(
                skeleton=skeleton,
                motion_type=motion,
                duration=3.0 if motion == "idle" else 1.5,
            )

            output_path = output_dir / f"{motion}.anim"
            exporter.export(model, [clip], path=str(output_path))
            generated[motion] = str(output_path)

        return {
            "generated": len(generated),
            "files": generated,
        }
