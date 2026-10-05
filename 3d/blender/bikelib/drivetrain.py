"""Drivetrain: FC-MT511-1 32T crankset, BB-MT500-PA, KMC X12 chain, CS-M6100-12 10-51T cassette,
RD-M6100-SGS derailleur, Feimin flat pedals."""
import math

import bpy
from mathutils import Vector

from . import materials as M
from . import meshkit as mk
from . import spec as S
from .meshkit import Part, X, Y, Z


def _crank_dir(angle_deg):
    a = math.radians(angle_deg)
    return Vector((math.cos(a), 0.0, math.sin(a)))


def pedal_points():
    d = _crank_dir(S.CRANK_ANGLE)
    return (S.BB + d * S.CRANK_LEN - Y * S.Q_HALF, S.BB - d * S.CRANK_LEN + Y * S.Q_HALF)


ARM_KEYS = [(0.0, (0.0095, 0.0235)), (0.18, (0.0088, 0.0180)), (0.65, (0.0080, 0.0145)), (1.0, (0.0078, 0.0132))]


def _text_on_arm(part, a, b, side, text, height, length, mat):
    """Lettering on the outer face of a crank arm (side -1 drive, +1 left), following its slant and taper."""
    probe = mk._text_mesh(text, 1.0, 0.0)
    xs = [v.co.x for v in probe.vertices]
    bpy.data.meshes.remove(probe)
    sx = length / (max(xs) - min(xs))
    arm_len = (b - a).length
    d = Vector((b.x - a.x, 0.0, b.z - a.z)).normalized()
    up = Vector((-d.z, 0.0, d.x))
    flip = -1.0 if side > 0 else 1.0           # keep the text readable from each side

    def xform(v):
        s = 0.55 + flip * (v.x * sx) / arm_len
        w = mk.interp_keys(ARM_KEYS, s)[0]
        c = a.lerp(b, s)
        return Vector((c.x, c.y + side * (w + 0.0004), c.z)) + up * (v.y * sx)
    mk.add_text(part, text, 1.0, 0.0, mat, xform)


# --------------------------------------------------------------------------------- crankset

def build_crankset(coll):
    part = Part("crankset", "Drivetrain")
    black, steel, gloss = M.get("black_anodised"), M.get("steel"), M.get("black_gloss")
    mk.cyl(part, S.BB + Y * 0.068, S.BB - Y * 0.068, 0.0120, black, n=32)                 # 24 mm spindle
    d = _crank_dir(S.CRANK_ANGLE)
    for side, direction in ((-1.0, d), (1.0, -d)):
        a = S.BB + Y * (side * 0.0645)
        b = S.BB + direction * S.CRANK_LEN + Y * (side * (S.Q_HALF - 0.0085))
        mk.tube(part, a, b, ARM_KEYS, black, samples=12, n=28, power=2.8)
        mk.cyl(part, b + Y * (side * -0.0080), b + Y * (side * 0.0085), 0.0132, black, n=32)  # pedal eye
        _text_on_arm(part, a, b, side, "SHIMANO", 0.006, 0.050, M.get("tyre_text"))
        if side > 0:
            # left arm clamp: split boss, two pinch bolts, preload cap
            mk.cyl(part, a + Y * -0.006, a + Y * 0.012, 0.0215, black, n=32)
            back = -direction
            for dz in (-0.006, 0.006):
                p = a + back * 0.019 + Y * (0.003 + dz)
                perp = Vector((-back.z, 0.0, back.x))
                mk.cyl(part, p - perp * 0.010, p + perp * 0.010, 0.0030, steel, n=10)
            mk.cyl(part, a + Y * 0.012, a + Y * 0.0145, 0.0115, gloss, n=24)
        else:
            mk.cyl(part, a + Y * 0.006, a + Y * -0.010, 0.0230, black, n=32)

    # 4-arm spider (96 mm BCD)
    yr = S.CHAINLINE_Y
    bolts = []
    for k in range(4):
        ang = math.radians(S.CRANK_ANGLE + 45 + 90 * k)
        bolts.append((0.048 * math.cos(ang), 0.048 * math.sin(ang)))
    for bx, bz in bolts:
        arm = mk.plate2d(mk.capsule_outline((0.0, 0.0), (bx, bz), 0.0080), thickness=0.0060, bevel=0.0010)
        mk.in_bike_plane(arm, S.BB, y=yr + 0.0045)
        part.add_bm(arm, black)
    hub = mk.plate2d(mk.circle_pts(0, 0, 0.0260, 40), thickness=0.010, bevel=0.0015)
    mk.in_bike_plane(hub, S.BB, y=yr + 0.007)
    part.add_bm(hub, black)

    # 32T narrow-wide chainring with bolt tabs
    inner = []
    for k in range(120):
        phi = 2 * math.pi * k / 120
        bump = 0.0
        for bx, bz in bolts:
            dphi = math.atan2(math.sin(phi - math.atan2(bz, bx)), math.cos(phi - math.atan2(bz, bx)))
            if abs(dphi) < 0.26:
                bump = max(bump, math.cos(math.pi / 2 * dphi / 0.26) ** 2)
        r = 0.0530 - 0.0110 * bump
        inner.append((r * math.cos(phi), r * math.sin(phi)))
    holes = [inner] + [mk.circle_pts(bx, bz, 0.0045, 16) for bx, bz in bolts]
    ring = mk.plate2d(mk.sprocket_outline(S.CHAINRING_T), holes=holes, thickness=0.0022, bevel=0.0003)
    mk.in_bike_plane(ring, S.BB, y=yr)
    part.add_bm(ring, gloss)
    for bx, bz in bolts:
        p = S.BB + Vector((bx, yr, bz))
        mk.cyl(part, p - Y * 0.0045, p - Y * 0.0012, 0.0050, steel, n=16)                 # bolt head
        mk.cyl(part, p + Y * 0.0012, p + Y * 0.0080, 0.0042, steel, n=16)                 # nut
    return part.finish(coll, pivot=S.BB, sharp_angle=50.0)


def build_bottom_bracket(coll):
    part = Part("bottom_bracket", "Drivetrain")
    black = M.get("black_gloss")
    for side in (1.0, -1.0):
        cup = mk.scratch()
        mk.revolve(cup, Vector((0, 0, 0)), [(0.0125, 0.0), (0.0225, 0.0), (0.0225, 0.0020), (0.0205, 0.0042),
                                            (0.0125, 0.0042)], None, n=48)
        bm = cup.bm
        if side < 0:
            bmesh_scale = -1.0
            for v in bm.verts:
                v.co.y = -v.co.y
        mk.place(bm, S.BB + Y * (side * 0.0448), X, Y, Z)
        part.add_bm(bm, black, free=False)
    return part.finish(coll, pivot=S.BB)


# --------------------------------------------------------------------------------- cassette

def build_cassette(coll):
    part = Part("cassette", "Drivetrain")
    silver, black = M.get("alu_silver"), M.get("black_anodised")
    c = S.REAR_AXLE
    for teeth in S.CASSETTE:
        y = S.cog_y(teeth)
        R = S.pitch_r(teeth)
        outline = mk.sprocket_outline(teeth, phase=0.13 * teeth)
        if teeth >= 33:
            holes = [mk.circle_pts(0, 0, R - 0.0120, 96)]
        elif teeth >= 21:
            holes = [mk.circle_pts(0, 0, 0.0175, 32)]
            r0, r1 = 0.0175 + 0.0045, R - 0.0085
            for k in range(6):
                a0 = 2 * math.pi * k / 6 + 0.25
                win = [((r0 + (r1 - r0) * t) * math.cos(a0 + w), (r0 + (r1 - r0) * t) * math.sin(a0 + w))
                       for t, w in ((0, -0.20), (1, -0.32), (1, 0.32), (0, 0.20))]
                holes.append(win)
        else:
            holes = [mk.circle_pts(0, 0, 0.0175, 32)]
        cog = mk.plate2d(outline, holes=holes, thickness=0.0018)
        mk.in_bike_plane(cog, c, y=y)
        part.add_bm(cog, silver, smooth=False)
        if teeth >= 33:      # black aluminium spider carrying the big cogs
            r_band = R - 0.0115
            for k in range(6):
                ang = 2 * math.pi * k / 6 + 0.1 * teeth
                tip = (r_band * math.cos(ang), r_band * math.sin(ang))
                arm = mk.plate2d(mk.capsule_outline((0.0185 * math.cos(ang), 0.0185 * math.sin(ang)), tip, 0.0042),
                                 thickness=0.0016)
                mk.in_bike_plane(arm, c, y=y + 0.0016)
                part.add_bm(arm, black)
            hubring = mk.plate2d(mk.circle_pts(0, 0, 0.0240, 40), holes=[mk.circle_pts(0, 0, 0.0175, 40)],
                                 thickness=0.0016)
            mk.in_bike_plane(hubring, c, y=y + 0.0016)
            part.add_bm(hubring, black)
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


def build_chain(coll):
    part = Part("chain", "Drivetrain")
    steel, dark = M.get("steel"), M.get("grey_plastic")
    path = chain_path()
    total = sum(math.dist(path[i], path[(i + 1) % len(path)]) for i in range(len(path)))
    n_links = int(round(total / S.CHAIN_PITCH / 2)) * 2
    pins, _ = _resample_closed(path, n_links)
    for k in range(n_links):
        a, b = pins[k], pins[(k + 1) % n_links]
        pa = Vector((a[0], _chain_y(a[0]), a[1]))
        pb = Vector((b[0], _chain_y(b[0]), b[1]))
        mid, d = pa.lerp(pb, 0.5), (pb - pa)
        length = d.length
        u = Vector((d.x, 0.0, d.z)).normalized()
        v = Vector((-u.z, 0.0, u.x))
        inner = k % 2 == 0
        half_gap = 0.0021 if inner else 0.0030
        r_end, waist = (0.0042, 0.0031) if inner else (0.0039, 0.0029)
        # figure-8 link plate: round ends with a waist, like a real chain plate
        outline = [(-length / 2 + r_end * math.cos(t), r_end * math.sin(t))
                   for t in (math.pi / 2 + math.pi * i / 6 for i in range(7))]
        outline.append((0.0, -waist))
        outline += [(length / 2 + r_end * math.cos(t), r_end * math.sin(t))
                    for t in (-math.pi / 2 + math.pi * i / 6 for i in range(7))]
        outline.append((0.0, waist))
        for side in (-1.0, 1.0):
            y0 = mid.y + side * half_gap
            mk.prism(part, outline, Vector((mid.x, 0.0, mid.z)), u, v, Y, y0 - 0.0004, y0 + 0.0004,
                     steel if inner else M.get("alu_silver"))
        mk.cyl(part, pa - Y * 0.0026, pa + Y * 0.0026, 0.0030, dark, n=8)
        mk.cyl(part, pa - Y * 0.0039, pa + Y * 0.0039, 0.0013, steel, n=6)                # pin heads
    return part.finish(coll)


# ------------------------------------------------------------------------------- derailleur

def build_derailleur(coll):
    part = Part("derailleur", "Drivetrain")
    grey, black, steel, gloss = M.get("grey_plastic"), M.get("black_anodised"), M.get("steel"), M.get("black_gloss")
    up, low = _pulley_centers()
    y = S.cog_y(S.CHAIN_ON)
    bolt = _rd(S.RD_MOUNT_BOLT)
    clutch = _rd(S.RD_CLUTCH)
    bx, bz, cx, cz = bolt.x, bolt.z, clutch.x, clutch.z

    # B-knuckle on the hanger bolt, with the mounting bolt and B-tension screw
    mk.cyl(part, bolt + Y * -0.077, bolt + Y * -0.093, 0.0115, black, n=32)
    mk.cyl(part, bolt + Y * -0.093, bolt + Y * -0.0955, 0.0055, steel, n=12)
    mk.cyl(part, bolt + Vector((0.004, -0.088, 0.012)), bolt + Vector((0.004, -0.088, 0.019)), 0.0022, steel, n=8)

    # parallelogram: chunky outer body with DEORE, inner link plate
    body = mk.hull2d(mk.circle_pts(bx, bz, 0.0130, 20) + mk.circle_pts(cx, cz, 0.0185, 20)
                     + [(bx + 0.024, bz - 0.018), (cx - 0.030, cz + 0.012)])
    outer = mk.plate2d(body, holes=[], thickness=0.0120, bevel=0.0025)
    mk.place(outer, Vector((0, -0.0905, 0)), X, Z, -Y)
    part.add_bm(outer, grey)
    inner_link = mk.plate2d(mk.hull2d(mk.circle_pts(bx, bz, 0.010, 16) + mk.circle_pts(cx, cz, 0.012, 16)),
                            holes=[mk.rounded_rect((bx + cx) / 2, (bz + cz) / 2, 0.016, 0.010, 0.004)],
                            thickness=0.0040, bevel=0.0008)
    mk.place(inner_link, Vector((0, -0.0765, 0)), X, Z, -Y)
    part.add_bm(inner_link, black)
    mid = Vector(((bx + cx) / 2, -0.0993, (bz + cz) / 2))
    dvec = Vector((cx - bx, 0.0, cz - bz)).normalized()
    up_v = Vector((-dvec.z, 0.0, dvec.x))
    if up_v.z < 0:
        up_v = -up_v
    probe = mk._text_mesh("DEORE", 1.0, 0.0)
    xs = [v.co.x for v in probe.vertices]
    bpy.data.meshes.remove(probe)
    sx = 0.030 / (max(xs) - min(xs))
    mk.add_text(part, "DEORE", 1.0, 0.0, M.get("tyre_text"),
                lambda v: mid + dvec * (v.x * sx) + up_v * (v.y * sx) - Y * 0.0003)

    # P-knuckle with the Shadow RD+ clutch housing and switch
    mk.cyl(part, clutch + Y * (y - 0.008 - clutch.y), clutch + Y * (-0.0985 - clutch.y), 0.0172, black, n=40)
    mk.cyl(part, clutch + Y * (-0.0985 - clutch.y), clutch + Y * (-0.1000 - clutch.y), 0.0130, grey, n=32)
    sw = clutch + Vector((0.008, -0.096 - clutch.y, 0.014))
    mk.box(part, sw, (0.014, 0.004, 0.007), grey, rot=mk.rot_y(math.radians(20)))

    # cage: outer plate with windows, inner plate
    cage = mk.hull2d(mk.circle_pts(cx, cz, 0.0165, 20) + mk.circle_pts(up.x, up.z, 0.0190, 24)
                     + mk.circle_pts(low.x, low.z, 0.0200, 24))
    w1 = mk.rounded_rect((up.x + low.x) / 2, (up.z + low.z) / 2, 0.012, 0.022, 0.004)
    win1 = [((px - (up.x + low.x) / 2) * math.cos(0.42) - (pz - (up.z + low.z) / 2) * math.sin(0.42) + (up.x + low.x) / 2,
             (px - (up.x + low.x) / 2) * math.sin(0.42) + (pz - (up.z + low.z) / 2) * math.cos(0.42) + (up.z + low.z) / 2)
            for px, pz in w1]
    outer_cage = mk.plate2d(cage, holes=[win1], thickness=0.0018, bevel=0.0004)
    mk.place(outer_cage, Vector((0, y - 0.0070, 0)), X, Z, -Y)
    part.add_bm(outer_cage, black)
    inner_cage = mk.plate2d(mk.hull2d(mk.circle_pts(up.x, up.z, 0.0170, 20) + mk.circle_pts(low.x, low.z, 0.0185, 20)),
                            holes=[win1], thickness=0.0014)
    mk.place(inner_cage, Vector((0, y + 0.0055, 0)), X, Z, -Y)
    part.add_bm(inner_cage, black)

    # 13T pulleys with six holes, centre bolts
    for centre in (up, low):
        holes = [mk.circle_pts(0.0145 * math.cos(2 * math.pi * k / 6), 0.0145 * math.sin(2 * math.pi * k / 6), 0.0032, 12)
                 for k in range(6)]
        pulley = mk.plate2d(mk.sprocket_outline(S.PULLEY_T, roller_r=0.0038, tip_h=0.0030), holes=holes,
                            thickness=0.0046, bevel=0.0004)
        mk.in_bike_plane(pulley, Vector((centre.x, 0.0, centre.z)), y=y)
        part.add_bm(pulley, gloss)
        mk.cyl(part, Vector((centre.x, y + 0.0062, centre.z)), Vector((centre.x, y - 0.0085, centre.z)), 0.0055,
               steel, n=16)
    return part.finish(coll, sharp_angle=50.0)


# ----------------------------------------------------------------------------------- pedals

def build_pedals(coll):
    part = Part("pedals", "Drivetrain")
    black, steel, refl = M.get("black_matte"), M.get("steel"), M.get("reflector")
    outline = mk.rounded_rect(0.0, 0.0, 0.096, 0.094, 0.010)
    windows = [mk.rounded_rect(0.0, dy, 0.060, 0.026, 0.006) for dy in (-0.026, 0.026)]
    for p, side in zip(pedal_points(), (-1.0, 1.0)):
        mk.cyl(part, p, p + Y * (side * 0.016), 0.0065, steel, n=16)                        # axle
        centre = p + Y * (side * 0.063)
        body = mk.plate2d(outline, holes=windows, thickness=0.0170, bevel=0.0020)
        mk.place(body, centre, X, Y * side, Z * side)
        part.add_bm(body, black)
        mk.cyl(part, centre - Y * 0.048, centre + Y * 0.048, 0.0105, black, n=24)          # axle housing
        mk.cyl(part, centre + Y * (side * 0.048), centre + Y * (side * 0.052), 0.0080, black, n=16)  # end cap
        for sx_ in (-0.042, 0.042):                                                           # pins
            for sy_ in (-0.034, -0.012, 0.012, 0.034):
                for sz in (-1.0, 1.0):
                    q = centre + X * sx_ + Y * sy_ + Z * (sz * 0.0085)
                    mk.cyl(part, q, q + Z * (sz * 0.0035), 0.0013, steel, n=6)
        for sx_ in (-0.0485, 0.0485):                                                         # reflectors
            r = mk.plate2d(mk.rounded_rect(0.0, 0.0, 0.040, 0.011, 0.002), thickness=0.0016)
            mk.place(r, centre + X * sx_, Y, Z, X * (1.0 if sx_ > 0 else -1.0))
            part.add_bm(r, refl)
    return part.finish(coll, pivot=S.BB, sharp_angle=50.0)
