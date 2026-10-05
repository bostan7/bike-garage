"""Suntour XCR32 RL-R fork (100 mm, coil, remote lockout) and the Syncros reducer headset.

Crown and lowers are cast parts: their pieces are fused and smoothed into single shapes."""
import math

from mathutils import Vector

from . import materials as M
from . import meshkit as mk
from . import spec as S
from .frame import StraightTube, _text_on_tube
from .meshkit import Part, X, Y, Z


def crown_center():
    return S.on_axis(S.HT_LEN + S.LOWER_CUP + 15.0)


def leg_top(side):
    c = crown_center()
    along = (S.FRONT_AXLE - c).dot(S.AXIS_DOWN)
    return S.FRONT_AXLE - S.AXIS_DOWN * along + Y * (side * S.FORK_LEG_Y)


def seal_point(side):
    return S.FRONT_AXLE - S.AXIS_DOWN * S.FORK_SEAL_FROM_AXLE + Y * (side * S.FORK_LEG_Y)


def _crown(part):
    c = crown_center()
    up = S.AXIS_UP * 0.016
    shape = mk.scratch()
    mk.cyl(shape, c - up, c + up * 1.1, 0.0245, None, n=40)                     # steerer boss
    for side in (1.0, -1.0):
        q = leg_top(side)
        mk.cyl(shape, q - up * 1.35, q + up, 0.0240, None, n=40)              # leg collars
        # arm from the boss to the collar, thicker at the front
        mid = c.lerp(q, 0.5) + S.AXIS_FWD * 0.004
        mk.box(shape, mid, ((q - c).length * 1.05, 0.020, 0.030), None, rot=mk.basis(q - c, S.AXIS_UP))
    mk.box(shape, c + S.AXIS_FWD * 0.034 - up * 0.2, (0.026, 0.110, 0.024), None,
           rot=mk.basis(S.AXIS_FWD, S.AXIS_UP))                               # front bridge of the crown
    part.add_bm(mk.fused(shape, voxel=0.0008, smooth=4, smooth_factor=0.5, ratio=0.12), M.get("black_matte"))
    # pinch bolts at the back of each collar
    for side in (1.0, -1.0):
        q = leg_top(side)
        p = q - S.AXIS_FWD * 0.026 + Y * (side * 0.004)
        mk.cyl(part, p - S.AXIS_FWD * 0.004, p + S.AXIS_FWD * 0.004, 0.0040, M.get("steel"), n=10)


def _lowers(part):
    shape = mk.scratch()
    tubes = {}
    for side in (1.0, -1.0):
        bottom = S.FRONT_AXLE + Y * (side * S.FORK_LEG_Y) + S.AXIS_DOWN * 0.018
        lower = StraightTube(bottom, seal_point(side) + S.AXIS_DOWN * 0.002,
                             [(0.0, (0.0145, 0.0150)), (0.10, (0.0175, 0.0185)), (0.80, (0.0218, 0.0222)),
                              (0.94, (0.0245, 0.0245)), (1.0, (0.0250, 0.0250))])
        lower.build(shape, None, samples=14, n=36)
        tubes[side] = lower
        # dropout tab around the QR axle
        tab = mk.hull2d(mk.circle_pts(0.0, 0.0, 0.0125, 20) + mk.circle_pts(0.0, 0.030, 0.014, 20))
        plate = mk.plate2d(tab, thickness=0.012, bevel=0.002)
        mk.place(plate, S.FRONT_AXLE + Y * (side * S.FORK_LEG_Y), S.AXIS_FWD, S.AXIS_UP, -Y)
        shape.add_bm(plate, None)
    # arch over the tyre, in front of the legs
    a = seal_point(1.0) + S.AXIS_FWD * 0.010 + S.AXIS_DOWN * 0.030
    b = seal_point(-1.0) + S.AXIS_FWD * 0.010 + S.AXIS_DOWN * 0.030
    peak = S.FRONT_AXLE - S.AXIS_DOWN * (S.FORK_SEAL_FROM_AXLE + 0.040) + S.AXIS_FWD * 0.032
    ctrl = [a + S.AXIS_DOWN * 0.035, a + S.AXIS_UP * 0.010 + S.AXIS_FWD * 0.010 + Y * -0.008, peak,
            b + S.AXIS_UP * 0.010 + S.AXIS_FWD * 0.010 + Y * 0.008, b + S.AXIS_DOWN * 0.035]
    pts = mk.catmull_rom(ctrl, 10)
    mk.tube_path(shape, pts, (0.0095, 0.0150), None, n=24)
    # post mount bosses and hose guide on the back of the left leg
    rot = mk.basis(S.AXIS_FWD, S.AXIS_UP)
    for d in (0.030, 0.096):
        p = S.FRONT_AXLE + Y * (S.FORK_LEG_Y - 0.003) + S.AXIS_UP * d - S.AXIS_FWD * 0.024
        mk.box(shape, p, (0.026, 0.016, 0.018), None, rot=rot)
    g = S.FRONT_AXLE + Y * (S.FORK_LEG_Y + 0.004) + S.AXIS_UP * 0.24 - S.AXIS_FWD * 0.020
    mk.box(shape, g, (0.012, 0.010, 0.022), None, rot=rot)
    # light smoothing keeps the legs full size (heavy smoothing shrinks them)
    part.add_bm(mk.fused(shape, voxel=0.0009, smooth=3, smooth_factor=0.5, ratio=0.09), M.get("black_matte"))
    return tubes


def build(coll, bar_anchor):
    """bar_anchor(side) -> point on the handlebar where the remote sits (left side)."""
    part = Part("fork", "Frame & fork")
    black, gloss, stanch, steel = M.get("black_matte"), M.get("black_gloss"), M.get("stanchion"), M.get("steel")
    c = crown_center()

    # steerer (1 1/8") up through the head tube to the top of the stem
    mk.cyl(part, c, S.on_axis(-(S.HEADSET_COVER + S.SPACERS + S.STEM_STACK + 2)), 0.0143, M.get("black_anodised"),
           n=32)
    _crown(part)
    tubes = _lowers(part)

    for side in (1.0, -1.0):
        q, seal = leg_top(side), seal_point(side)
        mk.cyl(part, q + S.AXIS_UP * 0.012, seal + S.AXIS_DOWN * 0.02, S.STANCHION_R, stanch, n=48)
        # dust wiper: lip profile revolved around the leg
        wiper = mk.scratch()
        prof = [(0.0162, 0.000), (0.0175, -0.002), (0.0228, -0.003), (0.0250, 0.004), (0.0248, 0.012),
                (0.0175, 0.014), (0.0162, 0.010)]
        mk.revolve(wiper, Vector((0, 0, 0)), prof, None, n=48)
        mk.place(wiper.bm, seal, S.AXIS_FWD, S.AXIS_UP, -Y)   # revolve axis (local Y) -> leg axis
        part.add_bm(wiper.bm, gloss, free=False)
        # top caps: lockout cap with cable arm (drive side), knurled preload knob (left)
        top = q + S.AXIS_UP * 0.016
        if side < 0:
            mk.cyl(part, top, top + S.AXIS_UP * 0.010, 0.0125, gloss, n=32)
            arm = top + S.AXIS_UP * 0.008 + S.AXIS_FWD * 0.012
            mk.box(part, arm, (0.026, 0.008, 0.008), M.get("grey_plastic"), rot=mk.basis(S.AXIS_FWD, S.AXIS_UP))
        else:
            knob = mk.scratch()
            prof = []
            for k in range(48):
                r = 0.0120 + (0.0008 if k % 2 else 0.0)
                prof.append(r)
            ring = [top + (S.AXIS_FWD * math.cos(2 * math.pi * k / 48) + Y * math.sin(2 * math.pi * k / 48)) * prof[k]
                    for k in range(48)]
            mk.add_rings(knob, [ring, [p + S.AXIS_UP * 0.011 for p in ring]], None)
            part.add_bm(knob.bm, M.get("grey_plastic"), smooth=False, free=False)
        # rebound knob under the drive-side leg (red)
        if side < 0:
            bot = S.FRONT_AXLE + Y * (side * S.FORK_LEG_Y) + S.AXIS_DOWN * 0.018
            mk.cyl(part, bot, bot + S.AXIS_DOWN * 0.009, 0.0085, M.get("rebound_red"), n=24)
        # graphics on the outside of each lower
        lower = tubes[side]
        # SR SUNTOUR low on the leg with dark grey slash graphics above it (SCOTT's photo); XCR 32 on the left leg
        _text_on_tube(part, lower, "SR SUNTOUR", 0.26, side * math.radians(80), 0.0080, 0.065, side,
                      M.get("neon_yellow"), reverse=side > 0, lift=0.0007)
        _text_on_tube(part, lower, "///", 0.46, side * math.radians(80), 0.026, 0.048, side,
                      M.get("decal_grey"), reverse=side > 0, lift=0.0007, italic=0.3)
        if side > 0:
            _text_on_tube(part, lower, "XCR 32", 0.72, side * math.radians(80), 0.0105, 0.060, side,
                          M.get("tyre_text"), reverse=True, lift=0.0007, italic=0.2)

    # remote lockout lever (left of the stem, under the bar) and its cable to the lockout cap
    r = bar_anchor(1.0)
    body = mk.scratch()
    mk.box(body, r + Z * -0.016, (0.024, 0.020, 0.016), None)
    mk.box(body, r + Z * -0.022 + X * 0.018, (0.030, 0.010, 0.005), None, rot=mk.rot_y(math.radians(-15)))
    part.add_bm(mk.subdivided(body, 2), M.get("grey_plastic"))
    cap = leg_top(-1.0) + S.AXIS_UP * 0.024 + S.AXIS_FWD * 0.024
    mk.curve_tube(part, [r + Z * -0.02, r + X * 0.09 + Z * -0.04,
                         cap + S.AXIS_FWD * 0.06 + S.AXIS_UP * 0.10, cap + S.AXIS_FWD * 0.012 + S.AXIS_UP * 0.01, cap],
                  0.0022, gloss, samples=12, n=10)
    return part.finish(coll, sharp_angle=50.0)


def build_headset(coll):
    part = Part("headset", "Frame & fork")
    black, gloss = M.get("black_anodised"), M.get("black_gloss")
    # top cover (conical), two spacers, lower cup, top cap with bolt
    cover = mk.scratch()
    mk.revolve(cover, Vector((0, 0, 0)), [(0.0145, 0.0), (0.0300, 0.0), (0.0300, 0.0025), (0.0215, 0.0080),
                                          (0.0145, 0.0080)], None, n=48)
    mk.place(cover.bm, S.on_axis(0), S.AXIS_FWD, S.AXIS_UP, -Y)
    part.add_bm(cover.bm, black, free=False)
    y0 = S.HEADSET_COVER
    for i, h in enumerate((10.0, S.SPACERS - 10.0)):
        mk.cyl(part, S.on_axis(-y0), S.on_axis(-y0 - h + 0.3), 0.0180, gloss if i == 0 else black, n=40)
        y0 += h
    mk.cyl(part, S.on_axis(S.HT_LEN), S.on_axis(S.HT_LEN + S.LOWER_CUP), 0.0350, black, n=48)
    top = -(S.HEADSET_COVER + S.SPACERS + S.STEM_STACK)
    capm = mk.scratch()
    mk.revolve(capm, Vector((0, 0, 0)), [(0.004, 0.0), (0.0175, 0.0), (0.0175, 0.0030), (0.0150, 0.0055),
                                         (0.004, 0.0055)], None, n=48)
    mk.place(capm.bm, S.on_axis(top), S.AXIS_FWD, S.AXIS_UP, -Y)
    part.add_bm(capm.bm, black, free=False)
    mk.cyl(part, S.on_axis(top - 5.5), S.on_axis(top - 7.0), 0.0050, M.get("steel"), n=12)
    return part.finish(coll)
