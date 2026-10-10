"""Low-res sanity render of the garage (not part of the export): the prototype's four spot lights + a camera
on the drive side looking at the turntable. Only for checking the build; Toni asks for real renders."""
import math

import bpy
from mathutils import Vector

from . import spec as S

# Suggested app lights (Blender coordinates, from the prototype's spots: three.js (x, y, z) -> Blender (x, -z, y))
LIGHTS = {
    # name: (position, target, colour sRGB hex, cone half-angle deg, energy W for this preview)
    "key":   ((0.15, -0.30, 3.50), (0.133, 0.0, 0.5), "#FFFFFF", 36, 1400),
    "front": ((1.80, -3.20, 2.60), (0.133, 0.0, 0.5), "#E8F0FF", 29, 900),
    "rim":   ((-2.60, 2.40, 2.40), (0.133, 0.0, 0.5), "#D2F500", 34, 700),
    "wall":  ((0.30, 1.50, 3.40), (0.30, S.Y1, 0.8), "#9FB8FF", 57, 900),
}


def _lin(hx):
    h = hx.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return out


VIEWS = {
    # name: (camera position, look-at point, lens mm)
    "drive":  ((S.TT.x + 1.1, -3.9, 1.45), (S.TT.x, 0.6, 0.9), 22),      # drive side, towards the shutter
    "corner": ((3.6, 2.6, 2.6), (-2.0, -1.5, 1.4), 16),                 # back-right corner: ceiling, left wall, door
}


def render(path, width=800, height=450, view="drive"):
    scene = bpy.context.scene
    for name in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = name
            break
        except TypeError:
            continue
    ee = scene.eevee
    for attr, val in (("use_raytracing", True), ("taa_render_samples", 32), ("use_shadows", True)):
        if hasattr(ee, attr):
            try:
                setattr(ee, attr, val)
            except (TypeError, AttributeError):
                pass
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    world = bpy.data.worlds.new("garage_dark")
    scene.world = world
    if world.node_tree is None and hasattr(world, "use_nodes"):
        world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs["Color"].default_value = (0.02, 0.025, 0.035, 1.0)
    bg.inputs["Strength"].default_value = 0.3
    for name, (pos, tgt, col, ang, energy) in LIGHTS.items():
        ld = bpy.data.lights.new(name, 'SPOT')
        ld.energy = energy
        ld.color = _lin(col)
        ld.spot_size = math.radians(ang * 2)
        ld.spot_blend = 0.5
        ob = bpy.data.objects.new(name, ld)
        ob.location = pos
        ob.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y').to_euler()
        scene.collection.objects.link(ob)
    cam = bpy.data.cameras.new("check")
    pos, tgt, cam.lens = VIEWS[view]
    ob = bpy.data.objects.new("check", cam)
    ob.location = pos
    ob.rotation_euler = (Vector(tgt) - ob.location).to_track_quat('-Z', 'Y').to_euler()
    scene.collection.objects.link(ob)
    scene.camera = ob
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("rendered", path)
