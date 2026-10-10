"""Props along the walls (one node `props`): pegboard with tools, workbench, tool chest, tyre stack, oil drum,
shelving, fire extinguisher. Everything stays > 3 m from the turntable centre so the camera can orbit freely."""
import math
import random

from mathutils import Vector

from bikelib import meshkit as mk

from . import kit
from . import materials as M
from . import spec as S
from .kit import X, Y, Z, GPart, box_mm

V = Vector


# ------------------------------------------------------------------------------------------ pegboard

def _wrench(p, y, top, length, steel):
    r_open, r_ring = 0.012 + length * 0.06, 0.010 + length * 0.05
    w = 0.004 + length * 0.02          # half-width of the handle
    x = S.X0 + 0.045 + 0.006
    kit.plate_yz(p, mk.capsule_outline((y, top - r_open), (y, top - length + r_ring), w), x, steel, 0.004)
    # open end (C shape, opening upwards) and ring end
    c, pts_o, pts_i = (y, top - r_open), [], []
    for k in range(13):
        a = math.radians(125 + 290 * k / 12)
        pts_o.append((c[0] + r_open * math.cos(a), c[1] + r_open * math.sin(a)))
        pts_i.append((c[0] + r_open * 0.5 * math.cos(a), c[1] + r_open * 0.5 * math.sin(a)))
    kit.plate_yz(p, pts_o + pts_i[::-1], x, steel, 0.005)
    kit.ring_yz(p, y, top - length + r_ring, r_ring, r_ring * 0.55, x - 0.003, x + 0.003, steel, n=16)


def _hook(p, y, z, steel):
    x = S.X0 + 0.045
    mk.cyl(p, V((x, y, z)), V((x + 0.035, y, z + 0.006)), 0.0025, steel, n=6, caps=False)


def build_pegboard(p):
    peg, frame, steel, red = M.get("pegboard"), M.get("alu_dark"), M.get("steel_satin"), M.get("tool_handle_red")
    yel, black = M.get("cable_yellow"), M.get("rubber_black")
    (y0, y1), (z0, z1) = S.PEG_Y, S.PEG_Z
    xf = S.X0 + 0.045
    box_mm(p, (S.X0 + 0.03, y0, z0), (xf, y1, z1), peg)
    for a, b in (((y0 - 0.02, z0 - 0.02), (y1 + 0.02, z0)), ((y0 - 0.02, z1), (y1 + 0.02, z1 + 0.02)),
                 ((y0 - 0.02, z0), (y0, z1)), ((y1, z0), (y1 + 0.02, z1))):
        box_mm(p, (S.X0 + 0.03, a[0], a[1]), (xf + 0.008, b[0], b[1]), frame)
    # wrenches, sizes increasing
    for i in range(6):
        y, ln = y0 + 0.25 + i * 0.17, 0.16 + i * 0.028
        _hook(p, y, 2.40, steel)
        _wrench(p, y, 2.38, ln, steel)
    # screwdrivers: red handle up, steel shaft down
    for i in range(5):
        y = y0 + 1.35 + i * 0.12
        _hook(p, y, 2.40, steel)
        x = xf + 0.03
        mk.cyl(p, V((x, y, 2.37)), V((x, y, 2.26)), 0.015, red if i % 2 == 0 else black, n=10)
        mk.cyl(p, V((x, y, 2.26)), V((x, y, 2.10 - i * 0.012)), 0.0032, steel, n=6)
    # hammer
    y = y0 + 2.08
    x = xf + 0.025
    box_mm(p, (x - 0.012, y - 0.016, 1.98), (x + 0.012, y + 0.016, 2.34), black)
    box_mm(p, (x - 0.016, y - 0.075, 2.33), (x + 0.016, y + 0.06, 2.37), steel)
    _hook(p, y - 0.03, 2.31, steel)
    # pliers (steel plate, red grips)
    for y in (y0 + 2.35, y0 + 2.55):
        out = [(y - 0.006, 2.38), (y + 0.006, 2.38), (y + 0.012, 2.31), (y + 0.038, 2.14), (y + 0.026, 2.135),
               (y, 2.28), (y - 0.026, 2.135), (y - 0.038, 2.14), (y - 0.012, 2.31)]
        kit.plate_yz(p, out, xf + 0.012, steel, 0.006)
        for sgn in (-1, 1):
            mk.cyl(p, V((xf + 0.012, y + sgn * 0.016, 2.24)), V((xf + 0.012, y + sgn * 0.034, 2.145)), 0.0075, red, n=8)
        _hook(p, y, 2.395, steel)
    # coiled cables (yellow, like the prototype) on the bottom row
    for i, y in enumerate((y0 + 0.45, y0 + 1.15, y0 + 1.85, y0 + 2.55)):
        _hook(p, y, 1.45, steel)
        for k, (rr, dz) in enumerate(((0.115, 0.0), (0.105, 0.004), (0.11, -0.006))):
            kit.torus(p, V((xf + 0.02 + k * 0.012, y, 1.35 + dz)), X, rr, 0.0075, yel if i != 2 else black, nu=28, nv=6)


# ------------------------------------------------------------------------------------------ workbench

def build_workbench(p):
    wood, dark, steel, gun = M.get("bench_wood"), M.get("dark_metal"), M.get("steel_satin"), M.get("chest_gunmetal")
    yel, red, blue, grey = M.get("cable_yellow"), M.get("tool_handle_red"), M.get("drum_blue"), M.get("crate_grey")
    x0, x1 = S.X0 + 0.05, S.X0 + 0.05 + S.BENCH_DEPTH
    y0, y1 = S.BENCH_Y
    t = S.BENCH_TOP
    box_mm(p, (x0, y0, t - 0.06), (x1, y1, t), wood)
    for lx in (x0 + 0.03, x1 - 0.08):
        for ly in (y0 + 0.03, y1 - 0.08):
            box_mm(p, (lx, ly, 0.0), (lx + 0.05, ly + 0.05, t - 0.06), dark)
    box_mm(p, (x1 - 0.07, y0 + 0.08, t - 0.14), (x1 - 0.04, y1 - 0.08, t - 0.06), dark)   # front apron
    box_mm(p, (x0 + 0.04, y0 + 0.08, t - 0.14), (x0 + 0.07, y1 - 0.08, t - 0.06), dark)   # back apron
    box_mm(p, (x0 + 0.03, y0 + 0.03, 0.12), (x1 - 0.03, y1 - 0.03, 0.15), dark)           # lower shelf
    # drawer cabinet at the back-wall end
    cy0, cy1 = y1 - 0.75, y1 - 0.09
    box_mm(p, (x0 + 0.08, cy0, 0.16), (x1 - 0.05, cy1, t - 0.15), gun)
    zs = [0.17, 0.39, 0.58, t - 0.16]
    for za, zb in zip(zs, zs[1:]):
        box_mm(p, (x1 - 0.05, cy0 + 0.01, za + 0.005), (x1 - 0.035, cy1 - 0.01, zb - 0.005), gun)
        hz = zb - 0.04
        mk.cyl(p, V((x1 - 0.02, (cy0 + cy1) / 2 - 0.12, hz)), V((x1 - 0.02, (cy0 + cy1) / 2 + 0.12, hz)), 0.006, steel, n=8)
        for dy in (-0.11, 0.11):
            mk.cyl(p, V((x1 - 0.035, (cy0 + cy1) / 2 + dy, hz)), V((x1 - 0.02, (cy0 + cy1) / 2 + dy, hz)), 0.004, steel, n=6)
    # bench vise at the front end
    vy, vx = y0 + 0.25, x1 - 0.13
    box_mm(p, (vx - 0.08, vy - 0.07, t), (vx + 0.08, vy + 0.07, t + 0.03), dark)
    box_mm(p, (vx - 0.06, vy - 0.05, t + 0.03), (vx + 0.07, vy + 0.05, t + 0.12), blue)
    box_mm(p, (vx + 0.07, vy - 0.075, t + 0.06), (vx + 0.10, vy + 0.075, t + 0.15), blue)
    box_mm(p, (vx + 0.10, vy - 0.075, t + 0.06), (vx + 0.13, vy + 0.075, t + 0.15), blue)
    mk.cyl(p, V((vx + 0.13, vy, t + 0.09)), V((vx + 0.22, vy, t + 0.09)), 0.010, steel, n=10)
    mk.cyl(p, V((vx + 0.22, vy - 0.12, t + 0.09)), V((vx + 0.22, vy + 0.12, t + 0.09)), 0.006, steel, n=8)
    # portable tool box
    ty = y0 + 1.05
    box_mm(p, (x0 + 0.22, ty - 0.24, t), (x0 + 0.46, ty + 0.24, t + 0.17), gun)
    box_mm(p, (x0 + 0.215, ty - 0.245, t + 0.15), (x0 + 0.465, ty + 0.245, t + 0.20), gun)
    for dy in (-0.16, 0.16):
        box_mm(p, (x0 + 0.46, ty + dy - 0.02, t + 0.12), (x0 + 0.47, ty + dy + 0.02, t + 0.17), yel)
        mk.cyl(p, V((x0 + 0.34, ty + dy * 0.6, t + 0.20)), V((x0 + 0.34, ty + dy * 0.6, t + 0.24)), 0.008, dark, n=8)
    mk.cyl(p, V((x0 + 0.34, ty - 0.10, t + 0.245)), V((x0 + 0.34, ty + 0.10, t + 0.245)), 0.012, dark, n=10)
    # spray cans and a bottle
    for i, (mat, h) in enumerate(((red, 0.20), (blue, 0.18), (grey, 0.24))):
        cx, cy = x1 - 0.16 + (i % 2) * 0.05, y0 + 1.55 + i * 0.08
        mk.cyl(p, V((cx, cy, t)), V((cx, cy, t + h)), 0.032, mat, n=14)
        mk.cyl(p, V((cx, cy, t + h)), V((cx, cy, t + h + 0.035)), 0.02, M.get("rubber_black"), n=10)


# ------------------------------------------------------------------------------------------ tool chest

def build_tool_chest(p):
    gun, dark, neon, rub = M.get("chest_gunmetal"), M.get("dark_metal"), M.get("neon_yellow"), M.get("rubber_black")
    steel = M.get("steel_satin")
    x0, x1 = S.X0 + 0.05, S.X0 + 0.05 + S.CHEST_DEPTH
    y0, y1 = S.CHEST_Y
    zc = 0.09                                     # castor height
    box_mm(p, (x0, y0, zc), (x1 - 0.012, y1, S.CHEST_H - 0.04), gun)
    box_mm(p, (x0 - 0.005, y0 - 0.008, S.CHEST_H - 0.04), (x1 + 0.008, y1 + 0.008, S.CHEST_H), dark)
    box_mm(p, (x0 + 0.02, y0 + 0.02, S.CHEST_H), (x1 - 0.02, y1 - 0.02, S.CHEST_H + 0.006), rub)   # top mat
    # six drawers; the glowing handle bars are the prototype's neon accents
    edges = [zc + 0.01, 0.25, 0.41, 0.57, 0.71, 0.85, S.CHEST_H - 0.05]
    for za, zb in zip(edges, edges[1:]):
        box_mm(p, (x1 - 0.012, y0 + 0.012, za + 0.004), (x1, y1 - 0.012, zb - 0.004), gun)
        hz = zb - 0.035
        box_mm(p, (x1, (y0 + y1) / 2 - 0.30, hz - 0.006), (x1 + 0.02, (y0 + y1) / 2 + 0.30, hz + 0.006), neon)
    # side handle
    mk.cyl(p, V(((x0 + x1) / 2 - 0.12, y1 + 0.05, 0.95)), V(((x0 + x1) / 2 + 0.12, y1 + 0.05, 0.95)), 0.01, steel, n=8)
    for dx in (-0.12, 0.12):
        mk.cyl(p, V(((x0 + x1) / 2 + dx, y1, 0.95)), V(((x0 + x1) / 2 + dx, y1 + 0.05, 0.95)), 0.008, steel, n=8)
    # castors
    for cx in (x0 + 0.06, x1 - 0.07):
        for cy in (y0 + 0.07, y1 - 0.07):
            box_mm(p, (cx - 0.03, cy - 0.025, zc - 0.012), (cx + 0.03, cy + 0.025, zc), dark)
            mk.cyl(p, V((cx, cy - 0.015, 0.038)), V((cx, cy + 0.015, 0.038)), 0.038, rub, n=14)


# ------------------------------------------------------------------------------------------ right wall

def build_tyres(p):
    """Stack of five car tyres lying flat (tread grooves on the outside)."""
    rub = M.get("tyre_rubber")
    prof = [(0.27, -0.035), (0.30, -0.055), (0.36, -0.06), (0.385, -0.046), (0.39, -0.034), (0.39, -0.02),
            (0.382, -0.018), (0.382, -0.008), (0.39, -0.006), (0.39, 0.006), (0.382, 0.008), (0.382, 0.018),
            (0.39, 0.02), (0.39, 0.034), (0.385, 0.046), (0.36, 0.06), (0.30, 0.055), (0.27, 0.035)]
    rng = random.Random(7)
    for i in range(5):
        c = S.TYRES_AT + V((rng.uniform(-0.025, 0.025), rng.uniform(-0.025, 0.025), 0.06 + i * 0.12))
        kit.revolve_z(p, c, prof, rub, n=36, smooth=True, closed=True)


def build_drum(p):
    """200 l oil drum: chimes, two rolling hoops, recessed lid with two bungs."""
    blue, steel = M.get("drum_blue"), M.get("steel_satin")
    prof = [(0.0, 0.004), (0.28, 0.004), (0.29, 0.0), (0.293, 0.012), (0.287, 0.02),
            (0.287, 0.27), (0.297, 0.282), (0.297, 0.298), (0.287, 0.31),
            (0.287, 0.57), (0.297, 0.582), (0.297, 0.598), (0.287, 0.61),
            (0.287, 0.858), (0.293, 0.866), (0.29, 0.88), (0.281, 0.877), (0.276, 0.866), (0.0, 0.866)]
    kit.revolve_z(p, S.DRUM_AT.copy(), prof, blue, n=32, smooth=True)
    for (dx, dy, r) in ((0.17, 0.05, 0.03), (-0.17, 0.05, 0.016)):
        c = S.DRUM_AT + V((dx, dy, 0.866))
        mk.cyl(p, c, c + V((0, 0, 0.014)), r, steel, n=12)


def build_shelving(p):
    """Steel shelving unit with boxes and crates (right wall, front half of the room)."""
    dark, card, crate = M.get("dark_metal"), M.get("cardboard"), M.get("crate_grey")
    x1 = S.X1 - 0.06
    x0 = x1 - S.SHELF_DEPTH
    y0, y1 = S.SHELF_Y
    for px in (x0, x1 - 0.035):
        for py in (y0, y1 - 0.035):
            box_mm(p, (px, py, 0.0), (px + 0.035, py + 0.035, S.SHELF_H), dark)
    levels = [0.10, 0.55, 1.00, 1.45, 1.90]
    for z in levels:
        box_mm(p, (x0, y0, z), (x1, y1, z + 0.025), dark)
    rng = random.Random(980)
    for z, z_next in zip(levels, levels[1:] + [S.SHELF_H + 0.4]):
        y = y0 + 0.06
        while True:
            w = rng.uniform(0.28, 0.48)
            if y + w > y1 - 0.05:
                break
            d = rng.uniform(0.28, 0.40)
            h = min(rng.uniform(0.18, 0.34), z_next - z - 0.08)
            mat = card if rng.random() < 0.6 else crate
            xa = x1 - 0.02 - d
            box_mm(p, (xa, y, z + 0.025), (x1 - 0.02, y + w, z + 0.025 + h), mat)
            if mat is card:                     # a strip of tape on the front of the box
                box_mm(p, (xa - 0.002, y + w / 2 - 0.025, z + 0.025 + h - 0.08), (xa, y + w / 2 + 0.025, z + 0.025 + h), crate)
            y += w + rng.uniform(0.03, 0.08)


def build_extinguisher(p):
    """Fire extinguisher on a wall bracket next to the door."""
    red, steel, black = M.get("extinguisher_red"), M.get("steel_satin"), M.get("rubber_black")
    x, y = S.DOOR_X + S.DOOR_W / 2 + 0.45, S.Y0 + 0.09
    box_mm(p, (x - 0.05, S.Y0, 1.05), (x + 0.05, S.Y0 + 0.012, 1.35), M.get("dark_metal"))
    mk.cyl(p, V((x, y, 0.92)), V((x, y, 1.40)), 0.075, red, n=16)
    mk.cyl(p, V((x, y, 1.40)), V((x, y, 1.43)), 0.05, red, n=16)
    mk.cyl(p, V((x, y, 1.43)), V((x, y, 1.49)), 0.016, steel, n=10)
    box_mm(p, (x - 0.07, y - 0.012, 1.48), (x + 0.03, y + 0.012, 1.50), black)
    mk.curve_tube(p, [V((x + 0.01, y + 0.01, 1.47)), V((x + 0.08, y + 0.03, 1.40)), V((x + 0.09, y + 0.02, 1.15)),
                      V((x + 0.07, y + 0.0, 1.00))], 0.008, black, samples=4, n=6)


def build_props(coll):
    p = GPart("props", {"pegboard": (0.4, 0.4, 0.0, 0.0)})
    build_pegboard(p)
    build_workbench(p)
    build_tool_chest(p)
    build_tyres(p)
    build_drum(p)
    build_shelving(p)
    build_extinguisher(p)
    return p.finish(coll)
