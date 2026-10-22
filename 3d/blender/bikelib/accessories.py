"""Toni's accessories (photos of 2026-10-18), v2 rebuilt from product photos (2026-10-22, references and sizes in
photos/online-reference/accessories/SOURCES.md). Each accessory is its own node named `acc_*`, so the app can select
it and hide or show all of them with one button (GarageScene.ACCESSORY_SLOTS).

  acc_mudguard_front  SKS Mud-X: 310 mm wide blade flat under the down tube, opening away from it towards the BB,
                      raised centre rail, two ladder straps, MUD X + SKS logo on its top face
  acc_mudguard_rear   Polisport Cross Country EVO: black clamp + red latch on the seatpost, hinged arm with a bolt,
                      long U-section blade with grey ridges, deep front fin, red Polisport tip decal
  acc_light_rear      red "M" light (McDonald's arches traced from the logo outline), 20 mm thick, strapped behind
                      the seatpost under the saddle, facing back
  acc_light_front     square black rubber front light on top of the bar, left of the stem: sloped top, power-icon
                      button, wide lens; velcro strap next to it
  acc_light_clip      small yellow silicone strap light (Knog Frog type) on the front of the bar right of the stem
  acc_bell            55 mm black dome bell behind the bar, left of the stem, with the knurled ding-dong wheel
  acc_lock            Kryptonite Evolution Standard U-lock (102 x 229 mm, 13 mm shackle) in its FlexFrame-U bracket
                      on the drive side of the down tube near the BB, shackle hanging down in front of the crank
  acc_reflectors      two amber spoke reflectors (80 x 36 mm, prismatic face, clip tabs) bridging two drive-side
                      spokes of the front wheel (origin on the front axle, like the wheel)
"""
import math
import re

import bpy
from mathutils import Matrix, Vector

from . import cockpit as C
from . import frame as F
from . import materials as M
from . import meshkit as mk
from . import spec as S
from .meshkit import Part, X, Y, Z

CATEGORY = "Accessories"
NAMES = ["acc_mudguard_front", "acc_mudguard_rear", "acc_light_rear", "acc_light_front", "acc_light_clip",
         "acc_bell", "acc_lock", "acc_reflectors"]

FONTS = "C:/Windows/Fonts/"


# ------------------------------------------------------------------------------------------ helpers

def _finish(part, coll, pivot=None, sharp=45.0):
    ob = part.finish(coll, pivot=pivot, sharp_angle=sharp)
    ob["accessory"] = 1
    return ob


def _text_size(text, font=mk.FONT_PATH, **style):
    probe = mk._text_mesh(text, 1.0, 0.0, font, **style)
    xs = [v.co.x for v in probe.vertices]
    ys = [v.co.y for v in probe.vertices]
    bpy.data.meshes.remove(probe)
    return max(xs) - min(xs), max(ys) - min(ys)


def _text(part, text, mat, xform, length, height=None, font=mk.FONT_PATH, **style):
    """Text scaled to `length` (and `height`, else uniform); xform(x, y) -> world point, x along the text,
    y up, both in metres and centred on the text."""
    w, h = _text_size(text, font, **style)
    sx = length / w
    sy = (height / h) if height else sx
    return mk.add_text(part, text, 1.0, 0.0, mat, lambda v: xform(v.x * sx, v.y * sy), font, **style)


def _rblock(part, centre, size, axes, mat, r=0.003, bevel=0.0012, res=1, smooth=False):
    """Moulded block with rounded corners: size = (along U, along V, along W) in metres (bevel included),
    corners rounded with radius r in the U-V plane, all edges bevelled."""
    U, V, W = axes
    b = bevel
    su, sv = size[0] - 2 * b, size[1] - 2 * b
    rr = max(1e-4, min(r, 0.49 * min(su, sv)))
    bm = mk.plate2d(mk.rounded_rect(0.0, 0.0, su, sv, rr, n=3), thickness=max(1e-5, size[2] - 2 * b),
                    bevel=b, bevel_res=res)
    mk.place(bm, centre, U, V, W)
    return part.add_bm(bm, mat, smooth=smooth)


def _collar(part, centre, axis, r, width, mat, n=32, edge=0.0008, inner=None):
    """Ring round a round tube (strap, clamp band): outer radius r with softened edges, open inside down to
    `inner` (default r - 1.8 mm), so nothing cuts through the tube it wraps."""
    a = axis.normalized()
    e = min(edge, width / 3)
    ri = inner if inner is not None else r - 0.0018
    e1 = (a.cross(Z) if abs(a.dot(Z)) < 0.9 else a.cross(X)).normalized()
    e2 = a.cross(e1).normalized()
    sec = [(-width / 2, ri), (-width / 2, r - e), (-width / 2 + e, r), (width / 2 - e, r), (width / 2, r - e),
           (width / 2, ri)]
    rings = []
    for k in range(n):
        ang = 2 * math.pi * k / n
        rad = e1 * math.cos(ang) + e2 * math.sin(ang)
        rings.append([centre + a * x + rad * rr for x, rr in sec])
    rings.append(rings[0])
    return mk.add_rings(part, rings, mat, caps=(False, False), closed=True)


def _sheet(part, f, hw, u0, u1, n_u, n_v, mat, thick=1.0, w0=0.0, caps=True, smooth=True):
    """Thick sheet: rows along u, n_v points across v in [-hw(u), hw(u)], f(u, v, w) -> world point;
    w runs from w0 - thick/2 to w0 + thick/2."""
    rings = []
    for i in range(n_u + 1):
        u = u0 + (u1 - u0) * i / n_u
        h = max(1e-5, hw(u))
        vs = [-h + 2 * h * k / (n_v - 1) for k in range(n_v)]
        a = [f(u, v, w0 - thick / 2) for v in vs]
        b = [f(u, v, w0 + thick / 2) for v in vs]
        rings.append(a + b[::-1])
    return mk.add_rings(part, rings, mat, caps=(caps, caps), smooth=smooth)


def _inset(pts, d):
    """Move a closed 2-D outline inwards by d (miter offset, fine for smooth outlines)."""
    clean = [pts[0]]
    for p in pts[1:]:
        if (Vector(p) - Vector(clean[-1])).length > 1e-9:
            clean.append(p)
    pts = clean
    n = len(pts)
    area = sum(pts[i][0] * pts[(i + 1) % n][1] - pts[(i + 1) % n][0] * pts[i][1] for i in range(n)) / 2
    s = 1.0 if area > 0 else -1.0
    out = []
    for i in range(n):
        p0, p1, p2 = Vector(pts[i - 1]), Vector(pts[i]), Vector(pts[(i + 1) % n])
        e0, e1 = (p1 - p0).normalized(), (p2 - p1).normalized()
        n0, n1 = Vector((-e0.y, e0.x)) * s, Vector((-e1.y, e1.x)) * s
        b = n0 + n1
        b = b.normalized() if b.length > 1e-6 else n0
        q = p1 + b * (d / max(0.35, b.dot(n0)))
        out.append((q.x, q.y))
    return out


def _inside(pt, poly):
    """Point in polygon (2-D, ray casting)."""
    x, y = pt
    hit = False
    for i in range(len(poly)):
        (x0, y0), (x1, y1) = poly[i - 1], poly[i]
        if (y0 > y) != (y1 > y) and x < x0 + (y - y0) * (x1 - x0) / (y1 - y0):
            hit = not hit
    return hit


def _ring_pts(centre, e1, e2, r, a0, a1, n):
    return [centre + (e1 * math.cos(a0 + (a1 - a0) * k / n) + e2 * math.sin(a0 + (a1 - a0) * k / n)) * r
            for k in range(n + 1)]


def _gear2d(cx, cy, r_out, r_root, teeth, pts_per=6):
    out = []
    for k in range(teeth * pts_per):
        a = 2 * math.pi * k / (teeth * pts_per)
        ph = (k % pts_per) / pts_per
        r = r_out if 0.15 < ph < 0.55 else r_root
        out.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return out


def _lerp(keys, x):
    """Piecewise-linear scalar keys [(x, value), ...]."""
    return mk.interp_keys([(k, (v,)) for k, v in keys], x)[0]


def _strap_lift(phi):
    """Strap centre above a frame tube surface at tube.surface angle phi: clear of the decal layers, and bulging
    over the brake hose / gear housing that run along both flanks of the down tube."""
    return 0.0032 + 0.0070 * max(0.0, abs(math.sin(phi)) - 0.55) / 0.45


def _tube_r(tube, s, d):
    """Radius of a frame tube's elliptic section in the (unit, perpendicular) direction d."""
    w, h = tube.size(s)
    a, b = d.dot(tube.n), d.dot(Y)
    return 1.0 / math.sqrt((a / h) ** 2 + (b / w) ** 2)


# ------------------------------------------------------------------------- front mudguard (SKS Mud-X)

MUDX_LEN = 0.310            # SKS: 310 mm long
MUDX_TOP = 0.052            # upper end of the blade, metres down the tube axis from the head-tube end of the down tube
MUDX_ROLL = -15.0           # blade roll about the tube (deg, + = towards the drive side): drive edge hangs lower, top face
                            # (logo) turned to the drive side, as in Toni's drive-side and top photos
MUDX_GAP = (0.013, 0.046)   # blade below the tube surface at its upper / lower end (it opens away from the tube)
MUDX_STRAPS = (0.072, 0.200)  # ladder straps, metres from the upper end (the upper one just below the cable ports)
MUDX_HW = [(0.0, 0.044), (0.004, 0.049), (0.014, 0.051), (0.200, 0.054), (0.282, 0.062), (0.297, 0.054),
           (MUDX_LEN, 0.041)]  # half width along the blade: narrow upper end, flared lower end with cut corners


def build_mudguard_front(coll):
    """SKS Mud-X: flat 2 mm blade, slightly arched across, with a raised rail along its middle (tube side) under the
    down tube; two black ladder straps loop over the tube. MUD (white) X (orange) + the orange SKS gear on the top
    face, drive-side half, reading up the tube (Toni's top photos)."""
    part = Part("acc_mudguard_front", CATEGORY)
    blade, rail, strap = M.get("plastic_black"), M.get("black_matte"), M.get("rubber")
    _, _, down, _ = F._tubes()
    t, n = down.t, down.n
    th = math.radians(MUDX_ROLL)
    d = (-n * math.cos(th) - Y * math.sin(th)).normalized()     # tube axis -> blade (down, to the drive side)
    vh = (Y * math.cos(th) - n * math.sin(th)).normalized()     # across the blade (+v: non-drive edge, the low one)
    L = MUDX_LEN
    s_top = 1.0 - MUDX_TOP / down.length
    thick = 0.0022

    def s_of(u):
        return s_top - u / down.length

    def gap(u):
        return MUDX_GAP[0] + (MUDX_GAP[1] - MUDX_GAP[0]) * u / L

    def f(u, v, w):
        """u along the blade from its upper end, v across, w away from the tube (0 = blade mid-plane)."""
        s = s_of(u)
        dist = _tube_r(down, s, d) + gap(u) + thick / 2 + w + 0.0035 * (v / 0.06) ** 2
        return down.point(s) + d * dist + vh * v

    def hw(u):
        return _lerp(MUDX_HW, u)
    _sheet(part, f, hw, 0.0, L, 46, 15, blade, thick=thick)

    # raised rail on the tube side: fills the gap up to the tube (foam pad), widest between the straps
    rail_hw = [(0.050, 0.004), (0.056, 0.012), (0.066, 0.015), (0.210, 0.015), (0.220, 0.012), (0.226, 0.004)]

    def f_rail(u, v, w):                                         # w in [-0.5, 0.5]: blade face .. pad top
        h = min(gap(u) - 0.0010, 0.0085)
        return f(u, v, -thick / 2 - h * (w + 0.5) + 0.0003)
    _sheet(part, f_rail, lambda u: _lerp(rail_hw, u), 0.050, 0.226, 24, 7, rail, thick=1.0)
    for u_s in (0.050 + 0.012, 0.226 - 0.012):                  # slots in the rail (ends of the strap anchors)
        for k in (-1, 1):
            c = f(u_s + k * 0.004, 0.0, -thick / 2 - 0.0005)
            mk.ellipsoid(part, c, (0.0012, 0.0045, 0.0012), M.get("black_gloss"), rot=Matrix((-t, vh, d)).transposed(),
                         segs=10, rings=4)

    # ladder straps: from the hook on one side of the rail, over the top of the tube, to the other side
    for u_s in MUDX_STRAPS:
        s = s_of(u_s)
        phi_d = math.pi + th                                    # tube.surface angle of direction d (0 = top, +90 = +Y)
        pts = [f(u_s, 0.020, -thick / 2 - 0.0015)]
        steps = 26
        for k in range(steps + 1):
            phi = phi_d - math.radians(52) - (math.radians(256) * k / steps)
            pts.append(down.surface(s, phi, _strap_lift(phi)))
        pts.append(f(u_s, -0.020, -thick / 2 - 0.0015))
        mk.tube_path(part, pts, (0.0060, 0.0011), strap, n=10, ref=t, power=4.0)
        for k in (-1, 1):                                       # hooks the strap ends sit on
            _rblock(part, f(u_s, k * 0.021, -thick / 2 - 0.003), (0.012, 0.008, 0.006), (-t, vh, -d), rail,
                    r=0.002, bevel=0.0008)
        for k in range(1, steps, 2):                            # ladder holes (dark slots on the strap)
            phi = phi_d - math.radians(52) - (math.radians(256) * k / steps)
            p = down.surface(s, phi, _strap_lift(phi))
            rad = (p - down.point(s))
            rad = (rad - t * rad.dot(t)).normalized()
            tang = t.cross(rad).normalized()
            mk.ellipsoid(part, p + rad * 0.0009, (0.0026, 0.0018, 0.0005), M.get("black_gloss"),
                         rot=Matrix((t, tang, rad)).transposed(), segs=8, rings=3)

    # logos on the top (tube-side) face, drive-side half, near the lower end (Toni's top photos): MUD + X reading
    # up the tube, letter tops towards the middle of the blade; SKS gear below them
    face = -(thick / 2 + 0.0004)
    u_txt, v_txt = 0.236, -0.031
    w_mud, h_mud = _text_size("MUD", mk.FONT_PATH, shear=0.25)
    w_x, _ = _text_size("X", mk.FONT_PATH, shear=0.25)
    scale = 0.058 / (w_mud + w_x * 1.25)                       # MUD + a 25 % bigger X, one word
    x_mud = -(w_x * 1.25 * scale) / 2
    x_x = (w_mud * scale) / 2 - 0.0008
    _text(part, "MUD", M.get("tyre_text"), lambda x, y: f(u_txt - (x + x_mud), v_txt + y, face), w_mud * scale,
          h_mud * scale, shear=0.25)
    _text(part, "X", M.get("mudx_orange"), lambda x, y: f(u_txt - (x + x_x), v_txt + y + 0.0011, face - 0.0001),
          w_x * scale * 1.25, h_mud * scale * 1.32, shear=0.25)
    gear = mk.plate2d(_gear2d(0.0, 0.0, 0.0072, 0.0058, 8), holes=[mk.circle_pts(0.0, 0.0, 0.0035, 16)[::-1]],
                      thickness=0.0003)
    u_g, v_g = u_txt + 0.044, v_txt + 0.006
    for vert in gear.verts:
        x, y, z = vert.co
        vert.co = f(u_g - x, v_g + y, face - z)
    part.add_bm(gear, M.get("mudx_orange"), smooth=False)
    _text(part, "S", M.get("tyre_text"), lambda x, y: f(u_g - x, v_g + y, face - 0.0002), 0.0034,
          font=FONTS + "arialbd.ttf")
    return _finish(part, coll)


# ------------------------------------------------------------------- rear mudguard (Polisport CC EVO)

POLI_CLAMP_AT = S.SEAT_TUBE + 86.0       # clamp on the seatpost, mm from the BB along the seat axis (Toni's photo)
M_LIGHT_AT = S.SEAT_TUBE + 158.0         # M light, just under the saddle clamp
POLI_HINGE = (-0.071, -0.015)            # arm hinge: metres behind / below the clamp centre (side photo)
# blade top centre line, metres from the hinge (x back = negative, z up): rises a little, then drops to the tip
POLI_BLADE = [(-0.012, 0.004), (-0.050, 0.013), (-0.110, 0.024), (-0.200, 0.034), (-0.300, 0.036), (-0.400, 0.026),
              (-0.480, 0.004), (-0.545, -0.026), (-0.590, -0.052)]
POLI_HW = [(0.0, 0.016), (0.08, 0.024), (0.30, 0.034), (0.70, 0.033), (0.84, 0.027), (0.93, 0.018), (0.975, 0.010),
           (0.993, 0.005), (1.0, 0.0015)]
# deep fin under the front of the blade (Toni's photos): front edge down from the hinge to a point, concave rear edge
POLI_FIN = [(-0.004, 0.000), (-0.003, -0.030), (-0.010, -0.058), (-0.021, -0.086), (-0.040, -0.064), (-0.075, -0.042),
            (-0.130, -0.026), (-0.200, -0.012), (-0.222, 0.022), (-0.160, 0.026), (-0.100, 0.018), (-0.045, 0.009)]


class _Blade:
    """Centre line of the rear blade (arc-length parametrised) + its arched cross-section."""

    def __init__(self, ctrl, arch=0.016):
        pts = mk.catmull_rom(ctrl, 8)
        self.pts = pts
        self.cum = [0.0]
        for a, b in zip(pts, pts[1:]):
            self.cum.append(self.cum[-1] + (b - a).length)
        self.length = self.cum[-1]
        self.arch = arch

    def at(self, s):
        """(point, tangent, up) at arc length s."""
        s = max(0.0, min(self.length, s))
        for i in range(1, len(self.cum)):
            if self.cum[i] >= s:
                k = (s - self.cum[i - 1]) / max(1e-9, self.cum[i] - self.cum[i - 1])
                p = self.pts[i - 1].lerp(self.pts[i], k)
                tan = (self.pts[i] - self.pts[i - 1]).normalized()
                break
        up = Y.cross(tan).normalized()
        if up.z < 0:
            up = -up
        return p, tan, up

    def hw(self, s):
        return _lerp(POLI_HW, s / self.length)

    def surface(self, s, q, lift):
        """q in [-1, 1] across (+Y), lift above the top surface."""
        p, _, up = self.at(s)
        return p + Y * (q * self.hw(s)) - up * (self.arch * q * q) + up * lift


def build_mudguard_rear(coll):
    """Polisport Cross Country EVO: black clamp on the seatpost with its red quick-release latch on the drive side,
    black arm back to a bolted hinge, long U-section blade (grey ridges along both sides), deep pointed fin under
    its front, red Polisport decal at the tip."""
    part = Part("acc_mudguard_rear", CATEGORY)
    red, black, grey, steel = M.get("clamp_red"), M.get("plastic_black"), M.get("grey_stripe"), M.get("steel")
    axis = S.SEAT_DIR
    back = (-X + axis * axis.dot(X)).normalized()               # perpendicular to the post, pointing back
    c = S.on_seat_axis(POLI_CLAMP_AT)
    R = S.SEATPOST_R
    # clamp: rubber-lined ring, body behind the post, red latch on its drive side
    _collar(part, c, axis, R + 0.0030, 0.016, black, n=36, edge=0.0012)
    body = c + back * (R + 0.0118)
    _rblock(part, body, (0.022, 0.028, 0.022), (back, Y, axis), black, r=0.005, bevel=0.002, res=2, smooth=True)
    _rblock(part, body - Y * 0.0165 + back * 0.002, (0.024, 0.008, 0.021), (back, Y, axis), red, r=0.004,
            bevel=0.0015, res=2, smooth=True)
    _rblock(part, body - Y * 0.0170 + back * 0.004 + axis * 0.013, (0.010, 0.006, 0.008), (back, Y, axis), red,
            r=0.002, bevel=0.0010)                              # pull tab of the latch
    mk.cyl(part, body - Y * 0.0215 - back * 0.006, body - Y * 0.0195 - back * 0.006, 0.0026, M.get("black_gloss"), n=12)
    # arm from the clamp body to the hinge (adjustable in two points)
    hinge = c - X * (-POLI_HINGE[0]) + Z * POLI_HINGE[1]
    arm = mk.scratch()
    a0 = body + back * 0.009
    mk.tube_path(arm, [a0, a0.lerp(hinge, 0.5) + Z * 0.002, hinge],
                 [(0.010, 0.0065), (0.009, 0.0060), (0.010, 0.0070)], None, n=10, ref=Y, power=3.0)
    part.add_bm(mk.subdivided(arm, 1), black)
    mk.cyl(part, hinge + Y * 0.012, hinge - Y * 0.012, 0.0095, black, n=28)            # hinge knuckle
    mk.cyl(part, hinge - Y * 0.012, hinge - Y * 0.0145, 0.0048, steel, n=6)             # bolt head (hex)
    mk.cyl(part, hinge - Y * 0.0144, hinge - Y * 0.0147, 0.0021, M.get("black_gloss"), n=6)  # hex socket
    mk.cyl(part, hinge + Y * 0.012, hinge + Y * 0.0140, 0.0045, black, n=16)             # nut cover (left)
    # blade
    bl = _Blade([hinge + Vector((dx, 0.0, dz)) for dx, dz in POLI_BLADE])
    n_s = 64
    m = 13
    rings = []
    thick = 0.0026
    for i in range(n_s + 1):
        s = bl.length * i / n_s
        _, _, up = bl.at(s)
        top = [bl.surface(s, -1 + 2 * k / (m - 1), 0.0) for k in range(m)]
        rings.append(top + [p - up * thick for p in reversed(top)])
    mk.add_rings(part, rings, black)
    # neck: blade front joined to the hinge knuckle
    p0, _, up0 = bl.at(0.0)
    _rblock(part, (p0 + hinge) / 2 - up0 * 0.002, (0.026, 0.022, 0.012), ((p0 - hinge).normalized(), Y,
            (p0 - hinge).normalized().cross(Y).normalized() * -1), black, r=0.006, bevel=0.002, res=2, smooth=True)

    def layer(s0, s1, q0, q1, mat, lift, ns=40, mq=5):
        rr = []
        for i in range(ns + 1):
            s = s0 + (s1 - s0) * i / ns
            _, _, up = bl.at(s)
            top = [bl.surface(s, q0 + (q1 - q0) * k / (mq - 1), lift) for k in range(mq)]
            rr.append(top + [p - up * 0.0003 for p in reversed(top)])
        mk.add_rings(part, rr, mat)
    # grey ridges along both upper sides (raised a little), from behind the neck to near the tip
    for q0, q1 in ((0.38, 0.62), (-0.62, -0.38)):
        layer(bl.length * 0.07, bl.length * 0.86, q0, q1, grey, 0.0009)
    # red tip decal with the Polisport logo
    layer(bl.length * 0.855, bl.length * 0.985, -0.97, 0.97, red, 0.0007, ns=16, mq=13)
    s_mid = bl.length * 0.915

    def logo_xf(x, y):
        s = s_mid - x                                             # reads from the tip towards the hinge
        q = y / max(0.004, bl.hw(s))
        return bl.surface(s, max(-0.95, min(0.95, q)), 0.0012)
    _text(part, "Polisport", M.get("decal_black"), logo_xf, 0.050, 0.010, font=mk.FONT_PATH, shear=0.20)
    # fin under the front of the blade, in the bike plane
    fin = mk.plate2d(mk.rounded_poly(POLI_FIN, 0.004, n=3), thickness=0.0024, bevel=0.0008, bevel_res=1)
    mk.in_bike_plane(fin, hinge)
    part.add_bm(fin, black, smooth=False)
    return _finish(part, coll)


# ---------------------------------------------------------------------------------- rear light (M)

# McDonald's Golden Arches outline (Wikimedia Commons "McDonald's Golden Arches.svg", 272.7 x 238.5 units)
M_PATH = ("m195.8 17.933c23.3 0 42.2 98.3 42.2 219.7h34c0-130.7-34.3-236.5-76.3-236.5-24 0-45.2 31.7-59.2 81.5"
          "-14-49.8-35.2-81.5-59-81.5-42 0-76.2 105.7-76.2 236.4h34c0-121.4 18.7-219.6 42-219.6s42.2 90.8 42.2 202.8"
          "h33.8c0-112 19-202.8 42.3-202.8")
M_VIEW = (272.7, 238.5)
M_SIZE = (0.056, 0.049, 0.019)            # width, height, depth of Toni's M light (photos: ~50 mm tall)


def _svg_outline(d, samples=10):
    toks = re.findall(r"[a-zA-Z]|-?(?:\d+\.\d*|\.\d+|\d+)", d)
    pts, i, cmd = [], 0, None
    cur, last_c2 = Vector((0.0, 0.0)), None

    def num():
        nonlocal i
        v = float(toks[i])
        i += 1
        return v
    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
        if cmd == "m":
            cur = cur + Vector((num(), num()))
            pts.append(cur.copy())
            cmd, last_c2 = "l", None
        elif cmd == "l":
            cur = cur + Vector((num(), num()))
            pts.append(cur.copy())
            last_c2 = None
        elif cmd == "h":
            cur = cur + Vector((num(), 0.0))
            pts.append(cur.copy())
            last_c2 = None
        elif cmd == "v":
            cur = cur + Vector((0.0, num()))
            pts.append(cur.copy())
            last_c2 = None
        elif cmd in ("c", "s"):
            c1 = cur + Vector((num(), num())) if cmd == "c" else (cur * 2 - last_c2 if last_c2 else cur.copy())
            c2 = cur + Vector((num(), num()))
            p = cur + Vector((num(), num()))
            for k in range(1, samples + 1):
                tt = k / samples
                q = (1 - tt) ** 3 * cur + 3 * (1 - tt) ** 2 * tt * c1 + 3 * (1 - tt) * tt ** 2 * c2 + tt ** 3 * p
                pts.append(q)
            last_c2, cur = c2, p
        else:
            raise ValueError(f"svg command {cmd}")
    if (pts[-1] - pts[0]).length < 1e-3:
        pts.pop()
    return pts


def build_light_rear(coll):
    """Red "M" light behind the seatpost, facing back, tilted with the post: the McDonald's arches as a 19 mm thick
    matte red body on a small red mount, held by a red silicone strap with a pull tab (Toni's two seat photos)."""
    part = Part("acc_light_rear", CATEGORY)
    red = M.get("clamp_red")
    axis = S.SEAT_DIR
    back = (-X + axis * axis.dot(X)).normalized()
    c = S.on_seat_axis(M_LIGHT_AT)
    R = S.SEATPOST_R
    W, H, D = M_SIZE
    b = 0.0014
    outline = [((x / M_VIEW[0] - 0.5) * W, (0.5 - y / M_VIEW[1]) * H) for x, y in _svg_outline(M_PATH)]
    body = mk.plate2d(_inset(outline, b), thickness=D - 2 * b, bevel=b, bevel_res=2)
    mount_d = 0.007
    mid = c + back * (R + mount_d + D / 2)
    mk.place(body, mid, -Y, axis, back)
    part.add_bm(body, red, smooth=False)
    # mount block (post side) and strap with its pull tab sticking out at the front drive side
    _rblock(part, c + back * (R + mount_d / 2 + 0.0010), (mount_d, 0.020, 0.030), (back, Y, axis), red,
            r=0.003, bevel=0.0012)
    sc = c + axis * 0.012
    _collar(part, sc, axis, R + 0.0018, 0.008, red, n=32, edge=0.0006, inner=R + 0.0003)
    out = (-back * 0.55 - Y * 0.83).normalized()
    _rblock(part, sc + out * (R + 0.008), (0.014, 0.0028, 0.008), (out, axis.cross(out).normalized(), axis), red,
            r=0.0025, bevel=0.0008)
    return _finish(part, coll)


# ------------------------------------------------------------------------------------------ cockpit

def _bar_frame(y):
    p = C.bar_point(y)
    axis = C.bar_dir(y)
    fwd = (X - axis * X.dot(axis)).normalized()
    return p, axis, fwd


def _bar_r(y):
    ay = abs(y)
    return 0.0159 if ay < 0.04 else (0.0111 if ay > 0.10 else 0.0159 + (0.0111 - 0.0159) * (ay - 0.04) / 0.06)


LIGHT_Y, BELL_Y, VELCRO_Y, CLIP_Y = 0.152, 0.104, 0.127, -0.098


def build_light_front(coll):
    """Toni's square front light: matte black rubber body 58 x 42 x 26 mm on top of the bar left of the stem,
    top sloping down to the front, round power button (ring + power icon) on top, wide lens with two LEDs at the
    front; held by a rubber strap, and the black velcro strap wrapped round the bar next to it."""
    part = Part("acc_light_front", CATEGORY)
    rubber, gloss, lens, led = M.get("rubber_soft"), M.get("black_gloss"), M.get("lens_clear"), M.get("led_white")
    p, axis, fwd = _bar_frame(LIGHT_Y)
    r = _bar_r(LIGHT_Y)
    side = Z.cross(fwd).normalized()
    _collar(part, p, axis, r + 0.0022, 0.014, rubber, n=28)
    _rblock(part, p + Z * (r + 0.0066), (0.020, 0.024, 0.008), (fwd, side, Z), rubber, r=0.004, bevel=0.0015)
    Dd, Ww, Hh, B = 0.042, 0.058, 0.026, 0.0055
    slope = 0.0045
    c = p + Z * (r + 0.0100 + Hh / 2)
    body = mk.plate2d(mk.rounded_rect(0.0, 0.0, Dd - 2 * B, Ww - 2 * B, 0.009, n=4), thickness=Hh - 2 * B, bevel=B,
                      bevel_res=3)
    for v in body.verts:
        if v.co.z > 0:
            v.co.z -= slope * ((v.co.x + Dd / 2) / Dd) * (v.co.z / (Hh / 2))
    mk.place(body, c, fwd, side, Z)
    part.add_bm(body, rubber, smooth=True)
    # lens + LEDs on the front face
    z_l = -0.0025
    lp = mk.plate2d(mk.rounded_rect(0.0, 0.0, 0.040, 0.0085, 0.0035, n=3), thickness=0.0010, bevel=0.0004)
    mk.place(lp, c + fwd * (Dd / 2 + 0.0002) + Z * z_l, side, Z, fwd)
    part.add_bm(lp, lens, smooth=False)
    for k in (-1, 1):
        q = c + fwd * (Dd / 2 + 0.0010) + Z * z_l + side * (k * 0.009)
        mk.cyl(part, q - fwd * 0.0006, q + fwd * 0.0006, 0.0024, led, n=14)
    # power button on the sloping top: raised disc, outer ring, power icon (C with a line in its gap)
    x_b = -0.003
    z_top = Hh / 2 - slope * ((x_b + Dd / 2) / Dd)
    nrm = (Z + fwd * (slope / Dd)).normalized()
    e1 = side
    e2 = nrm.cross(side).normalized()
    pc = c + fwd * x_b + Z * z_top
    mk.cyl(part, pc - nrm * 0.0004, pc + nrm * 0.0006, 0.0090, rubber, n=32)
    ring = _ring_pts(pc + nrm * 0.0007, e1, e2, 0.0078, 0.0, 2 * math.pi, 32)
    mk.tube_path(part, ring, (0.00055, 0.00045), gloss, n=6, ref=nrm, caps=False)
    gap_dir = (e2 * math.cos(math.radians(-30)) + e1 * math.sin(math.radians(-30)))   # gap to the front-right
    g0 = math.atan2(gap_dir.dot(e2), gap_dir.dot(e1))
    arc = _ring_pts(pc + nrm * 0.0008, e1, e2, 0.0044, g0 + math.radians(38), g0 + math.radians(322), 20)
    mk.tube_path(part, arc, (0.00065, 0.00050), gloss, n=6, ref=nrm)
    mk.tube_path(part, [pc + nrm * 0.0008 + gap_dir * 0.0006, pc + nrm * 0.0008 + gap_dir * 0.0052],
                 (0.00065, 0.00050), gloss, n=6, ref=nrm)
    # black velcro strap wrapped round the bar between the light and the bell, loose end hanging down
    pv, av, fv = _bar_frame(VELCRO_Y)
    rv = _bar_r(VELCRO_Y)
    _collar(part, pv, av, rv + 0.0028, 0.017, rubber, n=28, edge=0.0010)
    _collar(part, pv + av * 0.002, av, rv + 0.0042, 0.013, rubber, n=28, edge=0.0008)
    _rblock(part, pv - fv * (rv + 0.004) - Z * 0.012, (0.004, 0.016, 0.022), (fv, av, Z), rubber, r=0.003,
            bevel=0.0010)
    return _finish(part, coll)


def build_bell(coll):
    """55 mm black steel dome bell (Contec Push-a-Ding size) hanging just behind the bar left of the stem, dome
    facing up, back and a little outwards; flat centre cap, black base, knurled ding-dong wheel at the rider side,
    clamp and arm to the bar; white paint chips (Toni's photos)."""
    part = Part("acc_bell", CATEGORY)
    gloss, matte, anod, steel = M.get("black_gloss"), M.get("black_matte"), M.get("black_anodised"), M.get("steel")
    p, axis, fwd = _bar_frame(BELL_Y)
    r = _bar_r(BELL_Y)
    up = (Z * 0.85 - fwd * 0.45 + axis * 0.20).normalized()
    base = p - fwd * 0.040 - Z * 0.016
    u1 = axis.cross(up).normalized()          # dome plane axes (u1 ~ forward/back, u2 ~ along the bar)
    u2 = up.cross(u1).normalized()

    def revolve_to(profile, mat, n=48, smooth=True):
        sh = mk.scratch()
        mk.revolve(sh, Vector((0.0, 0.0, 0.0)), profile, None, n=n)
        mk.place(sh.bm, base, u1, up, u2)
        part.add_bm(sh.bm, mat, smooth=smooth)
    dome_out = [(0.0275, 0.0000), (0.0277, 0.0016), (0.0271, 0.0050), (0.0256, 0.0095), (0.0229, 0.0140),
                (0.0190, 0.0178), (0.0140, 0.0205), (0.0080, 0.0222), (0.0004, 0.0228)]
    dome_in = [(0.0004, 0.0220), (0.0078, 0.0214), (0.0136, 0.0197), (0.0184, 0.0171), (0.0221, 0.0134),
               (0.0247, 0.0091), (0.0262, 0.0049), (0.0267, 0.0012), (0.0267, 0.0000)]
    revolve_to(dome_out + dome_in, gloss)
    revolve_to([(0.0004, 0.0252), (0.0080, 0.0251), (0.0103, 0.0244), (0.0111, 0.0230), (0.0109, 0.0212),
                (0.0004, 0.0212)], matte, n=40)                                         # centre cap
    revolve_to([(0.0004, -0.0040), (0.0230, -0.0040), (0.0246, -0.0025), (0.0246, 0.0004), (0.0004, 0.0004)],
               matte, n=40, smooth=False)                                             # base plate
    # clamp on the bar + arm to the base plate
    _collar(part, p, axis, r + 0.0020, 0.010, anod, n=28)
    arm = mk.scratch()
    start = p - (fwd * 0.6 + Z * 0.8) * (r + 0.0045)
    end = base - up * 0.0035
    mk.tube_path(arm, [start, start.lerp(end, 0.5) - Z * 0.002, end], (0.0055, 0.0040), None, n=10, ref=axis,
                 power=3.0)
    part.add_bm(mk.subdivided(arm, 1), anod)
    mk.cyl(part, start - axis * 0.007, start + axis * 0.007, 0.0028, steel, n=6)        # clamp bolt
    # knurled ding-dong wheel under the dome rim, rider side, turning about an axis parallel to the bar
    rider = -u1 if u1.dot(fwd) > 0 else u1
    wc = base + rider * 0.024 - up * 0.008
    wheel = mk.scratch()
    nt = 36
    ring = [wc + (rider * math.cos(2 * math.pi * k / (2 * nt)) + (-up) * math.sin(2 * math.pi * k / (2 * nt)))
            * (0.0074 if k % 2 else 0.0082) for k in range(2 * nt)]
    mk.add_rings(wheel, [[q - axis * 0.0025 for q in ring], [q + axis * 0.0025 for q in ring]], None)
    part.add_bm(wheel.bm, gloss, smooth=False)
    mk.cyl(part, wc - axis * 0.0045, wc + axis * 0.0045, 0.0022, steel, n=10)
    mk.tube_path(part, [wc - rider * 0.002, base + rider * 0.012 - up * 0.004], (0.0022, 0.0018), matte, n=8)
    # chipped paint (white flecks) low on the dome, rider side
    for ang, h, size in ((200.0, 0.0055, 0.0022), (215.0, 0.0035, 0.0013), (190.0, 0.0090, 0.0010)):
        a = math.radians(ang)
        dvec = u1 * math.cos(a) + u2 * math.sin(a)
        rr = 0.0271 - 0.06 * h
        q = base + up * h + dvec * rr
        nr = (dvec * 0.8 + up * 0.6).normalized()
        mk.ellipsoid(part, q, (size, size * 0.7, 0.0004), M.get("tyre_text"),
                     rot=Matrix((nr.cross(up).normalized(), nr.cross(nr.cross(up)).normalized(), nr)).transposed(),
                     segs=8, rings=4)
    return _finish(part, coll)


def build_light_clip(coll):
    """Yellow silicone strap light (Knog Frog type, 35 x 42 mm body) on the front of the bar right of the stem:
    rounded pod with a clear lens and LED at the top front, silicone strap looped round the bar to a hook at the
    bottom of the pod."""
    part = Part("acc_light_clip", CATEGORY)
    yellow, lens, led = M.get("silicone_yellow"), M.get("lens_clear"), M.get("led_white")
    p, axis, fwd = _bar_frame(CLIP_Y)
    r = _bar_r(CLIP_Y)
    side = Z.cross(fwd).normalized()
    tilt = math.radians(35)                                       # pod leans back over the top of the bar
    up = (Z * math.cos(tilt) - fwd * math.sin(tilt)).normalized()
    front = up.cross(side).normalized() * -1 if up.cross(side).dot(fwd) < 0 else up.cross(side).normalized()
    pod = p + fwd * (r + 0.0098) * math.cos(tilt) + Z * (r + 0.0098) * math.sin(tilt) + up * 0.004
    _rblock(part, pod, (0.026, 0.019, 0.034), (side, front, up), yellow, r=0.0085, bevel=0.0065, res=3, smooth=True)
    lp = mk.plate2d(mk.rounded_rect(0.0, 0.0, 0.018, 0.0090, 0.0040, n=3), thickness=0.0012, bevel=0.0005)
    lc = pod + front * (0.0095 + 0.0004) + up * 0.0080
    mk.place(lp, lc, side, up, front)
    part.add_bm(lp, lens, smooth=False)
    mk.cyl(part, lc - front * 0.0002, lc + front * 0.0012, 0.0026, led, n=14)
    mk.ellipsoid(part, pod + up * 0.0168 - front * 0.001, (0.0045, 0.0045, 0.0012), yellow,
                 rot=Matrix((side, front, up)).transposed(), segs=12, rings=5)          # button under the silicone
    # strap: from the top back of the pod, over the bar, round the back and under it, to the hook at the bottom
    e1, e2 = fwd, Z
    pts = [pod - front * 0.007 + up * 0.014]
    for k in range(17):
        a = math.radians(70 + 250 * k / 16)
        pts.append(p + (e1 * math.cos(a) + e2 * math.sin(a)) * (r + 0.0016))
    pts.append(pod - front * 0.007 - up * 0.016)
    mk.tube_path(part, pts, (0.0042, 0.0011), yellow, n=10, ref=axis, power=4.0)
    _rblock(part, pod - up * 0.0195 + front * 0.002, (0.010, 0.006, 0.008), (side, front, up), yellow, r=0.003,
            bevel=0.0012)
    return _finish(part, coll)


# --------------------------------------------------------------------------------------------- lock

LOCK_Y = -0.042            # lateral position of the crossbar axis (drive side of the down tube, inside the crank)
LOCK_ALONG = 0.262         # where the crossbar axis leaves the down tube, metres along it from the BB
LOCK_TILT = 0.0            # crossbar square to the tube, shackle legs parallel to it (Toni's photo)
LOCK_A0 = 0.040            # near end of the crossbar, metres from the tube axis
CB_LEN, CB_W, CB_H, CB_POW = 0.180, 0.0150, 0.0175, 2.6   # crossbar length, half width / height, section shape
CB_CAP = 0.040             # black key end cap
LEG_IN, LEG_SPAN = 0.026, 0.115   # first shackle leg from the near end; leg centre distance (102 mm inside)
SHACKLE_R, INSIDE_LEN = 0.0065, 0.229


def build_lock(coll):
    """Kryptonite Evolution Standard: orange crossbar with a black key cap at the far end, black label plate with
    the red dust slider on its upper face, KRYPTONITE / EVOLUTION on the drive-side face; 13 mm black coated
    shackle with a silver sleeve on the near leg; carried in the black FlexFrame-U bracket (cradle round the near
    end of the crossbar, foot strapped to the down tube)."""
    part = Part("acc_lock", CATEGORY)
    orange, cap_mat, coat, steel = M.get("lock_orange"), M.get("black_gloss"), M.get("coat_black"), M.get("steel")
    matte = M.get("black_matte")
    _, _, down, _ = F._tubes()
    t, n = down.t, down.n
    tl = math.radians(LOCK_TILT)
    ex = (-n * math.cos(tl) - t * math.sin(tl)).normalized()   # along the crossbar, away from the tube
    ez = (t * math.cos(tl) - n * math.sin(tl)).normalized()    # up the tube side; the shackle hangs along -ez
    O = S.BB + t * LOCK_ALONG + Y * LOCK_Y
    a0, a1 = LOCK_A0, LOCK_A0 + CB_LEN

    def P(a, z=0.0, y=0.0):
        return O + ex * a + ez * z + Y * y

    def sweep(stations, mat):
        mk.tube_path(part, [P(a) for a, _ in stations], [(CB_W * k, CB_H * k) for _, k in stations], mat, n=32,
                     ref=Y, power=CB_POW)
    sweep([(a0, 0.80), (a0 + 0.0012, 0.93), (a0 + 0.0040, 0.99), (a0 + 0.0080, 1.0), (a1 - CB_CAP - 0.0010, 1.0)],
          orange)
    sweep([(a1 - CB_CAP - 0.0012, 0.95), (a1 - CB_CAP, 1.04), (a1 - 0.0060, 1.04), (a1 - 0.0030, 1.00),
           (a1 - 0.0010, 0.93), (a1, 0.82)], cap_mat)
    # key cylinder in the end cap
    kc = P(a1)
    mk.cyl(part, kc - ex * 0.0004, kc + ex * 0.0006, 0.0074, matte, n=24)
    mk.cyl(part, kc + ex * 0.0004, kc + ex * 0.0010, 0.0052, steel, n=24)
    mk.box(part, kc + ex * 0.0011, (0.0006, 0.0012, 0.0050), M.get("black_gloss"), rot=Matrix((ex, Y, ez)).transposed())
    # label plate on the upper face, with screws and the red dust slider
    def top(a, y):
        z = CB_H * max(0.0, 1 - abs(y / CB_W) ** CB_POW) ** (1 / CB_POW)
        return P(a, z, y)
    pa = a0 + 0.088
    plate = mk.plate2d(mk.rounded_poly([(-0.036, 0.0), (-0.030, -0.0055), (0.030, -0.0055), (0.036, 0.0),
                                        (0.030, 0.0055), (-0.030, 0.0055)], 0.002, n=2), thickness=0.0016,
                       bevel=0.0004)
    mk.place(plate, top(pa, 0.0) - ez * 0.0002, ex, Y, ez)
    part.add_bm(plate, matte, smooth=False)
    for k in (-1, 1):
        q = top(pa + k * 0.026, 0.0) + ez * 0.0012
        mk.cyl(part, q - ez * 0.0004, q + ez * 0.0004, 0.0016, steel, n=10)
    _rblock(part, top(pa + 0.004, 0.0) + ez * 0.0014, (0.008, 0.0045, 0.0016), (ex, Y, ez), M.get("clamp_red"),
            r=0.0015, bevel=0.0004)
    # KRYPTONITE / EVOLUTION on the drive-side face: letter tops towards the shackle, reading towards the bracket

    def side_face(a, z, lift=0.0003):
        y = CB_W * max(0.0, 1 - abs(z / CB_H) ** CB_POW) ** (1 / CB_POW) + lift
        return P(a, z, -y)
    ta = a0 + 0.070
    _text(part, "KRYPTONITE", M.get("black_gloss"), lambda x, y: side_face(ta - x, 0.0015 - y), 0.070, 0.0095,
          font=mk.FONT_PATH)
    _text(part, "EVOLUTION", M.get("black_gloss"), lambda x, y: side_face(ta - 0.004 - x, 0.0098 - y), 0.034, 0.0034,
          font=FONTS + "arialbd.ttf")
    # shackle: two legs along -ez, U bend at the bottom
    a_in, a_out = a0 + LEG_IN, a0 + LEG_IN + LEG_SPAN
    rb = LEG_SPAN / 2
    z_c = -(CB_H + INSIDE_LEN + SHACKLE_R) + rb
    leg = [P(a_in, z) for z in [-0.002 - (abs(z_c) - 0.002) * k / 14 for k in range(15)]]
    bend = [P((a_in + a_out) / 2 - rb * math.cos(math.pi * k / 18), z_c - rb * math.sin(math.pi * k / 18))
            for k in range(1, 18)]
    leg2 = [P(a_out, z) for z in [z_c + (abs(z_c) - 0.002) * k / 14 for k in range(15)]]
    path = leg + bend + leg2
    mk.tube_path(part, path, (SHACKLE_R, SHACKLE_R), coat, n=20, ref=Y)
    mk.cyl(part, P(a_in, -CB_H - 0.0005), P(a_in, -CB_H - 0.018), SHACKLE_R + 0.0022, steel, n=24)   # sleeve
    mk.cyl(part, P(a_in, -CB_H - 0.018), P(a_in, -CB_H - 0.0195), SHACKLE_R + 0.0010, steel, n=24)
    # FlexFrame-U bracket: cradle round the near end of the crossbar ...
    ca, cb = a0 - 0.002, a0 + 0.017
    mk.tube_path(part, [P(ca), P(ca + 0.0015), P(cb - 0.0015), P(cb)],
                 [(CB_W * 1.22, CB_H * 1.20), (CB_W * 1.30, CB_H * 1.27), (CB_W * 1.30, CB_H * 1.27),
                  (CB_W * 1.22, CB_H * 1.20)], matte, n=32, ref=Y, power=2.4)
    _rblock(part, P((ca + cb) / 2, CB_H * 1.27 + 0.0015, -0.004), (0.010, 0.012, 0.004), (ex, Y, ez),
            M.get("button_grey"), r=0.002, bevel=0.0008)                       # release button
    # ... foot down to the tube, pad and strap round the down tube
    cr = P((ca + cb) / 2)
    s_c = (cr - S.BB).dot(t) / down.length
    axis_pt = down.point(s_c)
    dd = cr - axis_pt
    dd = (dd - t * dd.dot(t)).normalized()
    surf = axis_pt + dd * _tube_r(down, s_c, dd)
    foot = mk.scratch()
    mk.tube_path(foot, [cr - dd * (CB_W * 0.9), (cr + surf) / 2, surf + dd * 0.0015],
                 [(0.012, 0.010), (0.014, 0.011), (0.020, 0.013)], None, n=12, ref=t, power=3.0)
    part.add_bm(mk.subdivided(foot, 1), matte)
    s_pad = s_c + 0.016 / down.length
    pad_c = down.point(s_pad) + dd * (_tube_r(down, s_pad, dd) + 0.0040)
    _rblock(part, pad_c, (0.046, 0.026, 0.006), (t, dd.cross(t).normalized(), dd), matte, r=0.006, bevel=0.0015)
    s_strap = s_c + 0.028 / down.length
    phi_d = math.atan2(dd.dot(Y), dd.dot(n))
    rings = []
    for k in range(48):
        phi = 2 * math.pi * k / 48
        bump = 0.0068 * max(0.0, math.cos(phi - phi_d)) ** 6
        boss = 0.0045 * max(0.0, math.cos(phi)) ** 10           # over the bottle-cage rivnuts on top of the tube
        rings.append(down.surface(s_strap, phi, _strap_lift(phi) + bump + boss))
    rings.append(rings[0])
    mk.tube_path(part, rings, (0.0090, 0.0012), M.get("rubber"), n=10, ref=t, power=4.0, caps=False)
    return _finish(part, coll)


# ---------------------------------------------------------------------------------------- reflectors

REFL_OUTLINE = [(-0.017, -0.033), (-0.010, -0.040), (0.010, -0.040), (0.017, -0.033), (0.017, 0.033),
                (0.010, 0.040), (-0.010, 0.040), (-0.017, 0.033)]   # x radial, y along the reflector (80 x 34 mm)
REFL_AT = ((160.0, 0.200), (-12.0, 0.205))   # angle on the wheel (deg, 0 = forward, 90 = up) and radius
REFL_Y = -0.0200                             # centre plane, just outside the drive-side spokes


def build_reflectors(coll):
    """Two amber spoke reflectors (EN/StVZO type, ~80 x 34 mm) on the drive side of the front wheel, each bridging
    two spokes with its long side across the radius (Toni's photo): bevelled body, prismatic face of small
    pyramids inside a smooth rim, lighter clip tabs at both ends gripping the spokes. Origin on the front axle."""
    part = Part("acc_reflectors", CATEGORY)
    amber, tab = M.get("reflector_amber"), M.get("reflector_tab")
    c = S.FRONT_AXLE
    outline = mk.rounded_poly(REFL_OUTLINE, 0.003, n=3)
    inner = _inset(REFL_OUTLINE, 0.0030)
    cell = 0.0024
    for a_deg, rr in REFL_AT:
        a = math.radians(a_deg)
        radial = Vector((math.cos(a), 0.0, math.sin(a)))
        tang = Vector((-math.sin(a), 0.0, math.cos(a)))
        out = -Y
        centre = c + radial * rr + Y * REFL_Y

        def L(x, y, z):
            return centre + radial * x + tang * y + out * z
        body = mk.plate2d(_inset(outline, 0.0008), thickness=0.0052, bevel=0.0008, bevel_res=1)
        mk.place(body, centre, radial, tang, out)
        part.add_bm(body, amber, smooth=False)
        # prismatic face: pyramids on a grid inside the rim, away from the tabs
        bm = part.bm
        faces = []
        nx, ny = int(0.034 / cell), int(0.080 / cell)
        z0, z1 = 0.0034, 0.0042
        for i in range(nx):
            for j in range(ny):
                x0, y0 = -0.017 + i * cell, -0.040 + j * cell
                corners = [(x0, y0), (x0 + cell, y0), (x0 + cell, y0 + cell), (x0, y0 + cell)]
                if not all(_inside(q, inner) for q in corners) or max(abs(y0), abs(y0 + cell)) > 0.027:
                    continue
                vs = [bm.verts.new(L(x, y, z0)) for x, y in corners]
                apex = bm.verts.new(L(x0 + cell / 2, y0 + cell / 2, z1))
                for k in range(4):
                    faces.append(bm.faces.new((vs[k], vs[(k + 1) % 4], apex)))
        part.tag(faces, amber, smooth=False)
        # clip tabs at both ends (lighter, raised) and the spoke clips behind them
        for k in (-1, 1):
            _rblock(part, L(0.0, k * 0.0335, 0.0038), (0.014, 0.011, 0.0022), (radial, tang, out), tab, r=0.003,
                    bevel=0.0006)
            _rblock(part, L(0.0, k * 0.033, -0.0042), (0.010, 0.009, 0.0040), (radial, tang, out), tab, r=0.002,
                    bevel=0.0008)
            mk.cyl(part, L(-0.006, k * 0.033, -0.0052), L(0.006, k * 0.033, -0.0052), 0.0011,
                   M.get("black_matte"), n=8)                                  # spoke groove (shadow)
    return _finish(part, coll, pivot=c)


def build_all(coll):
    return [build_mudguard_front(coll), build_mudguard_rear(coll), build_light_rear(coll), build_light_front(coll),
            build_light_clip(coll), build_bell(coll), build_lock(coll), build_reflectors(coll)]
