"""animation_engine.editor — public re-exports."""

from .state import PlaybackState

try:  # pragma: no cover - optional when tkinter isn't available in test env
    from .main import AnimationEditor
except ModuleNotFoundError:  # pragma: no cover
    AnimationEditor = None  # type: ignore[assignment]

__all__ = ["PlaybackState", "AnimationEditor"]
