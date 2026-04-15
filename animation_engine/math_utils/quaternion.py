"""
animation_engine.math_utils.quaternion
========================================
Unit-quaternion type for 3-D rotations.

Quaternions are the preferred rotation representation for skeletal animation
because they interpolate smoothly (SLERP), avoid gimbal lock, and compose
cheaply compared to rotation matrices.

Convention: q = w + xi + yj + zk  (scalar-first storage: [x, y, z, w])
"""

from __future__ import annotations

import math
import numpy as np

from .vector import Vector3


class Quaternion:
    """
    Unit quaternion representing a 3-D rotation.

    Components are stored in (x, y, z, w) order internally so that the layout
    matches GLTF 2.0 and most real-time engines.
    """

    __slots__ = ("_data",)

    def __init__(
        self, x: float = 0.0, y: float = 0.0, z: float = 0.0, w: float = 1.0
    ) -> None:
        self._data = np.array([x, y, z, w], dtype=np.float64)

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

    # -- class constants / factories -----------------------------------------

    @classmethod
    def identity(cls) -> "Quaternion":
        """Return the identity rotation (no rotation)."""
        return cls(0.0, 0.0, 0.0, 1.0)

    @classmethod
    def from_axis_angle(cls, axis: Vector3, angle_rad: float) -> "Quaternion":
        """
        Construct a quaternion from an axis-angle representation.

        Parameters
        ----------
        axis:       Unit vector defining the rotation axis.
        angle_rad:  Rotation angle in **radians**.
        """
        ax = axis.normalized()
        half = angle_rad * 0.5
        s = math.sin(half)
        return cls(ax.x * s, ax.y * s, ax.z * s, math.cos(half))

    @classmethod
    def from_euler(cls, pitch: float, yaw: float, roll: float) -> "Quaternion":
        """
        Construct from Euler angles (pitch / yaw / roll) in **radians**.

        Rotation order: X (pitch) → Y (yaw) → Z (roll).
        """
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)
        return cls(
            sp * cy * cr - cp * sy * sr,
            cp * sy * cr + sp * cy * sr,
            cp * cy * sr - sp * sy * cr,
            cp * cy * cr + sp * sy * sr,
        )

    @classmethod
    def from_rotation_matrix(cls, m) -> "Quaternion":
        """
        Extract a quaternion from the upper-left 3×3 of a 4×4 rotation matrix.

        Uses Shepperd's method for numerical stability.
        """
        r = np.asarray(m, dtype=np.float64)
        trace = r[0, 0] + r[1, 1] + r[2, 2]
        if trace > 0.0:
            s = 0.5 / math.sqrt(trace + 1.0)
            return cls(
                (r[2, 1] - r[1, 2]) * s,
                (r[0, 2] - r[2, 0]) * s,
                (r[1, 0] - r[0, 1]) * s,
                0.25 / s,
            )
        elif r[0, 0] > r[1, 1] and r[0, 0] > r[2, 2]:
            s = 2.0 * math.sqrt(1.0 + r[0, 0] - r[1, 1] - r[2, 2])
            return cls(
                0.25 * s,
                (r[0, 1] + r[1, 0]) / s,
                (r[0, 2] + r[2, 0]) / s,
                (r[2, 1] - r[1, 2]) / s,
            )
        elif r[1, 1] > r[2, 2]:
            s = 2.0 * math.sqrt(1.0 + r[1, 1] - r[0, 0] - r[2, 2])
            return cls(
                (r[0, 1] + r[1, 0]) / s,
                0.25 * s,
                (r[1, 2] + r[2, 1]) / s,
                (r[0, 2] - r[2, 0]) / s,
            )
        else:
            s = 2.0 * math.sqrt(1.0 + r[2, 2] - r[0, 0] - r[1, 1])
            return cls(
                (r[0, 2] + r[2, 0]) / s,
                (r[1, 2] + r[2, 1]) / s,
                0.25 * s,
                (r[1, 0] - r[0, 1]) / s,
            )

    @classmethod
    def from_list(cls, data: list) -> "Quaternion":
        """Reconstruct from [x, y, z, w] list (GLTF convention)."""
        return cls(float(data[0]), float(data[1]), float(data[2]), float(data[3]))

    # -- arithmetic ----------------------------------------------------------

    def __mul__(self, other: "Quaternion") -> "Quaternion":
        """Hamilton product — compose two rotations."""
        ax, ay, az, aw = self.x, self.y, self.z, self.w
        bx, by, bz, bw = other.x, other.y, other.z, other.w
        return Quaternion(
            aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz,
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Quaternion):
            return NotImplemented
        # Two quaternions represent the same rotation if q == ±q
        return bool(
            np.allclose(self._data, other._data, atol=1e-5)
            or np.allclose(self._data, -other._data, atol=1e-5)
        )

    def __repr__(self) -> str:
        return f"Quaternion(x={self.x:.4f}, y={self.y:.4f}, z={self.z:.4f}, w={self.w:.4f})"

    # -- operations ----------------------------------------------------------

    @property
    def length(self) -> float:
        return float(np.linalg.norm(self._data))

    def normalized(self) -> "Quaternion":
        """Return a copy normalised to unit length."""
        mag = self.length
        if mag < 1e-10:
            return Quaternion.identity()
        d = self._data / mag
        return Quaternion(float(d[0]), float(d[1]), float(d[2]), float(d[3]))

    def conjugate(self) -> "Quaternion":
        """Return the conjugate (inverse for unit quaternions)."""
        return Quaternion(-self.x, -self.y, -self.z, self.w)

    def inverse(self) -> "Quaternion":
        """Return the multiplicative inverse."""
        mag_sq = float(np.dot(self._data, self._data))
        if mag_sq < 1e-10:
            return Quaternion.identity()
        c = self.conjugate()
        return Quaternion(c.x / mag_sq, c.y / mag_sq, c.z / mag_sq, c.w / mag_sq)

    def rotate_vector(self, v: Vector3) -> Vector3:
        """Rotate a Vector3 by this quaternion using sandwich product q·v·q⁻¹."""
        # Convert v to a pure quaternion
        qv = Quaternion(v.x, v.y, v.z, 0.0)
        result = self * qv * self.conjugate()
        return Vector3(result.x, result.y, result.z)

    def dot(self, other: "Quaternion") -> float:
        """4-D dot product — used by slerp to detect antipodal pairs."""
        return float(np.dot(self._data, other._data))

    def slerp(self, other: "Quaternion", t: float) -> "Quaternion":
        """
        Spherical Linear Interpolation between *self* and *other* at parameter *t*.

        This produces smooth, constant-angular-velocity rotation blending — the
        same technique used in FF15's animation blending system.
        """
        d = self.dot(other)
        # Ensure we take the shortest arc
        if d < 0.0:
            d = -d
            flip = True
        else:
            flip = False

        if d > 0.9995:
            # Quaternions are nearly identical — fall back to NLERP for stability
            scale0 = 1.0 - t
            scale1 = -t if flip else t
        else:
            theta_0 = math.acos(d)
            inv_sin = 1.0 / math.sin(theta_0)
            scale0 = math.sin((1.0 - t) * theta_0) * inv_sin
            scale1 = (-math.sin(t * theta_0) if flip else math.sin(t * theta_0)) * inv_sin

        d0 = self._data * scale0 + other._data * scale1
        q = Quaternion(float(d0[0]), float(d0[1]), float(d0[2]), float(d0[3]))
        return q.normalized()

    def to_euler(self) -> tuple:
        """
        Return (pitch, yaw, roll) Euler angles in **radians**.

        Rotation order: X (pitch) → Y (yaw) → Z (roll).
        """
        x, y, z, w = self.x, self.y, self.z, self.w
        # Pitch (x-axis rotation)
        sinr_cosp = 2.0 * (w * x + y * z)
        cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
        pitch = math.atan2(sinr_cosp, cosr_cosp)
        # Yaw (y-axis rotation)
        sinp = 2.0 * (w * y - z * x)
        sinp = max(-1.0, min(1.0, sinp))
        yaw = math.asin(sinp)
        # Roll (z-axis rotation)
        siny_cosp = 2.0 * (w * z + x * y)
        cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
        roll = math.atan2(siny_cosp, cosy_cosp)
        return (pitch, yaw, roll)

    def to_rotation_matrix_3x3(self) -> np.ndarray:
        """Return a 3×3 NumPy rotation matrix."""
        x, y, z, w = self.x, self.y, self.z, self.w
        return np.array(
            [
                [1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)],
            ],
            dtype=np.float64,
        )

    # -- serialisation -------------------------------------------------------

    def to_list(self) -> list:
        """Serialise to [x, y, z, w] list (GLTF convention)."""
        return [float(self.x), float(self.y), float(self.z), float(self.w)]
