"""Shimano MT200 brakes (levers, hoses, calipers) and SM-RT10 Center Lock rotors (180 / 160 mm)."""
import math

from mathutils import Vector

from . import cockpit as C
from . import materials as M
from . import meshkit as mk
from . import spec as S
from .meshkit import Part, X, Y, Z


def _lever(part, side):
    """BL-MT200 lever on the bar: side +1 = left (front brake), -1 = right (rear brake)."""
    grey, gloss, black, steel = M.get("grey_plastic"), M.get("black_gloss"), M.get("black_anodised"), M.get("steel")
    y = side * (S.BAR_HALF - S.GRIP_LEN - 0.012)
    p = C.bar_point(y)
    axis = C.bar_dir(y)                       # along the bar, outwards
    # split clamp around the bar with its bolt
    mk.cyl(part, p - axis * 0.009, p + axis * 0.009, 0.0150, black, n=24)
    mk.cyl(part, p + Z * -0.016 + X * -0.004 - axis * 0.004, p + Z * -0.016 + X * -0.004 + axis * 0.004, 0.0040,
           steel, n=10)
    # master cylinder body: subdivided cage running forward from the clamp, reservoir on top
    body_c = p + X * 0.020 + Z * 0.010
    cage = mk.scratch()
    mk.box(cage, body_c, (0.044, 0.022, 0.020), None, rot=mk.basis(X, Z))
    mk.box(cage, p + X * 0.006 + Z * 0.004, (0.016, 0.020, 0.024), None)
    part.add_bm(mk.subdivided(cage, 2), grey)
    res = body_c + Z * 0.0105 + X * -0.004
    mk.cyl(part, res, res + Z * 0.0018, 0.0090, gloss, n=24)                              # reservoir cap
    for dx in (-0.006, 0.006):
        mk.cyl(part, res + X * dx + Z * 0.0018, res + X * dx + Z * 0.0026, 0.0014, steel, n=8)
    # blade: forward from the pivot, then outwards along the grip, with a curved finger hook
    pivot = body_c + X * 0.020 + Z * -0.004
    mk.cyl(part, pivot - axis * 0.010 + Z * 0.0, pivot + axis * 0.010, 0.0038, steel, n=12)
    blade = [pivot, pivot + X * 0.014 + Z * -0.010 + axis * 0.006, pivot + X * 0.018 + Z * -0.016 + axis * 0.030,
             pivot + X * 0.016 + Z * -0.020 + axis * 0.065, pivot + X * 0.010 + Z * -0.021 + axis * 0.090]
    pts = mk.catmull_rom(blade, 6)
    prof = [mk.interp_keys([(0.0, (0.0060, 0.0080)), (0.4, (0.0045, 0.0075)), (1.0, (0.0040, 0.0060))],
                           i / (len(pts) - 1)) for i in range(len(pts))]
    shape = mk.scratch()
    mk.tube_path(shape, pts, prof, None, n=10, power=3.0)
    part.add_bm(mk.subdivided(shape, 1), black)
    return body_c + X * 0.022


def _caliper(part, axle, rotor_r, rotor_y, angle_deg):
    """BR-MT200 post-mount 2-piston caliper straddling the rotor at angle (0 = forward, 90 = up),
    on an adapter plate with four bolts."""
    a = math.radians(angle_deg)
    er = Vector((math.cos(a), 0.0, math.sin(a)))
    tang = Vector((-math.sin(a), 0.0, math.cos(a)))
    centre = axle + er * (rotor_r - 0.0085) + Y * rotor_y
    grey, black, steel = M.get("grey_plastic"), M.get("black_anodised"), M.get("steel")
    rot = mk.basis(tang, er)
    cage = mk.scratch()
    for s in (-1.0, 1.0):                         # two caliper halves either side of the rotor
        mk.box(cage, centre + Y * (s * 0.0105) + er * 0.002, (0.054, 0.014, 0.026), None, rot=rot)
    mk.box(cage, centre + er * 0.0135, (0.054, 0.034, 0.010), None, rot=rot)               # bridge over the rotor
    part.add_bm(mk.subdivided(cage, 2), grey)
    # adapter plate between caliper and frame/fork mounts
    outline = mk.hull2d(mk.circle_pts(-0.030, 0.0, 0.0085, 12) + mk.circle_pts(0.030, 0.0, 0.0085, 12)
                        + mk.circle_pts(-0.036, 0.016, 0.0080, 12) + mk.circle_pts(0.036, 0.016, 0.0080, 12))
    plate = mk.plate2d(outline, thickness=0.0065, bevel=0.0010)
    mk.place(plate, centre + er * 0.016 + Y * 0.0195, tang, er, Y)
    part.add_bm(plate, black)
    for dt, dr in ((-0.030, 0.0), (0.030, 0.0), (-0.036, 0.016), (0.036, 0.016)):
        p = centre + er * (0.016 + dr) + tang * dt + Y * 0.0195
        mk.cyl(part, p + Y * 0.0030, p + Y * 0.0065, 0.0040, steel, n=12)
    # banjo fitting and bleed nipple on the outer half
    top = centre + er * 0.0105 + Y * 0.0165 + tang * 0.012
    mk.cyl(part, top, top + Y * 0.006, 0.0055, black, n=16)
    mk.cyl(part, centre + er * 0.012 + Y * 0.016 - tang * 0.018, centre + er * 0.020 + Y * 0.016 - tang * 0.018,
           0.0022, steel, n=8)
    return top + Y * 0.006


def build_brake(coll, front):
    name = "brake_front" if front else "brake_rear"
    part = Part(name, "Brakes")
    hose = M.get("black_gloss")
    lever = _lever(part, 1.0 if front else -1.0)
    if front:
        cal = _caliper(part, S.FRONT_AXLE, S.FRONT_ROTOR_R, S.FRONT_ROTOR_Y, 152.0)
        leg = S.FRONT_AXLE + Y * (S.FORK_LEG_Y + 0.006)
        ctrl = [lever, lever + X * 0.07 + Z * -0.03,
                S.on_axis(40) + S.AXIS_FWD * 0.09 + Y * 0.07,
                leg + S.AXIS_UP * 0.30 - S.AXIS_FWD * 0.022,
                leg + S.AXIS_UP * 0.24 - S.AXIS_FWD * 0.020,
                leg + S.AXIS_UP * 0.12 - S.AXIS_FWD * 0.028,
                cal + Z * 0.012]
    else:
        cal = _caliper(part, S.REAR_AXLE, S.REAR_ROTOR_R, S.REAR_ROTOR_Y, 32.0)
        port = S.on_axis(S.DT_AT_HT) + (S.BB - S.on_axis(S.DT_AT_HT)).normalized() * 0.10 + Y * 0.031
        ctrl = [lever, lever + X * 0.08 + Z * -0.02,
                S.on_axis(10) + S.AXIS_FWD * 0.10 + Y * 0.02,
                port + Y * 0.02 + Z * 0.03, port]
        cs_exit = S.P(S.REAR_X + 110, S.BB_DROP - 4, 72)
        mk.curve_tube(part, [cs_exit, cs_exit + X * -0.025 + Z * 0.012, cal + X * 0.012 + Z * 0.010, cal],
                      0.0025, hose, samples=8, n=10)
    mk.curve_tube(part, ctrl, 0.0025, hose, samples=12, n=10)
    return part.finish(coll, sharp_angle=50.0)


def build_rotor(coll, front):
    """SM-RT10: steel braking track with two staggered rows of holes, six curved arms, Center Lock carrier."""
    name = "rotor_front" if front else "rotor_rear"
    axle = S.FRONT_AXLE if front else S.REAR_AXLE
    r_out = S.FRONT_ROTOR_R if front else S.REAR_ROTOR_R
    y = S.FRONT_ROTOR_Y if front else S.REAR_ROTOR_Y
    part = Part(name, "Brakes")
    steel, silver, black = M.get("alu_silver"), M.get("steel"), M.get("black_anodised")
    r_in = r_out - 0.0160
    outer = []
    for k in range(144):
        a = 2 * math.pi * k / 144
        r = r_out - 0.0010 * (0.5 + 0.5 * math.cos(a * 12))       # gently scalloped edge
        outer.append((r * math.cos(a), r * math.sin(a)))
    holes = [mk.circle_pts(0, 0, r_in, 144)]
    n_holes = 30 if front else 26
    for row, rr in ((0, r_out - 0.0048), (1, r_out - 0.0110)):
        for k in range(n_holes):
            a = 2 * math.pi * (k + 0.5 * row) / n_holes
            holes.append(mk.circle_pts(rr * math.cos(a), rr * math.sin(a), 0.0017, 8))
    track = mk.plate2d(outer, holes=holes, thickness=0.0018)
    mk.in_bike_plane(track, axle, y=y)
    part.add_bm(track, steel, smooth=False)
    # six curved arms from the carrier to the track
    for k in range(6):
        a0 = 2 * math.pi * k / 6
        pts = []
        for j in range(7):
            t = j / 6
            r = 0.0290 + t * (r_in + 0.0012 - 0.0290)
            a = a0 + 0.38 * t
            pts.append((r * math.cos(a), r * math.sin(a)))
        left = [(p[0] - 0.0036 * math.sin(math.atan2(p[1], p[0]) + 0.6), p[1] + 0.0036 * math.cos(math.atan2(p[1], p[0]) + 0.6))
                for p in pts]
        right = [(p[0] + 0.0036 * math.sin(math.atan2(p[1], p[0]) + 0.6), p[1] - 0.0036 * math.cos(math.atan2(p[1], p[0]) + 0.6))
                 for p in pts]
        arm = mk.plate2d(left + right[::-1], thickness=0.0016)
        mk.in_bike_plane(arm, axle, y=y)
        part.add_bm(arm, steel, smooth=False)
    carrier = mk.plate2d(mk.circle_pts(0, 0, 0.0320, 48), holes=[mk.circle_pts(0, 0, 0.0185, 48)], thickness=0.0030,
                         bevel=0.0004)
    mk.in_bike_plane(carrier, axle, y=y + 0.0006)
    part.add_bm(carrier, black)
    lock = [(((0.0200 if k % 2 else 0.0192) * math.cos(2 * math.pi * k / 40)),
             ((0.0200 if k % 2 else 0.0192) * math.sin(2 * math.pi * k / 40))) for k in range(40)]
    lr = mk.plate2d(lock, holes=[mk.circle_pts(0, 0, 0.0125, 24)], thickness=0.0035)
    mk.in_bike_plane(lr, axle, y=y + 0.0035)
    part.add_bm(lr, silver, smooth=False)
    return part.finish(coll, pivot=axle, sharp_angle=50.0)
