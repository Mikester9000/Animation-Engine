"""
animation_engine.io.anim_format
==================================
Custom .anim file format (JSON-based).

The .anim format is the native serialisation format for Animation Engine.
It stores a complete animation package — model, skeleton, clips, and morph
tracks — in a single human-readable JSON file.  This format is designed to
be the primary import/export target for Game Engine for Teaching.

File layout
-----------
{
  "format":    "AnimEngine",
  "version":   "1.0",
  "model":     { ... Model dict ... },
  "clips":     [ { ... AnimationClip dict ... }, ... ],
  "morph_tracks": [ { ... MorphTrack dict ... }, ... ]
}
"""

from __future__ import annotations

import json
import os
from typing import Any, List, Optional, Tuple

from ..model.model import Model
from ..animation.clip import AnimationClip
from ..animation.morph_track import MorphTrack


# Current format version — bump the minor version for backward-compatible
# additions; bump major for breaking changes.
FORMAT_VERSION = "1.0"
FORMAT_NAME = "AnimEngine"

# Minimum clip-level schema revision produced by this version of the engine.
# Older .anim payloads lack fields like `events` and `gameplay_tags` on each
# clip dict; `migrate_anim_dict` upgrades them before parsing.
_CLIP_SCHEMA_REVISION = 2


def migrate_anim_dict(payload: dict) -> dict:
    """Upgrade a legacy .anim payload dict to the current clip schema revision.

    Operates on the in-memory dict — no file I/O is performed.  The function
    is idempotent: running it twice returns the same result.

    Changes applied when missing:

    * Each clip dict gains ``"events": []`` (introduced with event-marker
      support).
    * Each clip dict gains ``"gameplay_tags": {}`` (introduced with gameplay
      semantic metadata).
    * The payload gains ``"clip_schema_revision": 2`` so callers can detect
      that migration has already been applied.

    Parameters
    ----------
    payload:
        The parsed JSON dict from a .anim file (or any dict containing a
        ``"clips"`` list of clip dicts).

    Returns
    -------
    The same dict object, mutated in place and also returned for convenience.
    """
    if payload.get("clip_schema_revision", 1) >= _CLIP_SCHEMA_REVISION:
        return payload

    for clip_dict in payload.get("clips", []):
        if not isinstance(clip_dict, dict):
            continue
        clip_dict.setdefault("events", [])
        clip_dict.setdefault("gameplay_tags", {})

    payload["clip_schema_revision"] = _CLIP_SCHEMA_REVISION
    return payload


class AnimExporter:
    """
    Export a Model + AnimationClips to a .anim JSON file.

    Example
    -------
    >>> exporter = AnimExporter()
    >>> exporter.export(model, clips, morph_tracks, "character.anim")
    """

    def export(
        self,
        model: Model,
        clips: List[AnimationClip] = None,
        morph_tracks: List[MorphTrack] = None,
        metadata: Optional[dict[str, Any]] = None,
        path: str = "output.anim",
        indent: int = 2,
    ) -> str:
        """
        Serialise and write the animation package to *path*.

        Parameters
        ----------
        model       : The Model to export.
        clips       : Animation clips to bundle (may be empty).
        morph_tracks: Morph-target weight tracks (may be empty).
        metadata    : Optional JSON-serializable metadata object stored under
                      top-level ``metadata`` in the exported .anim payload.
        path        : Output file path (must end in .anim by convention).
        indent      : JSON pretty-print indentation level (0 = compact).

        Returns
        -------
        Absolute path of the written file.
        """
        payload = self._build_payload(model, clips or [], morph_tracks or [], metadata)
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True) \
            if os.path.dirname(path) else None
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=indent if indent else None)
        return os.path.abspath(path)

    def export_string(
        self,
        model: Model,
        clips: List[AnimationClip] = None,
        morph_tracks: List[MorphTrack] = None,
        metadata: Optional[dict[str, Any]] = None,
        indent: int = 2,
    ) -> str:
        """Return the serialised payload as a JSON string (no file written)."""
        payload = self._build_payload(model, clips or [], morph_tracks or [], metadata)
        return json.dumps(payload, indent=indent if indent else None)

    @staticmethod
    def _build_payload(
        model: Model,
        clips: List[AnimationClip],
        morph_tracks: List[MorphTrack],
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict:
        payload = {
            "format": FORMAT_NAME,
            "version": FORMAT_VERSION,
            "model": model.to_dict(),
            "clips": [c.to_dict() for c in clips],
            "morph_tracks": [mt.to_dict() for mt in morph_tracks],
        }
        if metadata is not None:
            payload["metadata"] = metadata
        return payload


class AnimImporter:
    """
    Import a .anim JSON file back into engine objects.

    Example
    -------
    >>> importer = AnimImporter()
    >>> model, clips, morph_tracks = importer.import_file("character.anim")
    """

    def import_file(
        self,
        path: str,
        include_metadata: bool = False,
    ) -> (
        Tuple[Model, List[AnimationClip], List[MorphTrack]]
        | Tuple[Model, List[AnimationClip], List[MorphTrack], Optional[dict[str, Any]]]
    ):
        """
        Read and deserialise *path*.

        Returns
        -------
        If ``include_metadata`` is False:
            (model, clips, morph_tracks)
        If ``include_metadata`` is True:
            (model, clips, morph_tracks, metadata), where metadata is either
            the top-level ``metadata`` object or ``None`` when not present.
        """
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
        model, clips, morph_tracks, metadata = self._parse_payload(payload)
        if include_metadata:
            return model, clips, morph_tracks, metadata
        return model, clips, morph_tracks

    def import_string(
        self,
        json_string: str,
        include_metadata: bool = False,
    ) -> (
        Tuple[Model, List[AnimationClip], List[MorphTrack]]
        | Tuple[Model, List[AnimationClip], List[MorphTrack], Optional[dict[str, Any]]]
    ):
        """Deserialise from a JSON string (no file I/O)."""
        payload = json.loads(json_string)
        model, clips, morph_tracks, metadata = self._parse_payload(payload)
        if include_metadata:
            return model, clips, morph_tracks, metadata
        return model, clips, morph_tracks

    @staticmethod
    def _parse_payload(
        payload: dict,
    ) -> Tuple[Model, List[AnimationClip], List[MorphTrack], Optional[dict[str, Any]]]:
        # Upgrade legacy clip-level fields before parsing.
        migrate_anim_dict(payload)
        # Validate header
        fmt = payload.get("format", "")
        if fmt != FORMAT_NAME:
            raise ValueError(
                f"Unrecognised format '{fmt}'; expected '{FORMAT_NAME}'."
            )
        ver = payload.get("version", "0.0")
        major = int(ver.split(".")[0])
        if major != int(FORMAT_VERSION.split(".")[0]):
            raise ValueError(
                f"Incompatible format version '{ver}'; "
                f"current version is '{FORMAT_VERSION}'."
            )
        model = Model.from_dict(payload["model"])
        clips = [AnimationClip.from_dict(c) for c in payload.get("clips", [])]
        morph_tracks = [
            MorphTrack.from_dict(mt) for mt in payload.get("morph_tracks", [])
        ]
        metadata = payload.get("metadata")
        parsed_metadata: Optional[dict[str, Any]] = None
        if isinstance(metadata, dict):
            parsed_metadata = metadata
        return model, clips, morph_tracks, parsed_metadata
