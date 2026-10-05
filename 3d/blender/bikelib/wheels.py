"""Wheels (Syncros 32H rims, black 15G spokes 3-cross, Formula CL-51 / Shimano FH-MT401-B hubs, QR)
and Maxxis Rekon Race 29 x 2.25 tyres."""
import math

import bpy
from mathutils import Vector

from . import materials as M
from . import meshkit as mk
from . import spec as S
from .meshkit import Part, X, Y, Z

# rim cross-section (radius from axle, lateral y): hooked bead seats, double wall, spoke bed
RIM_PROFILE = [(0.2955, 0.000), (0.2962, 0.0050), (0.2985, 0.0095), (0.3025, 0.0128), (0.3080, 0.0136),
               (0.3150, 0.0137), (0.3178, 0.0130), (0.3183, 0.0118), (0.3170, 0.0110), (0.3112, 0.0109),
               (0.3100, 0.0095), (0.3098, 0.0030), (0.3085, 0.000), (0.3098, -0.0030), (0.3100, -0.0095),
               (0.3112, -0.0109), (0.3170, -0.0110), (0.3183, -0.0118), (0.3178, -0.0130), (0.3150, -0.0137),
               (0.3080, -0.0136), (0.3025, -0.0128), (0.2985, -0.0095), (0.2962, -0.0050)]
SPOKE_HOLE_R = 0.2990


def _text_around(part, c, text, a0, r_text, y_side, side, height, length, mat):
    """Text running around the wheel axis on a flat side at lateral y_side; readable from that side."""
    probe = mk._text_mesh(text, 1.0, 0.0)
    xs = [v.co.x for v in probe.vertices]
    ys = [v.co.y for v in probe.vertices]
    bpy.data.meshes.remove(probe)
    sx, sy = length / (max(xs) - min(xs)), height / (max(ys) - min(ys))

    def xform(v):
        a = a0 + side * (v.x * sx) / r_text
        r = r_text + v.y * sy
        return c + Vector((r * math.cos(a), y_side, r * math.sin(a)))
    mk.add_text(part, text, 1.0, 0.0, mat, xform)


def _hub(part, c, flanges, front, mat):
    yl, yr = flanges
    old = (S.FRONT_OLD if front else S.REAR_OLD) / 2

    def flange(y, r):
        return [(0.0140, y - 0.0050), (r - 0.0015, y - 0.0018), (r, y - 0.0008), (r, y + 0.0008),
                (r - 0.0015, y + 0.0018), (0.0140, y + 0.0045)]
    if front:
        prof = [(0.0055, -old), (0.0115, -old), (0.0118, yr - 0.007)] + flange(yr, 0.0245) + \
               [(0.0128, 0.0)] + flange(yl, 0.0245) + \
               [(0.0175, yl + 0.006), (0.0175, old - 0.005), (0.0115, old - 0.004), (0.0115, old), (0.0055, old)]
    else:
        prof = [(0.0055, -old), (0.0110, -old), (0.0110, -old + 0.004), (0.0172, -old + 0.006),
                (0.0172, yr - 0.006)] + flange(yr, 0.0255) + [(0.0150, 0.008)] + flange(yl, 0.0255) + \
               [(0.0175, yl + 0.006), (0.0175, old - 0.005), (0.0110, old - 0.004), (0.0110, old), (0.0055, old)]
    mk.revolve(part, c, prof, mat, n=48)


def _spokes(part, c, flanges, hub_r):
    black, steel = M.get("spoke_black"), M.get("steel")
    step = 2 * math.pi / S.SPOKES
    cross = 3 * 4 * math.pi / S.SPOKES          # 3-cross: 3 x 720 deg / 32
    for i in range(S.SPOKES):
        theta = step * i
        left = i % 2 == 0
        lead = 1.0 if (i // 2) % 2 == 0 else -1.0
        phi = theta + lead * cross
        fy = flanges[0] if left else flanges[1]
        hub = c + Vector((hub_r * math.cos(phi), fy, hub_r * math.sin(phi)))
        rim = c + Vector((SPOKE_HOLE_R * math.cos(theta), 0.0015 if left else -0.0015, SPOKE_HOLE_R * math.sin(theta)))
        d = (rim - hub).normalized()
        mk.cyl(part, hub + d * 0.002, rim, 0.0009, black, n=6, caps=False)
        # J-bend: the spoke turns through the flange and ends in a round head on the outside
        out = Y * (0.0035 if left else -0.0035)
        mk.curve_tube(part, [hub + d * 0.003, hub, hub + out], 0.0009, black, samples=3, n=6)
        mk.ellipsoid(part, hub + out, (0.0016, 0.0016, 0.0016), black, segs=6, rings=4)
        # nipple: shaft + head in the rim
        mk.cyl(part, rim - d * 0.012, rim + d * 0.0005, 0.0019, steel, n=8)
        mk.cyl(part, rim + d * 0.0005, rim + d * 0.0025, 0.0028, steel, r2=0.0024, n=8)


def _valve(part, c, theta):
    steel, black = M.get("steel"), M.get("black_matte")
    er = Vector((math.cos(theta), 0.0, math.sin(theta)))
    base = c + er * 0.2960
    mk.cyl(part, base + er * 0.004, base - er * 0.022, 0.0030, steel, n=12)
    mk.cyl(part, base - er * 0.010, base - er * 0.016, 0.0045, steel, n=12)                 # lock nut
    mk.cyl(part, base - er * 0.022, base - er * 0.034, 0.0040, black, n=12)                 # cap


def _skewer(part, c, front):
    """QR skewer: shaped lever on the left (+Y), knurled nut on the drive side."""
    old = (S.FRONT_OLD if front else S.REAR_OLD) / 2
    black, steel = M.get("black_anodised"), M.get("steel")
    mk.cyl(part, c + Y * (old + 0.012), c - Y * (old + 0.012), 0.0025, steel, n=10)
    nut = mk.scratch()
    ring = [c - Y * (old + 0.004) + (X * math.cos(2 * math.pi * k / 36) + Z * math.sin(2 * math.pi * k / 36))
            * (0.0105 + (0.0006 if k % 2 else 0.0)) for k in range(36)]
    mk.add_rings(nut, [ring, [p - Y * 0.010 for p in ring]], None)
    part.add_bm(nut.bm, black, smooth=False, free=False)
    mk.cyl(part, c + Y * (old + 0.002), c + Y * (old + 0.014), 0.0110, black, r2=0.0095, n=24)  # cam body
    lever = mk.scratch()
    d = Vector((-0.80, 0.0, 0.60)).normalized()
    p0 = c + Y * (old + 0.010)
    mk.tube_path(lever, [p0, p0 + d * 0.025 + Y * 0.004, p0 + d * 0.050 + Y * 0.003, p0 + d * 0.066],
                 [(0.0065, 0.0040), (0.0060, 0.0035), (0.0075, 0.0030), (0.0080, 0.0028)], None, n=8, power=3.0)
    part.add_bm(mk.subdivided(lever, 1), black)


def build_wheel(coll, front):
    name = "wheel_front" if front else "wheel_rear"
    c = S.FRONT_AXLE if front else S.REAR_AXLE
    flanges = S.FRONT_FLANGE_Y if front else S.REAR_FLANGE_Y
    part = Part(name, "Wheels & tyres")
    mk.revolve(part, c, RIM_PROFILE, M.get("black_matte"), n=128)
    for side in (-1.0, 1.0):
        for a0 in (math.radians(60), math.radians(240)):
            _text_around(part, c, "SYNCROS", a0, 0.3045, side * 0.01385, side, 0.0055, 0.055, M.get("tyre_text"))
    _hub(part, c, flanges, front, M.get("black_anodised"))
    _spokes(part, c, flanges, 0.0215 if front else 0.0225)
    _valve(part, c, 2 * math.pi / S.SPOKES * 0.5 + math.pi)
    _skewer(part, c, front)
    return part.finish(coll, pivot=c, sharp_angle=50.0)


# ------------------------------------------------------------------------------------- tyres

TYRE_RC = 0.3390        # centre of the tyre cross-section (radius from the axle)
TYRE_AR = 0.0280        # radial half-height (casing at 0.367, knobs reach 0.370)
TYRE_AY = S.TYRE_HALF_W


def _tyre_surface(c, ang, y):
    s = max(-0.999, min(0.999, y / TYRE_AY))
    th = math.asin(s)
    r = TYRE_RC + TYRE_AR * math.cos(th)
    er = Vector((math.cos(ang), 0.0, math.sin(ang)))
    p = c + er * r + Y * y
    nrm = (er * (math.cos(th) / TYRE_AR) + Y * (math.sin(th) / TYRE_AY)).normalized()
    return p, nrm


def _knob(bm, p, nrm, tang, length, width, height, taper=0.72, ramp=0.0, sink=0.0008):
    """Tapered tread block; `ramp` lowers the leading edge (Rekon Race centre knobs are ramped)."""
    lat = nrm.cross(tang).normalized()
    base = p - nrm * sink
    vs = []
    for dz, scale in ((0.0, 1.0), (height + sink, taper)):
        for sl, sw in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            h = dz
            if dz > 0 and sl > 0:
                h -= ramp * height
            vs.append(bm.verts.new(base + tang * (sl * length / 2 * scale) + lat * (sw * width / 2 * scale) + nrm * h))
    b, t = vs[:4], vs[4:]
    faces = [bm.faces.new((b[3], b[2], b[1], b[0])), bm.faces.new((t[0], t[1], t[2], t[3]))]
    for i in range(4):
        j = (i + 1) % 4
        faces.append(bm.faces.new((b[i], b[j], t[j], t[i])))
    return faces


def build_tyre(coll, front):
    name = "tire_front" if front else "tire_rear"
    c = S.FRONT_AXLE if front else S.REAR_AXLE
    part = Part(name, "Wheels & tyres")
    rubber = M.get("rubber")
    prof = [(TYRE_RC + TYRE_AR * math.cos(2 * math.pi * k / 36), TYRE_AY * math.sin(2 * math.pi * k / 36))
            for k in range(36)]
    mk.revolve(part, c, prof, rubber, n=144)
    # bead line just above the rim on both sides
    for side in (-1.0, 1.0):
        r = 0.3215
        cos_t = (r - TYRE_RC) / TYRE_AR
        y = side * (TYRE_AY * math.sqrt(1 - cos_t * cos_t) + 0.0003)
        ring = [c + Vector((r * math.cos(2 * math.pi * k / 144), y, r * math.sin(2 * math.pi * k / 144)))
                for k in range(144)]
        ring.append(ring[0])
        mk.tube_path(part, ring, (0.0007, 0.0007), rubber, n=5, caps=False)

    # Rekon Race tread
    rows = 150
    faces = []
    for k in range(rows):
        ang = 2 * math.pi * k / rows
        odd = k % 2 == 1
        if odd:
            knobs = [(0.0, 0.0052, 0.0052, 0.0028, 0.45), (-0.0128, 0.0058, 0.0046, 0.0031, 0.25),
                     (0.0128, 0.0058, 0.0046, 0.0031, 0.25)]
        else:
            knobs = [(-0.0048, 0.0050, 0.0040, 0.0027, 0.45), (0.0048, 0.0050, 0.0040, 0.0027, 0.45)]
        knobs += [(-0.0218 if odd else -0.0226, 0.0072, 0.0058, 0.0038, 0.0),
                  (0.0226 if odd else 0.0218, 0.0072, 0.0058, 0.0038, 0.0)]
        for y, l, w, h, ramp in knobs:
            a = ang + (0.010 if odd else 0.0)
            p, nrm = _tyre_surface(c, a, y)
            t = Vector((-math.sin(a), 0.0, math.cos(a)))
            t = (t - nrm * t.dot(nrm)).normalized()
            faces += _knob(part.bm, p, nrm, t, l, w, h, ramp=ramp)
    part.tag(faces, rubber, smooth=False)

    # MAXXIS on both sidewalls (twice per side), REKON RACE and size once per side
    txt = M.get("tyre_text")
    r_text = 0.3505
    for side in (-1.0, 1.0):
        for a0, text, height, length in ((math.radians(118), "MAXXIS", 0.0110, 0.085),
                                         (math.radians(298), "MAXXIS", 0.0110, 0.085),
                                         (math.radians(208), "REKON RACE", 0.0065, 0.080),
                                         (math.radians(30), "29 x 2.25", 0.0050, 0.040)):
            probe = mk._text_mesh(text, 1.0, 0.0)
            xs = [v.co.x for v in probe.vertices]
            ys = [v.co.y for v in probe.vertices]
            bpy.data.meshes.remove(probe)
            sx, sy = length / (max(xs) - min(xs)), height / (max(ys) - min(ys))

            def xform(v, a0=a0, side=side, sx=sx, sy=sy):
                a = a0 + side * (v.x * sx) / r_text
                r = r_text + v.y * sy
                cos_t = max(-1.0, min(1.0, (r - TYRE_RC) / TYRE_AR))
                y = TYRE_AY * math.sqrt(1.0 - cos_t * cos_t) + 0.0005
                return c + Vector((r * math.cos(a), side * y, r * math.sin(a)))
            mk.add_text(part, text, 1.0, 0.0, txt, xform)
    return part.finish(coll, pivot=c, sharp_angle=50.0)
