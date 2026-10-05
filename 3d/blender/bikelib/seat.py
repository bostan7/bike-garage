"""Syncros 31.6 x 400 mm seatpost (+ seat clamp) and Syncros Belcarra Regular 2.5 saddle."""
import math

import bpy
from mathutils import Vector

from . import materials as M
from . import meshkit as mk
from . import spec as S
from .meshkit import Part, X, Y, Z


def saddle_top():
    return S.on_seat_axis(S.SADDLE_HEIGHT)


def post_head():
    return S.on_seat_axis(S.SADDLE_HEIGHT - 50.0)


def build_seatpost(coll):
    part = Part("seatpost", "Saddle & seatpost")
    black, steel, gloss = M.get("black_anodised"), M.get("steel"), M.get("black_gloss")
    head = post_head()
    mk.cyl(part, S.on_seat_axis(S.SEAT_TUBE - 100), head - S.SEAT_DIR * 0.004, S.SEATPOST_R, black, n=40)
    # two-bolt cradle head: lower cradle on the post, upper clamp plate over the rails
    cage = mk.scratch()
    mk.box(cage, head + Z * 0.004, (0.060, 0.030, 0.012), None)
    mk.cyl(cage, head - S.SEAT_DIR * 0.012, head + Z * 0.004, 0.0170, None, n=12)
    part.add_bm(mk.subdivided(cage, 2), black)
    mk.box(part, head + Z * 0.018, (0.040, 0.050, 0.004), black)
    for dx in (-0.020, 0.020):
        mk.cyl(part, head + X * dx + Z * -0.004, head + X * dx + Z * 0.022, 0.0035, steel, n=10)
        mk.cyl(part, head + X * dx + Z * -0.004, head + X * dx + Z * -0.008, 0.0050, steel, n=6)
    # seat clamp (34.9 mm) with slot and bolt
    clamp = mk.scratch()
    mk.revolve(clamp, Vector((0, 0, 0)), [(0.0162, 0.0), (0.0210, 0.0), (0.0215, 0.0060), (0.0210, 0.0120),
                                          (0.0162, 0.0120)], None, n=48)
    st_front = Vector((math.sin(math.radians(S.STA)), 0.0, math.cos(math.radians(S.STA))))
    mk.place(clamp.bm, S.ST_TOP - S.SEAT_DIR * 0.004, st_front, S.SEAT_DIR, -Y)
    part.add_bm(clamp.bm, gloss, free=False)
    lug = S.ST_TOP + S.SEAT_DIR * 0.002 - st_front * 0.024
    mk.box(part, lug, (0.010, 0.016, 0.012), gloss, rot=mk.basis(st_front, S.SEAT_DIR))
    mk.cyl(part, lug + Y * 0.012, lug - Y * 0.012, 0.0030, steel, n=10)
    mk.cyl(part, lug - Y * 0.012, lug - Y * 0.015, 0.0045, steel, n=6)
    # Syncros logo running down the drive side of the post
    probe = mk._text_mesh("SYNCROS", 1.0, 0.0)
    xs = [v.co.x for v in probe.vertices]
    bpy.data.meshes.remove(probe)
    sx = 0.055 / (max(xs) - min(xs))
    base = S.on_seat_axis(S.SEAT_TUBE + 75)

    def xform(v):
        ang = -math.pi / 2 + (v.y * sx) / S.SEATPOST_R
        r = S.SEATPOST_R + 0.0004
        return base - S.SEAT_DIR * (v.x * sx) + Y * (math.sin(ang) * r) + st_front * (math.cos(ang) * r)
    mk.add_text(part, "SYNCROS", 1.0, 0.0, M.get("tyre_text"), xform)
    return part.finish(coll, sharp_angle=50.0)


# saddle stations: x (forward, m), half width, half thickness, vertical offset of the top line
SADDLE = [(-0.122, 0.030, 0.006, 0.004), (-0.118, 0.050, 0.011, 0.003), (-0.110, 0.062, 0.014, 0.002),
          (-0.096, 0.068, 0.016, 0.001), (-0.075, 0.068, 0.017, 0.0), (-0.050, 0.062, 0.017, -0.001),
          (-0.025, 0.052, 0.017, -0.002), (0.000, 0.040, 0.016, -0.003), (0.025, 0.030, 0.015, -0.003),
          (0.050, 0.024, 0.014, -0.0025), (0.080, 0.021, 0.013, -0.0015), (0.105, 0.019, 0.012, -0.001),
          (0.125, 0.016, 0.011, -0.0015), (0.138, 0.012, 0.009, -0.003), (0.145, 0.006, 0.006, -0.005)]


def build_saddle(coll):
    part = Part("saddle", "Saddle & seatpost")
    cover, base_mat, rails_mat = M.get("black_matte"), M.get("black_gloss"), M.get("black_anodised")
    top = saddle_top() + X * 0.012
    pts, prof = [], []
    for x, w, h, dz in SADDLE:
        pts.append(top + X * x + Z * (dz - h))
        prof.append((w, h))
    shell = mk.scratch()
    mk.tube_path(shell, mk.catmull_rom(pts, 3), [mk.interp_keys([(i / (len(prof) - 1), p) for i, p in enumerate(prof)],
                                                                 t / (3 * (len(prof) - 1)))
                                                  for t in range(3 * (len(prof) - 1) + 1)],
                 None, n=40, power=3.0)
    part.add_bm(mk.subdivided(shell, 1), cover)
    # plastic base, slightly smaller and lower
    base_pts = [p + Z * -0.006 for p in pts[1:-1]]
    base_prof = [(w * 0.88, h * 0.55) for (w, h) in prof[1:-1]]
    mk.tube_path(part, base_pts, base_prof, base_mat, n=24, power=3.0)
    # rails (7 mm), bending up into the base at both ends
    head = post_head()
    for side in (-1.0, 1.0):
        y = side * 0.021
        z_rail = head.z + 0.022
        ctrl = [top + X * -0.098 + Y * (y * 1.5) + Z * -0.016, Vector((top.x - 0.078, top.y + y * 1.1, z_rail + 0.004)),
                Vector((top.x - 0.040, top.y + y, z_rail)), Vector((top.x + 0.040, top.y + y, z_rail)),
                Vector((top.x + 0.080, top.y + y * 0.7, z_rail + 0.006)), top + X * 0.102 + Y * (y * 0.45) + Z * -0.014]
        mk.curve_tube(part, ctrl, 0.0035, rails_mat, samples=8, n=12)
    # SYNCROS on the back of the saddle
    probe = mk._text_mesh("SYNCROS", 1.0, 0.0)
    xs = [v.co.x for v in probe.vertices]
    bpy.data.meshes.remove(probe)
    sx = 0.040 / (max(xs) - min(xs))
    back = top + X * -0.1235 + Z * (0.004 - 0.008)
    mk.add_text(part, "SYNCROS", 1.0, 0.0, M.get("tyre_text"),
                lambda v: back + Y * (-v.x * sx) + Z * (v.y * sx) + X * -0.0006)
    return part.finish(coll, sharp_angle=60.0)
