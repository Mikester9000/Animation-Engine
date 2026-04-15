"""
animation_engine.animation.keyframe
======================================
Keyframe types and interpolation.

Keyframes store a (time, value) sample for a single animated channel.
Three interpolation modes are supported — matching the glTF 2.0 spec and
the animation authoring style used in FF15:

  STEP   — Instant snap; used for discrete state changes (e.g. visibility).
  LINEAR — Linear interpolation; fast and predictable.
  CUBIC  — Hermite cubic spline; produces the smooth, organic curves used for
           character motion in FF15.  Each keyframe stores in-tangent and
           out-tangent handles for full control over the curve shape.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Union

import numpy as np


class KeyframeType(Enum):
    """Interpolation mode for a keyframe."""

    STEP = auto()    # Instant value snap
    LINEAR = auto()  # Lerp between keyframes
    CUBIC = auto()   # Hermite cubic-spline (glTF CUBICSPLINE)


# A keyframe value can be a scalar (float), a 3-vector or a 4-vector (quaternion)
KeyframeValue = Union[float, list]


@dataclass
class Keyframe:
    """
    A single keyframe sample.

    Attributes
    ----------
    time        : Time in seconds where this keyframe lives.
    value       : Animated value — float | [x,y,z] | [x,y,z,w].
    in_tangent  : Hermite in-tangent (same shape as value); only used for CUBIC.
    out_tangent : Hermite out-tangent (same shape as value); only used for CUBIC.
    interp      : Interpolation mode to use when evaluating between this and the
                  *next* keyframe.
    """

    time: float = 0.0
    value: KeyframeValue = field(default_factory=float)
    in_tangent: KeyframeValue = field(default_factory=float)
    out_tangent: KeyframeValue = field(default_factory=float)
    interp: KeyframeType = KeyframeType.LINEAR

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "time": self.time,
            "value": self.value,
            "in_tangent": self.in_tangent,
            "out_tangent": self.out_tangent,
            "interp": self.interp.name,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Keyframe":
        return cls(
            time=d["time"],
            value=d["value"],
            in_tangent=d.get("in_tangent", 0.0),
            out_tangent=d.get("out_tangent", 0.0),
            interp=KeyframeType[d.get("interp", "LINEAR")],
        )


# ---------------------------------------------------------------------------
# Interpolation helpers
# ---------------------------------------------------------------------------

def _to_array(v) -> np.ndarray:
    """Convert a scalar or list value to a NumPy array."""
    if isinstance(v, (int, float)):
        return np.array([v], dtype=np.float64)
    return np.asarray(v, dtype=np.float64)


def _from_array(arr: np.ndarray, original):
    """Convert back from a NumPy array to the original value type."""
    if isinstance(original, (int, float)):
        return float(arr[0])
    return arr.tolist()


def interpolate_keyframes(kf0: Keyframe, kf1: Keyframe, time: float):
    """
    Evaluate the interpolated value between two keyframes at *time*.

    Parameters
    ----------
    kf0  : The keyframe at or before *time*.
    kf1  : The keyframe after *time*.
    time : Query time in seconds.

    Returns
    -------
    Interpolated value with the same shape as the keyframe values.
    """
    dt = kf1.time - kf0.time
    if dt < 1e-10:
        return kf0.value

    # Normalised parameter in [0, 1]
    t = (time - kf0.time) / dt

    if kf0.interp == KeyframeType.STEP:
        # Instant snap
        return kf0.value

    v0 = _to_array(kf0.value)
    v1 = _to_array(kf1.value)

    if kf0.interp == KeyframeType.LINEAR:
        result = v0 + (v1 - v0) * t

    elif kf0.interp == KeyframeType.CUBIC:
        # Hermite cubic spline interpolation (glTF CUBICSPLINE)
        # p(t) = (2t³ - 3t² + 1)v₀ + (t³ - 2t² + t)·dt·T₀
        #       + (-2t³ + 3t²)v₁   + (t³ - t²)·dt·T₁
        t2 = t * t
        t3 = t2 * t
        h00 = 2.0 * t3 - 3.0 * t2 + 1.0  # Basis for v0
        h10 = t3 - 2.0 * t2 + t           # Basis for out-tangent of kf0
        h01 = -2.0 * t3 + 3.0 * t2        # Basis for v1
        h11 = t3 - t2                      # Basis for in-tangent of kf1
        t0 = _to_array(kf0.out_tangent)
        t1 = _to_array(kf1.in_tangent)
        result = (
            h00 * v0
            + h10 * dt * t0
            + h01 * v1
            + h11 * dt * t1
        )
    else:
        result = v0 + (v1 - v0) * t

    return _from_array(result, kf0.value)
