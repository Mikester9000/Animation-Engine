"""
Profile-aware validation for generated animation packs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from animation_engine.integration import get_style_profile
from animation_engine.qa.loop_analyzer import LoopReport

__all__ = ["StyleValidationReport", "StyleValidator"]


@dataclass
class StyleValidationReport:
    """Validation result for a generated style pack."""

    profile_id: str
    is_valid: bool
    errors: list[str]
    warnings: list[str]
    missing_clips: list[str]
    extra_clips: list[str]

    def summary(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        return (
            f"{status} – profile={self.profile_id}, "
            f"errors={len(self.errors)}, warnings={len(self.warnings)}, "
            f"missing={len(self.missing_clips)}, extra={len(self.extra_clips)}"
        )


class StyleValidator:
    """Validate profile completeness and style-health signals for a pack."""

    # Motions expected to loop seamlessly.
    _CYCLIC_MOTIONS = {"idle", "walk", "run", "jump_loop"}

    def __init__(self, duration_warning_ratio: float = 0.35, duration_error_ratio: float = 0.60):
        self.duration_warning_ratio = duration_warning_ratio
        self.duration_error_ratio = duration_error_ratio

    def validate_pack(
        self,
        manifest: dict[str, Any],
        clip_durations: dict[str, float] | None = None,
        loop_reports: dict[str, LoopReport] | None = None,
    ) -> StyleValidationReport:
        """
        Validate a generated pack using manifest + optional measured clip data.
        """
        errors: list[str] = []
        warnings: list[str] = []
        missing: list[str] = []
        extra: list[str] = []

        profile_id = str(manifest.get("profile_id", "")).strip()
        if not profile_id:
            errors.append("Manifest missing profile_id")
            return StyleValidationReport("unknown", False, errors, warnings, missing, extra)

        try:
            profile = get_style_profile(profile_id)
        except ValueError as exc:
            errors.append(str(exc))
            return StyleValidationReport(profile_id, False, errors, warnings, missing, extra)

        if manifest.get("status") not in (None, "ok"):
            errors.append(f"Manifest status is '{manifest.get('status')}', expected 'ok'")

        expected = [clip.motion_type for clip in profile.required_clips]
        files = manifest.get("files")
        if files is None:
            files = {}
        if not isinstance(files, dict):
            errors.append("Manifest files must be an object")
            files = {}

        ordered_files_present = "ordered_files" in manifest
        ordered_files = manifest.get("ordered_files")
        if ordered_files_present:
            if not isinstance(ordered_files, list):
                errors.append("Manifest ordered_files must be a list")
                ordered_files = []
            actual = []
            seen: set[str] = set()
            duplicates: list[str] = []
            reported_duplicates: set[str] = set()
            for index, entry in enumerate(ordered_files):
                if not isinstance(entry, dict):
                    errors.append(f"Manifest ordered_files[{index}] entries must be objects")
                    continue
                motion = entry.get("motion_type")
                if not isinstance(motion, str):
                    errors.append(
                        f"Manifest ordered_files[{index}] entries must have string motion_type"
                    )
                    continue
                motion = motion.strip()
                if not motion:
                    errors.append(
                        f"Manifest ordered_files[{index}] entries must have non-empty motion_type"
                    )
                    continue
                actual.append(motion)
                if motion in seen and motion not in reported_duplicates:
                    duplicates.append(motion)
                    reported_duplicates.add(motion)
                seen.add(motion)
            if duplicates:
                errors.append(f"Duplicate clip ids: {', '.join(duplicates)}")
        else:
            actual = list(files.keys())

        expected_set = set(expected)
        actual_set = set(actual)
        missing = sorted(expected_set - actual_set)
        extra = sorted(actual_set - expected_set)

        if missing:
            errors.append(f"Missing required clips: {', '.join(missing)}")
        if extra:
            errors.append(f"Unexpected clip ids: {', '.join(extra)}")

        if ordered_files_present and actual and actual != expected:
            errors.append(
                "Clip order mismatch: expected "
                f"{', '.join(expected)}; got {', '.join(actual)}"
            )

        # Optional duration sanity checks.
        if clip_durations:
            expected_duration = {clip.motion_type: clip.duration for clip in profile.required_clips}
            for motion, expected_value in expected_duration.items():
                if motion not in clip_durations:
                    continue
                actual_value = float(clip_durations[motion])
                if expected_value <= 1e-6:
                    continue
                relative_diff = abs(actual_value - expected_value) / expected_value
                if relative_diff > self.duration_error_ratio:
                    errors.append(
                        f"{motion}: duration {actual_value:.3f}s too far from expected "
                        f"{expected_value:.3f}s (diff={relative_diff:.0%})"
                    )
                elif relative_diff > self.duration_warning_ratio:
                    warnings.append(
                        f"{motion}: duration {actual_value:.3f}s differs from expected "
                        f"{expected_value:.3f}s (diff={relative_diff:.0%})"
                    )

        # Optional loop continuity checks on cyclic motions.
        if loop_reports:
            for motion in sorted(self._CYCLIC_MOTIONS):
                report = loop_reports.get(motion)
                if report is None:
                    continue
                if not report.is_seamless:
                    errors.append(
                        f"{motion}: loop not seamless "
                        f"(pos_jump={report.max_position_jump:.3f}, "
                        f"rot_jump={report.max_rotation_jump_deg:.2f}°)"
                    )

        is_valid = len(errors) == 0
        return StyleValidationReport(profile_id, is_valid, errors, warnings, missing, extra)
