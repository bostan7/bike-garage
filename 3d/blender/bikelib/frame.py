"""Frame: Scale Alloy 6061, size L.

All tubes, gussets, weld beads, bridges and dropouts are built overlapping, then fused into one welded
surface (voxel remesh + smoothing), like a real hydroformed and TIG-welded aluminium frame.
Decals are then shrink-wrapped onto that surface. Positions come from the official geometry.
"""
import math

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from . import materials as M
from . import meshkit as mk
from . import spec as S
from .meshkit import Part, X, Y, Z


class StraightTube:
    """A straight tube with a varying (w, h) cross-section; also used to place decals on its surface."""

    def __init__(self, a, b, keys):
        self.a, self.b, self.keys = a, b, keys
        self.t, self.n, self.bv = mk.frame_at(b - a, Y)
        self.length = (b - a).length

    def size(self, s):
        return mk.interp_keys(self.keys, s)

    def point(self, s):
        return self.a.lerp(self.b, s)

    def surface(self, s, angle, lift=0.0):
        """Point on the surface at fraction s along the tube; angle 0 = top (+n), +90 deg = +Y side."""
        w, h = self.size(s)
        c = self.point(s)
        return c + self.n * ((h + lift) * math.cos(angle)) + self.bv * ((w + lift) * math.sin(angle))

    def build(self, part, mat, samples=12, n=32, power=2.0, caps=True):
        return mk.tube(part, self.a, self.b, self.keys, mat, samples=samples, n=n, power=power, caps=caps)


def _sleeve(part, tube, s0, s1, a0, a1, mat, lift=0.0015, steps=40, arc_steps=24):
    """Partial shell on a tube surface (painted panels, stripes, protectors)."""
    rings = []
    for i in range(steps + 1):
        s = s0 + (s1 - s0) * i / steps
        rings.append([tube.surface(s, a0 + (a1 - a0) * k / arc_steps, lift) for k in range(arc_steps + 1)])
    return mk.add_rings(part, rings, mat, caps=(False, False), closed=False)


def _text_on_tube(part, tube, text, s_center, angle_center, height, length, side, mat, reverse=False, lift=0.0015,
                  italic=0.0, extrude=0.0, font=mk.FONT_PATH, space=1.0):
    """Wrap text onto a tube side. side = -1 drive side (-Y), +1 non-drive side (+Y), 0 = on top (+n)."""
    probe = mk._text_mesh(text, 1.0, 0.0, font, space=space)
    xs = [v.co.x for v in probe.vertices]
    ys = [v.co.y for v in probe.vertices]
    bpy.data.meshes.remove(probe)
    w0, h0 = max(xs) - min(xs), max(ys) - min(ys)
    sx, sy = length / w0, height / h0
    direction = -1.0 if reverse else 1.0
    turn = side if side != 0 else -1.0

    def xform(v):
        along = s_center + direction * (v.x * sx + italic * v.y * sy) / tube.length
        w, h = tube.size(along)
        r = (w + h) * 0.5
        ang = angle_center - turn * (v.y * sy) / r          # letter "up" towards the top of the tube
        return tube.surface(along, ang, lift + v.z * 0.0003)
    return mk.add_text(part, text, 1.0, extrude, mat, xform, font, space=space)


# ----------------------------------------------------------------------------------- geometry

def _tubes():
    head = StraightTube(S.on_axis(-3), S.on_axis(S.HT_LEN + 1),       # smooth taper, as in SCOTT's photo
                        [(0.0, (0.0275, 0.0280)), (0.50, (0.0298, 0.0303)), (1.0, (0.0345, 0.0352))])
    top = StraightTube(S.on_seat_axis(S.SEAT_TUBE - S.TT_AT_ST), S.on_axis(S.TT_AT_HT),
                       [(0.0, (0.0175, 0.0185)), (0.20, (0.0165, 0.0170)), (0.70, (0.0180, 0.0175)),
                        (0.90, (0.0215, 0.0215)), (1.0, (0.0250, 0.0270))])
    down = StraightTube(S.BB, S.on_axis(S.DT_AT_HT),
                        [(0.0, (0.0250, 0.0270)), (0.10, (0.0290, 0.0285)), (0.55, (0.0300, 0.0300)),
                         (0.75, (0.0310, 0.0328)), (0.90, (0.0314, 0.0385)), (1.0, (0.0308, 0.0440))])
    seat = StraightTube(S.on_seat_axis(-14), S.ST_TOP,
                        [(0.0, (0.0235, 0.0235)), (0.20, (0.0195, 0.0200)), (0.85, (0.0175, 0.0175)),
                         (1.0, (0.0180, 0.0180))])
    return head, top, down, seat


def _bead(part, tube, s, extra=0.0016, n=36):
    """Weld bead: a fat ring around a tube where it meets another tube."""
    w, h = tube.size(s)
    c = tube.point(s)
    ring = []
    for k in range(n):
        a = 2 * math.pi * k / n
        ring.append(c + tube.n * ((h + extra * 0.4) * math.cos(a)) + tube.bv * ((w + extra * 0.4) * math.sin(a)))
    ring.append(ring[0])
    mk.tube_path(part, ring, (extra, extra), None, n=8, caps=False)


def _dime(shape, bvh, p, across):
    """One ripple of a TIG bead, snapped onto the welded surface."""
    loc, nrm, _, _ = bvh.find_nearest(p)
    if loc is None:
        return
    across = (across - nrm * across.dot(nrm)).normalized()
    mk.ellipsoid(shape, loc + nrm * 0.0003, (0.0026, 0.0012, 0.0011), None, rot=mk.basis(across, nrm), segs=6, rings=4)


def _weld_ripples(shape, bvh, tube, s, extra, pitch=0.0015):
    """Rippled TIG bead ("stack of dimes") around a tube where it meets another tube."""
    w, h = tube.size(s)
    c = tube.point(s)
    n = max(24, int(2 * math.pi * ((w + h) / 2 + extra) / pitch))
    for k in range(n):
        a = 2 * math.pi * k / n
        p = c + tube.n * ((h + extra * 0.5) * math.cos(a)) + tube.bv * ((w + extra * 0.5) * math.sin(a))
        _dime(shape, bvh, p, tube.t)


def _head_tube_seam(shape, bvh, head, side, pitch=0.0015):
    """The front section (top + down tube) is welded to the head tube with one seam down each side,
    curving back at the top and bottom (SCOTT's photo)."""
    pts = []
    for i in range(121):
        s = 0.06 + 0.86 * i / 120
        th = side * math.radians(138 + 26 * (2 * s - 1) ** 4)
        pts.append(head.surface(s, th, 0.0004))
    length = sum((b - a).length for a, b in zip(pts, pts[1:]))
    n = int(length / pitch)
    acc, j = 0.0, 0
    for k in range(n):
        target = k * pitch
        while j < len(pts) - 2 and acc + (pts[j + 1] - pts[j]).length < target:
            acc += (pts[j + 1] - pts[j]).length
            j += 1
        seg = pts[j + 1] - pts[j]
        p = pts[j] + seg * ((target - acc) / max(seg.length, 1e-9))
        nrm = (p - head.point(max(0.0, min(1.0, (p - head.a).dot(head.t) / head.length)))).normalized()
        _dime(shape, bvh, p, nrm.cross(seg.normalized()))


def _structure(shape):
    head, top, down, seat = _tubes()
    for t in (top, down, seat):
        t.build(shape, None, n=40)
    head.build(shape, None, n=48, power=2.2)
    # head-tube gusset filling the corner between top tube and down tube
    g = S.on_axis(52) - S.AXIS_FWD * 0.020
    mk.ellipsoid(shape, g, (0.050, 0.024, 0.030), None, rot=mk.basis(S.AXIS_UP, -S.AXIS_FWD), segs=32, rings=16)
    # weld beads (the head tube gets one seam down each side instead, added after fusing)
    _bead(shape, top, 0.03, extra=0.0013)
    _bead(shape, down, 0.03, extra=0.0016)
    # seat tube collar and BB92 shell
    mk.cyl(shape, S.ST_TOP - S.SEAT_DIR * 0.016, S.ST_TOP, 0.0192, None, n=40)
    mk.cyl(shape, S.BB + Y * 0.0448, S.BB - Y * 0.0448, 0.0240, None, n=40)

    ra = S.REAR_AXLE
    for side in (1.0, -1.0):
        drive = side < 0
        cs_ctrl = [S.P(-25, 4, side * (32 if drive else 38)), S.P(-150, 22, side * (48 if drive else 52)),
                   S.P(-320, 46, side * 63), S.P(S.REAR_X + 14, S.BB_DROP + 1, side * 66)]
        pts = mk.catmull_rom(cs_ctrl, 8)
        prof = [mk.interp_keys([(0.0, (0.0105, 0.0175)), (0.35, (0.0090, 0.0130)), (1.0, (0.0072, 0.0095))],
                               i / (len(pts) - 1)) for i in range(len(pts))]
        mk.tube_path(shape, pts, prof, None, n=24)

        ss_top = S.on_seat_axis(S.SEAT_TUBE - S.SS_AT_ST) + Y * (side * 0.016)
        ss_end = S.P(S.REAR_X + 20, S.BB_DROP + 30, side * 64)
        ss_ctrl = [ss_top, ss_top.lerp(ss_end, 0.35) + Y * (side * 0.010), ss_end]
        pts = mk.catmull_rom(ss_ctrl, 10)
        prof = [mk.interp_keys([(0.0, (0.0090, 0.0095)), (1.0, (0.0072, 0.0078))], i / (len(pts) - 1))
                for i in range(len(pts))]
        mk.tube_path(shape, pts, prof, None, n=20)

        # dropout around the axle
        outline = mk.hull2d(mk.circle_pts(0.0, 0.0, 0.017, 20) + mk.circle_pts(0.030, 0.003, 0.012, 12)
                            + mk.circle_pts(0.016, 0.034, 0.010, 12))
        plate = mk.plate2d(outline, thickness=0.0065, bevel=0.0012)
        mk.in_bike_plane(plate, ra, y=side * 0.0735)
        shape.add_bm(plate, None)

    # bridges: seatstays near the seat tube, chainstays behind the BB
    ss_top0 = S.on_seat_axis(S.SEAT_TUBE - S.SS_AT_ST)
    sa = ss_top0.lerp(S.P(S.REAR_X + 20, S.BB_DROP + 30), 0.13)
    mk.cyl(shape, sa + Y * 0.030, sa - Y * 0.030, 0.0062, None, n=20)
    cb = S.P(-95, 14)
    mk.tube_path(shape, [cb + Y * 0.044, cb + Y * 0.015 + Z * 0.004, cb - Y * 0.015 + Z * 0.004, cb - Y * 0.040],
                 (0.0075, 0.0060), None, n=16)
    # rear brake post mount (non-drive chainstay, in front of the axle)
    # (bolt bosses for a 160 mm caliper centred at 32 deg; bracket between chainstay and seatstay)
    pm = mk.hull2d(mk.circle_pts(0.082, 0.010, 0.0095, 16) + mk.circle_pts(0.045, 0.070, 0.0095, 16)
                   + mk.circle_pts(0.092, -0.010, 0.0085, 12) + mk.circle_pts(0.030, 0.050, 0.008, 12))
    bracket = mk.plate2d(pm, thickness=0.009, bevel=0.0015)
    mk.in_bike_plane(bracket, ra, y=0.0640)
    shape.add_bm(bracket, None)
    return head, top, down, seat


def build(coll):
    part = Part("frame", "Frame & fork")
    grey, black, steel = M.get("frame_grey"), M.get("decal_black"), M.get("steel")

    shape = mk.scratch()
    head, top, down, seat = _structure(shape)
    body = mk.fused(shape, voxel=0.0011, smooth=8, smooth_factor=0.5, ratio=0.075)
    bvh = BVHTree.FromBMesh(body)
    target = mk.bm_to_object(body.copy(), "frame_surface")
    part.add_bm(body, grey)

    # replaceable derailleur hanger (separate black part, bolted on)
    hanger = mk.plate2d(mk.hull2d(mk.circle_pts(0.0, 0.0, 0.010, 16) + mk.circle_pts(-0.022, -0.034, 0.008, 16)
                                  + [(0.012, 0.004)]),
                        holes=[mk.circle_pts(-0.022, -0.034, 0.0032, 12)], thickness=0.004, bevel=0.0008)
    mk.in_bike_plane(hanger, S.REAR_AXLE, y=-0.0790)
    part.add_bm(hanger, M.get("black_anodised"))
    mk.cyl(part, S.REAR_AXLE + Vector((-0.022, -0.0815, -0.034)), S.REAR_AXLE + Vector((-0.022, -0.0770, -0.034)),
           0.0042, steel, n=12)

    # bottle-cage rivnuts (2 on the down tube, 2 on the seat tube)
    for s in (0.40, 0.56):
        p = down.surface(s, 0.0)
        mk.cyl(part, p - down.n * 0.003, p + down.n * 0.0035, 0.0045, steel, n=14)
        mk.cyl(part, p + down.n * 0.0035, p + down.n * 0.0042, 0.0025, M.get("black_gloss"), n=10)
    st_front = Vector((math.sin(math.radians(S.STA)), 0.0, math.cos(math.radians(S.STA))))
    for d in (170.0, 290.0):
        p = S.on_seat_axis(d) + st_front * 0.0165
        mk.cyl(part, p - st_front * 0.003, p + st_front * 0.0035, 0.0045, steel, n=14)

    # ---- decals, wrapped onto the welded surface ------------------------------------------
    deco = {}

    def layer(mat):
        if mat not in deco:
            deco[mat] = mk.scratch()
        return deco[mat]

    yellow, stripe = M.get("neon_yellow"), M.get("decal_grey")
    # down tube: black panel on the lower half, two thin grey pinstripes, neon italic SCOTT on both sides
    _sleeve(layer(black), down, 0.12, 0.83, math.radians(98), math.radians(262), black)
    for side in (1.0, -1.0):
        for a in (150.0, 160.0):
            _sleeve(layer(stripe), down, 0.16, 0.80, side * math.radians(a), side * math.radians(a + 1.6), stripe,
                    lift=0.0018, steps=24, arc_steps=1)
    _text_on_tube(layer(yellow), down, "SCOTT", 0.47, math.radians(-127), 0.030, 0.40, -1, yellow, italic=0.35)
    _text_on_tube(layer(yellow), down, "SCOTT", 0.47, math.radians(127), 0.030, 0.40, 1, yellow, reverse=True,
                  italic=0.35)
    # top tube: black SCOTT on both sides near the head tube; black band with SCALE on top
    _text_on_tube(layer(black), top, "SCOTT", 0.82, math.radians(-68), 0.016, 0.115, -1, black, italic=0.35)
    _text_on_tube(layer(black), top, "SCOTT", 0.82, math.radians(68), 0.016, 0.115, 1, black, reverse=True,
                  italic=0.35)
    # Toni's photos (2026-10-18): glossy black band along the whole top of the top tube, SCALE in thin, wide-spaced
    # neon capitals (the A has no crossbar), reading from the seat towards the head tube, letter tops to the left
    _sleeve(layer(black), top, 0.05, 0.95, math.radians(-42), math.radians(42), black, steps=60)
    _text_on_tube(layer(yellow), top, "SC\u039bLE", 0.79, 0.0, 0.0105, 0.088, 0, yellow,
                  font="C:/Windows/Fonts/segoeuil.ttf", space=1.9)
    # chainstay protector (drive side)
    cs = StraightTube(S.P(-40, 10, -36), S.P(-330, 47, -63), [(0.0, (0.0100, 0.0160)), (1.0, (0.0080, 0.0110))])
    _sleeve(layer(black), cs, 0.05, 0.95, math.radians(-150), math.radians(10), black, lift=0.0022)
    # internal cable ports near the head tube (both sides) and Scott emblem on the head tube front
    for side in (1.0, -1.0):
        p = down.surface(0.90, side * math.radians(78), 0.0006)
        mk.ellipsoid(layer(black), p, (0.011, 0.0035, 0.006), black, rot=mk.basis(down.t, Z))
    front = head.surface(0.40, 0.0, 0.0015)
    mk.add_text(layer(black), "S", 1.0, 0.0, black,
                lambda v: front + S.AXIS_UP * (v.y * 0.034) + Y * ((v.x + 0.3 * v.y) * 0.030))

    # seat tube rear: model number
    _text_on_tube(layer(black), seat, "980", 0.80, math.pi, 0.012, 0.034, 0, black)

    # TIG weld seams ("stack of dimes") over the smooth weld fillets
    ripples = mk.scratch()
    for tube, s, extra in ((top, 0.03, 0.0013), (down, 0.03, 0.0016)):
        _weld_ripples(ripples, bvh, tube, s, extra)
    for side in (1.0, -1.0):
        _head_tube_seam(ripples, bvh, head, side)
    part.add_bm(ripples.bm, grey)

    # stacked layers so decals never fight for the same depth: panel < stripes < letters
    offsets = {black: 0.0006, stripe: 0.0010, yellow: 0.0013}
    for mat, shape in deco.items():
        part.add_bm(mk.wrapped(shape, target, offset=offsets[mat]), mat, smooth=False)
    mk.remove_object(target)
    return part.finish(coll, sharp_angle=50.0)
