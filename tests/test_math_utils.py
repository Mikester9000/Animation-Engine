"""
tests/test_math_utils.py
=========================
Unit tests for animation_engine.math_utils (Vector, Quaternion, Matrix, Transform).
"""

import math
import pytest
import numpy as np

from animation_engine.math_utils import (
    Vector2, Vector3, Vector4,
    Quaternion,
    Matrix3x3, Matrix4x4,
    Transform,
)


# ---------------------------------------------------------------------------
# Vector2
# ---------------------------------------------------------------------------

class TestVector2:
    def test_construction(self):
        v = Vector2(1.0, 2.0)
        assert v.x == pytest.approx(1.0)
        assert v.y == pytest.approx(2.0)

    def test_zero(self):
        v = Vector2.zero()
        assert v.x == pytest.approx(0.0)
        assert v.y == pytest.approx(0.0)

    def test_add(self):
        a = Vector2(1.0, 2.0)
        b = Vector2(3.0, 4.0)
        c = a + b
        assert c.x == pytest.approx(4.0)
        assert c.y == pytest.approx(6.0)

    def test_sub(self):
        a = Vector2(3.0, 4.0)
        b = Vector2(1.0, 2.0)
        c = a - b
        assert c.x == pytest.approx(2.0)
        assert c.y == pytest.approx(2.0)

    def test_mul_scalar(self):
        v = Vector2(2.0, 3.0) * 2.0
        assert v.x == pytest.approx(4.0)
        assert v.y == pytest.approx(6.0)

    def test_length(self):
        v = Vector2(3.0, 4.0)
        assert v.length == pytest.approx(5.0)

    def test_normalized(self):
        v = Vector2(3.0, 4.0).normalized()
        assert v.length == pytest.approx(1.0, abs=1e-5)

    def test_dot(self):
        a = Vector2(1.0, 0.0)
        b = Vector2(0.0, 1.0)
        assert a.dot(b) == pytest.approx(0.0)

    def test_lerp(self):
        a = Vector2(0.0, 0.0)
        b = Vector2(2.0, 4.0)
        c = a.lerp(b, 0.5)
        assert c.x == pytest.approx(1.0)
        assert c.y == pytest.approx(2.0)

    def test_serialise(self):
        v = Vector2(1.5, 2.5)
        lst = v.to_list()
        assert lst == pytest.approx([1.5, 2.5])
        v2 = Vector2.from_list(lst)
        assert v2 == v


# ---------------------------------------------------------------------------
# Vector3
# ---------------------------------------------------------------------------

class TestVector3:
    def test_construction(self):
        v = Vector3(1.0, 2.0, 3.0)
        assert v.x == pytest.approx(1.0)
        assert v.y == pytest.approx(2.0)
        assert v.z == pytest.approx(3.0)

    def test_cross_product(self):
        # X cross Y = Z
        x = Vector3(1, 0, 0)
        y = Vector3(0, 1, 0)
        z = x.cross(y)
        assert z.x == pytest.approx(0.0)
        assert z.y == pytest.approx(0.0)
        assert z.z == pytest.approx(1.0)

    def test_dot_product(self):
        a = Vector3(1, 2, 3)
        b = Vector3(4, 5, 6)
        assert a.dot(b) == pytest.approx(32.0)

    def test_length(self):
        v = Vector3(1, 0, 0)
        assert v.length == pytest.approx(1.0)

    def test_normalized(self):
        v = Vector3(3, 4, 0).normalized()
        assert v.length == pytest.approx(1.0, abs=1e-5)

    def test_distance_to(self):
        a = Vector3(0, 0, 0)
        b = Vector3(3, 4, 0)
        assert a.distance_to(b) == pytest.approx(5.0)

    def test_reflect(self):
        incident = Vector3(1, -1, 0).normalized()
        normal = Vector3(0, 1, 0)
        reflected = incident.reflect(normal)
        # After reflection, Y component should flip sign
        assert reflected.y == pytest.approx(-incident.y)

    def test_serialise(self):
        v = Vector3(1.0, 2.0, 3.0)
        lst = v.to_list()
        assert lst == pytest.approx([1.0, 2.0, 3.0])
        v2 = Vector3.from_list(lst)
        assert v2 == v


# ---------------------------------------------------------------------------
# Quaternion
# ---------------------------------------------------------------------------

class TestQuaternion:
    def test_identity(self):
        q = Quaternion.identity()
        assert q.w == pytest.approx(1.0)
        assert q.x == pytest.approx(0.0)

    def test_rotate_vector_identity(self):
        q = Quaternion.identity()
        v = Vector3(1, 2, 3)
        rotated = q.rotate_vector(v)
        assert rotated.x == pytest.approx(v.x)
        assert rotated.y == pytest.approx(v.y)
        assert rotated.z == pytest.approx(v.z)

    def test_rotate_90_degrees_around_y(self):
        """Rotating (1,0,0) by 90° around Y should give (0,0,-1)."""
        q = Quaternion.from_axis_angle(Vector3.up(), math.pi / 2)
        v = Vector3(1, 0, 0)
        rotated = q.rotate_vector(v)
        assert rotated.x == pytest.approx(0.0, abs=1e-5)
        assert rotated.y == pytest.approx(0.0, abs=1e-5)
        assert rotated.z == pytest.approx(-1.0, abs=1e-5)

    def test_slerp_midpoint(self):
        q0 = Quaternion.identity()
        q1 = Quaternion.from_axis_angle(Vector3.up(), math.pi / 2)
        mid = q0.slerp(q1, 0.5)
        # Midpoint should be ~45 degrees around Y
        v = mid.rotate_vector(Vector3(1, 0, 0))
        expected_angle = math.pi / 4
        assert v.x == pytest.approx(math.cos(expected_angle), abs=1e-4)
        assert v.z == pytest.approx(-math.sin(expected_angle), abs=1e-4)

    def test_from_euler_roundtrip(self):
        q = Quaternion.from_euler(0.1, 0.2, 0.3)
        pitch, yaw, roll = q.to_euler()
        q2 = Quaternion.from_euler(pitch, yaw, roll)
        assert q == q2

    def test_conjugate(self):
        """q * q.conjugate() should be close to identity."""
        q = Quaternion.from_axis_angle(Vector3(1, 1, 0).normalized(), 1.0)
        qc = q.conjugate()
        product = q * qc
        assert product.w == pytest.approx(1.0, abs=1e-5)
        assert abs(product.x) == pytest.approx(0.0, abs=1e-5)

    def test_from_to_list(self):
        q = Quaternion(0.1, 0.2, 0.3, 0.9272)
        lst = q.to_list()
        q2 = Quaternion.from_list(lst)
        assert q2.x == pytest.approx(q.x)
        assert q2.w == pytest.approx(q.w)


# ---------------------------------------------------------------------------
# Matrix4x4
# ---------------------------------------------------------------------------

class TestMatrix4x4:
    def test_identity(self):
        m = Matrix4x4.identity()
        v = Vector3(1, 2, 3)
        result = m.transform_point(v)
        assert result.x == pytest.approx(v.x)
        assert result.y == pytest.approx(v.y)
        assert result.z == pytest.approx(v.z)

    def test_translation(self):
        m = Matrix4x4.from_translation(Vector3(1, 2, 3))
        v = Vector3(0, 0, 0)
        result = m.transform_point(v)
        assert result.x == pytest.approx(1.0)
        assert result.y == pytest.approx(2.0)
        assert result.z == pytest.approx(3.0)

    def test_scale(self):
        m = Matrix4x4.from_scale(Vector3(2, 3, 4))
        v = Vector3(1, 1, 1)
        result = m.transform_point(v)
        assert result.x == pytest.approx(2.0)
        assert result.y == pytest.approx(3.0)
        assert result.z == pytest.approx(4.0)

    def test_multiply_identity(self):
        m = Matrix4x4.from_translation(Vector3(5, 0, 0))
        result = m * Matrix4x4.identity()
        v = Vector3(0, 0, 0)
        pt = result.transform_point(v)
        assert pt.x == pytest.approx(5.0)

    def test_inverse(self):
        m = Matrix4x4.from_translation(Vector3(1, 2, 3))
        inv = m.inverse()
        product = m * inv
        diag = [product.get(i, i) for i in range(4)]
        assert all(d == pytest.approx(1.0, abs=1e-5) for d in diag)

    def test_compose_decompose(self):
        t = Vector3(1, 2, 3)
        r = Quaternion.from_axis_angle(Vector3.up(), 0.5)
        s = Vector3(1, 1, 1)
        m = Matrix4x4.compose(t, r, s)
        t2, r2, s2 = m.decompose()
        assert t2.x == pytest.approx(t.x, abs=1e-4)
        assert t2.y == pytest.approx(t.y, abs=1e-4)
        assert r2 == r


# ---------------------------------------------------------------------------
# Transform
# ---------------------------------------------------------------------------

class TestTransform:
    def test_identity_matrix(self):
        tf = Transform.identity()
        m = tf.to_matrix()
        v = Vector3(3, 4, 5)
        result = m.transform_point(v)
        assert result.x == pytest.approx(v.x)

    def test_lerp(self):
        t0 = Transform(position=Vector3(0, 0, 0))
        t1 = Transform(position=Vector3(10, 0, 0))
        mid = t0.lerp(t1, 0.5)
        assert mid.position.x == pytest.approx(5.0)

    def test_serialise_roundtrip(self):
        tf = Transform(
            position=Vector3(1, 2, 3),
            rotation=Quaternion.from_axis_angle(Vector3.up(), 0.3),
            scale=Vector3(2, 2, 2),
        )
        d = tf.to_dict()
        tf2 = Transform.from_dict(d)
        assert tf2.position.x == pytest.approx(1.0)
        assert tf2 == tf
