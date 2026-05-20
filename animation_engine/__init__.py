"""
Animation Engine
================
A professional animation tool for creating models and animated assets
compatible with Game Engine for Teaching.

Inspired by Final Fantasy 15's animation pipeline, this engine supports:
  - Hierarchical skeletal animation (50+ bone rigs)
  - Smooth cubic-spline keyframe interpolation
  - Animation blending and state-machine driven transitions
  - Inverse Kinematics (foot-placement, hand IK)
  - Blend-shape / morph-target facial animation
  - Physically-Based Rendering (PBR) material authoring
  - Export / import in custom .anim (JSON) and GLTF 2.0 formats

Package layout
--------------
animation_engine.math_utils   – Vector, Quaternion, Matrix, Transform
animation_engine.model        – Vertex, Mesh, Material, Bone, Skeleton, Model
animation_engine.animation    – Keyframe, Channel, Clip, BlendTree, IKSolver, MorphTarget
animation_engine.io           – Exporter / Importer (.anim and GLTF 2.0)
animation_engine.runtime      – Runtime Animator and CPU Skinning
animation_engine.editor       – Tkinter-based timeline / model editor
"""

__version__ = "1.0.0"
__author__ = "Animation Engine Team"

from animation_engine.animation import AnimationClip
from animation_engine.backend import AnimationBackend, BackendRegistry, ProceduralBackend
from animation_engine.model import Model

__all__ = [
    "Model",
    "AnimationClip",
    "AnimationBackend",
    "ProceduralBackend",
    "BackendRegistry",
]
