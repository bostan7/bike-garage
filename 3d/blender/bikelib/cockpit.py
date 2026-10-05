"""Cockpit: Syncros stem (6 deg), Syncros 740 mm flat bar (9 deg backsweep), Toni's black WTB lock-on grips,
Deore 12s shifter."""
import math

import bpy
from mathutils import Vector

from . import materials as M
from . import meshkit as mk
from . import spec as S
from .meshkit import Part, X, Y, Z


def stem_clamp_center():
    return S.on_axis(-(S.HEADSET_COVER + S.SPACERS + S.STEM_STACK / 2))


def stem_dir():
    a = math.radians((90.0 - S.HTA) - S.STEM_ANGLE)        # 14.5 deg above horizontal
    return Vector((math.cos(a), 0.0, math.sin(a)))


def bar_center():
    return stem_clamp_center() + stem_dir() * S.STEM_LEN


def _sweep_x(y):
    """Backsweep: straight in the middle, ends swept back 9 deg."""
    return -max(0.0, abs(y) - 0.06) * math.tan(math.radians(S.BAR_SWEEP))


def bar_point(y):
    return bar_center() + Vector((_sweep_x(y), y, 0.0))


def bar_dir(y):
    """Unit vector along the bar at lateral position y, pointing outwards."""
    s = 1.0 if y >= 0 else -1.0
    return (bar_point(y + s * 0.001) - bar_point(y)).normalized()


def _logo(part, text, origin, along, up, length, mat):
    probe = mk._text_mesh(text, 1.0, 0.0)
    xs = [v.co.x for v in probe.vertices]
    bpy.data.meshes.remove(probe)
    sx = length / (max(xs) - min(xs))
    mk.add_text(part, text, 1.0, 0.0, mat, lambda v: origin + along * (v.x * sx) + up * (v.y * sx))


def build_stem(coll):
    part = Part("stem", "Cockpit")
    black, steel = M.get("black_anodised"), M.get("steel")
    c = stem_clamp_center()
    d = stem_dir()
    b = bar_center()
    half = S.AXIS_UP * (S.STEM_STACK / 2 * S.MM)
    up = d.cross(Y).normalized()                              # top of the stem
    cage = mk.scratch()
    # steerer clamp, extension, bar clamp: overlapping cages, subdivided into one smooth forging
    mk.cyl(cage, c - half, c + half, 0.0205, None, n=12)
    mk.box(cage, c.lerp(b, 0.5), ((b - c).length * 0.85, 0.034, 0.030), None, rot=mk.basis(d, up))
    mk.cyl(cage, b + Y * 0.023, b - Y * 0.023, 0.0215, None, n=12)
    part.add_bm(mk.subdivided(cage, 2), black)
    # steerer clamp slit bolts at the back
    back = -S.AXIS_FWD
    for dz in (-0.0095, 0.0095):
        p = c + back * 0.021 + S.AXIS_UP * dz
        mk.cyl(part, p + Y * 0.013, p - Y * 0.013, 0.0045, steel, n=12)
        mk.cyl(part, p + Y * 0.013, p + Y * 0.015, 0.0030, black, n=6)
    # 2-bolt faceplate (SCOTT spec)
    fp = mk.plate2d(mk.rounded_rect(0.0, 0.0, 0.048, 0.040, 0.008),
                    holes=[mk.rounded_rect(0.0, 0.0, 0.016, 0.012, 0.004)], thickness=0.008, bevel=0.0015)
    mk.place(fp, b + d * 0.020, Y, up, d)
    part.add_bm(fp, black)
    for dz in (-0.0135, 0.0135):
        p = b + d * 0.024 + up * dz
        mk.cyl(part, p - d * 0.001, p + d * 0.0028, 0.0046, steel, n=16)
        mk.cyl(part, p + d * 0.0028, p + d * 0.0030, 0.0022, M.get("black_gloss"), n=6)     # hex socket
    _logo(part, "SYNCROS", c.lerp(b, 0.52) + up * 0.0156, d, Y, 0.030, M.get("tyre_text"))
    return part.finish(coll, sharp_angle=50.0)


def build_handlebar(coll):
    part = Part("handlebar", "Cockpit")
    black = M.get("black_anodised")
    ys = [-S.BAR_HALF, -0.30, -0.20, -0.10, -0.05, 0.0, 0.05, 0.10, 0.20, 0.30, S.BAR_HALF]
    pts = mk.catmull_rom([bar_point(y) for y in ys], 6)
    prof = []
    for p in pts:
        ay = abs(p.y - bar_center().y)
        r = 0.0159 if ay < 0.04 else (0.0111 if ay > 0.10 else 0.0159 + (0.0111 - 0.0159) * (ay - 0.04) / 0.06)
        prof.append((r, r))
    mk.tube_path(part, pts, prof, black, n=40)
    for side in (-1.0, 1.0):
        p = bar_point(side * 0.075)
        _logo(part, "SYNCROS", p + Z * 0.0136, Y * side if side > 0 else -Y, -X if side > 0 else X, 0.035,
              M.get("tyre_text"))
    return part.finish(coll)


def build_grips(coll):
    """Toni's grips: black WTB lock-on, clamp ring with a bolt at both ends, waffle-pattern rubber
    (WTB Wafel-like; exact model to be confirmed by Toni)."""
    part = Part("grips", "Cockpit")
    rubber, black, steel = M.get("rubber"), M.get("black_anodised"), M.get("steel")
    for side in (1.0, -1.0):
        y_end = side * S.BAR_HALF
        y_in = side * (S.BAR_HALF - S.GRIP_LEN)
        a, b = bar_point(y_in), bar_point(y_end)
        d = (b - a).normalized()
        ring_w = 0.0085
        g0, g1 = a + d * ring_w, b - d * ring_w
        L = (g1 - g0).length
        mk.cyl(part, g0, g1, 0.0152, rubber, n=32, caps=False)                                  # rubber core
        _, nn, bb = mk.frame_at(d, Z)
        n_around, n_along = 16, max(6, int(L / 0.0062))
        for i in range(n_along):                                                                 # waffle blocks
            c = g0.lerp(g1, (i + 0.5) / n_along)
            for k in range(n_around):
                ang = 2 * math.pi * (k + 0.5 * (i % 2)) / n_around
                rd = nn * math.cos(ang) + bb * math.sin(ang)
                mk.box(part, c + rd * 0.0158, (0.0044, 0.0044, 0.0016), rubber, rot=mk.basis(d, rd))
        for e0, e1 in ((a, a + d * ring_w), (b - d * ring_w, b)):                               # clamp rings
            mk.cyl(part, e0, e1, 0.0170, black, n=36)
            q = e0.lerp(e1, 0.5) + Z * -0.0168
            mk.cyl(part, q, q + Z * -0.0022, 0.0021, steel, n=10)
            mk.cyl(part, q + Z * -0.0022, q + Z * -0.0024, 0.0011, M.get("black_gloss"), n=6)
        mk.cyl(part, b, b + d * 0.0030, 0.0158, black, r2=0.0150, n=36)                        # end plug
    return part.finish(coll)


def build_shifter(coll):
    part = Part("shifter", "Cockpit")
    grey, black, gloss, steel = M.get("grey_plastic"), M.get("black_anodised"), M.get("black_gloss"), M.get("steel")
    y = -(S.BAR_HALF - S.GRIP_LEN - 0.040)
    p = bar_point(y)
    axis = bar_dir(y)
    mk.cyl(part, p - axis * 0.007, p + axis * 0.007, 0.0145, black, n=24)                 # band clamp
    mk.cyl(part, p + Z * -0.0165 - axis * 0.004, p + Z * -0.0165 + axis * 0.004, 0.0035, steel, n=10)
    pod = p + Z * -0.024 + X * -0.004
    cage = mk.scratch()
    mk.box(cage, pod, (0.050, 0.026, 0.022), None, rot=mk.basis(X, Z))
    mk.box(cage, pod + X * 0.020 + Z * 0.006, (0.020, 0.020, 0.018), None)
    part.add_bm(mk.subdivided(cage, 2), grey)
    # main (thumb) paddle and release lever
    paddle = mk.scratch()
    mk.tube_path(paddle, [pod + X * -0.016 + Z * -0.004, pod + X * -0.034 + Z * -0.012 + axis * 0.004,
                          pod + X * -0.042 + Z * -0.020 + axis * 0.010],
                 [(0.0050, 0.0110), (0.0042, 0.0115), (0.0040, 0.0110)], None, n=10, power=3.0)
    part.add_bm(mk.subdivided(paddle, 1), black)
    rel = mk.scratch()
    mk.tube_path(rel, [pod + X * 0.004 + Z * 0.008, pod + X * -0.006 + Z * 0.016 + axis * 0.004,
                       pod + X * -0.012 + Z * 0.020 + axis * 0.010],
                 [(0.0030, 0.0060), (0.0028, 0.0060), (0.0028, 0.0055)], None, n=8, power=3.0)
    part.add_bm(mk.subdivided(rel, 1), black)
    probe = mk._text_mesh("12s", 1.0, 0.0)
    xs = [v.co.x for v in probe.vertices]
    bpy.data.meshes.remove(probe)
    s12 = 0.010 / (max(xs) - min(xs))
    o12 = pod + X * -0.0262 + Z * 0.002
    mk.add_text(part, "12s", 1.0, 0.0, M.get("tyre_text"), lambda v: o12 + axis * (v.x * s12) + Z * (v.y * s12))
    # cable adjuster barrel at the front
    adj = pod + X * 0.032 + Z * 0.004
    mk.cyl(part, adj - X * 0.004, adj + X * 0.008, 0.0045, steel, n=16)
    # shift housing: forward, then into the drive-side down-tube port; out of the chainstay to the derailleur
    port = S.on_axis(S.DT_AT_HT) + (S.BB - S.on_axis(S.DT_AT_HT)).normalized() * 0.10 - Y * 0.031
    ctrl = [adj + X * 0.008, adj + X * 0.09 + Z * -0.03, S.on_axis(15) + S.AXIS_FWD * 0.11 - Y * 0.03,
            port - Y * 0.02 + Z * 0.03, port]
    mk.curve_tube(part, ctrl, 0.0025, gloss, samples=12, n=10)
    cs_exit = S.P(S.REAR_X + 70, S.BB_DROP + 4, -70)
    # loops up and back over the cassette into the end of the derailleur's bracket arm (SCOTT's photo)
    ra = S.REAR_AXLE
    loop = [ra + Vector((x * 0.001, y, z * 0.001)) for x, z, y in
            ((48, -2, -0.080), (14, 19, -0.084), (-18, 28, -0.086), (-42, 24, -0.087), (-55, 8, -0.087),
             (-57, -14, -0.087))]
    mk.curve_tube(part, [cs_exit, cs_exit + X * -0.02 + Y * -0.008 + Z * -0.016] + loop, 0.0025, gloss,
                  samples=10, n=10)
    return part.finish(coll, sharp_angle=50.0)
