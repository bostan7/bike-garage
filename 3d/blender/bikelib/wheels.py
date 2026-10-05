"""Wheels (stock: Syncros 32H rims, black 15G spokes 3-cross, Formula CL-51 / Shimano FH-MT401-B hubs, QR)
and Toni's tyres: Maxxis Rekon Race 29 x 2.35 EXO TR Tan Wall (replaced the stock 29 x 2.25)."""
import math

import bmesh
import bpy
from mathutils import Vector

from . import materials as M
from . import meshkit as mk
from . import spec as S
from .meshkit import Part, X, Y, Z


def _rim_profile():
    """Rim cross-section (radius from axle, lateral y): rounded double-wall body, flat sidewall,
    hooked bead seat and centre well. Built for +y and mirrored."""
    half = []
    for k in range(10):                                   # rounded spoke bed -> sidewall
        a = math.radians(180 - 90 * k / 9)
        half.append((0.3080 + 0.0125 * math.cos(a), 0.0136 * math.sin(a)))
    half += [(0.3118, 0.01375), (0.3150, 0.0137), (0.3170, 0.01345), (0.3180, 0.0129), (0.3184, 0.0121),
             (0.3180, 0.0114), (0.3168, 0.0110), (0.3115, 0.0109), (0.3104, 0.0101), (0.3100, 0.0090),
             (0.3098, 0.0030), (0.3094, 0.0012)]
    centre = [(0.3086, 0.0)]
    other = [(r, -y) for (r, y) in reversed(half[1:])]
    return half + centre + other


RIM_PROFILE = _rim_profile()
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


def _hub(part, c, flanges, front, mat, n):
    yl, yr = flanges
    old = (S.FRONT_OLD if front else S.REAR_OLD) / 2

    def flange(y, r):
        return [(0.0140, y - 0.0050), (r - 0.0030, y - 0.0024), (r - 0.0008, y - 0.0016), (r, y - 0.0006),
                (r, y + 0.0006), (r - 0.0008, y + 0.0016), (r - 0.0030, y + 0.0024), (0.0140, y + 0.0045)]

    def end(y_out, s):
        """Lock nut with a small chamfer and a step down to the axle end (s = +1 left, -1 right)."""
        return [(0.0122, s * (y_out - 0.0050)), (0.0122, s * (y_out - 0.0034)), (0.0112, s * (y_out - 0.0030)),
                (0.0112, s * (y_out - 0.0008)), (0.0100, s * y_out), (0.0055, s * y_out)]
    left_end = end(old, 1.0)
    right_end = list(reversed(end(old, -1.0)))
    if front:
        prof = right_end + [(0.0118, yr - 0.007)] + flange(yr, 0.0245) + \
               [(0.0132, -0.012), (0.0128, 0.0), (0.0132, 0.012)] + flange(yl, 0.0245) + \
               [(0.0175, yl + 0.006), (0.0178, yl + 0.0075), (0.0178, old - 0.008), (0.0168, old - 0.006)] + left_end
    else:
        prof = right_end + [(0.0172, -old + 0.006), (0.0176, -old + 0.008), (0.0176, yr - 0.008), (0.0172, yr - 0.006)] + \
               flange(yr, 0.0255) + [(0.0150, 0.0), (0.0150, 0.008)] + flange(yl, 0.0255) + \
               [(0.0175, yl + 0.006), (0.0178, yl + 0.0075), (0.0178, old - 0.008), (0.0168, old - 0.006)] + left_end
    mk.revolve(part, c, prof, mat, n=n)


def _spokes(part, c, flanges, hub_r, name):
    black, steel = M.get("spoke_black"), M.get("steel")
    n_spoke, n_nip = S.seg(name, 8), S.seg(name, 10)
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
        mk.cyl(part, hub + d * 0.002, rim - d * 0.010, 0.0009, black, n=n_spoke, caps=False)
        # J-bend: the spoke turns through the flange and ends in a round head on the outside
        out = Y * (0.0035 if left else -0.0035)
        mk.curve_tube(part, [hub + d * 0.003, hub, hub + out], 0.0009, black, samples=4, n=n_spoke)
        mk.ellipsoid(part, hub + out, (0.0016, 0.0016, 0.0016), black, segs=n_spoke, rings=5)
        # nipple: square-flatted shaft (for the spoke key) + round head seated in the rim
        mk.tube_path(part, [rim - d * 0.012, rim - d * 0.004], (0.0019, 0.0019), steel, n=n_nip, power=3.2)
        mk.cyl(part, rim - d * 0.004, rim + d * 0.0005, 0.0021, steel, n=n_nip)
        mk.cyl(part, rim + d * 0.0005, rim + d * 0.0025, 0.0028, steel, r2=0.0024, n=n_nip)


def _ribbed_ring(part, a, b, r, ribs, mat):
    """Short knurled cylinder from a to b (valve nut, valve cap)."""
    shape = mk.scratch()
    _, nn, bb = mk.frame_at(b - a, Y)
    ring_a = []
    for k in range(2 * ribs):
        rr = r + (0.0003 if k % 2 else 0.0)
        t = 2 * math.pi * k / (2 * ribs)
        ring_a.append(a + nn * (rr * math.cos(t)) + bb * (rr * math.sin(t)))
    mk.add_rings(shape, [ring_a, [p + (b - a) for p in ring_a]], None)
    part.add_bm(shape.bm, mat, smooth=False)


def _valve(part, c, theta, name):
    steel, black = M.get("steel"), M.get("black_matte")
    er = Vector((math.cos(theta), 0.0, math.sin(theta)))
    base = c + er * 0.2960
    mk.cyl(part, base + er * 0.004, base - er * 0.022, 0.0030, steel, n=S.seg(name, 16))
    _ribbed_ring(part, base - er * 0.010, base - er * 0.016, 0.0045, S.seg(name, 12), steel)    # lock nut
    _ribbed_ring(part, base - er * 0.022, base - er * 0.034, 0.0040, S.seg(name, 10), black)    # cap


def _skewer(part, c, front, name):
    """QR skewer: shaped lever on the left (+Y), knurled nut on the drive side."""
    old = (S.FRONT_OLD if front else S.REAR_OLD) / 2
    black, steel = M.get("black_anodised"), M.get("steel")
    mk.cyl(part, c + Y * (old + 0.012), c - Y * (old + 0.012), 0.0025, steel, n=S.seg(name, 12))
    nut = mk.scratch()
    k_n = S.seg(name, 48)
    n0 = c - Y * (old + 0.004)
    ring = [n0 + (X * math.cos(2 * math.pi * k / k_n) + Z * math.sin(2 * math.pi * k / k_n))
            * (0.0105 + (0.0006 if k % 2 else 0.0)) for k in range(k_n)]
    mk.add_rings(nut, [ring, [p - Y * 0.009 for p in ring],
                       [n0 - Y * 0.0105 + (p - n0) * 0.85 for p in ring]], None)
    part.add_bm(nut.bm, black, smooth=False)
    mk.cyl(part, c + Y * (old + 0.002), c + Y * (old + 0.014), 0.0110, black, r2=0.0095, n=S.seg(name, 32))  # cam body
    mk.cyl(part, c + Y * (old + 0.006), c + Y * (old + 0.0175), 0.0032, steel, n=S.seg(name, 12))           # cam pin
    lever = mk.scratch()
    d = Vector((-0.80, 0.0, 0.60)).normalized()
    p0 = c + Y * (old + 0.010)
    mk.tube_path(lever, [p0, p0 + d * 0.020 + Y * 0.004, p0 + d * 0.040 + Y * 0.004, p0 + d * 0.056 + Y * 0.003,
                         p0 + d * 0.068],
                 [(0.0065, 0.0040), (0.0060, 0.0034), (0.0068, 0.0030), (0.0080, 0.0029), (0.0070, 0.0026)],
                 None, n=10, power=3.0)
    part.add_bm(mk.subdivided(lever, 2), black)


def build_wheel(coll, front):
    name = "wheel_front" if front else "wheel_rear"
    c = S.FRONT_AXLE if front else S.REAR_AXLE
    flanges = S.FRONT_FLANGE_Y if front else S.REAR_FLANGE_Y
    part = Part(name, "Wheels & tyres")
    mk.revolve(part, c, RIM_PROFILE, M.get("black_matte"), n=S.seg(name, 128))
    for side in (-1.0, 1.0):
        for a0 in (math.radians(60), math.radians(240)):
            _text_around(part, c, "SYNCROS", a0, 0.3045, side * 0.01390, side, 0.0055, 0.055, M.get("tyre_text"))
    _hub(part, c, flanges, front, M.get("black_anodised"), S.seg(name, 64))
    _spokes(part, c, flanges, 0.0215 if front else 0.0225, name)
    _valve(part, c, 2 * math.pi / S.SPOKES * 0.5 + math.pi, name)
    _skewer(part, c, front, name)
    return part.finish(coll, pivot=c, sharp_angle=50.0)


# ------------------------------------------------------------------------------------- tyres
# Toni's Maxxis Rekon Race 29 x 2.35 EXO TR Tan Wall (TB00219800), modelled from Maxxis' product photos
# (photos/online-reference/maxxis-rekon-race/). The casing crown is half an ellipse above the widest point;
# below it the sidewall curves in to the bead, which tucks into the rim hook. Black tread rubber covers the
# crown and the shoulder knobs; the rest of the sidewall is tan.

TYRE_RC = 0.3390                         # radius of the widest point of the casing
TYRE_AR = S.TYRE_R - 0.0022 - TYRE_RC    # crown height above it (centre knobs add ~2.2 mm)
TYRE_AY = S.TYRE_HALF_W
BEAD = (0.3180, 0.0143)                  # where the tyre meets the top of the rim hook
TOE = [(0.3110, 0.0110), (0.3150, 0.0128)]  # bead toe, hidden inside the rim
TAN_FROM = math.radians(80)              # crown angle (0 = top of the tread) where the black tread rubber ends
                                         # (a black band runs ~3 mm below the shoulder knobs)
MM = 0.001
FONTS = "C:/Windows/Fonts/"


def _bezier(p0, p1, p2, t):
    return tuple((1 - t) ** 2 * a + 2 * (1 - t) * t * b + t * t * e for a, b, e in zip(p0, p1, p2))


def _side_points(n):
    """+y sidewall from the bead up to (not including) the widest point, as (r, y)."""
    return [_bezier(BEAD, (0.3245, TYRE_AY * 0.995), (TYRE_RC, TYRE_AY), k / n) for k in range(n)]


def _crown_points(th0, th1, n):
    return [(TYRE_RC + TYRE_AR * math.cos(th), TYRE_AY * math.sin(th))
            for th in (th0 + (th1 - th0) * k / n for k in range(n + 1))]


def _casing_profiles(n_crown, n_side):
    """Open (r, y) profiles that share their end points: tan +y sidewall, black crown, tan -y sidewall."""
    tan_r = TOE + _side_points(n_side) + _crown_points(math.pi / 2, TAN_FROM, 3)
    black = _crown_points(TAN_FROM, -TAN_FROM, n_crown)
    tan_l = [(r, -y) for (r, y) in reversed(tan_r)]
    return tan_r, black, tan_l


_HALF = _side_points(40) + _crown_points(math.pi / 2, 0.0, 60)    # r rises along the list


def _profile_y(r):
    """Lateral half-width of the casing surface at radius r (whole sidewall, bead to crown)."""
    if r <= _HALF[0][0]:
        return _HALF[0][1]
    for (r0, y0), (r1, y1) in zip(_HALF, _HALF[1:]):
        if r <= r1:
            return y0 + (y1 - y0) * (r - r0) / max(1e-9, r1 - r0)
    return _HALF[-1][1]


def _tyre_surface(c, ang, y):
    s = max(-0.999, min(0.999, y / TYRE_AY))
    th = math.asin(s)
    r = TYRE_RC + TYRE_AR * math.cos(th)
    er = Vector((math.cos(ang), 0.0, math.sin(ang)))
    p = c + er * r + Y * y
    nrm = (er * (math.cos(th) / TYRE_AR) + Y * (math.sin(th) / TYRE_AY)).normalized()
    return p, nrm


# --- tread -------------------------------------------------------------------------------------
# Measured on Maxxis' straight-on tread photo (9.4 px/mm). The pattern repeats every 3 rows (~32.5 mm),
# 72 times around the tyre. Knob outlines are (u, v) in mm: u = along the tread (+u = next row = downwards
# on the front of the tyre, as in the photo), v = across it (+v = left side of the bike); drawn for knobs on
# the -v half and mirrored for the +v half.

def _slot(cu, cv, length, width, angle_deg):
    a = math.radians(angle_deg)
    du, dv = math.cos(a), math.sin(a)
    pu, pv = -dv, du
    return [(cu + sl * du * length / 2 + sw * pu * width / 2, cv + sl * dv * length / 2 + sw * pv * width / 2)
            for sl, sw in ((-1, -1), (1, -1), (1, 1), (-1, 1))]


KNOBS = {
    # row A centre: trapezoid, wide edge first
    "u_plain": ([(-3.5, -4.25), (3.5, -3.0), (3.5, 3.0), (-3.5, 4.25)], []),
    # row C centre: wider trapezoid with a notch in the wide edge
    "u_wide": ([(-3.9, -5.25), (-3.9, -1.5), (-2.5, -1.0), (-2.5, 1.0), (-3.9, 1.5), (-3.9, 5.25),
                (3.9, 3.75), (3.9, -3.75)], []),
    # rows A and C flankers: square with a diagonal sipe slot
    "sipe": ([(-3.4, -3.4), (3.4, -3.4), (3.4, 3.4), (-3.4, 3.4)], [_slot(0.0, 0.0, 4.0, 0.7, 45)]),
    # row B centre pair: notch in the first edge, on the side facing the tyre centre
    "pair": ([(-3.5, -4.0), (-3.5, 0.9), (-1.3, 0.9), (-1.3, 2.1), (-3.5, 2.1), (-3.5, 4.0), (3.5, 4.0),
              (3.5, -4.0)], []),
    # row B transition knob (placed turned by 25 deg), notch in the first edge
    "trans": ([(-3.25, -4.0), (-3.25, -0.5), (-1.25, -0.5), (-1.25, 0.5), (-3.25, 0.5), (-3.25, 4.0),
               (3.25, 4.0), (3.25, -4.0)], []),
    # shoulder: inner block with a sipe across it + lower outer block behind it (together an L)
    "sh_in": ([(-3.8, -3.1), (3.8, -3.1), (3.8, 3.1), (-3.8, 3.1)], [_slot(0.6, 0.0, 3.4, 0.55, 90)]),
    "sh_out": ([(-2.9, -2.25), (2.9, -2.25), (2.9, 2.25), (-2.9, 2.25)], []),
}
KNOB_SCALE = 1.12     # outlines above x 1.12 = knob sizes on the 2.35 (checked side by side with the photo)

# (phase in the 3-row period, knob, lateral position mm (-v half), height mm, turn deg, ramp)
_LAYOUT_HALF = [
    (0.000, "sipe", -9.6, 2.2, 0, 0.0),
    (1 / 3, "pair", -5.2, 2.2, 0, 0.0),
    (1 / 3, "trans", -17.8, 2.6, -25, 0.0),
    (2 / 3, "sipe", -12.8, 2.2, 90, 0.0),          # row C slots lean the other way
    (0.180, "sh_in", -23.3, 3.0, 0, 0.0),
    (0.310, "sh_out", -27.4, 3.4, 0, 0.0),
    (2 / 3, "sh_in", -23.3, 3.0, 0, 0.0),
    (0.797, "sh_out", -27.4, 3.4, 0, 0.0),
]
TREAD_LAYOUT = [(0.000, "u_plain", 0.0, 2.0, 0, 0.2), (2 / 3, "u_wide", 0.0, 2.0, 0, 0.2)] + \
    [(ph, k, y, h, t, rp) for (ph, k, y, h, t, rp) in _LAYOUT_HALF] + \
    [(ph, k, -y, h, -t, rp) for (ph, k, y, h, t, rp) in _LAYOUT_HALF]
TREAD_PERIODS = 72


def _knob_templates():
    """One small mesh per knob shape (extruded outline with sipe holes), z from 0 (base) to 1 (top)."""
    out = {}
    for key, (outline, holes) in KNOBS.items():
        for mirror in (1.0, -1.0):
            k = KNOB_SCALE * MM
            o = [(u * k, mirror * v * k) for (u, v) in outline]
            hs = [[(u * k, mirror * v * k) for (u, v) in h] for h in holes]
            bm = mk.plate2d(o, hs, thickness=1.0)
            bmesh.ops.translate(bm, verts=bm.verts[:], vec=Vector((0.0, 0.0, 0.5)))
            me = bpy.data.meshes.new("tmp_knob_" + key)
            bm.to_mesh(me)
            bm.free()
            out[key, mirror] = (me, max(abs(u) for u, _ in outline) * k)
    return out


def _place_knob(bm, template, p, nrm, tang, h, turn=0.0, taper=0.92, ramp=0.0, sink=0.0008):
    """Copy a knob template onto the tyre: base sunk into the casing, sides tapered, optional ramp
    that lowers the +u end of the top."""
    me, umax = template
    lat = tang.cross(nrm).normalized()
    cr, sr = math.cos(turn), math.sin(turn)
    n0, f0 = len(bm.verts), len(bm.faces)
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    bm.faces.ensure_lookup_table()
    for i in range(n0, len(bm.verts)):
        v = bm.verts[i]
        x, y, z = v.co
        s = 1.0 - (1.0 - taper) * z
        hz = z * (h + sink) - sink - ramp * h * z * max(0.0, x) / umax
        x, y = x * cr - y * sr, x * sr + y * cr
        v.co = p + tang * (x * s) + lat * (y * s) + nrm * hz
    return [bm.faces[i] for i in range(f0, len(bm.faces))]


# --- sidewall graphics ---------------------------------------------------------------------------
# Order and sizes from Maxxis' Tan Wall photo: REKON RACE (white, black outline) - 29X2.35 / 60 PSI -
# EXO PROTECTION badge - TR / TUBELESS READY. Letter tops face the tread. MAXXIS sits on the opposite
# side of the tyre (layout as on the stock tyres in SCOTT's photo).

def _sidewall_frame(c, a_mid, side, s, r, lift):
    """Point at arc length s (along the reading direction) from a_mid, radius r, `lift` off the casing."""
    a = a_mid + side * s / r
    return c + Vector((r * math.cos(a), side * (_profile_y(r) + lift), r * math.sin(a)))


def _logo(part, c, a_mid, side, text, s_mm, r_mm, height_mm, length_mm, layers, font, shear=0.0, space=1.0):
    """Text centred at (s_mm, r_mm); layers = [(outline offset, lift mm, material)], drawn bottom to top."""
    probe = mk._text_mesh(text, 1.0, 0.0, FONTS + font, shear=shear, space=space)
    xs = [v.co.x for v in probe.vertices]
    ys = [v.co.y for v in probe.vertices]
    bpy.data.meshes.remove(probe)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    sx, sy = length_mm * MM / (max(xs) - min(xs)), height_mm * MM / (max(ys) - min(ys))
    r0 = r_mm * MM
    for offset, lift, mat in layers:
        def xform(v, lift=lift):
            return _sidewall_frame(c, a_mid, side, s_mm * MM + (v.x - cx) * sx, r0 + (v.y - cy) * sy, lift * MM)
        mk.add_text(part, text, 1.0, 0.0, mat, xform, FONTS + font, max_edge=0.25,
                    offset=offset, shear=shear, space=space)


def _panel(part, c, a_mid, side, s_mm, r_mm, length_mm, height_mm, lift_mm, mat, nu=12, nv=3):
    """Flat label panel (EXO badge) following the sidewall."""
    bm = part.bm
    rows = []
    for j in range(nv + 1):
        r = (r_mm + height_mm * (j / nv - 0.5)) * MM
        rows.append([bm.verts.new(_sidewall_frame(c, a_mid, side, (s_mm + length_mm * (i / nu - 0.5)) * MM, r,
                                                  lift_mm * MM)) for i in range(nu + 1)])
    faces = [bm.faces.new((a[i], a[i + 1], b[i + 1], b[i])) for a, b in zip(rows, rows[1:]) for i in range(nu)]
    part.tag(faces, mat, smooth=False)


def _sidewall_graphics(part, c, a_mid, side):
    white, black, red = M.get("tyre_text"), M.get("decal_black"), M.get("exo_red")
    outlined = [(0.07, 0.30, black), (0.0, 0.45, white)]
    _logo(part, c, a_mid, side, "REKON RACE", -61, 335.5, 12.0, 150, outlined, "ROCKEB.TTF", shear=0.12)
    _logo(part, c, a_mid, side, "29X2.35", 35, 338.6, 3.8, 24, [(0.0, 0.30, black)], "arialbd.ttf")
    _logo(part, c, a_mid, side, "60 PSI", 35, 333.1, 3.8, 17, [(0.0, 0.30, black)], "arialbd.ttf")
    _panel(part, c, a_mid, side, 76, 336.0, 36, 13.0, 0.25, black)
    _panel(part, c, a_mid, side, 76, 331.6, 34, 3.4, 0.35, red)
    _logo(part, c, a_mid, side, "EXO", 76, 338.6, 6.6, 20, [(0.0, 0.45, white)], "FRAHVIT.TTF")
    _logo(part, c, a_mid, side, "PROTECTION", 76, 331.6, 2.1, 28, [(0.0, 0.50, white)], "arialbd.ttf")
    _logo(part, c, a_mid, side, "TR", 119, 336.8, 8.5, 26, outlined, "ariblk.ttf", shear=0.25)
    _logo(part, c, a_mid, side, "TUBELESS READY", 119, 330.9, 2.4, 34, [(0.0, 0.30, red)], "arialbd.ttf")
    _logo(part, c, a_mid + math.pi, side, "MAXXIS", 0, 336.5, 10.5, 120, [(0.06, 0.30, black), (0.0, 0.45, white)],
          "ariblk.ttf", space=1.35)


def build_tyre(coll, front):
    name = "tire_front" if front else "tire_rear"
    c = S.FRONT_AXLE if front else S.REAR_AXLE
    part = Part(name, "Wheels & tyres")
    rubber, tan = M.get("rubber"), M.get("tanwall")
    n_around = S.seg(name, 128)
    tan_r, black, tan_l = _casing_profiles(S.seg(name, 36), S.seg(name, 8))
    for prof, mat in ((tan_r, tan), (black, rubber), (tan_l, tan)):
        mk.revolve(part, c, prof, mat, n=n_around, closed=False)
    # moulded rim line just above the bead on both sides
    for side in (-1.0, 1.0):
        r = 0.3240
        y = side * (_profile_y(r) + 0.0002)
        ring = [c + Vector((r * math.cos(2 * math.pi * k / n_around), y, r * math.sin(2 * math.pi * k / n_around)))
                for k in range(n_around)]
        ring.append(ring[0])
        mk.tube_path(part, ring, (0.0005, 0.0005), tan, n=6, caps=False)

    templates = _knob_templates()
    faces = []
    for k in range(TREAD_PERIODS):
        for phase, key, y_mm, h_mm, turn, ramp in TREAD_LAYOUT:
            a = 2 * math.pi * (k - phase) / TREAD_PERIODS
            p, nrm = _tyre_surface(c, a, y_mm * MM)
            t0 = Vector((math.sin(a), 0.0, -math.cos(a)))      # +u: towards the next row (decreasing angle)
            tang = (t0 - nrm * t0.dot(nrm)).normalized()
            mirror = 1.0 if y_mm <= 0 else -1.0
            faces += _place_knob(part.bm, templates[key, mirror], p, nrm, tang, h_mm * MM,
                                 turn=math.radians(turn), ramp=ramp)
    for me, _ in templates.values():
        bpy.data.meshes.remove(me)
    part.tag(faces, rubber, smooth=False)

    for side in (-1.0, 1.0):
        _sidewall_graphics(part, c, math.radians(145), side)
    return part.finish(coll, pivot=c, sharp_angle=40.0)
