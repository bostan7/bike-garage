"""Emissive parts: neon wall strips, hexagon LED ceiling, "SCALE 980" neon sign."""
import math

import bpy
from mathutils import Vector

from bikelib import meshkit as mk

from . import kit
from . import materials as M
from . import spec as S
from .kit import X, Y, Z, GPart, box_mm


def _tube(p, a, b, mat, clip_mat=None, clip_every=0.9):
    a, b = Vector(a), Vector(b)
    mk.cyl(p, a, b, S.NEON_TUBE_R, mat, n=8)
    if clip_mat is None:
        return
    n = max(1, int((b - a).length / clip_every))
    for k in range(n + 1):
        c = a.lerp(b, (k + 0.5) / (n + 1))
        d = (b - a).normalized()
        size = Vector((0.03, 0.03, 0.03)) + Vector((abs(d.x), abs(d.y), abs(d.z))) * -0.012
        mk.box(p, c, size * 1.05, clip_mat)


def build_strips(coll):
    """Wall base lines on all four walls (broken by the shutter and the door) + the four vertical corners."""
    p = GPart("neon_strips")
    neon, clip = M.get("neon_yellow"), M.get("alu_dark")
    o, z = 0.03, S.NEON_BASE_Z
    xl, xr, yb, yf = S.X0 + o, S.X1 - o, S.Y1 - o, S.Y0 + o
    rail_l, rail_r = S.SHUTTER_X[0] - 0.11, S.SHUTTER_X[1] + 0.11
    door_l, door_r = S.DOOR_X - S.DOOR_W / 2 - 0.09, S.DOOR_X + S.DOOR_W / 2 + 0.09
    runs = [
        ((xl, yb, z), (rail_l, yb, z)), ((rail_r, yb, z), (xr, yb, z)),        # back wall, either side of the shutter
        ((xl, yf, z), (door_l, yf, z)), ((door_r, yf, z), (xr, yf, z)),        # front wall, either side of the door
        ((xl, yf, z), (xl, yb, z)), ((xr, yf, z), (xr, yb, z)),                # left and right walls
    ]
    for cx, cy in ((xl, yb), (xr, yb), (xl, yf), (xr, yf)):                   # vertical corners
        runs.append(((cx, cy, z), (cx, cy, S.H - 0.02)))
    for a, b in runs:
        _tube(p, a, b, neon, clip)
    return p.finish(coll)


def _hex_edges():
    r = S.HEX_R
    edges = {}
    for q in range(-6, 7):
        for s in range(-5, 6):
            cx = q * r * 1.5
            cz = (s + (0.5 if q % 2 else 0.0)) * r * math.sqrt(3)
            if math.hypot(cx, cz) > S.HEX_LIMIT:
                continue
            for k in range(6):
                a, b = math.pi / 3 * k, math.pi / 3 * (k + 1)
                # prototype (three.js x, z) -> Blender (x, -z)
                p1 = (S.TT.x + cx + r * math.cos(a), S.TT.y - (cz + r * math.sin(a)))
                p2 = (S.TT.x + cx + r * math.cos(b), S.TT.y - (cz + r * math.sin(b)))
                key = tuple(sorted((tuple(round(v, 4) for v in p1), tuple(round(v, 4) for v in p2))))
                edges[key] = (p1, p2)
    return list(edges.values())


def build_hex_lights(coll):
    """Hexagon LED grid on the ceiling above the turntable: one bar per shared hexagon edge."""
    p = GPart("hex_lights")
    led = M.get("led_white")
    w, h = S.HEX_BAR
    for (x1, y1), (x2, y2) in _hex_edges():
        c = Vector(((x1 + x2) / 2, (y1 + y2) / 2, S.HEX_Z))
        ln = math.hypot(x2 - x1, y2 - y1)
        mk.box(p, c, Vector((ln + w * 0.55, w, h)), led, rot=kit.rot_z(math.atan2(y2 - y1, x2 - x1)))
    return p.finish(coll)


def _text_bounds(text, font, shear):
    me = mk._text_mesh(text, 1.0, 0.0, font, shear=shear)
    xs = [v.co.x for v in me.vertices]
    ys = [v.co.y for v in me.vertices]
    bpy.data.meshes.remove(me)
    return min(xs), max(xs), min(ys), max(ys)


def build_sign(coll):
    """'SCALE 980' on the back wall: black backing plate, neon-yellow halo layer, yellow-white letter cores."""
    p = GPart("sign")
    x0, x1, y0, y1 = _text_bounds(S.SIGN_TEXT, S.SIGN_FONT, S.SIGN_SHEAR)
    s = S.SIGN_WIDTH / (x1 - x0)
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    th = (y1 - y0) * s
    c = S.SIGN_CENTER
    plate_d = 0.015
    pf = S.Y1 - plate_d                          # plate front face (y)
    plate = mk.rounded_rect(c.x, c.z, S.SIGN_WIDTH + 0.16, th + 0.18, 0.04, n=3)
    mk.prism(p, kit.ccw(plate), Vector((0.0, S.Y1, 0.0)), X, Z, -Y, 0.0, plate_d, M.get("sign_backing"))
    # letters: a slightly fatter neon-yellow layer behind (reads as the yellow glow rim) and the core in front
    for layer, (d0, d1), mat, offset in (("halo", (0.002, 0.014), M.get("neon_yellow"), 0.028),
                                         ("core", (0.008, 0.030), M.get("sign_core"), 0.0)):
        dc, e = (d0 + d1) / 2, (d1 - d0) / 2

        def xform(v, dc=dc, e=e):
            return Vector((c.x + (v.x - mx) * s, pf - (dc + v.z * e), c.z + (v.y - my) * s))
        mk.add_text(p, S.SIGN_TEXT, 1.0, 1.0, mat, xform, S.SIGN_FONT, max_edge=100.0,
                    offset=offset, shear=S.SIGN_SHEAR)
    return p.finish(coll)
