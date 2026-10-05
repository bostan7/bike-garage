"""Preview renders: a studio rig plus fixed camera views. The 'side_photo' view matches the scale and
framing of SCOTT's official 2000 x 2000 studio photo so the two can be overlaid."""
import math
import os

import bpy
from mathutils import Vector

from . import spec as S

# Studio photo: rear axle at pixel (413, 1145), 1041.5 px per metre... per mm: 1.0415
PHOTO_PX = 2000
PHOTO_SCALE = 1.0415 / S.MM                 # pixels per metre
PHOTO_REAR_AXLE_PX = (413.0, 1145.0)


def _engine(scene):
    for name in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            scene.render.engine = name
            return name
        except TypeError:
            continue
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 64
    return "CYCLES"


def setup(scene):
    eng = _engine(scene)
    scene.render.film_transparent = True
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    try:
        scene.view_settings.view_transform = 'Standard'
    except TypeError:
        pass
    world = bpy.data.worlds.new("studio")
    scene.world = world
    if world.node_tree is None and hasattr(world, "use_nodes"):
        world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs["Color"].default_value = (0.85, 0.86, 0.88, 1.0)
    bg.inputs["Strength"].default_value = 0.35

    def light(name, kind, loc, rot, energy, size=2.0):
        ld = bpy.data.lights.new(name, kind)
        ld.energy = energy
        if kind == 'AREA':
            ld.size = size
        ob = bpy.data.objects.new(name, ld)
        ob.location = loc
        ob.rotation_euler = rot
        scene.collection.objects.link(ob)
    light("key", 'AREA', (1.0, -3.0, 3.0), (math.radians(50), 0, math.radians(15)), 650, 3.0)
    light("fill", 'AREA', (-1.5, 3.0, 2.0), (math.radians(-55), 0, math.radians(200)), 250, 3.0)
    light("top", 'AREA', (0.1, 0.0, 4.0), (0, 0, 0), 300, 4.0)
    return eng


def _camera(scene, name, loc, rot, ortho_scale=None, lens=70):
    cd = bpy.data.cameras.new(name)
    if ortho_scale:
        cd.type = 'ORTHO'
        cd.ortho_scale = ortho_scale
    else:
        cd.lens = lens
    cd.clip_end = 100
    ob = bpy.data.objects.new(name, cd)
    ob.location = loc
    ob.rotation_euler = rot
    scene.collection.objects.link(ob)
    return ob


def _look_at(cam, target):
    d = (Vector(target) - cam.location)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def render_views(out_dir, views=None):
    scene = bpy.context.scene
    os.makedirs(out_dir, exist_ok=True)
    centre = Vector((0.13, 0.0, 0.55))
    all_views = {}

    # matches the official studio photo (ortho, same px/mm, rear axle at the same pixel)
    width_m = PHOTO_PX / PHOTO_SCALE
    cx = S.REAR_AXLE.x + (PHOTO_PX / 2 - PHOTO_REAR_AXLE_PX[0]) / PHOTO_SCALE
    cz = S.REAR_AXLE.z + (PHOTO_REAR_AXLE_PX[1] - PHOTO_PX / 2) / PHOTO_SCALE
    all_views["side_photo"] = (_camera(scene, "cam_side_photo", (cx, -6.0, cz), (math.radians(90), 0, 0), width_m),
                               (PHOTO_PX, PHOTO_PX))
    all_views["side_nondrive"] = (_camera(scene, "cam_side_nd", (cx, 6.0, cz), (math.radians(90), 0, math.radians(180)),
                                          width_m), (1400, 1400))
    for name, loc, size in (("front34", (2.2, -2.4, 1.3), (1600, 1200)),
                            ("rear34", (-2.4, -2.0, 1.4), (1600, 1200)),
                            ("front34_nd", (2.2, 2.4, 1.2), (1600, 1200)),
                            ("front", (4.0, 0.0, 0.9), (1000, 1200)),
                            ("top", (0.13, 0.0, 5.0), (1200, 1000)),
                            ("cockpit", (0.0, -0.9, 1.55), (1400, 1000)),
                            ("drivetrain", (-0.1, -1.1, 0.55), (1400, 1000)),
                            ("wheel_close", (S.FRONT_AXLE.x + 0.55, -0.75, 0.62), (1400, 1000)),
                            ("tyre_close", (S.FRONT_AXLE.x + 0.62, -0.36, 0.66), (1400, 1000)),
                            # straight at the front of the front tyre, like Maxxis' tread photo
                            ("tread_front", (S.FRONT_AXLE.x + 0.95, 0.0, S.FRONT_AXLE.z + 0.10), (1000, 1000)),
                            # drive-side sidewall graphics of the front tyre (REKON RACE ... TR)
                            ("tyre_logo", (S.FRONT_AXLE.x - 0.20, -0.62, S.FRONT_AXLE.z + 0.30), (1400, 1000)),
                            # straight side views (long lens, ~4 px/mm) of the rear drivetrain and the crank
                            ("cassette_side", (S.REAR_AXLE.x - 0.01, -1.30, S.REAR_AXLE.z - 0.07), (1200, 1200)),
                            ("crank_side", (S.BB.x + 0.06, -1.30, S.BB.z), (1400, 1000)),
                            # pass 3 close-ups: head tube joints, fork leg, quick-release seat clamp (left side)
                            ("head_close", tuple(S.on_axis(60) + Vector((0.30, -0.42, 0.12))), (1400, 1000)),
                            ("fork_close", tuple(S.FRONT_AXLE + Vector((0.32, -0.55, 0.30))), (1000, 1200)),
                            ("seat_close", tuple(S.ST_TOP + Vector((0.20, 0.36, 0.10))), (1400, 1000)),
                            # pass 4 close-ups: left lever + grip from above/behind, both calipers from the left side
                            ("lever_close", tuple(Vector((0.30, 0.48, 1.16))), (1400, 1000)),
                            ("caliper_front", tuple(S.FRONT_AXLE + Vector((-0.16, 0.42, 0.14))), (1400, 1000)),
                            ("caliper_rear", tuple(S.REAR_AXLE + Vector((0.20, 0.42, 0.16))), (1400, 1000))):
        lens = {"cockpit": 50, "drivetrain": 50, "wheel_close": 50, "tyre_close": 50, "tread_front": 135,
                "tyre_logo": 60, "cassette_side": 120, "crank_side": 110, "head_close": 60, "fork_close": 55,
                "seat_close": 70, "lever_close": 55, "caliper_front": 60, "caliper_rear": 60}.get(name, 70)
        cam = _camera(scene, "cam_" + name, loc, (0, 0, 0), lens=lens)
        target = {"cockpit": (0.52, 0.0, 1.02), "drivetrain": (-0.2, 0.0, 0.33),
                  "wheel_close": tuple(S.FRONT_AXLE), "tyre_close": (S.FRONT_AXLE.x + 0.30, -0.02, S.FRONT_AXLE.z + 0.17),
                  "tread_front": (S.FRONT_AXLE.x + 0.37, 0.0, S.FRONT_AXLE.z + 0.02),
                  "tyre_logo": (S.FRONT_AXLE.x - 0.25, -0.03, S.FRONT_AXLE.z + 0.20),
                  "cassette_side": (S.REAR_AXLE.x - 0.01, 0.0, S.REAR_AXLE.z - 0.07),
                  "crank_side": (S.BB.x + 0.06, 0.0, S.BB.z),
                  "head_close": tuple(S.on_axis(60)), "fork_close": tuple(S.FRONT_AXLE + Vector((0.0, 0.0, 0.17))),
                  "seat_close": tuple(S.ST_TOP), "lever_close": (0.53, 0.25, 0.99),
                  "caliper_front": tuple(S.FRONT_AXLE + Vector((-0.07, 0.05, 0.035))),
                  "caliper_rear": tuple(S.REAR_AXLE + Vector((0.065, 0.05, 0.04)))}.get(name, centre)
        _look_at(cam, target)
        all_views[name] = (cam, size)

    for name, (cam, (w, h)) in all_views.items():
        if views and name not in views:
            continue
        scene.camera = cam
        scene.render.resolution_x, scene.render.resolution_y = w, h
        scene.render.filepath = os.path.join(out_dir, f"{name}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", scene.render.filepath)
