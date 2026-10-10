"""Room shell: floor, safety stripes, walls + ceiling + door, roll-up shutter, turntable and its neon ring."""
import math

from mathutils import Vector

from bikelib import meshkit as mk

from . import kit
from . import materials as M
from . import spec as S
from .kit import X, Y, Z, GPart, box_mm


def build_floor(coll):
    p = GPart("floor", {"floor_concrete": (S.SLAB, S.SLAB, *S.SLAB_ORIGIN)})
    # one quad facing up (+Z); a few cuts so the far corners don't stretch the UVs on low-precision GPUs
    nx, ny = 6, 6
    bm = p.bm
    vs = [[bm.verts.new((S.X0 + (S.X1 - S.X0) * i / nx, S.Y0 + (S.Y1 - S.Y0) * j / ny, 0.0)) for j in range(ny + 1)]
          for i in range(nx + 1)]
    faces = [bm.faces.new((vs[i][j], vs[i + 1][j], vs[i + 1][j + 1], vs[i][j + 1])) for i in range(nx) for j in range(ny)]
    p.tag(faces, M.get("floor_concrete"), smooth=False)
    return p.finish(coll, recalc=False)


def build_stripes(coll):
    """Yellow / black diagonal safety stripes forming a square around the turntable bay (painted on the floor)."""
    p = GPart("stripes")
    yel, blk = M.get("stripe_yellow"), M.get("stripe_black")
    cx, cy = S.TT.x, S.TT.y
    hb, w = S.BAY / 2, S.STRIPE_W
    h = S.STRIPE_PERIOD / 2
    sides = [  # (u0, v0, u1, v1, vertical): u along the side, v across it
        (cx - hb - w / 2, cy - hb - w / 2, cx + hb + w / 2, cy - hb + w / 2, False),
        (cx - hb - w / 2, cy + hb - w / 2, cx + hb + w / 2, cy + hb + w / 2, False),
        (cy - hb + w / 2, cx - hb - w / 2, cy + hb - w / 2, cx - hb + w / 2, True),
        (cy - hb + w / 2, cx + hb - w / 2, cy + hb - w / 2, cx + hb + w / 2, True),
    ]
    for u0, v0, u1, v1, vertical in sides:
        d = v1 - v0
        i0 = math.floor((u0 - d) / h) - 1
        i1 = math.ceil(u1 / h) + 1
        for i in range(i0, i1):
            band = [(i * h, v0), ((i + 1) * h, v0), ((i + 1) * h + d, v1), (i * h + d, v1)]
            poly = kit.clip_poly(band, (u0, v0, u1, v1))
            if len(poly) < 3:
                continue
            if vertical:
                pts = [(v, u, S.STRIPE_Z) for (u, v) in reversed(poly)]
            else:
                pts = [(u, v, S.STRIPE_Z) for (u, v) in poly]
            kit.quad(p, pts, yel if i % 2 == 0 else blk)
    return p.finish(coll, recalc=False)


def build_walls(coll):
    """Concrete block walls on all four sides, dark ceiling with two steel beams, steel door in the front wall."""
    p = GPart("walls", {"wall_blocks": (1.6, 1.6, 0.0, 0.0)})
    wall, ceil, beam = M.get("wall_blocks"), M.get("garage_ceiling"), M.get("steel_beam")
    T, H = S.WALL_T, S.H
    box_mm(p, (S.X0 - T, S.Y1, 0), (S.X1 + T, S.Y1 + T, H), wall)          # back
    box_mm(p, (S.X0 - T, S.Y0 - T, 0), (S.X1 + T, S.Y0, H), wall)          # front
    box_mm(p, (S.X0 - T, S.Y0, 0), (S.X0, S.Y1, H), wall)                  # left
    box_mm(p, (S.X1, S.Y0, 0), (S.X1 + T, S.Y1, H), wall)                  # right
    box_mm(p, (S.X0 - T, S.Y0 - T, H), (S.X1 + T, S.Y1 + T, H + T), ceil)   # ceiling
    # steel I-beams under the ceiling, running front to back, clear of the hexagon lights
    for bx in (-3.3, 3.3):
        box_mm(p, (bx - 0.07, S.Y0, H - 0.016), (bx + 0.07, S.Y1, H), beam)
        box_mm(p, (bx - 0.005, S.Y0, H - 0.284), (bx + 0.005, S.Y1, H - 0.016), beam)
        box_mm(p, (bx - 0.07, S.Y0, H - 0.30), (bx + 0.07, S.Y1, H - 0.284), beam)
    # door (front wall, facing +Y into the room)
    door, frame, glass, steel = M.get("door_steel"), M.get("alu_dark"), M.get("glass_dark"), M.get("steel_satin")
    x0, x1, dh, y = S.DOOR_X - S.DOOR_W / 2, S.DOOR_X + S.DOOR_W / 2, S.DOOR_H, S.Y0
    box_mm(p, (x0 - 0.07, y, 0), (x0, y + 0.05, dh + 0.07), frame)
    box_mm(p, (x1, y, 0), (x1 + 0.07, y + 0.05, dh + 0.07), frame)
    box_mm(p, (x0, y, dh), (x1, y + 0.05, dh + 0.07), frame)
    box_mm(p, (x0 + 0.004, y, 0.006), (x1 - 0.004, y + 0.035, dh - 0.004), door)
    box_mm(p, (S.DOOR_X - 0.15, y + 0.035, 1.35), (S.DOOR_X + 0.15, y + 0.039, 1.85), frame)        # window frame
    box_mm(p, (S.DOOR_X - 0.13, y + 0.039, 1.37), (S.DOOR_X + 0.13, y + 0.041, 1.83), glass)
    box_mm(p, (x0 + 0.06, y + 0.035, 0.03), (x1 - 0.06, y + 0.038, 0.26), steel)                   # kick plate
    hx = x1 - 0.085
    mk.cyl(p, Vector((hx, y + 0.035, 1.05)), Vector((hx, y + 0.048, 1.05)), 0.028, steel, n=16)   # rose
    mk.cyl(p, Vector((hx, y + 0.048, 1.05)), Vector((hx, y + 0.075, 1.05)), 0.010, steel, n=10)
    box_mm(p, (hx - 0.13, y + 0.066, 1.040), (hx + 0.01, y + 0.084, 1.060), steel)                 # lever
    return p.finish(coll)


def _slat_outline(yf):
    """Closed (y, z) outline of the shutter curtain: rounded slats in front, flat back."""
    pts = []
    z, top = 0.07, S.SHUTTER_TOP
    while z < top - 1e-6:
        for dz, dy in ((0.0, 0.008), (0.007, 0.001), (S.SLAT * 0.5, -0.005), (S.SLAT - 0.007, 0.001)):
            if z + dz < top:
                pts.append((yf + dy, z + dz))
        z += S.SLAT
    pts.append((yf + 0.008, top))
    back = yf + 0.016
    return [(back, 0.07)] + pts + [(back, top)]


def build_shutter(coll):
    """Roll-up shutter on the back wall: corrugated curtain, guide rails, roll box, bottom bar with handles."""
    p = GPart("shutter")
    metal, dark, rub, steel = M.get("shutter_metal"), M.get("alu_dark"), M.get("rubber_black"), M.get("steel_satin")
    xa, xb = S.SHUTTER_X
    yf = S.Y1 - 0.05                         # front plane of the slats
    outline = _slat_outline(yf)
    mk.prism(p, kit.ccw(outline), Vector((0, 0, 0)), Y, Z, X, xa - 0.04, xb + 0.04, metal, smooth=True)
    # guide rails (U channels seen from the front: outer box + inner lip)
    for x0, x1 in ((xa - 0.09, xa), (xb, xb + 0.09)):
        box_mm(p, (x0, S.Y1 - 0.10, 0), (x1, S.Y1, S.SHUTTER_TOP + 0.10), dark)
    # roll box with a rounded front
    rr = mk.rounded_rect(S.Y1 - 0.13, S.SHUTTER_TOP + 0.16, 0.26, 0.32, 0.05, n=4)
    mk.prism(p, kit.ccw(rr), Vector((0, 0, 0)), Y, Z, X, xa - 0.12, xb + 0.12, dark, smooth=False)
    # bottom bar, rubber seal, two pull handles and a lock
    box_mm(p, (xa - 0.04, yf - 0.014, 0.008), (xb + 0.04, yf + 0.02, 0.075), dark)
    box_mm(p, (xa - 0.04, yf - 0.004, 0.0), (xb + 0.04, yf + 0.012, 0.008), rub)
    for hx in (xa + 0.55, xb - 0.55):
        for dx in (-0.06, 0.06):
            mk.cyl(p, Vector((hx + dx, yf - 0.014, 0.045)), Vector((hx + dx, yf - 0.05, 0.045)), 0.006, steel, n=8)
        mk.cyl(p, Vector((hx - 0.066, yf - 0.05, 0.045)), Vector((hx + 0.066, yf - 0.05, 0.045)), 0.008, steel, n=8)
    cx = (xa + xb) / 2
    mk.cyl(p, Vector((cx, yf - 0.014, 0.045)), Vector((cx, yf - 0.024, 0.045)), 0.016, steel, n=16)
    return p.finish(coll)


def build_turntable(coll):
    """Round base with a rubber top (two shallow grooves) and a polished metal edge. Origin = turntable centre."""
    p = GPart("turntable")
    top, met = M.get("turntable_mat"), M.get("turntable_metal")
    t = S.TT_TOP
    prof = [(0.0, t), (0.30, t), (0.302, t - 0.002), (0.308, t - 0.002), (0.31, t),
            (0.62, t), (0.622, t - 0.002), (0.628, t - 0.002), (0.63, t),
            (0.925, t), (0.928, t - 0.002), (0.932, t - 0.002), (0.935, t),
            (S.TT_R - 0.005, t), (S.TT_R, t - 0.003), (S.TT_R_BASE, 0.002), (S.TT_R_BASE, 0.0), (0.0, 0.0)]
    mats = []
    for (r0, _), (r1, _) in zip(prof, prof[1:]):
        mats.append(top if max(r0, r1) <= 0.928 and not (r0 == 0 and r1 == 0) else met)
    mats[-1] = met
    kit.revolve_z(p, S.TT.copy(), prof, mats, n=96, smooth=True)
    return p.finish(coll, pivot=S.TT.copy(), sharp_angle=30.0)


def build_neon_ring(coll):
    p = GPart("neon_ring")
    kit.torus(p, S.TT + Vector((0, 0, S.TT_TOP)), Z, S.RING_R, S.RING_TUBE, M.get("neon_yellow"), nu=160, nv=8)
    return p.finish(coll, pivot=S.TT.copy())
