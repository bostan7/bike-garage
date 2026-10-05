"""PBR materials (glTF-compatible Principled BSDF only), colour-matched to SCOTT's photos of article 280483."""
import bpy

# name: (base colour linear RGB, metallic, roughness)
PALETTE = {
    "frame_grey":     ((0.052, 0.055, 0.060), 0.50, 0.42),   # metallic dark grey paint
    "decal_black":    ((0.008, 0.008, 0.009), 0.0, 0.30),    # down-tube panel, top-tube logo
    "neon_yellow":    ((0.50, 0.82, 0.0), 0.0, 0.42),        # SCOTT logo, grips, fork logo
    "decal_grey":     ((0.090, 0.094, 0.100), 0.3, 0.40),    # pinstripes on the down-tube panel
    "black_matte":    ((0.012, 0.012, 0.013), 0.0, 0.62),
    "black_gloss":    ((0.010, 0.010, 0.011), 0.2, 0.22),
    "black_anodised": ((0.015, 0.015, 0.017), 0.6, 0.38),    # stem, bar, crank arms, hubs
    "stanchion":      ((0.030, 0.030, 0.032), 0.9, 0.18),    # fork stanchions
    "rubber":         ((0.009, 0.009, 0.010), 0.0, 0.72),    # tyres
    "grey_plastic":   ((0.05, 0.05, 0.055), 0.0, 0.55),      # derailleur body, lever bodies
    "alu_silver":     ((0.62, 0.63, 0.65), 1.0, 0.30),       # cassette, rotors
    "steel":          ((0.70, 0.70, 0.72), 1.0, 0.22),       # chain, bolts, spokes nipples
    "spoke_black":    ((0.02, 0.02, 0.022), 0.8, 0.35),
    "tyre_text":      ((0.80, 0.81, 0.83), 0.0, 0.50),       # MAXXIS sidewall lettering
    "tanwall":        ((0.30, 0.16, 0.08), 0.0, 0.62),       # Rekon Race Tan Wall sidewall (Maxxis photo: warm orange-brown)
    "exo_red":        ((0.62, 0.05, 0.02), 0.0, 0.45),       # EXO PROTECTION band, TUBELESS READY text
    "deore_grey":     ((0.055, 0.057, 0.062), 0.65, 0.32),   # RD-M6100 body (dark grey aluminium)
    "deore_logo":     ((0.52, 0.53, 0.62), 0.85, 0.22),      # DEORE lettering (silver with a violet sheen)
    "reflector":      ((1.0, 0.30, 0.01), 0.0, 0.30),        # pedal reflectors
    "rebound_red":    ((0.55, 0.03, 0.04), 0.3, 0.40),       # fork rebound knob
}

_cache = {}


def get(name):
    if name in _cache:
        return _cache[name]
    color, metallic, roughness = PALETTE[name]
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if mat.node_tree is None and hasattr(mat, "use_nodes"):
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf is None:
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        out = next((n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'), None) or nt.nodes.new("ShaderNodeOutputMaterial")
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    mat.diffuse_color = (*color, 1.0)
    mat.metallic = metallic
    mat.roughness = roughness
    _cache[name] = mat
    return mat


def reset():
    _cache.clear()
