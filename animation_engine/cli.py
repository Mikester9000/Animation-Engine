"""Command-line interface for Animation Engine QA and backend utilities."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _cmd_validate_clip(args: argparse.Namespace) -> int:
    """Validate animation clip correctness."""
    from animation_engine.io import AnimImporter
    from animation_engine.qa import ClipValidator

    print(f"Loading {args.input}...")
    _, clips, _ = AnimImporter().import_file(args.input)
    validator = ClipValidator()

    all_valid = True
    for clip in clips:
        report = validator.validate_clip(clip)
        print(f"\nClip '{clip.name}': {report.summary()}")
        if report.errors:
            all_valid = False
            for err in report.errors:
                print(f"  ERROR: {err}")
        for warn in report.warnings:
            print(f"  WARN: {warn}")

    if not all_valid:
        return 1
    return 0


def _cmd_validate_skeleton(args: argparse.Namespace) -> int:
    """Validate skeleton hierarchy."""
    from animation_engine.io import AnimImporter
    from animation_engine.qa import SkeletonValidator

    print(f"Loading {args.input}...")
    model, _, _ = AnimImporter().import_file(args.input)
    validator = SkeletonValidator()

    if model.skeleton:
        report = validator.validate_skeleton(model.skeleton)
        print(f"\nSkeleton '{model.skeleton.name}': {report.summary()}")
        if report.errors:
            for err in report.errors:
                print(f"  ERROR: {err}")
            return 1
        for warn in report.warnings:
            print(f"  WARN: {warn}")
    else:
        print("ERROR: No skeleton found in file")
        return 1

    return 0


def _cmd_check_loop(args: argparse.Namespace) -> int:
    """Analyze loop boundary quality."""
    from animation_engine.io import AnimImporter
    from animation_engine.qa import LoopAnalyzer

    print(f"Loading {args.input}...")
    _, clips, _ = AnimImporter().import_file(args.input)
    analyzer = LoopAnalyzer()

    all_seamless = True
    for clip in clips:
        report = analyzer.analyze_clip(clip)
        print(f"\nClip '{clip.name}': {report.summary()}")
        if not report.is_seamless:
            all_seamless = False

    if not all_seamless:
        return 1
    return 0


def _cmd_list_backends(args: argparse.Namespace) -> int:
    """List available animation backends."""
    del args
    from animation_engine.backend import BackendRegistry

    backends = BackendRegistry.available_backends()
    print("Available animation backends:")
    for name in backends:
        backend = BackendRegistry.get(name)
        status = "✓" if backend.is_available() else "✗"
        print(f"  {status} {name:20} — {', '.join(backend.supported_motion_types())}")

    return 0


def _manifest_backend_name(manifest: dict[str, Any]) -> Any:
    """Return the backend name from a pack manifest.

    Parameters
    ----------
    manifest:
        Parsed manifest JSON object.

    Returns
    -------
    Any
        `backend_name` when present, otherwise the legacy `backend` value.
    """
    backend_name = manifest.get("backend_name")
    if backend_name is not None:
        return backend_name
    return manifest.get("backend")


def _cmd_generate_pack(args: argparse.Namespace) -> int:
    """Generate a full profile pack from a source skeleton .anim."""
    from animation_engine.integration import AnimationPipeline
    from animation_engine.io import AnimImporter

    print(f"Loading skeleton source: {args.skeleton_anim}")
    model, _, _ = AnimImporter().import_file(args.skeleton_anim)
    if model.skeleton is None:
        print("ERROR: Source file does not contain a skeleton")
        return 1

    pipeline = AnimationPipeline(
        backend=args.backend,
        sample_rate=args.sample_rate,
        seed=args.seed,
        profile_id=args.profile,
    )
    manifest = pipeline.generate_all(args.output_dir, model.skeleton)

    # Optional override location for manifest output.
    if args.manifest_out:
        manifest_out = Path(args.manifest_out)
        manifest_out.parent.mkdir(parents=True, exist_ok=True)
        manifest["manifest_path"] = str(manifest_out)
        with open(manifest_out, "w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)

    # Strict mode: fail if any clip failed OR if any warning-level issue exists.
    if args.strict and manifest.get("failed"):
        print("STRICT MODE: generation failures are not allowed")
        return 1

    print("Pack generation summary:")
    print(f"  profile:        {manifest.get('profile_id')}")
    print(f"  schema_version: {manifest.get('schema_version', 'n/a')}")
    print(f"  status:         {manifest.get('status')}")
    print(f"  generated:      {manifest.get('generated')}/{manifest.get('expected')}")
    print(f"  backend:        {_manifest_backend_name(manifest)}")
    print(f"  seed:           {manifest.get('seed')}")
    print(f"  manifest:       {manifest.get('manifest_path')}")
    category_coverage = (manifest.get("gameplay_semantic") or {}).get("category_coverage", {})
    if category_coverage:
        print("  categories:")
        for cat, clips in sorted(category_coverage.items()):
            print(f"    {cat}: {len(clips)} clips")
    if manifest.get("failed"):
        for motion, reason in sorted(manifest["failed"].items()):
            print(f"  FAILED {motion}: {reason}")

    return 0 if manifest.get("status") == "ok" else 1


def _cmd_validate_pack(args: argparse.Namespace) -> int:
    """Run clip/skeleton/loop/style validation across a generated pack."""
    from animation_engine.io import AnimImporter
    from animation_engine.qa import ClipValidator, LoopAnalyzer, SkeletonValidator, StyleValidator

    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"ERROR: Manifest not found: {manifest_path}")
        return 1

    with open(manifest_path, "r", encoding="utf-8") as fh:
        manifest = json.load(fh)

    files = manifest.get("files")
    if files is None:
        files = {}
    ordered_files_present = "ordered_files" in manifest
    ordered_files = manifest.get("ordered_files")
    if ordered_files is None:
        ordered_files = []
    if not isinstance(files, dict):
        print("ERROR: Manifest files must be an object")
        return 1
    if ordered_files_present and not isinstance(ordered_files, list):
        print("ERROR: Manifest ordered_files must be a list")
        return 1
    if not files and not ordered_files:
        print("ERROR: Manifest has no files to validate")
        return 1

    clip_validator = ClipValidator()
    loop_analyzer = LoopAnalyzer()
    skeleton_validator = SkeletonValidator()
    style_validator = StyleValidator()

    all_valid = True
    clip_durations: dict[str, float] = {}
    loop_reports = {}
    clip_metadata: dict[str, dict[str, Any] | None] = {}
    profile_id = str(manifest.get("profile_id", "")).strip()

    # Structured report data (for --json-report output).
    clip_reports_data: list[dict[str, Any]] = []

    if ordered_files:
        file_entries = []
        for index, entry in enumerate(ordered_files):
            if not isinstance(entry, dict):
                print(f"ERROR: Manifest ordered_files[{index}] must be an object")
                return 1
            motion = str(entry.get("motion_type", "")).strip()
            file_path = str(entry.get("path", "")).strip()
            if not motion or not file_path:
                print(
                    f"ERROR: Manifest ordered_files[{index}] missing motion_type/path "
                    f"(motion_type={motion!r}, path={file_path!r})"
                )
                return 1
            file_entries.append((motion, file_path))
    else:
        file_entries = sorted(files.items())

    for motion, file_path in file_entries:
        path = Path(file_path)
        if not path.is_absolute():
            path = manifest_path.parent / path
        if not path.exists():
            all_valid = False
            print(f"ERROR [{motion}]: file missing -> {path}")
            clip_reports_data.append({"motion": motion, "status": "missing_file"})
            continue

        model, clips, _, metadata = AnimImporter().import_file(str(path), include_metadata=True)
        if model.skeleton is None:
            all_valid = False
            print(f"ERROR [{motion}]: no skeleton in file")
            clip_reports_data.append({"motion": motion, "status": "no_skeleton"})
            continue

        skel_report = skeleton_validator.validate_skeleton(model.skeleton)
        if not skel_report.is_valid:
            all_valid = False
            print(f"ERROR [{motion}] skeleton: {skel_report.summary()}")
            for err in skel_report.errors:
                print(f"  ERROR: {err}")

        if not clips:
            all_valid = False
            print(f"ERROR [{motion}]: no clips in file")
            clip_reports_data.append({"motion": motion, "status": "no_clips"})
            continue

        for clip in clips:
            clip_durations[motion] = clip.duration
            clip_report = clip_validator.validate_clip(clip)
            loop_report = loop_analyzer.analyze_clip(clip)
            loop_reports[motion] = loop_report
            print(f"[{motion}] clip={clip.name} | {clip_report.summary()} | {loop_report.summary()}")
            if not clip_report.is_valid:
                all_valid = False
                for err in clip_report.errors:
                    print(f"  ERROR: {err}")
            for warn in clip_report.warnings:
                print(f"  WARN: {warn}")
            clip_reports_data.append(
                {
                    "motion": motion,
                    "clip_name": clip.name,
                    "clip_valid": clip_report.is_valid,
                    "clip_errors": clip_report.errors,
                    "clip_warnings": clip_report.warnings,
                    "loop_seamless": loop_report.is_seamless,
                }
            )

        style_profile = metadata.get("style_profile") if metadata is not None else None
        if style_profile and style_profile != profile_id:
            all_valid = False
            print(
                f"ERROR [{motion}]: metadata style_profile "
                f"{style_profile} != manifest profile_id {profile_id}"
            )
        clip_metadata[motion] = metadata if isinstance(metadata, dict) else None

    style_report = style_validator.validate_pack(
        manifest,
        clip_durations=clip_durations,
        loop_reports=loop_reports,
        clip_metadata=clip_metadata,
    )
    print(f"\nStyle report: {style_report.summary()}")
    for err in style_report.errors:
        print(f"  ERROR: {err}")
    for warn in style_report.warnings:
        print(f"  WARN: {warn}")
    if not style_report.is_valid:
        all_valid = False

    # Optionally emit machine-readable JSON report.
    json_report_path = getattr(args, "json_report", None)
    if json_report_path:
        report_obj = {
            "manifest": str(manifest_path),
            "profile_id": profile_id,
            "overall_valid": all_valid,
            "style_report": {
                "is_valid": style_report.is_valid,
                "errors": style_report.errors,
                "warnings": style_report.warnings,
                "missing_clips": style_report.missing_clips,
                "extra_clips": style_report.extra_clips,
            },
            "clips": clip_reports_data,
        }
        report_out = Path(json_report_path)
        report_out.parent.mkdir(parents=True, exist_ok=True)
        with open(report_out, "w", encoding="utf-8") as fh:
            json.dump(report_obj, fh, indent=2)
        print(f"\nJSON report written to: {report_out}")

    return 0 if all_valid else 1


def build_parser() -> argparse.ArgumentParser:
    from animation_engine.integration.style_profiles import DEFAULT_STYLE_PROFILE_ID

    parser = argparse.ArgumentParser(prog="animation-engine")
    subparsers = parser.add_subparsers(dest="command")

    # validate-clip command
    validate_clip_parser = subparsers.add_parser(
        "validate-clip",
        help="Validate animation clip for errors",
    )
    validate_clip_parser.add_argument("--input", required=True, help="Input .anim file")
    validate_clip_parser.set_defaults(func=_cmd_validate_clip)

    # validate-skeleton command
    validate_skeleton_parser = subparsers.add_parser(
        "validate-skeleton",
        help="Validate skeleton hierarchy",
    )
    validate_skeleton_parser.add_argument("--input", required=True, help="Input .anim file")
    validate_skeleton_parser.set_defaults(func=_cmd_validate_skeleton)

    # check-loop command
    check_loop_parser = subparsers.add_parser(
        "check-loop",
        help="Analyze animation loop quality",
    )
    check_loop_parser.add_argument("--input", required=True, help="Input .anim file")
    check_loop_parser.set_defaults(func=_cmd_check_loop)

    # list-backends command
    list_backends_parser = subparsers.add_parser(
        "list-backends",
        help="List available animation backends",
    )
    list_backends_parser.set_defaults(func=_cmd_list_backends)

    # generate-pack command
    generate_pack_parser = subparsers.add_parser(
        "generate-pack",
        help="Generate a full profile animation pack",
    )
    generate_pack_parser.add_argument(
        "--skeleton-anim",
        required=True,
        help="Source .anim file containing the skeleton",
    )
    generate_pack_parser.add_argument(
        "--output-dir",
        required=True,
        help="Output directory for generated pack files",
    )
    generate_pack_parser.add_argument(
        "--profile",
        default=DEFAULT_STYLE_PROFILE_ID,
        help="Style profile ID (e.g. ff7_ps2, ff7_psx (alias for ff7_ps2), ff8_ps2, ff9_ps2, ff10_ps2, ff12_ps2)",
    )
    generate_pack_parser.add_argument(
        "--backend",
        default="procedural",
        help="Backend name used for clip generation",
    )
    generate_pack_parser.add_argument(
        "--sample-rate",
        type=float,
        default=30.0,
        help="Generated clip sample rate (FPS)",
    )
    generate_pack_parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Optional deterministic seed",
    )
    generate_pack_parser.add_argument(
        "--manifest-out",
        default=None,
        help="Optional explicit path for copied manifest JSON",
    )
    generate_pack_parser.add_argument(
        "--strict",
        action="store_true",
        default=False,
        help="Fail with non-zero exit code if any clip generation fails",
    )
    generate_pack_parser.set_defaults(func=_cmd_generate_pack)

    # validate-pack command
    validate_pack_parser = subparsers.add_parser(
        "validate-pack",
        help="Validate generated pack quality gates using pack_manifest.json",
    )
    validate_pack_parser.add_argument(
        "--manifest",
        required=True,
        help="Path to generated pack_manifest.json",
    )
    validate_pack_parser.add_argument(
        "--json-report",
        default=None,
        metavar="PATH",
        help="Write machine-readable JSON validation report to PATH",
    )
    validate_pack_parser.set_defaults(func=_cmd_validate_pack)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if not hasattr(args, "func"):
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
