"""
animation_engine.runtime.skinning
=====================================
CPU skeletal skinning — useful for tools, previews, and platforms without a
GPU skinning shader.

GPU skinning is the norm in production (skin matrices uploaded to a UBO and
applied in the vertex shader), but CPU skinning is invaluable for:
  - Collision mesh deformation
  - LOD baking
  - Offline rendering previews
  - Debugging bone weights

Algorithm
---------
For each vertex:
    world_pos = Σ (weight_i * skin_matrix_i * bind_pos)

This is the standard linear blend skinning (LBS) used in FF15 and the vast
majority of real-time characters.  Dual-quaternion skinning (DQS), which
avoids the "candy-wrapper" artifact, is noted but not implemented here to
keep the code readable.
"""

from __future__ import annotations

from copy import deepcopy
from typing import List

import numpy as np

from ..model.mesh import Mesh, Vertex, MorphTarget
from ..math_utils import Matrix4x4, Vector3, Vector4


def cpu_skin_mesh(
    mesh: Mesh,
    skin_matrices: List[Matrix4x4],
    morph_weights: dict = None,
) -> Mesh:
    """
    Apply skeletal skinning and morph targets to *mesh*, returning a new
    Mesh with deformed vertex positions and normals.

    The original mesh is not modified — the caller receives a shallow copy
    with newly computed vertex data.  Only positions and normals are skinned;
    UVs, colours, and bone weights are copied verbatim.

    Parameters
    ----------
    mesh            : Source (bind-pose) mesh.
    skin_matrices   : Per-bone skin matrices (world * inverse_bind).
    morph_weights   : Dict of morph-target name → weight (0 … 1).

    Returns
    -------
    A new Mesh with skinned vertex positions and normals.
    """
    morph_weights = morph_weights or {}

    # Convert skin matrices to NumPy for batch processing
    num_bones = len(skin_matrices)
    sm = np.zeros((num_bones, 4, 4), dtype=np.float64)
    for i, mat in enumerate(skin_matrices):
        sm[i] = mat.to_numpy()

    n_verts = len(mesh.vertices)

    # Batch extract vertex data
    positions = np.array(
        [[v.position.x, v.position.y, v.position.z, 1.0] for v in mesh.vertices],
        dtype=np.float64,
    )
    normals = np.array(
        [[v.normal.x, v.normal.y, v.normal.z, 0.0] for v in mesh.vertices],
        dtype=np.float64,
    )

    # Apply morph target deltas to positions and normals
    for morph in mesh.morph_targets:
        w = morph_weights.get(morph.name, morph.weight)
        if w < 1e-6:
            continue
        for idx, delta in morph.position_deltas.items():
            if idx < n_verts:
                positions[idx, :3] += np.array(
                    [delta.x, delta.y, delta.z], dtype=np.float64
                ) * w
        for idx, delta in morph.normal_deltas.items():
            if idx < n_verts:
                normals[idx, :3] += np.array(
                    [delta.x, delta.y, delta.z], dtype=np.float64
                ) * w

    # Linear Blend Skinning
    out_positions = np.zeros((n_verts, 4), dtype=np.float64)
    out_normals = np.zeros((n_verts, 4), dtype=np.float64)

    for i, vert in enumerate(mesh.vertices):
        pos_acc = np.zeros(4, dtype=np.float64)
        nor_acc = np.zeros(4, dtype=np.float64)
        for j in range(4):
            bone_idx = vert.bone_indices[j]
            weight = vert.bone_weights[j]
            if weight < 1e-6 or bone_idx >= num_bones:
                continue
            pos_acc += weight * (sm[bone_idx] @ positions[i])
            nor_acc += weight * (sm[bone_idx] @ normals[i])
        out_positions[i] = pos_acc
        out_normals[i] = nor_acc

    # Build output mesh (shallow copy preserving index/material/morph data)
    output_vertices = []
    for i, vert in enumerate(mesh.vertices):
        new_vert = Vertex(
            position=Vector3(
                float(out_positions[i, 0]),
                float(out_positions[i, 1]),
                float(out_positions[i, 2]),
            ),
            normal=Vector3(
                float(out_normals[i, 0]),
                float(out_normals[i, 1]),
                float(out_normals[i, 2]),
            ).normalized(),
            tangent=vert.tangent,
            uv0=vert.uv0,
            uv1=vert.uv1,
            color=vert.color,
            bone_indices=vert.bone_indices,
            bone_weights=vert.bone_weights,
        )
        output_vertices.append(new_vert)

    skinned = Mesh(
        name=mesh.name + "_skinned",
        vertices=output_vertices,
        indices=list(mesh.indices),
        material_name=mesh.material_name,
    )
    # Copy morph targets (weights already applied; kept for re-evaluation)
    skinned.morph_targets = mesh.morph_targets
    return skinned
