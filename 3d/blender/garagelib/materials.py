"""Garage materials: glTF-compatible Principled BSDF only.

Emissive materials (neon, LEDs, sign) set Emission Color + Emission Strength; the glTF exporter writes
emissiveFactor + KHR_materials_emissive_strength, which Filament's bloom picks up.
Material names are stable: the app may look them up (e.g. to fade the neon in during the intro).
"""
import bpy

from . import spec as S
from . import textures


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def lin(hex_str):
    h = hex_str.lstrip("#")
    return tuple(srgb_to_linear(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4))


# name: (sRGB hex, metallic, roughness)
PALETTE = {
    "garage_ceiling":   ("#0c0d10", 0.0, 0.95),
    "steel_beam":       ("#1a1d21", 0.6, 0.50),
    "door_steel":       ("#2a3038", 0.5, 0.45),
    "glass_dark":       ("#050607", 0.0, 0.06),
    "steel_satin":      ("#9aa1a8", 1.0, 0.30),
    "alu_dark":         ("#16191d", 0.6, 0.40),     # shutter rails and box, frames
    "shutter_metal":    ("#2e3339", 0.75, 0.45),
    "rubber_black":     ("#101112", 0.0, 0.80),
    "stripe_yellow":    ("#d9b400", 0.0, 0.55),
    "stripe_black":     ("#141414", 0.0, 0.60),
    "turntable_metal":  ("#15191f", 0.8, 0.30),
    "turntable_mat":    ("#0d0f12", 0.1, 0.55),
    "sign_backing":     ("#08090a", 0.2, 0.30),
    "bench_wood":       ("#3b2a1c", 0.0, 0.80),
    "dark_metal":       ("#15181c", 0.5, 0.50),
    "chest_gunmetal":   ("#1c2026", 0.7, 0.35),     # tool chest body (as in the prototype)
    "tyre_rubber":      ("#0e0f10", 0.0, 0.85),
    "drum_blue":        ("#1b2836", 0.6, 0.50),
    "cable_yellow":     ("#b8d200", 0.0, 0.50),     # coiled cables on the pegboard (paint, not emissive)
    "tool_handle_red":  ("#7a1414", 0.0, 0.45),
    "cardboard":        ("#4e3d2a", 0.0, 0.90),
    "crate_grey":       ("#24282d", 0.0, 0.60),
    "extinguisher_red": ("#8a1010", 0.1, 0.35),
}

EMISSIVE = {
    # name: (emission sRGB hex, strength)
    "neon_yellow": (S.NEON_HEX, S.NEON_STRENGTH),
    "led_white":   (S.LED_HEX, S.LED_STRENGTH),
    "sign_core":   (S.SIGN_CORE_HEX, S.SIGN_STRENGTH),
}

TEXTURED = {
    # name: (texture builder, metallic, roughness)
    "floor_concrete": (textures.concrete_floor, 0.0, 0.35),
    "wall_blocks":    (textures.concrete_blocks, 0.0, 0.90),
    "pegboard":       (textures.pegboard, 0.0, 0.70),
}

_cache = {}


def _bsdf(mat):
    if mat.node_tree is None and hasattr(mat, "use_nodes"):
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None) or nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return nt, bsdf


def get(name):
    if name in _cache:
        return _cache[name]
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    nt, bsdf = _bsdf(mat)
    if name in PALETTE:
        hx, metallic, rough = PALETTE[name]
        color = lin(hx)
    elif name in EMISSIVE:
        hx, strength = EMISSIVE[name]
        e = lin(hx)
        color = tuple(c * 0.35 for c in e)
        metallic, rough = 0.0, 0.40
        bsdf.inputs["Emission Color"].default_value = (*e, 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength
    else:
        build, metallic, rough = TEXTURED[name]
        img = build()
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.interpolation = 'Linear'
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        color = (0.03, 0.03, 0.035)
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = rough
    mat.diffuse_color = (*color, 1.0)
    mat.metallic = metallic
    mat.roughness = rough
    _cache[name] = mat
    return mat


def reset():
    _cache.clear()
