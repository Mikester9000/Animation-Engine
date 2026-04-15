"""
animation_engine.math_utils.matrix
=====================================
3×3 and 4×4 matrix types used throughout the engine.

Matrix4x4 is the primary type: it represents combined TRS (Translation,
Rotation, Scale) transforms and is used for bone world-space transforms,
the model-view-projection stack, and skin matrices.
"""

from __future__ import annotations

import math
import numpy as np

from .vector import Vector3, Vector4


class Matrix3x3:
    """Row-major 3×3 matrix."""

    __slots__ = ("_m",)

    def __init__(self, data=None) -> None:
        if data is None:
            self._m = np.eye(3, dtype=np.float64)
        else:
            self._m = np.asarray(data, dtype=np.float64).reshape(3, 3)

    # -- factories -----------------------------------------------------------

    @classmethod
    def identity(cls) -> "Matrix3x3":
        return cls()

    @classmethod
    def from_numpy(cls, arr: np.ndarray) -> "Matrix3x3":
        return cls(arr)

    # -- operators -----------------------------------------------------------

    def __mul__(self, other: "Matrix3x3") -> "Matrix3x3":
        return Matrix3x3(self._m @ other._m)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Matrix3x3):
            return NotImplemented
        return bool(np.allclose(self._m, other._m, atol=1e-5))

    def __repr__(self) -> str:
        return f"Matrix3x3(\n{self._m}\n)"

    def transpose(self) -> "Matrix3x3":
        return Matrix3x3(self._m.T)

    def determinant(self) -> float:
        return float(np.linalg.det(self._m))

    def inverse(self) -> "Matrix3x3":
        return Matrix3x3(np.linalg.inv(self._m))

    def to_numpy(self) -> np.ndarray:
        return self._m.copy()


class Matrix4x4:
    """
    Row-major 4×4 homogeneous transform matrix.

    Layout
    ------
    | m[0,0]  m[0,1]  m[0,2]  m[0,3] |   right.x   right.y   right.z   0
    | m[1,0]  m[1,1]  m[1,2]  m[1,3] |   up.x       up.y      up.z      0
    | m[2,0]  m[2,1]  m[2,2]  m[2,3] |   fwd.x      fwd.y     fwd.z     0
    | m[3,0]  m[3,1]  m[3,2]  m[3,3] |   tx         ty        tz        1

    (translation is in the last row, matching DirectX/HLSL convention that is
    common in console game engines; GLTF column-major matrices are converted
    on import/export.)
    """

    __slots__ = ("_m",)

    def __init__(self, data=None) -> None:
        if data is None:
            self._m = np.eye(4, dtype=np.float64)
        else:
            self._m = np.asarray(data, dtype=np.float64).reshape(4, 4)

    # -- factories -----------------------------------------------------------

    @classmethod
    def identity(cls) -> "Matrix4x4":
        return cls()

    @classmethod
    def from_translation(cls, t: Vector3) -> "Matrix4x4":
        """
        Build a pure-translation matrix (column-vector / OpenGL convention).
        Translation lives in the last column so that ``M @ [x,y,z,1]^T`` works.
        """
        m = np.eye(4, dtype=np.float64)
        m[0, 3] = t.x
        m[1, 3] = t.y
        m[2, 3] = t.z
        return cls(m)

    @classmethod
    def from_scale(cls, s: Vector3) -> "Matrix4x4":
        """Build a non-uniform scale matrix."""
        m = np.diag([s.x, s.y, s.z, 1.0]).astype(np.float64)
        return cls(m)

    @classmethod
    def from_rotation_x(cls, angle_rad: float) -> "Matrix4x4":
        """Build a rotation matrix about the X axis."""
        c, s = math.cos(angle_rad), math.sin(angle_rad)
        return cls(
            [[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]]
        )

    @classmethod
    def from_rotation_y(cls, angle_rad: float) -> "Matrix4x4":
        """Build a rotation matrix about the Y axis."""
        c, s = math.cos(angle_rad), math.sin(angle_rad)
        return cls(
            [[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]]
        )

    @classmethod
    def from_rotation_z(cls, angle_rad: float) -> "Matrix4x4":
        """Build a rotation matrix about the Z axis."""
        c, s = math.cos(angle_rad), math.sin(angle_rad)
        return cls(
            [[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
        )

    @classmethod
    def from_quaternion(cls, q) -> "Matrix4x4":
        """Build a rotation matrix from a Quaternion."""
        r3 = q.to_rotation_matrix_3x3()
        m = np.eye(4, dtype=np.float64)
        m[:3, :3] = r3
        return cls(m)

    @classmethod
    def compose(cls, translation: Vector3, rotation, scale: Vector3) -> "Matrix4x4":
        """
        Build a TRS matrix from translation, rotation (Quaternion) and scale.

        Uses the column-vector convention so that ``M @ [x,y,z,1]^T`` applies
        scale first, then rotation, then translation — the standard game-engine order.
        The matrix layout is::

            | sx*r00  sy*r01  sz*r02  tx |
            | sx*r10  sy*r11  sz*r12  ty |
            | sx*r20  sy*r21  sz*r22  tz |
            | 0       0       0       1  |
        """
        r3 = rotation.to_rotation_matrix_3x3()
        m = np.eye(4, dtype=np.float64)
        # Scale each column of the rotation block
        m[:3, 0] = r3[:, 0] * scale.x
        m[:3, 1] = r3[:, 1] * scale.y
        m[:3, 2] = r3[:, 2] * scale.z
        # Translation in the last column
        m[0, 3] = translation.x
        m[1, 3] = translation.y
        m[2, 3] = translation.z
        return cls(m)

    @classmethod
    def look_at(
        cls, eye: Vector3, target: Vector3, up: Vector3 = None
    ) -> "Matrix4x4":
        """
        Build a view matrix looking from *eye* towards *target*
        (column-vector / right-hand coordinate system).
        """
        if up is None:
            up = Vector3.up()
        fwd = (target - eye).normalized()
        right = fwd.cross(up).normalized()
        true_up = right.cross(fwd)
        m = np.zeros((4, 4), dtype=np.float64)
        # Rotation part (transpose of the camera axes gives the view rotation)
        m[0, 0] = right.x;   m[0, 1] = right.y;   m[0, 2] = right.z
        m[1, 0] = true_up.x; m[1, 1] = true_up.y; m[1, 2] = true_up.z
        m[2, 0] = -fwd.x;    m[2, 1] = -fwd.y;    m[2, 2] = -fwd.z
        m[3, 3] = 1.0
        # Translation: negate the dot products to move world to camera space
        m[0, 3] = -right.dot(eye)
        m[1, 3] = -true_up.dot(eye)
        m[2, 3] = fwd.dot(eye)
        return cls(m)

    @classmethod
    def perspective(
        cls, fov_y_rad: float, aspect: float, near: float, far: float
    ) -> "Matrix4x4":
        """Build a right-handed perspective projection matrix."""
        f = 1.0 / math.tan(fov_y_rad * 0.5)
        z_range = near - far
        return cls(
            [
                [f / aspect, 0, 0, 0],
                [0, f, 0, 0],
                [0, 0, (far + near) / z_range, -1],
                [0, 0, (2 * far * near) / z_range, 0],
            ]
        )

    @classmethod
    def from_numpy(cls, arr: np.ndarray) -> "Matrix4x4":
        return cls(arr)

    @classmethod
    def from_list(cls, flat: list) -> "Matrix4x4":
        """
        Reconstruct from a flat 16-element list in column-major order (GLTF convention).

        glTF stores matrices in column-major order::

            flat = [m00, m10, m20, m30,  m01, m11, m21, m31,  m02, ...  m33]

        NumPy ``reshape(..., order='F')`` reads column-major, giving the correct
        row-major numpy array directly.
        """
        arr = np.asarray(flat, dtype=np.float64).reshape(4, 4, order="F")
        return cls(arr)

    # -- operators -----------------------------------------------------------

    def __mul__(self, other: "Matrix4x4") -> "Matrix4x4":
        """Matrix multiplication (composition of transforms)."""
        return Matrix4x4(self._m @ other._m)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Matrix4x4):
            return NotImplemented
        return bool(np.allclose(self._m, other._m, atol=1e-5))

    def __repr__(self) -> str:
        return f"Matrix4x4(\n{self._m}\n)"

    # -- access helpers ------------------------------------------------------

    def get(self, row: int, col: int) -> float:
        return float(self._m[row, col])

    def set(self, row: int, col: int, value: float) -> None:
        self._m[row, col] = value

    # -- transforms ----------------------------------------------------------

    def transform_point(self, v: Vector3) -> Vector3:
        """
        Transform a point by this matrix (applies translation).
        Uses column-vector convention: result = M @ [x, y, z, 1]^T.
        """
        p = np.array([v.x, v.y, v.z, 1.0], dtype=np.float64)
        r = self._m @ p
        return Vector3(float(r[0]), float(r[1]), float(r[2]))

    def transform_direction(self, v: Vector3) -> Vector3:
        """
        Transform a direction vector (ignores translation).
        Uses column-vector convention: result = M @ [x, y, z, 0]^T.
        """
        p = np.array([v.x, v.y, v.z, 0.0], dtype=np.float64)
        r = self._m @ p
        return Vector3(float(r[0]), float(r[1]), float(r[2]))

    def transform_vector4(self, v: Vector4) -> Vector4:
        """Full 4-component transform (column-vector convention)."""
        p = np.array([v.x, v.y, v.z, v.w], dtype=np.float64)
        r = self._m @ p
        return Vector4(float(r[0]), float(r[1]), float(r[2]), float(r[3]))

    # -- matrix operations ---------------------------------------------------

    def transpose(self) -> "Matrix4x4":
        return Matrix4x4(self._m.T)

    def determinant(self) -> float:
        return float(np.linalg.det(self._m))

    def inverse(self) -> "Matrix4x4":
        return Matrix4x4(np.linalg.inv(self._m))

    def decompose(self) -> tuple:
        """
        Decompose this TRS matrix into (translation, rotation Quaternion, scale).

        Assumes column-vector convention::

            | sx*r00  sy*r01  sz*r02  tx |
            | sx*r10  sy*r11  sz*r12  ty |
            | sx*r20  sy*r21  sz*r22  tz |
            | 0       0       0       1  |

        Returns
        -------
        translation : Vector3
        rotation    : Quaternion
        scale       : Vector3
        """
        from .quaternion import Quaternion

        # Translation is stored in the last column
        translation = Vector3(
            float(self._m[0, 3]),
            float(self._m[1, 3]),
            float(self._m[2, 3]),
        )
        # Scale = length of each column of the rotation-scale block
        sx = float(np.linalg.norm(self._m[:3, 0]))
        sy = float(np.linalg.norm(self._m[:3, 1]))
        sz = float(np.linalg.norm(self._m[:3, 2]))
        scale = Vector3(sx, sy, sz)
        # Remove scale to obtain a pure rotation matrix
        rot = self._m.copy()
        if sx > 1e-10:
            rot[:3, 0] /= sx
        if sy > 1e-10:
            rot[:3, 1] /= sy
        if sz > 1e-10:
            rot[:3, 2] /= sz
        rotation = Quaternion.from_rotation_matrix(rot)
        return translation, rotation, scale

    # -- serialisation -------------------------------------------------------

    def to_numpy(self) -> np.ndarray:
        return self._m.copy()

    def to_list(self) -> list:
        """Return a flat 16-element list in column-major order (GLTF convention)."""
        return self._m.T.flatten().tolist()
