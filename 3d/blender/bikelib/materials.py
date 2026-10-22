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
    "deore_logo":     ((0.74, 0.30, 0.70), 0.75, 0.20),      # DEORE lettering: iridescent pink-purple (Toni's photo)
    "reflector":      ((1.0, 0.30, 0.01), 0.0, 0.30),        # pedal reflectors
    "rebound_red":    ((0.55, 0.03, 0.04), 0.3, 0.40),       # fork rebound knob
    "leatherette":    ((0.011, 0.011, 0.012), 0.0, 0.36),    # hydrofoam saddle cover (smooth, semi-gloss)
    "foam":           ((0.66, 0.62, 0.36), 0.0, 0.90),       # saddle foam showing through the torn nose
    # accessories (photos 2026-10-18)
    "clamp_red":      ((0.72, 0.012, 0.018), 0.0, 0.42),     # Polisport mudguard clamps and tip
    "grey_stripe":    ((0.040, 0.041, 0.044), 0.0, 0.45),    # stripe on the rear mudguard blade
    "plastic_black":  ((0.006, 0.006, 0.007), 0.0, 0.40),    # mudguard blades (semi-gloss black plastic)
    "red_translucent": ((0.50, 0.004, 0.006), 0.0, 0.12),    # M rear light body
    "led_red":        ((0.90, 0.05, 0.04), 0.0, 0.30),       # LEDs in the M light (emissive, see EMISSIVE)
    "rubber_soft":    ((0.016, 0.016, 0.017), 0.0, 0.78),    # rubbery front light body
    "lens_clear":     ((0.55, 0.57, 0.60), 0.0, 0.06),       # light lenses
    "silicone_yellow": ((0.93, 0.55, 0.004), 0.0, 0.55),     # yellow strap light
    "lock_orange":    ((0.90, 0.17, 0.006), 0.0, 0.40),      # Kryptonite crossbar (Kryptonite orange, not yellow)
    "coat_black":     ((0.011, 0.011, 0.012), 0.0, 0.40),    # vinyl-coated U-lock shackle
    "button_grey":    ((0.30, 0.30, 0.31), 0.0, 0.55),       # FlexFrame bracket release button
    "mudx_orange":    ((0.95, 0.24, 0.0), 0.0, 0.45),        # orange X + SKS gear on the Mud-X
    "reflector_amber": ((0.80, 0.17, 0.003), 0.0, 0.22),     # spoke reflectors (amber, prismatic face)
    "reflector_tab":  ((0.95, 0.36, 0.020), 0.0, 0.45),       # lighter clip tabs of the spoke reflectors
    "led_white":      ((0.90, 0.92, 0.95), 0.0, 0.20),       # LEDs in the front lights (emissive, see EMISSIVE)
}

# emissive materials: name -> (linear RGB, strength). Exported as emissiveFactor (+ KHR_materials_emissive_strength)
EMISSIVE = {
    "led_red": ((1.0, 0.04, 0.02), 2.0),
    "led_white": ((1.0, 1.0, 0.96), 1.5),
}

# thin-film (iridescent) layer in nm, for Blender renders (glTF viewers without iridescence show the base colour)
THIN_FILM = {"deore_logo": 420.0}

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
    if name in EMISSIVE:
        ecol, strength = EMISSIVE[name]
        bsdf.inputs["Emission Color"].default_value = (*ecol, 1.0)
        bsdf.inputs["Emission Strength"].default_value = strength
    if name in THIN_FILM and "Thin Film Thickness" in bsdf.inputs:
        bsdf.inputs["Thin Film Thickness"].default_value = THIN_FILM[name]
    mat.diffuse_color = (*color, 1.0)
    mat.metallic = metallic
    mat.roughness = roughness
    _cache[name] = mat
    return mat


def reset():
    _cache.clear()
