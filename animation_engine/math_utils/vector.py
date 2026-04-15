"""
animation_engine.math_utils.vector
===================================
Immutable-style 2-D, 3-D and 4-D vector types built on top of NumPy.

All arithmetic operators return new instances so vectors can be safely used
as value objects throughout the engine.
"""

from __future__ import annotations

import math
import numpy as np


# ---------------------------------------------------------------------------
# Vector2
# ---------------------------------------------------------------------------

class Vector2:
    """Two-component vector (x, y) — used for UV coordinates and 2-D UI."""

    __slots__ = ("_data",)

    def __init__(self, x: float = 0.0, y: float = 0.0) -> None:
        self._data = np.array([x, y], dtype=np.float32)

    # -- properties ----------------------------------------------------------

    @property
    def x(self) -> float:
        return float(self._data[0])

    @property
    def y(self) -> float:
        return float(self._data[1])

    # -- construction helpers ------------------------------------------------

    @classmethod
    def zero(cls) -> "Vector2":
        """Return the additive identity (0, 0)."""
        return cls(0.0, 0.0)

    @classmethod
    def one(cls) -> "Vector2":
        """Return the multiplicative identity (1, 1)."""
        return cls(1.0, 1.0)

    @classmethod
    def from_array(cls, arr) -> "Vector2":
        """Construct from any sequence of length 2."""
        a = np.asarray(arr, dtype=np.float32)
        return cls(float(a[0]), float(a[1]))

    # -- arithmetic ----------------------------------------------------------

    def __add__(self, other: "Vector2") -> "Vector2":
        return Vector2.from_array(self._data + other._data)

    def __sub__(self, other: "Vector2") -> "Vector2":
        return Vector2.from_array(self._data - other._data)

    def __mul__(self, scalar: float) -> "Vector2":
        return Vector2.from_array(self._data * scalar)

    def __rmul__(self, scalar: float) -> "Vector2":
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> "Vector2":
        return Vector2.from_array(self._data / scalar)

    def __neg__(self) -> "Vector2":
        return Vector2.from_array(-self._data)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector2):
            return NotImplemented
        return bool(np.allclose(self._data, other._data))

    def __repr__(self) -> str:
        return f"Vector2({self.x:.4f}, {self.y:.4f})"

    # -- vector operations ---------------------------------------------------

    def dot(self, other: "Vector2") -> float:
        """Return the dot product of *self* and *other*."""
        return float(np.dot(self._data, other._data))

    @property
    def length_sq(self) -> float:
        """Squared magnitude — cheaper than *length* when only ordering matters."""
        return self.dot(self)

    @property
    def length(self) -> float:
        """Euclidean magnitude."""
        return float(np.linalg.norm(self._data))

    def normalized(self) -> "Vector2":
        """Return a unit vector in the same direction."""
        mag = self.length
        if mag < 1e-10:
            return Vector2.zero()
        return Vector2.from_array(self._data / mag)

    def lerp(self, other: "Vector2", t: float) -> "Vector2":
        """Linearly interpolate towards *other* by factor *t* ∈ [0, 1]."""
        return Vector2.from_array(self._data + (other._data - self._data) * t)

    # -- serialisation -------------------------------------------------------

    def to_list(self) -> list:
        """Convert to a plain Python list for JSON serialisation."""
        return [float(self.x), float(self.y)]

    @classmethod
    def from_list(cls, data: list) -> "Vector2":
        """Reconstruct from a plain Python list."""
        return cls(float(data[0]), float(data[1]))


# ---------------------------------------------------------------------------
# Vector3
# ---------------------------------------------------------------------------

class Vector3:
    """
    Three-component vector (x, y, z).

    This is the workhorse type of the engine and is used for positions,
    normals, tangents, scale axes, and any other 3-D quantity.
    """

    __slots__ = ("_data",)

    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> None:
        self._data = np.array([x, y, z], dtype=np.float32)

    # -- properties ----------------------------------------------------------

    @property
    def x(self) -> float:
        return float(self._data[0])

    @property
    def y(self) -> float:
        return float(self._data[1])

    @property
    def z(self) -> float:
        return float(self._data[2])

    # -- class constants -----------------------------------------------------

    @classmethod
    def zero(cls) -> "Vector3":
        return cls(0.0, 0.0, 0.0)

    @classmethod
    def one(cls) -> "Vector3":
        return cls(1.0, 1.0, 1.0)

    @classmethod
    def up(cls) -> "Vector3":
        return cls(0.0, 1.0, 0.0)

    @classmethod
    def forward(cls) -> "Vector3":
        return cls(0.0, 0.0, -1.0)

    @classmethod
    def right(cls) -> "Vector3":
        return cls(1.0, 0.0, 0.0)

    @classmethod
    def from_array(cls, arr) -> "Vector3":
        a = np.asarray(arr, dtype=np.float32)
        return cls(float(a[0]), float(a[1]), float(a[2]))

    # -- arithmetic ----------------------------------------------------------

    def __add__(self, other: "Vector3") -> "Vector3":
        return Vector3.from_array(self._data + other._data)

    def __sub__(self, other: "Vector3") -> "Vector3":
        return Vector3.from_array(self._data - other._data)

    def __mul__(self, scalar: float) -> "Vector3":
        return Vector3.from_array(self._data * scalar)

    def __rmul__(self, scalar: float) -> "Vector3":
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> "Vector3":
        return Vector3.from_array(self._data / scalar)

    def __neg__(self) -> "Vector3":
        return Vector3.from_array(-self._data)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector3):
            return NotImplemented
        return bool(np.allclose(self._data, other._data, atol=1e-5))

    def __repr__(self) -> str:
        return f"Vector3({self.x:.4f}, {self.y:.4f}, {self.z:.4f})"

    # -- vector operations ---------------------------------------------------

    def dot(self, other: "Vector3") -> float:
        """Return the dot product."""
        return float(np.dot(self._data, other._data))

    def cross(self, other: "Vector3") -> "Vector3":
        """Return the cross product (*self* × *other*)."""
        return Vector3.from_array(np.cross(self._data, other._data))

    @property
    def length_sq(self) -> float:
        return self.dot(self)

    @property
    def length(self) -> float:
        return float(np.linalg.norm(self._data))

    def normalized(self) -> "Vector3":
        mag = self.length
        if mag < 1e-10:
            return Vector3.zero()
        return Vector3.from_array(self._data / mag)

    def lerp(self, other: "Vector3", t: float) -> "Vector3":
        """Linear interpolation."""
        return Vector3.from_array(self._data + (other._data - self._data) * t)

    def reflect(self, normal: "Vector3") -> "Vector3":
        """Return the reflection of *self* about *normal* (must be unit length)."""
        return self - normal * (2.0 * self.dot(normal))

    def distance_to(self, other: "Vector3") -> float:
        """Euclidean distance to *other*."""
        return (other - self).length

    def to_vector4(self, w: float = 0.0) -> "Vector4":
        """Promote to a homogeneous Vector4."""
        return Vector4(self.x, self.y, self.z, w)

    # -- serialisation -------------------------------------------------------

    def to_list(self) -> list:
        return [float(self.x), float(self.y), float(self.z)]

    @classmethod
    def from_list(cls, data: list) -> "Vector3":
        return cls(float(data[0]), float(data[1]), float(data[2]))


# ---------------------------------------------------------------------------
# Vector4
# ---------------------------------------------------------------------------

class Vector4:
    """
    Four-component vector (x, y, z, w).

    Used for homogeneous coordinates and colour (r, g, b, a).
    """

    __slots__ = ("_data",)

    def __init__(
        self, x: float = 0.0, y: float = 0.0, z: float = 0.0, w: float = 0.0
    ) -> None:
        self._data = np.array([x, y, z, w], dtype=np.float32)

    # -- properties ----------------------------------------------------------

    @property
    def x(self) -> float:
        return float(self._data[0])

    @property
    def y(self) -> float:
        return float(self._data[1])

    @property
    def z(self) -> float:
        return float(self._data[2])

    @property
    def w(self) -> float:
        return float(self._data[3])

    # Colour-channel aliases
    r = x  # type: ignore[assignment]
    g = y  # type: ignore[assignment]
    b = z  # type: ignore[assignment]
    a = w  # type: ignore[assignment]

    # -- construction helpers ------------------------------------------------

    @classmethod
    def zero(cls) -> "Vector4":
        return cls(0.0, 0.0, 0.0, 0.0)

    @classmethod
    def one(cls) -> "Vector4":
        return cls(1.0, 1.0, 1.0, 1.0)

    @classmethod
    def from_array(cls, arr) -> "Vector4":
        a = np.asarray(arr, dtype=np.float32)
        return cls(float(a[0]), float(a[1]), float(a[2]), float(a[3]))

    @classmethod
    def from_vector3(cls, v: Vector3, w: float = 1.0) -> "Vector4":
        return cls(v.x, v.y, v.z, w)

    # -- arithmetic ----------------------------------------------------------

    def __add__(self, other: "Vector4") -> "Vector4":
        return Vector4.from_array(self._data + other._data)

    def __sub__(self, other: "Vector4") -> "Vector4":
        return Vector4.from_array(self._data - other._data)

    def __mul__(self, scalar: float) -> "Vector4":
        return Vector4.from_array(self._data * scalar)

    def __rmul__(self, scalar: float) -> "Vector4":
        return self.__mul__(scalar)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector4):
            return NotImplemented
        return bool(np.allclose(self._data, other._data, atol=1e-5))

    def __repr__(self) -> str:
        return f"Vector4({self.x:.4f}, {self.y:.4f}, {self.z:.4f}, {self.w:.4f})"

    def dot(self, other: "Vector4") -> float:
        return float(np.dot(self._data, other._data))

    @property
    def length(self) -> float:
        return float(np.linalg.norm(self._data))

    def normalized(self) -> "Vector4":
        mag = self.length
        if mag < 1e-10:
            return Vector4.zero()
        return Vector4.from_array(self._data / mag)

    def to_vector3(self) -> Vector3:
        """Perspective-divide and return the xyz components as a Vector3."""
        if abs(self.w) > 1e-10:
            return Vector3(self.x / self.w, self.y / self.w, self.z / self.w)
        return Vector3(self.x, self.y, self.z)

    def lerp(self, other: "Vector4", t: float) -> "Vector4":
        return Vector4.from_array(self._data + (other._data - self._data) * t)

    # -- serialisation -------------------------------------------------------

    def to_list(self) -> list:
        return [float(self.x), float(self.y), float(self.z), float(self.w)]

    @classmethod
    def from_list(cls, data: list) -> "Vector4":
        return cls(float(data[0]), float(data[1]), float(data[2]), float(data[3]))
