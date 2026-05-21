"""
Animation asset pipeline for GameRewritten engine.

Generates complete character animation library in batch.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from animation_engine.integration.style_profiles import DEFAULT_STYLE_PROFILE_ID

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
        profile_id: str = DEFAULT_STYLE_PROFILE_ID,
    ) -> None:
        from animation_engine.backend import BackendRegistry

        self.backend = BackendRegistry.get(backend, sample_rate=sample_rate, seed=seed)
        self.sample_rate = sample_rate
        self.profile_id = profile_id

    def generate_all(
        self,
        output_dir: str | Path,
        skeleton: Any,
        profile_id: str | None = None,
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
        from animation_engine.integration.style_profiles import get_style_profile
        from animation_engine.model import Model

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        active_profile_id = profile_id or self.profile_id
        profile = get_style_profile(active_profile_id)

        generated: dict[str, str] = {}
        failed: dict[str, str] = {}
        ordered_files: list[dict[str, Any]] = []

        exporter = AnimExporter()

        model = Model("generated_animation_model")
        model.skeleton = skeleton

        for clip_spec in profile.required_clips:
            motion = clip_spec.motion_type
            try:
                clip = self.backend.generate_clip(
                    skeleton=skeleton,
                    motion_type=motion,
                    duration=clip_spec.duration,
                    cadence_scale=profile.cadence_scale,
                    amplitude_scale=profile.amplitude_scale,
                    profile_id=profile.profile_id,
                )
                output_path = output_dir / f"{motion}.anim"
                exporter.export(
                    model,
                    [clip],
                    metadata={
                        "style_profile": profile.profile_id,
                        "style_profile_label": profile.label,
                        "visual_target": profile.visual_target,
                        "gameplay_target": profile.gameplay_target,
                        "reference_titles": list(profile.reference_titles),
                        "motion_type": motion,
                        "duration": clip_spec.duration,
                        "sample_rate": self.sample_rate,
                    },
                    path=str(output_path),
                )
                generated[motion] = str(output_path)
                ordered_files.append(
                    {
                        "motion_type": motion,
                        "path": str(output_path),
                        "duration": clip_spec.duration,
                    }
                )
            except (ValueError, RuntimeError, OSError, TypeError) as exc:
                failed[motion] = str(exc)

        manifest_path = output_dir / "pack_manifest.json"
        manifest = {
            "status": "failed" if failed else "ok",
            "profile_id": profile.profile_id,
            "profile_label": profile.label,
            "visual_target": profile.visual_target,
            "gameplay_target": profile.gameplay_target,
            "reference_titles": list(profile.reference_titles),
            "required_clips": [clip.motion_type for clip in profile.required_clips],
            "ordered_files": ordered_files,
            "expected": len(profile.required_clips),
            "generated": len(generated),
            "files": generated,
            "failed": failed,
            "backend_name": self.backend.name,
            "seed": getattr(self.backend, "seed", None),
            "sample_rate": self.sample_rate,
            "generation_version": 1,
            "manifest_path": str(manifest_path),
        }
        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)

        return manifest
