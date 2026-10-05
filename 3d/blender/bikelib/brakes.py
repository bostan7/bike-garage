"""Shimano MT200 brakes (levers, hoses, calipers) and SM-RT10 Center Lock rotors (180 / 160 mm).

Shapes from Shimano's product photos (photos/online-reference/cockpit-brakes/): BL-MT200 = master cylinder
running along the bar with SHIMANO on it, hinged clamp, long curved two-finger blade with a hooked tip;
BR-MT200 = rounded two-piece caliper with SHIMANO on the outer half, bleed nipple and banjo on top;
SM-RT10 = steel disc with swept arms and two rows of holes on a black 6-arm aluminium Center Lock spider."""
import math

import bpy
from mathutils import Vector

from . import cockpit as C
from . import materials as M
from . import meshkit as mk
from . import spec as S
from .meshkit import Part, X, Y, Z

FONTS = "C:/Windows/Fonts/"
LEVER_ANGLE = 25.0          # blade tilted down from horizontal (deg)


def _flat_text(part, text, origin, along, up, length, mat, font="arialbd.ttf"):
    """Flat text: along = reading direction, up = letter up. along x up points at the viewer."""
    probe = mk._text_mesh(text, 1.0, 0.0, FONTS + font)
    xs = [v.co.x for v in probe.vertices]
    bpy.data.meshes.remove(probe)
    sx = length / (max(xs) - min(xs))
    mk.add_text(part, text, 1.0, 0.0, mat, lambda v: origin + along * (v.x * sx) + up * (v.y * sx), FONTS + font)


def _lever(part, side):
    """BL-MT200 on the bar: side +1 = left (front brake), -1 = right (rear brake).
    Returns the point where the hose leaves the lever."""
    black, gloss, steel = M.get("black_anodised"), M.get("black_gloss"), M.get("steel")
    y = side * (S.BAR_HALF - S.GRIP_LEN - 0.012)
    p = C.bar_point(y)
    axis = C.bar_dir(y)                                     # along the bar, outwards
    fwd = (X - axis * X.dot(axis)).normalized()
    a = math.radians(LEVER_ANGLE)
    f_t = (fwd * math.cos(a) - Z * math.sin(a)).normalized()   # forward, tilted down like the blade
    d_t = axis.cross(f_t).normalized()
    if d_t.z > 0:
        d_t = -d_t                                          # 'down' across the blade
    # hinged clamp around the bar with its bolt underneath
    mk.cyl(part, p - axis * 0.002, p + axis * 0.010, 0.0156, black, n=32)
    mk.cyl(part, p + axis * 0.004 + Z * -0.0175 + fwd * -0.004, p + axis * 0.004 + Z * -0.0175 + fwd * 0.008,
           0.0030, steel, n=10)
    # master cylinder body along the bar, in front of it; integrated reservoir bulge near the clamp
    body_c = p + fwd * 0.019 + Z * 0.004 - axis * 0.024
    cage = mk.scratch()
    mk.box(cage, body_c, (0.070, 0.021, 0.019), None, rot=mk.basis(axis, Z))
    mk.box(cage, p + fwd * 0.010 + Z * 0.004 + axis * 0.002, (0.016, 0.022, 0.020), None, rot=mk.basis(axis, Z))
    mk.box(cage, body_c + axis * 0.012 + Z * 0.004, (0.026, 0.016, 0.012), None, rot=mk.basis(axis, Z))
    part.add_bm(mk.subdivided(cage, 2), black)
    # SHIMANO on top of the body, readable from the saddle (letters point forward)
    _flat_text(part, "SHIMANO", body_c + Z * 0.0104 - axis * 0.004, -axis if side > 0 else axis, fwd, 0.026,
               M.get("tyre_text"))
    # hose fitting at the inboard end
    hose_end = body_c - axis * 0.034
    mk.cyl(part, body_c - axis * 0.030, hose_end, 0.0060, black, r2=0.0050, n=20)
    mk.cyl(part, hose_end, hose_end - axis * 0.006, 0.0042, steel, n=16)
    # pivot pin and reach screw
    pivot = p + fwd * 0.028 + Z * 0.001 + axis * 0.006
    mk.cyl(part, pivot - Z * 0.0075, pivot + Z * 0.0075, 0.0034, steel, n=12)
    mk.cyl(part, pivot + Z * 0.0075, pivot + Z * 0.0088, 0.0048, gloss, n=16)
    # blade: forward from the pivot, along the grip, hooked tip
    ctrl = [pivot, pivot + axis * 0.006 + f_t * 0.012, pivot + axis * 0.022 + f_t * 0.017 + d_t * 0.004,
            pivot + axis * 0.052 + f_t * 0.018 + d_t * 0.008, pivot + axis * 0.080 + f_t * 0.016 + d_t * 0.010,
            pivot + axis * 0.094 + f_t * 0.010 + d_t * 0.015]
    pts = mk.catmull_rom(ctrl, 6)
    # flat blade: ~11 mm tall (across d_t), ~5 mm thick (front-back)
    prof = [mk.interp_keys([(0.0, (0.0068, 0.0040)), (0.3, (0.0058, 0.0026)), (0.85, (0.0052, 0.0024)),
                            (1.0, (0.0046, 0.0026))], i / (len(pts) - 1)) for i in range(len(pts))]
    shape = mk.scratch()
    mk.tube_path(shape, pts, prof, None, n=12, ref=d_t, power=3.0)
    part.add_bm(mk.subdivided(shape, 1), black)
    return hose_end - axis * 0.006


def _caliper(part, axle, rotor_r, rotor_y, angle_deg):
    """BR-MT200 post-mount 2-piston caliper straddling the rotor at angle (0 = forward, 90 = up),
    on an adapter plate with four bolts. Outer face is +Y (the rotors are on the left side)."""
    a = math.radians(angle_deg)
    er = Vector((math.cos(a), 0.0, math.sin(a)))
    tang = Vector((-math.sin(a), 0.0, math.cos(a)))
    centre = axle + er * (rotor_r - 0.0085) + Y * rotor_y
    black, gloss, steel = M.get("black_anodised"), M.get("black_gloss"), M.get("steel")

    def plate(outline_mm, y_off, thick, bevel, mat):
        bm = mk.plate2d([(u * 0.001, v * 0.001) for u, v in outline_mm], thickness=thick, bevel=bevel, bevel_res=2)
        mk.place(bm, centre + Y * y_off, tang, er, -Y)
        part.add_bm(bm, mat)

    body = mk.rounded_poly([(-29, -14), (29, -14), (33, -3), (29, 9), (12, 15), (-12, 15), (-29, 9), (-33, -3)], 6.0, n=4)
    plate(body, 0.0100, 0.0100, 0.0035, gloss)                         # outer half (rounded, deep)
    plate(body, -0.0090, 0.0070, 0.0026, gloss)                        # inner half
    plate(mk.rounded_poly([(-27, 8), (27, 8), (24, 17), (-24, 17)], 4.0, n=3), 0.0005, 0.0250, 0.0028, gloss)  # bridge
    # mounting ears on the radially outer edge (post mount: bolts run in the rotor plane, through the ears
    # into the adapter, which sits further out and bolts to the frame / fork posts)
    for dt in (-0.026, 0.026):
        ear = centre + tang * dt + er * 0.0175 + Y * 0.0020
        mk.box(part, ear, (0.012, 0.0160, 0.006), gloss, rot=mk.basis(tang, er))
    # piston boss on the outer face with SHIMANO below it (readable from the left side of the bike)
    boss = centre + Y * 0.0165 + er * -0.001
    mk.cyl(part, boss - Y * 0.003, boss + Y * 0.0035, 0.0128, gloss, r2=0.0112, n=48)
    mk.cyl(part, boss + Y * 0.0035, boss + Y * 0.0040, 0.0105, gloss, r2=0.0080, n=48)
    along, up = (er, -tang) if er.x < 0 else (tang, er)
    _flat_text(part, "SHIMANO", centre + Y * 0.0206 + er * -0.0112 - along * 0.010, along, up, 0.020,
               M.get("tyre_text"))
    # adapter block (post mount +20 front / +0 style rear) radially outside the ears, four radial bolts
    adapter = mk.plate2d(mk.rounded_poly([(-0.036, 0.0), (0.036, 0.0), (0.040, 0.012), (-0.040, 0.012)], 0.003, n=3),
                         thickness=0.0120, bevel=0.0010)
    mk.place(adapter, centre + er * 0.0215 + Y * 0.0030, tang, er, -Y)
    part.add_bm(adapter, black)
    for dt in (-0.026, 0.026):                                         # caliper bolts (heads under the ears)
        q = centre + tang * dt + er * 0.0145 + Y * 0.0020
        mk.cyl(part, q, q + er * 0.020, 0.0026, steel, n=12)
        mk.cyl(part, q, q - er * 0.0040, 0.0042, steel, n=6)
    for dt in (-0.034, 0.034):                                         # adapter-to-mount bolts (heads on top)
        q = centre + tang * dt + er * 0.0335 + Y * 0.0030
        mk.cyl(part, q, q + er * 0.0040, 0.0042, steel, n=6)
    # banjo fitting (hose in) and bleed nipple with its cap, on top
    top = centre + er * 0.0150 + Y * 0.0040 + tang * 0.013
    mk.cyl(part, top, top + er * 0.0080, 0.0055, gloss, n=20)
    mk.cyl(part, top + er * 0.0080, top + er * 0.0095, 0.0040, steel, n=6)
    bleed = centre + er * 0.0160 + Y * 0.0060 - tang * 0.010
    mk.cyl(part, bleed, bleed + er * 0.0060, 0.0025, steel, n=10)
    mk.cyl(part, bleed + er * 0.0060, bleed + er * 0.0090, 0.0033, M.get("grey_plastic"), n=12)
    return top + er * 0.0095


def build_brake(coll, front):
    name = "brake_front" if front else "brake_rear"
    part = Part(name, "Brakes")
    hose = M.get("black_gloss")
    lever = _lever(part, 1.0 if front else -1.0)
    if front:
        cal = _caliper(part, S.FRONT_AXLE, S.FRONT_ROTOR_R, S.FRONT_ROTOR_Y, 152.0)
        leg = S.FRONT_AXLE + Y * (S.FORK_LEG_Y + 0.006)
        ctrl = [lever, lever + X * 0.05 + Z * -0.03 + Y * -0.02,
                S.on_axis(40) + S.AXIS_FWD * 0.09 + Y * 0.07,
                leg + S.AXIS_UP * 0.30 - S.AXIS_FWD * 0.022,
                leg + S.AXIS_UP * 0.24 - S.AXIS_FWD * 0.020,
                leg + S.AXIS_UP * 0.12 - S.AXIS_FWD * 0.028,
                cal + Z * 0.012, cal]
    else:
        cal = _caliper(part, S.REAR_AXLE, S.REAR_ROTOR_R, S.REAR_ROTOR_Y, 32.0)
        port = S.on_axis(S.DT_AT_HT) + (S.BB - S.on_axis(S.DT_AT_HT)).normalized() * 0.10 + Y * 0.031
        ctrl = [lever, lever + X * 0.06 + Z * -0.02 + Y * 0.02,
                S.on_axis(10) + S.AXIS_FWD * 0.10 + Y * 0.02,
                port + Y * 0.02 + Z * 0.03, port]
        cs_exit = S.P(S.REAR_X + 110, S.BB_DROP - 4, 72)
        mk.curve_tube(part, [cs_exit, cs_exit + X * -0.025 + Z * 0.012, cal + X * 0.012 + Z * 0.010, cal],
                      0.0025, hose, samples=8, n=12)
    mk.curve_tube(part, ctrl, 0.0025, hose, samples=12, n=12)
    return part.finish(coll, sharp_angle=50.0)


def build_rotor(coll, front):
    """SM-RT10: steel braking track with two staggered rows of holes and swept arms,
    riveted to a black 6-arm aluminium Center Lock spider."""
    name = "rotor_front" if front else "rotor_rear"
    axle = S.FRONT_AXLE if front else S.REAR_AXLE
    r_out = S.FRONT_ROTOR_R if front else S.REAR_ROTOR_R
    y = S.FRONT_ROTOR_Y if front else S.REAR_ROTOR_Y
    part = Part(name, "Brakes")
    disc, steel, black = M.get("alu_silver"), M.get("steel"), M.get("black_anodised")
    r_in = r_out - 0.0160
    n_edge = S.seg(name, 192)
    outer = []
    for k in range(n_edge):
        a = 2 * math.pi * k / n_edge
        r = r_out - 0.0010 * (0.5 + 0.5 * math.cos(a * 12))       # gently scalloped edge
        outer.append((r * math.cos(a), r * math.sin(a)))
    holes = [mk.circle_pts(0, 0, r_in, n_edge)]
    n_holes = 30 if front else 26
    for row, rr in ((0, r_out - 0.0048), (1, r_out - 0.0110)):
        for k in range(n_holes):
            a = 2 * math.pi * (k + 0.5 * row) / n_holes
            holes.append(mk.circle_pts(rr * math.cos(a), rr * math.sin(a), 0.0017, 10))
    track = mk.plate2d(outer, holes=holes, thickness=0.0018)
    mk.in_bike_plane(track, axle, y=y)
    part.add_bm(track, disc, smooth=False)
    # six swept steel arms from the spider's rivets out to the track
    r_rivet = 0.0365

    def edge(p, s):
        t = math.atan2(p[1], p[0]) + 0.6
        return (p[0] - s * 0.0040 * math.sin(t), p[1] + s * 0.0040 * math.cos(t))
    for k in range(6):
        a0 = 2 * math.pi * k / 6
        pts = []
        for j in range(9):
            t = j / 8
            pts.append(((r_rivet + t * (r_in + 0.0012 - r_rivet)) * math.cos(a0 + 0.42 * t),
                        (r_rivet + t * (r_in + 0.0012 - r_rivet)) * math.sin(a0 + 0.42 * t)))
        arm = mk.plate2d([edge(p, 1.0) for p in pts] + [edge(p, -1.0) for p in pts[::-1]], thickness=0.0018)
        mk.in_bike_plane(arm, axle, y=y)
        part.add_bm(arm, disc, smooth=False)
        tab = mk.plate2d(mk.circle_pts(r_rivet * math.cos(a0), r_rivet * math.sin(a0), 0.0052, 20), thickness=0.0018)
        mk.in_bike_plane(tab, axle, y=y)
        part.add_bm(tab, disc, smooth=False)
    # black 6-arm spider (Center Lock) on the outer face, rivet heads at the arm tips
    for k in range(6):
        a0 = 2 * math.pi * k / 6
        tip = (r_rivet * math.cos(a0), r_rivet * math.sin(a0))
        sp_arm = mk.plate2d(mk.hull2d(mk.circle_pts(0.0285 * math.cos(a0), 0.0285 * math.sin(a0), 0.0062, 16)
                                      + mk.circle_pts(tip[0], tip[1], 0.0052, 16)),
                            thickness=0.0030, bevel=0.0004, bevel_res=1)
        mk.in_bike_plane(sp_arm, axle, y=y + 0.0024)
        part.add_bm(sp_arm, black)
        q = axle + Vector((tip[0], y + 0.0041, tip[1]))
        mk.cyl(part, q, q + Y * 0.0012, 0.0028, steel, r2=0.0022, n=14)
    carrier = mk.plate2d(mk.circle_pts(0, 0, 0.0320, 64), holes=[mk.circle_pts(0, 0, 0.0185, 64)], thickness=0.0030,
                         bevel=0.0004)
    mk.in_bike_plane(carrier, axle, y=y + 0.0024)
    part.add_bm(carrier, black)
    lock = [(((0.0200 if k % 2 else 0.0192) * math.cos(2 * math.pi * k / 40)),
             ((0.0200 if k % 2 else 0.0192) * math.sin(2 * math.pi * k / 40))) for k in range(40)]
    lr = mk.plate2d(lock, holes=[mk.circle_pts(0, 0, 0.0125, 24)], thickness=0.0035)
    mk.in_bike_plane(lr, axle, y=y + 0.0045)
    part.add_bm(lr, steel, smooth=False)
    return part.finish(coll, pivot=axle, sharp_angle=50.0)
