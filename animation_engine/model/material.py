"""
animation_engine.model.material
==================================
Physically-Based Rendering (PBR) material definition.

FF15 uses a full metalness/roughness PBR workflow identical to the glTF 2.0
material model — albedo, normal, metallic/roughness, emissive and occlusion
maps.  This class stores all parameters needed to author and re-export
compatible materials.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TextureRef:
    """
    Reference to an external texture asset.

    Texture data itself is not stored inside the material (it may be large),
    only the relative file path and the UV-set index to sample from.
    """

    path: str = ""          # Relative path from the .anim file
    uv_set: int = 0         # UV set index (0 = uv0, 1 = uv1)
    wrap_u: str = "repeat"  # "repeat" | "clamp" | "mirror"
    wrap_v: str = "repeat"

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "uv_set": self.uv_set,
            "wrap_u": self.wrap_u,
            "wrap_v": self.wrap_v,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "TextureRef":
        return cls(
            path=d.get("path", ""),
            uv_set=d.get("uv_set", 0),
            wrap_u=d.get("wrap_u", "repeat"),
            wrap_v=d.get("wrap_v", "repeat"),
        )


class PBRMaterial:
    """
    Metalness / roughness PBR material — matches the glTF 2.0 pbrMetallicRoughness
    extension used by modern AAA engines.

    Parameters follow the standard glTF / Unreal / Unity PBR naming:
      - albedo_color    : Base (diffuse) colour multiplier (RGBA linear)
      - metallic        : 0 = dielectric, 1 = conductor
      - roughness       : 0 = mirror-smooth, 1 = fully rough
      - emissive_color  : Self-illumination colour (HDR-capable)
      - emissive_strength : HDR multiplier for emissive
      - alpha_mode      : "opaque" | "mask" | "blend"
      - alpha_cutoff    : Threshold used in "mask" mode
      - double_sided    : Whether back-faces should be rendered
    """

    def __init__(self, name: str = "Material") -> None:
        self.name: str = name

        # --- base colour ---------------------------------------------------
        self.albedo_color: list = [1.0, 1.0, 1.0, 1.0]  # RGBA, linear
        self.albedo_texture: Optional[TextureRef] = None

        # --- metallic / roughness ------------------------------------------
        self.metallic: float = 0.0
        self.roughness: float = 0.5
        self.metallic_roughness_texture: Optional[TextureRef] = None

        # --- normal map ----------------------------------------------------
        self.normal_texture: Optional[TextureRef] = None
        self.normal_scale: float = 1.0  # Multiplier on the normal map XY channels

        # --- occlusion map -------------------------------------------------
        self.occlusion_texture: Optional[TextureRef] = None
        self.occlusion_strength: float = 1.0

        # --- emissive ------------------------------------------------------
        self.emissive_color: list = [0.0, 0.0, 0.0]  # RGB, linear
        self.emissive_texture: Optional[TextureRef] = None
        self.emissive_strength: float = 1.0  # HDR multiplier

        # --- transparency --------------------------------------------------
        self.alpha_mode: str = "opaque"   # "opaque" | "mask" | "blend"
        self.alpha_cutoff: float = 0.5    # Only used when alpha_mode == "mask"
        self.double_sided: bool = False

    # -- serialisation -------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dict."""

        def tex_to_dict(t):
            return t.to_dict() if t is not None else None

        return {
            "name": self.name,
            "albedo_color": self.albedo_color,
            "albedo_texture": tex_to_dict(self.albedo_texture),
            "metallic": self.metallic,
            "roughness": self.roughness,
            "metallic_roughness_texture": tex_to_dict(self.metallic_roughness_texture),
            "normal_texture": tex_to_dict(self.normal_texture),
            "normal_scale": self.normal_scale,
            "occlusion_texture": tex_to_dict(self.occlusion_texture),
            "occlusion_strength": self.occlusion_strength,
            "emissive_color": self.emissive_color,
            "emissive_texture": tex_to_dict(self.emissive_texture),
            "emissive_strength": self.emissive_strength,
            "alpha_mode": self.alpha_mode,
            "alpha_cutoff": self.alpha_cutoff,
            "double_sided": self.double_sided,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "PBRMaterial":

        def dict_to_tex(td):
            return TextureRef.from_dict(td) if td is not None else None

        mat = cls(name=d.get("name", "Material"))
        mat.albedo_color = d.get("albedo_color", [1.0, 1.0, 1.0, 1.0])
        mat.albedo_texture = dict_to_tex(d.get("albedo_texture"))
        mat.metallic = d.get("metallic", 0.0)
        mat.roughness = d.get("roughness", 0.5)
        mat.metallic_roughness_texture = dict_to_tex(d.get("metallic_roughness_texture"))
        mat.normal_texture = dict_to_tex(d.get("normal_texture"))
        mat.normal_scale = d.get("normal_scale", 1.0)
        mat.occlusion_texture = dict_to_tex(d.get("occlusion_texture"))
        mat.occlusion_strength = d.get("occlusion_strength", 1.0)
        mat.emissive_color = d.get("emissive_color", [0.0, 0.0, 0.0])
        mat.emissive_texture = dict_to_tex(d.get("emissive_texture"))
        mat.emissive_strength = d.get("emissive_strength", 1.0)
        mat.alpha_mode = d.get("alpha_mode", "opaque")
        mat.alpha_cutoff = d.get("alpha_cutoff", 0.5)
        mat.double_sided = d.get("double_sided", False)
        return mat

    def __repr__(self) -> str:
        return (
            f"PBRMaterial({self.name!r}, "
            f"metallic={self.metallic:.2f}, roughness={self.roughness:.2f})"
        )
