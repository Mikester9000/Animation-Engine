"""Command-line interface for Animation Engine QA and backend utilities."""

from __future__ import annotations

import argparse


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


def build_parser() -> argparse.ArgumentParser:
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
