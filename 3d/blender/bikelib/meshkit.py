"""Small mesh-building toolkit on top of bmesh.

Every bike part is a `Part`: one bmesh that several helpers add geometry to,
finished into one Blender object named after the part's slot.
"""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

Y = Vector((0.0, 1.0, 0.0))
Z = Vector((0.0, 0.0, 1.0))
X = Vector((1.0, 0.0, 0.0))

FONT_PATH = "C:/Windows/Fonts/ariblk.ttf"   # Arial Black, close to the SCOTT / MAXXIS lettering


class Part:
    def __init__(self, name, category=""):
        self.name = name
        self.category = category
        self.bm = bmesh.new()
        self.mats = []

    def mat_index(self, mat):
        if mat not in self.mats:
            self.mats.append(mat)
        return self.mats.index(mat)

    def tag(self, faces, mat, smooth=True):
        i = self.mat_index(mat)
        for f in faces:
            f.material_index = i
            f.smooth = smooth
        return faces

    def add_bm(self, src, mat, smooth=True, free=True):
        """Append the geometry of another bmesh (e.g. a fused or subdivided shape) with one material."""
        me = bpy.data.meshes.new("tmp_add")
        src.to_mesh(me)
        if free:
            src.free()
        self.bm.faces.ensure_lookup_table()
        n0 = len(self.bm.faces)
        self.bm.from_mesh(me)
        self.bm.faces.ensure_lookup_table()
        faces = [self.bm.faces[i] for i in range(n0, len(self.bm.faces))]
        bpy.data.meshes.remove(me)
        return self.tag(faces, mat, smooth)

    def finish(self, collection, pivot=None, sharp_angle=40.0):
        bm = self.bm
        # clean-up: remove zero-area faces / zero-length edges left by fusing, wrapping and text
        bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges[:])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        if pivot is not None:
            bmesh.ops.translate(bm, verts=bm.verts[:], vec=-pivot)
        me = bpy.data.meshes.new(self.name)
        bm.to_mesh(me)
        bm.free()
        me.validate(verbose=False)
        for m in self.mats:
            me.materials.append(m)
        if hasattr(me, "set_sharp_from_angle"):
            me.set_sharp_from_angle(angle=math.radians(sharp_angle))
        ob = bpy.data.objects.new(self.name, me)
        if pivot is not None:
            ob.location = pivot
        ob["slot"] = self.name
        ob["category"] = self.category
        collection.objects.link(ob)
        return ob


# ------------------------------------------------------------------------------------------ math

def frame_at(tangent, ref=Y):
    """Orthonormal frame for a tube: t along the tube, n in the bike plane, b roughly along `ref`."""
    t = tangent.normalized()
    n = t.cross(ref)
    if n.length < 1e-6:
        n = t.cross(Z)
    n.normalize()
    b = n.cross(t).normalized()
    return t, n, b


def basis(x_axis, up_hint=Z):
    """Rotation matrix whose local X points along x_axis and local Z is as close to up_hint as possible."""
    x = x_axis.normalized()
    y = up_hint.cross(x)
    if y.length < 1e-6:
        y = Y.copy()
    y.normalize()
    z = x.cross(y).normalized()
    return Matrix((x, y, z)).transposed()


def rot_y(angle_rad):
    """Rotation about the lateral axis; positive = nose up when looking at the drive side."""
    return Matrix.Rotation(-angle_rad, 3, 'Y')


def catmull_rom(points, samples=8):
    """Smooth curve through control points (open)."""
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(samples):
            t = k / samples
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(points[-1].copy())
    return out


def interp_keys(keys, t):
    """keys: [(t, value_tuple)], sorted; linear interpolation of tuples."""
    if t <= keys[0][0]:
        return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            k = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return tuple(a + (b - a) * k for a, b in zip(v0, v1))
    return keys[-1][1]


# ------------------------------------------------------------------------------------- builders

def ring_points(center, tangent, w, h, n=16, ref=Y, power=2.0, roll=0.0):
    """Super-ellipse cross-section: w = half-size along b (lateral), h = half-size along n (in-plane)."""
    _, nn, b = frame_at(tangent, ref)
    pts = []
    for k in range(n):
        a = 2.0 * math.pi * k / n + roll
        c, s = math.cos(a), math.sin(a)
        e = 2.0 / power
        cx = math.copysign(abs(c) ** e, c)
        sx = math.copysign(abs(s) ** e, s)
        pts.append(center + nn * (h * cx) + b * (w * sx))
    return pts


def add_rings(part, rings, mat, caps=(True, True), closed=True, smooth=True):
    bm = part.bm
    vr = [[bm.verts.new(p) for p in ring] for ring in rings]
    n = len(rings[0])
    faces = []
    for a, b in zip(vr, vr[1:]):
        for i in range(n if closed else n - 1):
            j = (i + 1) % n
            faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
    if caps[0]:
        faces.append(bm.faces.new(list(reversed(vr[0]))))
    if caps[-1]:
        faces.append(bm.faces.new(vr[-1]))
    return part.tag(faces, mat, smooth)


def tube_path(part, pts, prof, mat, n=16, ref=Y, caps=True, power=2.0):
    """Sweep a cross-section along points. prof = (w, h) or a list of (w, h) per point."""
    rings = []
    for i, p in enumerate(pts):
        if i == 0:
            t = pts[1] - pts[0]
        elif i == len(pts) - 1:
            t = pts[-1] - pts[-2]
        else:
            t = pts[i + 1] - pts[i - 1]
        w, h = prof[i] if isinstance(prof, list) else prof
        rings.append(ring_points(p, t, w, h, n, ref, power))
    return add_rings(part, rings, mat, (caps, caps))


def tube(part, a, b, keys, mat, samples=8, n=16, ref=Y, caps=True, power=2.0):
    """Straight tube from a to b with a profile given as keyframes [(t, (w, h)), ...]."""
    pts = [a.lerp(b, i / (samples - 1)) for i in range(samples)]
    prof = [interp_keys(keys, i / (samples - 1)) for i in range(samples)]
    return tube_path(part, pts, prof, mat, n, ref, caps, power)


def curve_tube(part, ctrl, r, mat, samples=8, n=8, ref=Y):
    """Round tube (hose, cable) through control points."""
    pts = catmull_rom(ctrl, samples)
    clean = [pts[0]]
    for p in pts[1:]:
        if (p - clean[-1]).length > 1e-5:
            clean.append(p)
    return tube_path(part, clean, (r, r), mat, n, ref)


def cyl(part, a, b, r, mat, r2=None, n=16, caps=True):
    r2 = r if r2 is None else r2
    return tube_path(part, [a, b], [(r, r), (r2, r2)], mat, n, Y, caps)


def revolve(part, center, profile, mat, n=64, closed=True, smooth=True, angle0=0.0):
    """Revolve a (radius, y) profile around the lateral axis through `center` (wheels, hubs)."""
    bm = part.bm
    rings = []
    for k in range(n):
        a = 2.0 * math.pi * k / n + angle0
        c, s = math.cos(a), math.sin(a)
        rings.append([bm.verts.new(center + Vector((r * c, y, r * s))) for (r, y) in profile])
    m = len(profile)
    faces = []
    for k in range(n):
        A, B = rings[k], rings[(k + 1) % n]
        for i in range(m if closed else m - 1):
            j = (i + 1) % m
            faces.append(bm.faces.new((A[i], A[j], B[j], B[i])))
    return part.tag(faces, mat, smooth)


def prism(part, outline, origin, U, V, W, w0, w1, mat, smooth=False):
    """Extrude a 2-D outline (u, v) placed in the plane origin + U*u + V*v, from W*w0 to W*w1."""
    bm = part.bm
    bot = [bm.verts.new(origin + U * u + V * v + W * w0) for (u, v) in outline]
    top = [bm.verts.new(origin + U * u + V * v + W * w1) for (u, v) in outline]
    faces = [bm.faces.new(list(reversed(bot))), bm.faces.new(top)]
    n = len(outline)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((bot[i], bot[j], top[j], top[i])))
    return part.tag(faces, mat, smooth)


def ring_prism(part, outer, inner, origin, U, V, W, w0, w1, mat, smooth=False):
    """Flat ring with a hole (gears, rotors): outer and inner outlines have the same point count."""
    bm = part.bm

    def mk(pts, w):
        return [bm.verts.new(origin + U * u + V * v + W * w) for (u, v) in pts]
    ob, ot, ib, it = mk(outer, w0), mk(outer, w1), mk(inner, w0), mk(inner, w1)
    faces = []
    n = len(outer)
    for i in range(n):
        j = (i + 1) % n
        faces.append(bm.faces.new((ob[i], ob[j], ot[j], ot[i])))
        faces.append(bm.faces.new((ib[j], ib[i], it[i], it[j])))
        faces.append(bm.faces.new((ob[j], ob[i], ib[i], ib[j])))
        faces.append(bm.faces.new((ot[i], ot[j], it[j], it[i])))
    return part.tag(faces, mat, smooth)


def circle2d(r, n, a0=0.0):
    return [(r * math.cos(a0 + 2 * math.pi * k / n), r * math.sin(a0 + 2 * math.pi * k / n)) for k in range(n)]


def gear_outlines(teeth, pitch_radius, inner_r, tooth_h=0.0042):
    """Simple trapezoid-tooth sprocket outline + matching inner circle."""
    outer, inner = [], []
    step = 2 * math.pi / teeth
    root, tip = pitch_radius - tooth_h * 0.55, pitch_radius + tooth_h * 0.45
    for k in range(teeth):
        for frac, r in ((0.0, root), (0.30, tip - 0.0006), (0.5, tip), (0.70, tip - 0.0006)):
            a = step * (k + frac)
            outer.append((r * math.cos(a), r * math.sin(a)))
            inner.append((inner_r * math.cos(a), inner_r * math.sin(a)))
    return outer, inner


def box(part, center, size, mat, rot=None, smooth=False):
    bm = part.bm
    verts = bmesh.ops.create_cube(bm, size=1.0)["verts"]
    m = Matrix.Translation(center) @ (rot.to_4x4() if rot is not None else Matrix.Identity(4)) \
        @ Matrix.Diagonal((size[0], size[1], size[2], 1.0))
    bmesh.ops.transform(bm, matrix=m, verts=verts)
    faces = list({f for v in verts for f in v.link_faces})
    return part.tag(faces, mat, smooth)


def ellipsoid(part, center, radii, mat, rot=None, segs=16, rings=10):
    bm = part.bm
    verts = bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)["verts"]
    m = Matrix.Translation(center) @ (rot.to_4x4() if rot is not None else Matrix.Identity(4)) \
        @ Matrix.Diagonal((radii[0], radii[1], radii[2], 1.0))
    bmesh.ops.transform(bm, matrix=m, verts=verts)
    faces = list({f for v in verts for f in v.link_faces})
    return part.tag(faces, mat, True)


# -------------------------------------------------------------------------------------- text

def _text_mesh(text, size, extrude, font_path=FONT_PATH, offset=0.0, shear=0.0, space=1.0):
    """offset > 0 grows every glyph outline (for an outline layer behind the letters),
    shear slants the letters (italic), space scales the letter spacing."""
    cu = bpy.data.curves.new("tmp_text", "FONT")
    cu.body = text
    cu.size = size
    cu.extrude = extrude
    cu.align_x = 'CENTER'
    cu.align_y = 'CENTER'
    cu.offset = offset
    cu.shear = shear
    cu.space_character = space
    cu.resolution_u = 3          # fewer triangles per glyph curve
    try:
        cu.font = bpy.data.fonts.load(font_path, check_existing=True)
    except (RuntimeError, OSError):
        pass
    ob = bpy.data.objects.new("tmp_text", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    return me


def _split_long_edges(me, max_len, rounds=4):
    """Glyph fills contain long thin triangles; wrapped onto a curved tube their middle would sink below
    the surface. Split long edges (in the flat text plane) so the wrapped letters follow the curve."""
    bm = bmesh.new()
    bm.from_mesh(me)
    for _ in range(rounds):
        long_edges = [e for e in bm.edges
                      if (e.verts[0].co.xy - e.verts[1].co.xy).length > max_len]
        if not long_edges:
            break
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1, use_grid_fill=False)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()


def add_text(part, text, size, extrude, mat, xform, font_path=FONT_PATH, max_edge=0.12, **style):
    """Text mesh; xform(Vector local) -> Vector world. Local: x along the text, y up, z = depth.
    max_edge: longest allowed edge in the text plane, relative to the font size.
    style: offset / shear / space, see _text_mesh."""
    me = _text_mesh(text, size, extrude, font_path, **style)
    _split_long_edges(me, max_edge * size)
    for v in me.vertices:
        v.co = xform(Vector(v.co))
    bm = part.bm
    bm.faces.ensure_lookup_table()
    n0 = len(bm.faces)
    bm.from_mesh(me)                 # appends every glyph face, including ones bm.faces.new would reject
    bm.faces.ensure_lookup_table()
    faces = [bm.faces[i] for i in range(n0, len(bm.faces))]
    bpy.data.meshes.remove(me)
    return part.tag(faces, mat, smooth=False)


# ------------------------------------------------------------------------- modifiers & plates

def scratch():
    """Temporary part used to build a shape before modifiers are applied to it."""
    return Part("scratch")


def apply_mods(bm, mods):
    """Run Blender modifiers on a bmesh and return the evaluated result as a new bmesh.
    mods: [(type, {prop: value})], e.g. [("REMESH", {"mode": "VOXEL", "voxel_size": 0.0015})]."""
    me = bpy.data.meshes.new("tmp_mod")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new("tmp_mod", me)
    bpy.context.scene.collection.objects.link(ob)
    for kind, props in mods:
        m = ob.modifiers.new(kind.lower(), kind)
        for k, v in props.items():
            setattr(m, k, v)
    dg = bpy.context.evaluated_depsgraph_get()
    out = bmesh.new()
    out.from_object(ob, dg)
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    return out


def fused(shape, voxel=0.0013, smooth=6, smooth_factor=0.5, ratio=None):
    """Melt overlapping pieces into one welded surface (voxel remesh), round the joints (smooth),
    then reduce the triangle count (decimate)."""
    mods = [("REMESH", {"mode": "VOXEL", "voxel_size": voxel, "adaptivity": 0.0}),
            ("SMOOTH", {"factor": smooth_factor, "iterations": smooth})]
    if ratio:
        mods.append(("DECIMATE", {"decimate_type": "COLLAPSE", "ratio": ratio}))
    return apply_mods(shape.bm, mods)


def subdivided(shape, levels=2):
    """Catmull-Clark subdivision: turns a low-poly cage into a smooth cast/forged-looking part."""
    return apply_mods(shape.bm, [("SUBSURF", {"levels": levels, "render_levels": levels})])


def bm_to_object(bm, name="tmp_target"):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def remove_object(ob):
    me = ob.data
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)


def wrapped(shape, target_ob, offset=0.0007):
    """Snap decal geometry onto a surface (shrinkwrap), floating `offset` above it."""
    return apply_mods(shape.bm, [("SHRINKWRAP", {"target": target_ob, "wrap_method": "NEAREST_SURFACEPOINT",
                                                 "wrap_mode": "OUTSIDE_SURFACE", "offset": offset})])


def plate2d(outline, holes=(), thickness=0.002, bevel=0.0, bevel_res=1):
    """Flat plate from a 2-D outline with real holes (curve fill). Local: XY plane, thickness along Z (centred).
    bevel rounds the edges; bevel_res 0 = a single chamfer, higher = rounder."""
    cu = bpy.data.curves.new("tmp_plate", 'CURVE')
    cu.dimensions = '2D'
    cu.fill_mode = 'BOTH'
    cu.extrude = thickness / 2
    cu.bevel_depth = bevel
    cu.bevel_resolution = bevel_res
    cu.resolution_u = 1
    for loop in [outline, *holes]:
        sp = cu.splines.new('POLY')
        sp.points.add(len(loop) - 1)
        for p, (u, v) in zip(sp.points, loop):
            p.co = (u, v, 0.0, 1.0)
        sp.use_cyclic_u = True
    ob = bpy.data.objects.new("tmp_plate", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    out = bmesh.new()
    out.from_mesh(me)
    bpy.data.objects.remove(ob)
    bpy.data.curves.remove(cu)
    bpy.data.meshes.remove(me)
    bmesh.ops.remove_doubles(out, verts=out.verts[:], dist=1e-7)
    return out


def place(bm, origin, U, V, W):
    """Move a local shape (x, y, z) to origin + U*x + V*y + W*z."""
    m = Matrix((
        (U.x, V.x, W.x, origin.x),
        (U.y, V.y, W.y, origin.y),
        (U.z, V.z, W.z, origin.z),
        (0.0, 0.0, 0.0, 1.0)))
    bmesh.ops.transform(bm, matrix=m, verts=bm.verts[:])
    return bm


def in_bike_plane(bm, origin, angle_deg=0.0, y=0.0):
    """Place a plate drawn in local XY into the bike plane (local X -> +X, local Y -> +Z), thickness along Y.
    angle_deg rotates it around the lateral axis (positive = counter-clockwise seen from the drive side)."""
    a = math.radians(angle_deg)
    U = Vector((math.cos(a), 0.0, math.sin(a)))
    V = Vector((-math.sin(a), 0.0, math.cos(a)))
    return place(bm, origin + Y * y, U, V, -Y)


def circle_pts(cx, cy, r, n=24, a0=0.0):
    return [(cx + r * math.cos(a0 + 2 * math.pi * k / n), cy + r * math.sin(a0 + 2 * math.pi * k / n)) for k in range(n)]


def rounded_rect(cx, cy, w, h, r, n=4):
    """Rounded rectangle outline (counter-clockwise)."""
    pts = []
    for (qx, qy, a0) in ((w / 2 - r, h / 2 - r, 0), (-w / 2 + r, h / 2 - r, 90), (-w / 2 + r, -h / 2 + r, 180),
                         (w / 2 - r, -h / 2 + r, 270)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + qx + r * math.cos(a), cy + qy + r * math.sin(a)))
    return pts


def hull2d(points):
    """Convex hull (monotone chain), counter-clockwise."""
    pts = sorted(set(points))

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def capsule_outline(a, b, r, n=10):
    """Stadium shape around the segment a-b (2-D)."""
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    pts = []
    for k in range(n + 1):
        t = ang + math.pi / 2 + math.pi * k / n
        pts.append((a[0] + r * math.cos(t), a[1] + r * math.sin(t)))
    for k in range(n + 1):
        t = ang - math.pi / 2 + math.pi * k / n
        pts.append((b[0] + r * math.cos(t), b[1] + r * math.sin(t)))
    return pts


def rounded_poly(points, radius, n=4):
    """Polygon (2-D, either winding) with every corner replaced by an arc of `radius` (smaller where the
    neighbouring edges are short). Used for traced outlines of cast or forged parts."""
    out = []
    m = len(points)
    for i in range(m):
        p0, p1, p2 = Vector(points[i - 1]), Vector(points[i]), Vector(points[(i + 1) % m])
        a, b = (p0 - p1), (p2 - p1)
        la, lb = a.length, b.length
        if la < 1e-9 or lb < 1e-9:
            continue
        a, b = a / la, b / lb
        cos_t = max(-1.0, min(1.0, a.dot(b)))
        half = math.acos(cos_t) / 2
        if half < 1e-3 or abs(half - math.pi / 2) < 1e-3:
            out.append((p1.x, p1.y))
            continue
        r = min(radius, 0.45 * min(la, lb) * math.tan(half))
        d = r / math.tan(half)                       # distance from the corner to the tangent points
        t0, t1 = p1 + a * d, p1 + b * d
        bis = (a + b).normalized()
        centre = p1 + bis * (r / math.sin(half))
        a0 = math.atan2(t0.y - centre.y, t0.x - centre.x)
        a1 = math.atan2(t1.y - centre.y, t1.x - centre.x)
        sweep = (a1 - a0 + math.pi) % (2 * math.pi) - math.pi
        for k in range(n + 1):
            t = a0 + sweep * k / n
            out.append((centre.x + r * math.cos(t), centre.y + r * math.sin(t)))
    return out


def tri_count(part):
    return sum(len(f.verts) - 2 for f in part.bm.faces)


def sprocket_outline(teeth, pitch=0.0127, roller_r=0.0040, tip_h=0.0034, pts_per_tooth=12, phase=0.0):
    """Realistic sprocket outline: round roller seats between teeth, curved flanks, rounded tips."""
    R = pitch / (2 * math.sin(math.pi / teeth))
    step = 2 * math.pi / teeth
    out = []
    for k in range(teeth):
        for j in range(pts_per_tooth):
            t = j / pts_per_tooth                       # 0 = seat centre, 0.5 = tooth tip, 1 = next seat
            a = phase + step * (k + t)
            d = min(t, 1 - t) * step * R                # arc distance from the nearest seat centre
            if d < roller_r * 0.92:
                r = R - math.sqrt(max(0.0, roller_r ** 2 - d ** 2)) + roller_r * 0.35
            else:
                u = (d - roller_r * 0.92) / max(1e-6, step * R * 0.5 - roller_r * 0.92)
                r = R + roller_r * 0.35 - math.sqrt(max(0.0, roller_r ** 2 - (roller_r * 0.92) ** 2)) \
                    + (tip_h + roller_r * 0.25) * math.sin(min(1.0, u) * math.pi / 2) ** 0.8
            out.append((r * math.cos(a), r * math.sin(a)))
    return out
