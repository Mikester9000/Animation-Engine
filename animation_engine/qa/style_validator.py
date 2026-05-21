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
        clip_metadata: dict[str, dict[str, Any] | None] | None = None,
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
        expected_duration = {
            clip.motion_type: float(getattr(clip, "duration", 0.0))
            for clip in profile.required_clips
        }

        if manifest.get("visual_target") != profile.visual_target:
            errors.append("Manifest visual_target does not match selected profile")
        if manifest.get("gameplay_target") != profile.gameplay_target:
            errors.append("Manifest gameplay_target does not match selected profile")
        if manifest.get("reference_titles") != list(profile.reference_titles):
            errors.append("Manifest reference_titles do not match selected profile")

        manifest_required = manifest.get("required_clips")
        if manifest_required is not None and manifest_required != expected:
            errors.append("Manifest required_clips does not match selected profile requirements")

        manifest_expected = manifest.get("expected")
        if manifest_expected is not None and manifest_expected != len(expected):
            errors.append(
                f"Manifest expected={manifest_expected} does not match required count {len(expected)}"
            )

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

        manifest_generated = manifest.get("generated")
        if manifest_generated is not None and manifest_generated != len(actual):
            errors.append(
                f"Manifest generated={manifest_generated} does not match discovered clips {len(actual)}"
            )

        manifest_failed = manifest.get("failed")
        if manifest.get("status") == "ok" and manifest_failed:
            errors.append("Manifest status is ok but failed clip list is not empty")

        # Optional duration sanity checks.
        if clip_durations:
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

        if clip_metadata:
            for motion in expected:
                metadata = clip_metadata.get(motion)
                if not isinstance(metadata, dict):
                    errors.append(f"{motion}: missing metadata for style validation")
                    continue
                if metadata.get("style_profile") != profile.profile_id:
                    errors.append(
                        f"{motion}: metadata style_profile {metadata.get('style_profile')!r} "
                        f"!= {profile.profile_id!r}"
                    )
                if metadata.get("motion_type") != motion:
                    errors.append(
                        f"{motion}: metadata motion_type {metadata.get('motion_type')!r} "
                        f"!= {motion!r}"
                    )
                if metadata.get("visual_target") != profile.visual_target:
                    errors.append(f"{motion}: metadata visual_target does not match profile")
                if metadata.get("gameplay_target") != profile.gameplay_target:
                    errors.append(f"{motion}: metadata gameplay_target does not match profile")
                if metadata.get("reference_titles") != list(profile.reference_titles):
                    errors.append(f"{motion}: metadata reference_titles do not match profile")
                if motion in expected_duration:
                    metadata_duration = metadata.get("duration")
                    if not isinstance(metadata_duration, (int, float)):
                        errors.append(f"{motion}: metadata duration missing or not numeric")
                    else:
                        diff = abs(float(metadata_duration) - expected_duration[motion])
                        if diff > 1e-6:
                            errors.append(
                                f"{motion}: metadata duration {float(metadata_duration):.3f}s "
                                f"!= expected {expected_duration[motion]:.3f}s"
                            )
                sample_rate = metadata.get("sample_rate")
                if not isinstance(sample_rate, (int, float)):
                    errors.append(f"{motion}: metadata sample_rate missing or wrong type")
                elif float(sample_rate) <= 0.0:
                    errors.append(f"{motion}: metadata sample_rate must be > 0 (got {sample_rate})")

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
