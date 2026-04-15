#!/usr/bin/env python3
"""
compat/anim_to_cpp_header.py
==============================
Converts a .anim JSON file (exported by Animation Engine) into a C++ header
that embeds the animation data as plain C++ structs and arrays.

This approach requires **zero runtime dependencies** in the Game Engine for
Teaching — no JSON parser, no external libraries.  The C++ Game Engine just
``#include``s the generated header alongside GameEngineCompat.hpp.

Usage
-----
::

    python compat/anim_to_cpp_header.py assets/noctis.anim > noctis_anim.hpp

    # With a custom C++ namespace identifier:
    python compat/anim_to_cpp_header.py assets/noctis.anim --var NOCTIS

Then in your C++ Game Engine source::

    #include "compat/GameEngineCompat.hpp"
    #include "noctis_anim.hpp"             // defines AE_AnimPackage NOCTIS

    // Load at startup
    AE_AnimPackage& pkg = NOCTIS;

    // Attach to entity
    AnimationComponent ac;
    ac.package  = &pkg;
    ac.clipName = "idle";
    world.AddComponent(hero, ac);

TEACHING NOTE — Pre-baked Data vs. Runtime Parsing
----------------------------------------------------
Two integration strategies exist:

1. **Runtime parsing** (``AnimLoader::Load``): the .anim JSON file ships
   with the game, is opened at runtime, and parsed by the built-in JSON parser
   in GameEngineCompat.hpp.  Pros: easy to swap assets; Cons: small runtime
   cost and file I/O dependency.

2. **Pre-baked header** (this script): the .anim data is compiled directly
   into the executable.  Pros: zero runtime I/O, zero JSON parsing overhead,
   no asset file required at runtime; Cons: the game must be recompiled when
   animations change.  Ideal for small student projects.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, List


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ident(text: str) -> str:
    """Convert an arbitrary string into a valid C++ identifier."""
    s = re.sub(r"[^A-Za-z0-9_]", "_", text)
    if s and s[0].isdigit():
        s = "_" + s
    return s or "_unnamed"


def _float_list(values: List[Any], indent: int = 0) -> str:
    """Format a flat list of floats as a C initialiser list."""
    pad = " " * indent
    items = ", ".join(f"{float(v):.8f}f" for v in values)
    return f"{{{items}}}"


# ---------------------------------------------------------------------------
# Code generators
# ---------------------------------------------------------------------------

def _gen_keyframe(kf: dict, target: str) -> str:
    """Emit a single AE_Keyframe initialiser."""
    time = float(kf.get("time", 0.0))
    raw_val = kf.get("value", 0.0)
    raw_in  = kf.get("in_tangent", 0.0)
    raw_out = kf.get("out_tangent", 0.0)
    interp  = kf.get("interp", "LINEAR")

    def _pad4(v: Any) -> List[float]:
        """Pad a scalar or list to 4 floats; rotation w defaults to 1."""
        if isinstance(v, (int, float)):
            return [float(v), 0.0, 0.0, 0.0]
        lst = [float(x) for x in v]
        while len(lst) < 4:
            lst.append(1.0 if (target == "ROTATION" and len(lst) == 3) else 0.0)
        return lst[:4]

    val = _pad4(raw_val)
    tin  = _pad4(raw_in)
    tout = _pad4(raw_out)

    interp_map = {"STEP": "AE_Keyframe::STEP",
                  "LINEAR": "AE_Keyframe::LINEAR",
                  "CUBIC": "AE_Keyframe::CUBIC"}
    interp_str = interp_map.get(interp, "AE_Keyframe::LINEAR")

    return (
        f"        AE_Keyframe{{"
        f"{time:.8f}f, "
        f"{_float_list(val)}, "
        f"{_float_list(tin)}, "
        f"{_float_list(tout)}, "
        f"{interp_str}"
        f"}}"
    )


def _gen_channel(ch: dict, clip_var: str, ch_idx: int) -> List[str]:
    """Emit the keyframe array and AE_Channel for one channel."""
    lines: List[str] = []
    bone  = ch.get("bone_name", "root")
    tgt   = ch.get("target", "TRANSLATION")
    kfs   = ch.get("keyframes", [])

    tgt_map = {
        "TRANSLATION": "AE_Channel::TRANSLATION",
        "ROTATION":    "AE_Channel::ROTATION",
        "SCALE":       "AE_Channel::SCALE",
        "WEIGHT":      "AE_Channel::WEIGHT",
    }
    tgt_str = tgt_map.get(tgt, "AE_Channel::TRANSLATION")

    kf_var = f"{clip_var}_ch{ch_idx}_kfs"

    if kfs:
        lines.append(f"    // Channel {ch_idx}: {bone} {tgt}")
        lines.append(f"    static const AE_Keyframe {kf_var}[] = {{")
        for kf in kfs:
            lines.append(_gen_keyframe(kf, tgt) + ",")
        lines.append(f"    }};")
    else:
        # Zero-length keyframe array — use a null reference trick
        lines.append(f"    // Channel {ch_idx}: {bone} {tgt} (no keyframes)")
        kf_var = "nullptr"  # handled below

    return lines, kf_var, tgt_str, bone, len(kfs)


def _gen_clip(clip: dict, pkg_var: str, clip_idx: int) -> List[str]:
    """Emit the full AE_AnimClip initialiser block."""
    lines: List[str] = []
    name  = clip.get("name", f"clip_{clip_idx}")
    fps   = float(clip.get("fps", 30.0))
    loop  = "true" if clip.get("loop", True) else "false"
    chs   = clip.get("channels", [])

    clip_var = f"{pkg_var}_clip{clip_idx}"

    # Emit keyframe arrays for each channel
    ch_meta = []  # (kf_var, kf_count, tgt_str, bone_name)
    for i, ch in enumerate(chs):
        ch_lines, kf_var, tgt_str, bone, kf_count = _gen_channel(
            ch, clip_var, i)
        lines.extend(ch_lines)
        ch_meta.append((kf_var, kf_count, tgt_str, bone))

    # Emit the AE_AnimClip
    lines.append(f"    // Clip: {name}")
    lines.append(f"    AE_AnimClip {clip_var};")
    lines.append(f"    {clip_var}.name = {json.dumps(name)};")
    lines.append(f"    {clip_var}.fps  = {fps:.2f}f;")
    lines.append(f"    {clip_var}.loop = {loop};")

    for (kf_var, kf_count, tgt_str, bone) in ch_meta:
        lines.append(f"    {{")
        lines.append(f"        AE_Channel ch;")
        lines.append(f"        ch.boneName = {json.dumps(bone)};")
        lines.append(f"        ch.target   = {tgt_str};")
        if kf_var != "nullptr" and kf_count > 0:
            lines.append(
                f"        ch.keyframes.assign({kf_var}, "
                f"{kf_var} + {kf_count});"
            )
        lines.append(f"        {clip_var}.channels.push_back(ch);")
        lines.append(f"    }}")

    lines.append(f"    pkg.clips.push_back({clip_var});")
    lines.append("")
    return lines


def _gen_bone(bone: dict) -> List[str]:
    """Emit an AE_Bone push_back block."""
    lines: List[str] = []
    name = bone.get("name", "bone")
    idx  = int(bone.get("index", 0))
    pid  = int(bone.get("parent_index", -1))
    lt   = bone.get("local_transform", {})
    # The Python exporter uses "position" as the translation key; also accept "translation"
    tr   = lt.get("position", lt.get("translation", [0, 0, 0]))
    rot  = lt.get("rotation", [0, 0, 0, 1])
    sc   = lt.get("scale", [1, 1, 1])
    inv  = bone.get("inverse_bind", [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1])

    while len(tr) < 3: tr.append(0.0)
    while len(rot) < 4: rot.append(1.0 if len(rot) == 3 else 0.0)
    while len(sc) < 3: sc.append(1.0)
    while len(inv) < 16: inv.append(0.0)

    # Format inverse_bind as a multi-column array for readability
    inv_rows = []
    for row in range(4):
        cols = ", ".join(f"{float(inv[row*4+col]):.8f}f" for col in range(4))
        inv_rows.append(f"            {cols}")
    inv_str = ",\n".join(inv_rows)

    lines += [
        f"    {{",
        f"        AE_Bone b;",
        f"        b.name        = {json.dumps(name)};",
        f"        b.index       = {idx};",
        f"        b.parentIndex = {pid};",
        f"        b.localBind.translation = {{{float(tr[0]):.8f}f, {float(tr[1]):.8f}f, {float(tr[2]):.8f}f}};",
        f"        b.localBind.rotation    = {{{float(rot[0]):.8f}f, {float(rot[1]):.8f}f, {float(rot[2]):.8f}f, {float(rot[3]):.8f}f}};",
        f"        b.localBind.scale       = {{{float(sc[0]):.8f}f, {float(sc[1]):.8f}f, {float(sc[2]):.8f}f}};",
        f"        b.inverseBind = {{",
        f"{inv_str}",
        f"        }};",
        f"        pkg.skeleton.bones.push_back(b);",
        f"    }}",
    ]
    return lines


def _gen_morph_track(mt: dict, pkg_var: str, mt_idx: int) -> List[str]:
    """Emit an AE_MorphTrack push_back block."""
    lines: List[str] = []
    morph_name = mt.get("morph_name", f"morph_{mt_idx}")
    kfs = mt.get("keyframes", [])

    kf_var = f"{pkg_var}_mt{mt_idx}_kfs"
    if kfs:
        lines.append(f"    // MorphTrack: {morph_name}")
        lines.append(f"    static const AE_Keyframe {kf_var}[] = {{")
        for kf in kfs:
            lines.append(_gen_keyframe(kf, "WEIGHT") + ",")
        lines.append(f"    }};")

    lines += [
        f"    {{",
        f"        AE_MorphTrack mt;",
        f"        mt.morphName = {json.dumps(morph_name)};",
    ]
    if kfs:
        lines.append(
            f"        mt.keyframes.assign({kf_var}, {kf_var} + {len(kfs)});"
        )
    lines += [
        f"        pkg.morphTracks.push_back(mt);",
        f"    }}",
        "",
    ]
    return lines


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate(payload: dict, var_name: str) -> str:
    """
    Generate a complete C++ header string from a .anim payload dict.

    Parameters
    ----------
    payload   : Parsed .anim JSON dict.
    var_name  : C++ identifier for the exported AE_AnimPackage variable.

    Returns
    -------
    C++ header source as a string.
    """
    model_data = payload.get("model", {})
    model_name = model_data.get("name", "Model")
    skel_data  = model_data.get("skeleton") or {}
    clips      = payload.get("clips", [])
    morph_trks = payload.get("morph_tracks", [])

    guard = f"AE_BAKED_{var_name}_HPP"
    pkg   = f"_ae_{var_name.lower()}_pkg"  # internal static var

    lines: List[str] = [
        f"// AUTO-GENERATED by anim_to_cpp_header.py — DO NOT EDIT",
        f"// Source model: {model_name}",
        f"// Clips: {len(clips)}  |  Bones: {len(skel_data.get('bones', []))}",
        f"// Morph tracks: {len(morph_trks)}",
        f"//",
        f"// Usage:",
        f"//   #include \"compat/GameEngineCompat.hpp\"",
        f"//   #include \"this_file.hpp\"",
        f"//   AnimationComponent ac; ac.package = &{var_name};",
        f"",
        f"#pragma once",
        f"#ifndef {guard}",
        f"#define {guard}",
        f"",
        f"#include \"compat/GameEngineCompat.hpp\"",
        f"",
        f"// ---------------------------------------------------------------",
        f"// Builder function — called once to populate the package.",
        f"// static local ensures the data is initialised at most once.",
        f"// ---------------------------------------------------------------",
        f"inline AE_AnimPackage& {var_name}() {{",
        f"    static AE_AnimPackage pkg;",
        f"    static bool init = false;",
        f"    if (init) return pkg;",
        f"    init = true;",
        f"",
        f"    // ---- Model metadata ------------------------------------------",
        f"    pkg.name = {json.dumps(model_name)};",
        f"    pkg.skeleton.name = {json.dumps(skel_data.get('name', 'Skeleton'))};",
        f"",
    ]

    # Bones
    for bone in skel_data.get("bones", []):
        lines += _gen_bone(bone)

    lines.append("")

    # Clips
    for i, clip in enumerate(clips):
        lines += _gen_clip(clip, var_name, i)

    # Morph tracks
    for i, mt in enumerate(morph_trks):
        lines += _gen_morph_track(mt, var_name, i)

    lines += [
        f"    return pkg;",
        f"}}",
        f"",
        f"// Convenience: global reference so callers can write &{var_name}",
        f"// e.g.: ac.package = &{var_name};",
        f"static AE_AnimPackage& {var_name} = {var_name}();",
        f"",
        f"#endif // {guard}",
        f"",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert a .anim file to a C++ header with pre-baked data."
    )
    parser.add_argument("input", help="Path to the .anim file")
    parser.add_argument(
        "--var",
        default=None,
        help="C++ variable name (default: derived from filename)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output file path (default: stdout)",
    )
    args = parser.parse_args()

    # Read input
    try:
        with open(args.input, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except OSError as exc:
        print(f"Error: cannot open '{args.input}': {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"Error: invalid JSON in '{args.input}': {exc}", file=sys.stderr)
        return 1

    # Derive variable name
    var_name = args.var
    if not var_name:
        stem = Path(args.input).stem  # e.g. "noctis" from "noctis.anim"
        var_name = _ident(stem).upper()

    # Generate
    cpp_source = generate(payload, var_name)

    # Write output
    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(cpp_source)
            print(f"Written: {args.output}", file=sys.stderr)
        except OSError as exc:
            print(f"Error: cannot write '{args.output}': {exc}", file=sys.stderr)
            return 1
    else:
        sys.stdout.write(cpp_source)

    return 0


if __name__ == "__main__":
    sys.exit(main())
