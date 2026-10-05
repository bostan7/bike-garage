"""Drivetrain: FC-MT511-1 32T crankset, BB-MT500-PA, KMC X12 chain, CS-M6100-12 10-51T cassette,
RD-M6100-SGS derailleur, Feimin flat pedals.

Shapes follow the reference photos in photos/online-reference/ (shimano-drivetrain/, buycycle-scale980-2022-L/)
and are placed with points traced on SCOTT's studio side photo (mm from the rear axle or the BB)."""
import math

import bpy
from mathutils import Vector

from . import materials as M
from . import meshkit as mk
from . import spec as S
from .meshkit import Part, X, Y, Z

MM = 0.001
FONTS = "C:/Windows/Fonts/"


def _crank_dir(angle_deg):
    a = math.radians(angle_deg)
    return Vector((math.cos(a), 0.0, math.sin(a)))


def pedal_points():
    d = _crank_dir(S.CRANK_ANGLE)
    return (S.BB + d * S.CRANK_LEN - Y * S.Q_HALF, S.BB - d * S.CRANK_LEN + Y * S.Q_HALF)


def _axle_plate(part, outline_mm, y, thickness, mat, holes_mm=(), bevel=0.0, bevel_res=1, origin=None):
    """Plate drawn in mm in the bike plane (x forward, z up) around `origin` (default: rear axle),
    centred at lateral position y."""
    o = origin if origin is not None else S.REAR_AXLE
    conv = lambda p: (o.x + p[0] * MM, o.z + p[1] * MM)          # noqa: E731
    bm = mk.plate2d([conv(p) for p in outline_mm], [[conv(p) for p in h] for h in holes_mm],
                    thickness=thickness, bevel=bevel, bevel_res=bevel_res)
    mk.place(bm, Vector((0.0, y, 0.0)), X, Z, -Y)
    return part.add_bm(bm, mat)


def _ax(x_mm, z_mm, y):
    return Vector((S.REAR_AXLE.x + x_mm * MM, y, S.REAR_AXLE.z + z_mm * MM))


# --------------------------------------------------------------------------------- crankset
# FC-MT511-1 (traced on SCOTT's photo): straight tapered arms with a raised, pointed face panel and
# SHIMANO on it; the drive arm carries a 4-arm spider (Shimano asymmetric 96 BCD: bolts at +-55 deg around
# the arm and around the opposite direction); 32T narrow-wide ring with slots in its band.

SPIDER_BOLTS = (55.0, -55.0, 125.0, -125.0)   # bolt angles relative to the drive arm
BCD_R = 0.048
ARM_T = 0.014                                  # arm thickness (lateral)


def _arm_outline(L):
    return mk.hull2d(mk.circle_pts(0.0, 0.0, 0.0200, 40) + mk.circle_pts(L, 0.0, 0.0128, 32))


def _facet_outline(L):
    pts = [(0.034, 0.0), (0.058, 0.0090), (L - 0.030, 0.0074), (L - 0.021, 0.0), (L - 0.030, -0.0074), (0.058, -0.0090)]
    return mk.rounded_poly(pts, 0.0035, n=3)


def _arm_mapper(side, d):
    """(u along the arm, v across it, w outwards) -> world. The arm leans out from the BB to the pedal."""
    up = Vector((-d.z, 0.0, d.x)) * (1.0 if side < 0 else -1.0)   # keeps the left arm's text readable
    y0, y1 = 0.0645, S.Q_HALF - 0.0085

    def f(u, v, w):
        return S.BB + d * u + up * v + Y * (side * (y0 + (y1 - y0) * u / S.CRANK_LEN + w))
    return f


def _mapped(bm, f, w_shift=0.0):
    for vert in bm.verts:
        u, v, w = vert.co
        vert.co = f(u, v, w + w_shift)
    return bm


def _arm(part, side, d, mat):
    f = _arm_mapper(side, d)
    L = S.CRANK_LEN
    part.add_bm(_mapped(mk.plate2d(_arm_outline(L), thickness=ARM_T, bevel=0.0022, bevel_res=2), f), mat)
    facet = mk.plate2d(_facet_outline(L), thickness=0.0012, bevel=0.0004, bevel_res=1)
    part.add_bm(_mapped(facet, f, ARM_T / 2 + 0.0016), mat)
    # SHIMANO on the panel, towards the pedal
    probe = mk._text_mesh("SHIMANO", 1.0, 0.0, FONTS + "arialbd.ttf")
    xs = [v.co.x for v in probe.vertices]
    bpy.data.meshes.remove(probe)
    sx = 0.027 / (max(xs) - min(xs))
    w_txt = ARM_T / 2 + 0.0016 + 0.0006 + 0.0006
    mk.add_text(part, "SHIMANO", 1.0, 0.0, M.get("tyre_text"),
                lambda v: f(0.100 + v.x * sx, v.y * sx, w_txt), FONTS + "arialbd.ttf")
    # pedal eye: threaded hole ring on the outer face
    mk.cyl(part, f(L, 0, ARM_T / 2 + 0.0019), f(L, 0, ARM_T / 2 + 0.0024), 0.0072, M.get("steel"), r2=0.0068, n=24)
    return f


def _chainring(part, bolts, yr):
    gloss = M.get("black_gloss")
    teeth = S.CHAINRING_T
    R = S.pitch_r(teeth)
    bolt_angles = [math.atan2(bz, bx) for bx, bz in bolts]
    inner = []
    for k in range(144):
        phi = 2 * math.pi * k / 144
        bump = 0.0
        for ba in bolt_angles:
            dphi = math.atan2(math.sin(phi - ba), math.cos(phi - ba))
            if abs(dphi) < 0.27:
                bump = max(bump, math.cos(math.pi / 2 * dphi / 0.27) ** 2)
        r = 0.0532 - 0.0112 * bump
        inner.append((r * math.cos(phi), r * math.sin(phi)))
    holes = [inner] + [mk.circle_pts(bx, bz, 0.0046, 18) for bx, bz in bolts]
    # slots in the band between the bolt tabs
    order = sorted(bolt_angles)
    for i, a0 in enumerate(order):
        a1 = order[(i + 1) % len(order)] + (2 * math.pi if i == len(order) - 1 else 0.0)
        start, end = a0 + math.radians(15), a1 - math.radians(15)
        n = max(1, int(round(math.degrees(end - start) / 18)))
        step = (end - start) / n
        for j in range(n):
            s0, s1 = start + step * j + math.radians(2.2), start + step * (j + 1) - math.radians(2.2)
            outer = [(0.0583 * math.cos(s0 + (s1 - s0) * t / 6), 0.0583 * math.sin(s0 + (s1 - s0) * t / 6)) for t in range(7)]
            inn = [(0.0557 * math.cos(s1 - (s1 - s0) * t / 6), 0.0557 * math.sin(s1 - (s1 - s0) * t / 6)) for t in range(7)]
            holes.append(mk.rounded_poly(outer + inn, 0.0010, n=2))
    ring = mk.plate2d(mk.sprocket_outline(teeth, pts_per_tooth=12), holes=holes, thickness=0.0022,
                      bevel=0.0003, bevel_res=0)
    mk.in_bike_plane(ring, S.BB, y=yr)
    part.add_bm(ring, gloss)
    # narrow-wide: every other tooth is thicker (pads on both faces of the wide teeth)
    step = 2 * math.pi / teeth
    for k in range(0, teeth, 2):
        a = step * (k + 0.5)
        ta = Vector((math.cos(a), 0.0, math.sin(a)))
        tt = Vector((-math.sin(a), 0.0, math.cos(a)))
        o = Vector((S.BB.x, 0.0, S.BB.z)) + ta * (R - 0.0020)
        outline = [(-0.0018, -0.0022), (0.0022, -0.0012), (0.0022, 0.0012), (-0.0018, 0.0022)]
        for s in (-1.0, 1.0):
            y0 = yr + s * 0.0011
            mk.prism(part, outline, o, ta, tt, Y, min(y0, y0 + s * 0.0005), max(y0, y0 + s * 0.0005), gloss)
    return ring


def build_crankset(coll):
    part = Part("crankset", "Drivetrain")
    black, steel, gloss = M.get("black_anodised"), M.get("steel"), M.get("black_gloss")
    d = _crank_dir(S.CRANK_ANGLE)
    mk.cyl(part, S.BB + Y * 0.066, S.BB - Y * 0.066, 0.0120, steel, n=32)                   # 24 mm spindle
    f_drive = _arm(part, -1.0, d, black)
    f_left = _arm(part, 1.0, -d, black)
    # drive arm: hollow spindle end showing on the outer face
    mk.cyl(part, f_drive(0, 0, ARM_T / 2 + 0.0019), f_drive(0, 0, ARM_T / 2 + 0.0023), 0.0120, steel, n=40)
    mk.cyl(part, f_drive(0, 0, ARM_T / 2 + 0.0023), f_drive(0, 0, ARM_T / 2 + 0.0024), 0.0104, gloss, n=40)
    # left arm: split clamp with two pinch bolts, preload cap
    slot = mk.scratch()
    mk.box(slot, f_left(-0.0165, 0.0, 0.0), (0.0090, 0.0010, ARM_T + 0.0046), None, rot=mk.basis(-d, Y))
    part.add_bm(slot.bm, gloss, smooth=False)
    upv = Vector((d.z, 0.0, -d.x))
    for wz in (-0.0035, 0.0035):
        c = f_left(-0.0160, 0.0, wz)
        mk.cyl(part, c - upv * 0.0105, c + upv * 0.0105, 0.0029, steel, n=12)
        mk.cyl(part, c + upv * 0.0105, c + upv * 0.0125, 0.0042, black, n=6)                # hex head
    mk.cyl(part, f_left(0, 0, ARM_T / 2 + 0.0019), f_left(0, 0, ARM_T / 2 + 0.0045), 0.0118, gloss, n=32)
    mk.cyl(part, f_left(0, 0, ARM_T / 2 + 0.0045), f_left(0, 0, ARM_T / 2 + 0.0047), 0.0060, black, n=6)

    # 4-arm spider on the drive arm, outboard of the ring
    yr = S.CHAINLINE_Y
    y_sp = yr - 0.0011 - 0.0034
    bolts = []
    for a_rel in SPIDER_BOLTS:
        ang = math.radians(S.CRANK_ANGLE + a_rel)
        bolts.append((BCD_R * math.cos(ang), BCD_R * math.sin(ang)))
    for bx, bz in bolts:
        arm = mk.plate2d(mk.hull2d(mk.circle_pts(0.0, 0.0, 0.0090, 20) + mk.circle_pts(bx, bz, 0.0066, 20)),
                         thickness=0.0068, bevel=0.0012, bevel_res=1)
        mk.in_bike_plane(arm, S.BB, y=y_sp)
        part.add_bm(arm, black)
    hub = mk.plate2d(mk.circle_pts(0, 0, 0.0245, 48), thickness=0.0100, bevel=0.0015, bevel_res=1)
    mk.in_bike_plane(hub, S.BB, y=y_sp - 0.0020)
    part.add_bm(hub, black)

    _chainring(part, bolts, yr)
    for bx, bz in bolts:
        p = S.BB + Vector((bx, 0.0, bz))
        head = p + Y * (y_sp - 0.0034)
        mk.cyl(part, head, head - Y * 0.0026, 0.0052, steel, n=18)                        # bolt head
        mk.cyl(part, head - Y * 0.0026, head - Y * 0.0027, 0.0022, gloss, n=6)            # hex socket
        nut = p + Y * (yr + 0.0011)
        mk.cyl(part, nut, nut + Y * 0.0040, 0.0043, steel, n=18)                          # nut
    return part.finish(coll, pivot=S.BB, sharp_angle=40.0)


def build_bottom_bracket(coll):
    """BB-MT500-PA press-fit cups (black resin with a flange) and the grey seals around the spindle."""
    part = Part("bottom_bracket", "Drivetrain")
    black, grey = M.get("black_gloss"), M.get("grey_plastic")
    cup_prof = [(0.0128, 0.0), (0.0226, 0.0), (0.0230, 0.0005), (0.0231, 0.0017), (0.0226, 0.0026),
                (0.0212, 0.0034), (0.0170, 0.0040), (0.0146, 0.0041), (0.0134, 0.0046), (0.0128, 0.0046)]
    seal_prof = [(0.0122, 0.0040), (0.0136, 0.0040), (0.0136, 0.0056), (0.0122, 0.0056)]
    for side in (1.0, -1.0):
        for prof, mat in ((cup_prof, black), (seal_prof, grey)):
            sh = mk.scratch()
            mk.revolve(sh, Vector((0, 0, 0)), prof, None, n=S.seg("bottom_bracket", 56))
            if side < 0:
                for v in sh.bm.verts:
                    v.co.y = -v.co.y
            mk.place(sh.bm, S.BB + Y * (side * 0.0448), X, Y, Z)
            part.add_bm(sh.bm, mat, free=False)
    return part.finish(coll, pivot=S.BB)


# --------------------------------------------------------------------------------- cassette
# CS-M6100-12: steel cogs (14..33T with windows), the three biggest on a black aluminium spider.
# Hyperglide+ shift ramps = a few lowered teeth per cog. Black spacers between the loose cogs.

def _cog_outline(teeth, ppt=10):
    pts = mk.sprocket_outline(teeth, pts_per_tooth=ppt, phase=0.13 * teeth)
    R = S.pitch_r(teeth)
    zones = max(2, teeth // 9)
    for zi in range(zones):
        k = int(round(zi * teeth / zones)) % teeth
        for j in range(ppt):
            x, y = pts[k * ppt + j]
            r, a = math.hypot(x, y), math.atan2(y, x)
            if r > R:
                r = R + (r - R) * 0.45
            pts[k * ppt + j] = (r * math.cos(a), r * math.sin(a))
    return pts


def build_cassette(coll):
    part = Part("cassette", "Drivetrain")
    silver, black = M.get("alu_silver"), M.get("black_anodised")
    c = S.REAR_AXLE
    for teeth in S.CASSETTE:
        y = S.cog_y(teeth)
        R = S.pitch_r(teeth)
        if teeth >= 39:
            holes = [mk.circle_pts(0, 0, R - 0.0120, 120)]
            n_win = teeth // 3
            for k in range(n_win):
                a = 2 * math.pi * (k + 0.5) / n_win + 0.05 * teeth
                holes.append(mk.circle_pts((R - 0.0088) * math.cos(a), (R - 0.0088) * math.sin(a), 0.0024, 12))
        elif teeth >= 21:
            holes = [mk.circle_pts(0, 0, 0.0175, 40)]
            r0, r1 = 0.0175 + 0.0045, R - 0.0085
            for k in range(6):
                a0 = 2 * math.pi * k / 6 + 0.25
                win = [((r0 + (r1 - r0) * t) * math.cos(a0 + w), (r0 + (r1 - r0) * t) * math.sin(a0 + w))
                       for t, w in ((0, -0.20), (1, -0.32), (1, 0.32), (0, 0.20))]
                holes.append(mk.rounded_poly(win, 0.0015, n=2))
        elif teeth >= 14:
            holes = [mk.circle_pts(0, 0, 0.0175, 40)]
            rm = (0.0175 + R - 0.0045) / 2
            for k in range(5):
                a = 2 * math.pi * k / 5 + 0.3
                holes.append(mk.circle_pts(rm * math.cos(a), rm * math.sin(a), 0.0016, 10))
        else:
            holes = [mk.circle_pts(0, 0, 0.0175 if teeth > 10 else 0.0160, 40)]
        cog = mk.plate2d(_cog_outline(teeth), holes=holes, thickness=0.0018)   # no chamfer: it folds at the tooth tips
        mk.in_bike_plane(cog, c, y=y)
        part.add_bm(cog, silver, smooth=False)
        if teeth >= 39:      # black aluminium spider carrying the big cogs
            r_band = R - 0.0115
            for k in range(6):
                ang = 2 * math.pi * k / 6 + 0.1 * teeth
                tip = (r_band * math.cos(ang), r_band * math.sin(ang))
                arm = mk.plate2d(mk.capsule_outline((0.0185 * math.cos(ang), 0.0185 * math.sin(ang)), tip, 0.0042),
                                 thickness=0.0016, bevel=0.0003, bevel_res=0)
                mk.in_bike_plane(arm, c, y=y + 0.0016)
                part.add_bm(arm, black)
            hubring = mk.plate2d(mk.circle_pts(0, 0, 0.0240, 48), holes=[mk.circle_pts(0, 0, 0.0175, 48)],
                                 thickness=0.0016)
            mk.in_bike_plane(hubring, c, y=y + 0.0016)
            part.add_bm(hubring, black)
    # black spacers between the loose cogs (12T .. 33T)
    loose = [t for t in S.CASSETTE if 12 <= t <= 33]
    for a, b in zip(loose, loose[1:]):
        ya, yb = S.cog_y(a), S.cog_y(b)
        sp = mk.plate2d(mk.circle_pts(0, 0, 0.0198, 40), holes=[mk.circle_pts(0, 0, 0.0176, 40)],
                        thickness=abs(ya - yb) - 0.0018)
        mk.in_bike_plane(sp, c, y=(ya + yb) / 2)
        part.add_bm(sp, black)
    # knurled lockring
    y_small = S.cog_y(10)
    lock = [(((0.0185 if k % 2 else 0.0178) * math.cos(2 * math.pi * k / 48)),
             ((0.0185 if k % 2 else 0.0178) * math.sin(2 * math.pi * k / 48))) for k in range(48)]
    lr = mk.plate2d(lock, holes=[mk.circle_pts(0, 0, 0.0110, 24)], thickness=0.004)
    mk.in_bike_plane(lr, c, y=y_small - 0.0030)
    part.add_bm(lr, silver, smooth=False)
    return part.finish(coll, pivot=c, sharp_angle=50.0)


# ---------------------------------------------------------------------------- chain geometry

def _rd(offset):
    return S.REAR_AXLE + X * offset[0] + Z * offset[1]


def _pulley_centers():
    return _rd(S.RD_UPPER_PULLEY), _rd(S.RD_LOWER_PULLEY)


def _tangent(c1, r1, s1, c2, r2, s2):
    """Belt tangent from circle 1 to circle 2 (2-D tuples x, z). s = +1 counter-clockwise, -1 clockwise."""
    dx, dz = c2[0] - c1[0], c2[1] - c1[1]
    dist = math.hypot(dx, dz)
    alpha = math.atan2(dz, dx)
    k = r1 * s1 - r2 * s2
    phi = alpha + math.asin(max(-1.0, min(1.0, k / dist)))
    m = (math.sin(phi), -math.cos(phi))
    p1 = (c1[0] + r1 * s1 * m[0], c1[1] + r1 * s1 * m[1])
    p2 = (c2[0] + r2 * s2 * m[0], c2[1] + r2 * s2 * m[1])
    return p1, p2


def _arc(c, r, s, p_in, p_out, step=0.004):
    a_in = math.atan2(p_in[1] - c[1], p_in[0] - c[0])
    a_out = math.atan2(p_out[1] - c[1], p_out[0] - c[0])
    if s > 0:
        sweep = (a_out - a_in) % (2 * math.pi)
    else:
        sweep = -((a_in - a_out) % (2 * math.pi))
    n = max(2, int(abs(sweep) * r / step))
    return [(c[0] + r * math.cos(a_in + sweep * i / n), c[1] + r * math.sin(a_in + sweep * i / n)) for i in range(n + 1)]


def chain_path():
    """Closed chain loop in the bike plane: list of (x, z)."""
    up, low = _pulley_centers()
    circles = [((S.BB.x, S.BB.z), S.pitch_r(S.CHAINRING_T), 1.0),
               ((S.REAR_AXLE.x, S.REAR_AXLE.z), S.pitch_r(S.CHAIN_ON), 1.0),
               ((up.x, up.z), S.pitch_r(S.PULLEY_T), -1.0),
               ((low.x, low.z), S.pitch_r(S.PULLEY_T), 1.0)]
    n = len(circles)
    tangents = [_tangent(*circles[i], *circles[(i + 1) % n]) for i in range(n)]
    path = []
    for i in range(n):
        c, r, s = circles[i]
        p_in = tangents[i - 1][1]
        p_out = tangents[i][0]
        path += _arc(c, r, s, p_in, p_out)
        path.append(tangents[i][1])
    return path


def _resample_closed(path, n_links):
    seg = [math.dist(path[i], path[(i + 1) % len(path)]) for i in range(len(path))]
    total = sum(seg)
    step = total / n_links
    out, i, acc = [], 0, 0.0
    for k in range(n_links):
        target = k * step
        while acc + seg[i] < target:
            acc += seg[i]
            i = (i + 1) % len(path)
        t = (target - acc) / seg[i] if seg[i] else 0.0
        a, b = path[i], path[(i + 1) % len(path)]
        out.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
    return out, total


def _chain_y(x):
    """Lateral position: chainring plane at the front, cog plane at the back."""
    y_cog = S.cog_y(S.CHAIN_ON)
    xr = S.REAR_AXLE.x + 0.07
    if x <= xr:
        return y_cog
    t = min(1.0, (x - xr) / (S.BB.x - xr))
    return y_cog + (S.CHAINLINE_Y - y_cog) * t


# --------------------------------------------------------------------------------------- chain
# KMC X12 (silver, nickel plated): figure-8 plates with chamfered outer edges, rollers, peened pins,
# one MissingLink-12 on the lower run.

def _link_outline(length, r_end, waist, n_end=8):
    out = [(-length / 2 + r_end * math.cos(t), r_end * math.sin(t))
           for t in (math.pi / 2 + math.pi * i / n_end for i in range(n_end + 1))]
    out.append((0.0, -waist))
    out += [(length / 2 + r_end * math.cos(t), r_end * math.sin(t))
            for t in (-math.pi / 2 + math.pi * i / n_end for i in range(n_end + 1))]
    out.append((0.0, waist))
    return out


def _chain_plate(part, outline, inset, mid, u, v, y_in, y_out, mat):
    """Plate between lateral y_in (inner face) and y_out (outer face); the outer edge is chamfered."""
    ch = (y_out - y_in) * 0.45

    def ring(pts, y):
        return [Vector((mid.x, 0.0, mid.z)) + u * a + v * b + Y * y for a, b in pts]
    mk.add_rings(part, [ring(outline, y_in), ring(outline, y_out - ch), ring(inset, y_out)], mat, smooth=False)


def build_chain(coll):
    part = Part("chain", "Drivetrain")
    steel, silver, dark = M.get("steel"), M.get("alu_silver"), M.get("grey_plastic")
    path = chain_path()
    total = sum(math.dist(path[i], path[(i + 1) % len(path)]) for i in range(len(path)))
    n_links = int(round(total / S.CHAIN_PITCH / 2)) * 2
    pins, _ = _resample_closed(path, n_links)
    # MissingLink: an outer link on the lower run, halfway between the derailleur and the chainring
    low_run = [k for k in range(1, n_links, 2) if pins[k][1] < S.BB.z - 0.02]
    x_mid = (S.RD_LOWER_PULLEY[0] + S.REAR_AXLE.x + S.BB.x) / 2
    quick = min(low_run, key=lambda k: abs(pins[k][0] - x_mid)) if low_run else -1
    n_end = max(4, S.seg("chain", 8))
    for k in range(n_links):
        a, b = pins[k], pins[(k + 1) % n_links]
        pa = Vector((a[0], _chain_y(a[0]), a[1]))
        pb = Vector((b[0], _chain_y(b[0]), b[1]))
        mid, d = pa.lerp(pb, 0.5), (pb - pa)
        length = d.length
        u = Vector((d.x, 0.0, d.z)).normalized()
        v = Vector((-u.z, 0.0, u.x))
        if k % 2 == 0:
            r_end, waist, y0, y1, mat = 0.00375, 0.00295, 0.00110, 0.00190, steel     # inner link
        elif k == quick:
            r_end, waist, y0, y1, mat = 0.00365, 0.00330, 0.00195, 0.00265, silver    # MissingLink-12
        else:
            r_end, waist, y0, y1, mat = 0.00360, 0.00275, 0.00195, 0.00265, silver    # outer link
        outline = _link_outline(length, r_end, waist, n_end)
        sx = 1.0 - 0.00028 / (length / 2 + r_end)
        sy = 1.0 - 0.00028 / r_end
        inset = [(p[0] * sx, p[1] * sy) for p in outline]
        for s in (-1.0, 1.0):
            _chain_plate(part, outline, inset, mid, u, v, mid.y + s * y0, mid.y + s * y1, mat)
        # roller on the bushing between the inner plates, pin through everything with peened heads
        mk.cyl(part, pa - Y * 0.00108, pa + Y * 0.00108, 0.00385, dark, n=12)
        mk.cyl(part, pa - Y * 0.00265, pa + Y * 0.00265, 0.00180, steel, n=10, caps=False)
        r_head = 0.0021 if k in (quick, (quick + 1) % n_links) else 0.0019
        for s in (-1.0, 1.0):
            mk.cyl(part, pa + Y * (s * 0.00265), pa + Y * (s * 0.00290), r_head, steel, r2=r_head * 0.7, n=10)
    return part.finish(coll)


# ------------------------------------------------------------------------------- derailleur
# RD-M6100-SGS, traced on SCOTT's studio photo (chain on the 10T cog). Points in mm from the rear axle
# (x forward, z up): B-axle (silver cap) at RD_MOUNT_BOLT, clutch housing around RD_CLUTCH, pulleys at
# RD_UPPER/LOWER_PULLEY. Shapes from Shimano's product photos.

RD_BRACKET_END = (-57.0, -21.0)          # end of the bracket arm, where the shift housing goes in
RD_BODY = [(-48, -46), (-34, -41), (-14, -43), (-4, -52), (22, -62), (32, -72), (30, -90), (14, -96), (-12, -88),
           (-30, -78), (-46, -62)]
RD_HOUSING = [(11, -89), (40, -90), (49, -108), (47, -128), (36, -137), (14, -131), (9, -110)]
RD_GUARD = [(-40, -168), (-62, -170), (-84, -175), (-85, -186), (-81, -204), (-71, -216), (-54, -222),
            (-36, -219), (-22, -209), (-15, -195), (-18, -178)]
RD_CAGE_TOP = (24.0, -128.0)             # top of the outer cage arm, under the clutch housing
Y_BODY_FACE = -0.0991                    # outer face of the body (centre -0.0905, half thickness 6 mm, bevel)
Y_HOUSING_FACE = -0.0988                 # outer face of the clutch housing


def _rd_text(part, text, centre_mm, angle_deg, height_mm, length_mm, y, mat, font):
    probe = mk._text_mesh(text, 1.0, 0.0, FONTS + font)
    xs = [v.co.x for v in probe.vertices]
    ys = [v.co.y for v in probe.vertices]
    bpy.data.meshes.remove(probe)
    sx, sy = length_mm * MM / (max(xs) - min(xs)), height_mm * MM / (max(ys) - min(ys))
    a = math.radians(angle_deg)
    du, dv = Vector((math.cos(a), 0.0, math.sin(a))), Vector((-math.sin(a), 0.0, math.cos(a)))
    c = _ax(centre_mm[0], centre_mm[1], y)
    mk.add_text(part, text, 1.0, 0.0, mat, lambda v: c + du * (v.x * sx) + dv * (v.y * sy), FONTS + font)


def _outer_cage_outline():
    cx, cz = RD_CAGE_TOP
    d = Vector((-56.0, -48.0)).normalized()
    n = Vector((-d.y, d.x))                     # across the arm (points down-right)
    hw = 8.5
    L0 = Vector((cx, cz)) - n * hw
    R0 = Vector((cx, cz)) + n * hw
    a_r, a_l = math.atan2(n.y, n.x), math.atan2(-n.y, -n.x)
    if a_l < a_r:
        a_l += 2 * math.pi
    top_arc = [(cx + hw * math.cos(a_r + (a_l - a_r) * k / 8), cz + hw * math.sin(a_r + (a_l - a_r) * k / 8))
               for k in range(9)]
    pts = [tuple(L0), tuple(L0 + d * 75.0)] + RD_GUARD[1:-1] + [tuple(R0 + d * 63.0), tuple(R0)] + top_arc[1:-1]
    return mk.rounded_poly(pts, 3.0, n=3), d


def build_derailleur(coll):
    part = Part("derailleur", "Drivetrain")
    grey, black, steel = M.get("deore_grey"), M.get("black_anodised"), M.get("steel")
    gloss, matte = M.get("black_gloss"), M.get("black_matte")
    up, low = _pulley_centers()
    y = S.cog_y(S.CHAIN_ON)
    bx, bz = S.RD_MOUNT_BOLT[0] / MM, S.RD_MOUNT_BOLT[1] / MM
    px, pz = S.RD_CLUTCH[0] / MM, S.RD_CLUTCH[1] / MM

    # B-knuckle on the hanger: dark grey drum, silver B-axle cap with hex socket standing out of the body
    mk.cyl(part, _ax(bx, bz, -0.0770), _ax(bx, bz, -0.0935), 0.0110, grey, n=40)
    mk.cyl(part, _ax(bx, bz, -0.0960), _ax(bx, bz, Y_BODY_FACE - 0.0012), 0.0085, steel, r2=0.0080, n=40)
    hexs = mk.scratch()
    mk.cyl(hexs, _ax(bx, bz, Y_BODY_FACE - 0.0006), _ax(bx, bz, Y_BODY_FACE - 0.0013), 0.0030, None, n=6)
    part.add_bm(hexs.bm, matte, smooth=False)
    # bracket arm out to the cable stop
    ex, ez = RD_BRACKET_END
    _axle_plate(part, mk.hull2d(mk.circle_pts(bx, bz, 8.0, 24) + mk.circle_pts(ex, ez, 6.0, 20)), -0.0870, 0.0075,
                grey, holes_mm=[mk.circle_pts(ex, ez, 2.6, 14)], bevel=0.0012, bevel_res=1)
    mk.cyl(part, _ax(ex, ez, -0.0830), _ax(ex, ez, -0.0912), 0.0030, steel, n=14)            # housing ferrule
    # B-tension screw
    mk.cyl(part, _ax(bx + 12, bz + 8, -0.0840), _ax(bx + 12, bz + 2, -0.0840), 0.0018, steel, n=8)

    # main body (base member + parallelogram cover), DEORE on its outer face
    _axle_plate(part, mk.rounded_poly(RD_BODY, 4.5, n=4), -0.0905, 0.0120, grey, bevel=0.0024, bevel_res=2)
    # raised, slanted parallelogram cover carrying the DEORE logo (traced: -17..24 mm, sloping down to the front)
    _axle_plate(part, mk.rounded_poly([(-18, -58), (22, -66), (25, -84), (-15, -76)], 2.5, n=3),
                Y_BODY_FACE - 0.0006, 0.0020, grey, bevel=0.0007, bevel_res=1)
    _rd_text(part, "DEORE", (4.0, -71.5), -11.5, 5.4, 27.0, Y_BODY_FACE - 0.0024, M.get("deore_logo"), "FRAHVIT.TTF")
    # inner link plate behind the body
    _axle_plate(part, mk.rounded_poly([(-30, -50), (20, -70), (28, -92), (-20, -78)], 4.0, n=3), -0.0790, 0.0040,
                black, bevel=0.0008)
    # limit screws (H / L) and the cable anchor bolt with its washer
    for sx_, sz_ in ((-49.0, -53.0), (-45.0, -65.0)):
        mk.cyl(part, _ax(sx_ + 6, sz_ + 3, -0.0900), _ax(sx_, sz_, -0.0900), 0.0019, steel, n=10)
        mk.cyl(part, _ax(sx_, sz_, -0.0900), _ax(sx_ - 1.2, sz_ - 0.6, -0.0900), 0.0024, steel, n=10)
    mk.cyl(part, _ax(-38.0, -52.0, Y_BODY_FACE + 0.0004), _ax(-38.0, -52.0, Y_BODY_FACE - 0.0006), 0.0034, steel, n=16)
    mk.cyl(part, _ax(-38.0, -52.0, Y_BODY_FACE - 0.0006), _ax(-38.0, -52.0, Y_BODY_FACE - 0.0022), 0.0024, steel, n=6)

    # P-knuckle: Shadow RD+ clutch housing with the SHIMANO cap and the ON/OFF lever
    _axle_plate(part, mk.rounded_poly(RD_HOUSING, 7.0, n=4), -0.0885, 0.0150, black, bevel=0.0028, bevel_res=2)
    cap_c = (31.0, -117.5)
    mk.cyl(part, _ax(*cap_c, Y_HOUSING_FACE + 0.0010), _ax(*cap_c, Y_HOUSING_FACE - 0.0005), 0.0115, gloss,
           r2=0.0110, n=40)
    _rd_text(part, "SHIMANO", cap_c, 8.0, 2.4, 15.0, Y_HOUSING_FACE - 0.0007, M.get("tyre_text"), "arialbd.ttf")
    mk.cyl(part, _ax(px - 4, pz + 8, Y_HOUSING_FACE + 0.0010), _ax(px - 4, pz + 8, Y_HOUSING_FACE - 0.0004), 0.0072,
           gloss, n=32)
    lever = mk.scratch()
    mk.box(lever, _ax(31.0, -88.0, -0.0905), (0.016, 0.006, 0.0045), None, rot=mk.rot_y(math.radians(-6)))
    part.add_bm(mk.subdivided(lever, 1), black)
    for sx_, sz_ in ((13.0, -127.0), (45.0, -124.0), (44.0, -96.0)):
        mk.cyl(part, _ax(sx_, sz_, Y_HOUSING_FACE + 0.0008), _ax(sx_, sz_, Y_HOUSING_FACE - 0.0006), 0.0023, matte, n=6)

    # outer cage plate: arm with slot windows, guard around the lower pulley with round cut-outs
    outline, d = _outer_cage_outline()
    holes = []
    cx, cz = RD_CAGE_TOP
    for t in (22.0, 37.0, 52.0):
        c = Vector((cx, cz)) + d * t
        holes.append(mk.capsule_outline(tuple(c - d * 3.8), tuple(c + d * 3.8), 1.9, n=6))
    lx, lz = S.RD_LOWER_PULLEY[0] / MM, S.RD_LOWER_PULLEY[1] / MM
    for a0, a1 in ((150, 210), (230, 300), (320, 390)):
        arc_o = [(lx + 20.0 * math.cos(math.radians(a0 + (a1 - a0) * k / 8)),
                  lz + 20.0 * math.sin(math.radians(a0 + (a1 - a0) * k / 8))) for k in range(9)]
        arc_i = [(lx + 9.5 * math.cos(math.radians(a1 - (a1 - a0) * k / 4)),
                  lz + 9.5 * math.sin(math.radians(a1 - (a1 - a0) * k / 4))) for k in range(5)]
        holes.append(mk.rounded_poly(arc_o + arc_i, 2.0, n=2))
    _axle_plate(part, outline, y - 0.0063, 0.0022, black, holes_mm=holes, bevel=0.0005, bevel_res=1)
    # inner cage plate (around both pulleys) with two windows
    ux, uz = S.RD_UPPER_PULLEY[0] / MM, S.RD_UPPER_PULLEY[1] / MM
    inner_out = mk.hull2d(mk.circle_pts(ux, uz, 17.0, 24) + mk.circle_pts(lx, lz, 19.0, 24))
    dm = Vector((lx - ux, lz - uz))
    nm = Vector((-dm.y, dm.x)).normalized()
    win = []
    for t in (0.38, 0.62):
        c = Vector((ux, uz)) + dm * t
        win.append(mk.rounded_poly([tuple(c + nm * 7 - dm.normalized() * 6), tuple(c + nm * 7 + dm.normalized() * 6),
                                    tuple(c - nm * 7)], 2.0, n=3))
    _axle_plate(part, inner_out, y + 0.0042, 0.0016, black, holes_mm=win, bevel=0.0003, bevel_res=0)

    # 13T pulleys: narrow teeth, six windows, black hub, steel bolts through the cage
    for centre in (up, low):
        holes = [mk.circle_pts(0.0145 * math.cos(2 * math.pi * k / 6), 0.0145 * math.sin(2 * math.pi * k / 6), 0.0034, 14)
                 for k in range(6)]
        pulley = mk.plate2d(mk.sprocket_outline(S.PULLEY_T, roller_r=0.0038, tip_h=0.0034, pts_per_tooth=12),
                            holes=holes, thickness=0.0042, bevel=0.0004, bevel_res=1)
        mk.in_bike_plane(pulley, Vector((centre.x, 0.0, centre.z)), y=y)
        part.add_bm(pulley, gloss)
        mk.cyl(part, Vector((centre.x, y + 0.0030, centre.z)), Vector((centre.x, y - 0.0030, centre.z)), 0.0085, black, n=24)
        mk.cyl(part, Vector((centre.x, y + 0.0052, centre.z)), Vector((centre.x, y - 0.0078, centre.z)), 0.0030, steel, n=12)
        mk.cyl(part, Vector((centre.x, y - 0.0074, centre.z)), Vector((centre.x, y - 0.0086, centre.z)), 0.0050, steel,
               r2=0.0046, n=20)
    return part.finish(coll, sharp_angle=40.0)


# ----------------------------------------------------------------------------------- pedals

def build_pedals(coll):
    """Toni's pedals: silver two-sided aluminium trekking pedals (Wellgo B087-like; exact model to come):
    box frame with an open centre, axle body across the middle, small pins on both faces, amber reflectors
    in the front and back walls, black dust cap."""
    part = Part("pedals", "Drivetrain")
    silver, black, steel, refl = M.get("alu_silver"), M.get("black_anodised"), M.get("steel"), M.get("reflector")
    L, W, T = 0.090, 0.098, 0.020                                   # fore-aft, across, thickness
    wall = 0.0075
    for p, side in zip(pedal_points(), (-1.0, 1.0)):
        mk.cyl(part, p, p + Y * (side * 0.020), 0.0065, black, n=20)                        # spindle
        centre = p + Y * (side * 0.063)
        # open box frame: four walls, so you can see through between the axle body and the ribs
        for sx_ in (-1.0, 1.0):                                                               # front / back walls
            mk.box(part, centre + X * (sx_ * (L / 2 - wall / 2)), (wall, W, T), silver)
        for sy_ in (-1.0, 1.0):                                                               # side walls
            mk.box(part, centre + Y * (sy_ * (W / 2 - 0.004)), (L - 2 * wall + 0.002, 0.008, T * 0.85), silver)
        a, b = centre - Y * (side * (W / 2 - 0.004)), centre + Y * (side * (W / 2 - 0.004))
        mk.cyl(part, a, b, 0.0085, silver, n=32)                                             # axle body
        mk.cyl(part, b, b + Y * (side * 0.0045), 0.0080, black, r2=0.0074, n=24)            # dust cap
        for sx_ in (-0.022, 0.022):                                                           # thin cross ribs
            mk.box(part, centre + X * sx_, (0.0030, W - 0.010, T * 0.45), silver)
        for sx_ in (-(L / 2 - wall / 2), L / 2 - wall / 2):                                  # pins, both faces
            for sy_ in (-0.033, -0.011, 0.011, 0.033):
                for sz in (-1.0, 1.0):
                    q = centre + X * sx_ + Y * sy_ + Z * (sz * T / 2)
                    mk.cyl(part, q, q + Z * (sz * 0.0028), 0.0013, steel, n=8)
        for sx_ in (-1.0, 1.0):                                                               # amber reflectors
            r = mk.plate2d(mk.rounded_rect(0.0, 0.0, 0.050, 0.010, 0.002), thickness=0.0016)
            mk.place(r, centre + X * (sx_ * (L / 2 + 0.0006)), Y, Z, X * sx_)
            part.add_bm(r, refl)
    return part.finish(coll, pivot=S.BB, sharp_angle=50.0)
