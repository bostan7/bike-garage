"""Garage mesh helpers on top of the bike's meshkit (bikelib/meshkit.py is reused, not changed)."""
import math

import bmesh
import bpy
from mathutils import Matrix, Vector

from bikelib import meshkit as mk

X, Y, Z = mk.X, mk.Y, mk.Z


class GPart(mk.Part):
    """A bike-style Part plus box-projected UVs (for the tiling concrete / block / pegboard textures).

    uv_tiles: {material name: (tile_u, tile_v, origin_u, origin_v)} in metres. Faces are projected on the
    plane of their dominant normal axis: floor/ceiling (x, y), walls facing +-Y (x, z), walls facing +-X (y, z).
    """

    def __init__(self, name, uv_tiles=None):
        super().__init__(name, "garage")
        self.uv_tiles = uv_tiles or {}

    def finish(self, collection, pivot=None, sharp_angle=40.0, recalc=True):
        """Like Part.finish, plus UVs. recalc=False keeps the winding as built: needed for open, one-sided
        surfaces (floor, stripes, shutter curtain) whose facing the normal recalculation could flip."""
        bm = self.bm
        bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges[:])
        if recalc:
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
        bm.normal_update()
        uv = bm.loops.layers.uv.new("UVMap")
        for f in bm.faces:
            mat = self.mats[f.material_index] if self.mats else None
            tu, tv, ou, ov = self.uv_tiles.get(mat.name if mat else "", (1.0, 1.0, 0.0, 0.0))
            n = f.normal
            ax = max(range(3), key=lambda i: abs(n[i]))
            for loop in f.loops:
                co = loop.vert.co
                if ax == 2:
                    u, v = co.x, co.y
                elif ax == 0:
                    u, v = co.y, co.z
                else:
                    u, v = co.x, co.z
                loop[uv].uv = ((u - ou) / tu, (v - ov) / tv)
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
        # garage nodes are not bike parts: no "slot" extra, so the app never mistakes them for one
        ob["garage"] = self.name
        collection.objects.link(ob)
        return ob


def box_mm(part, lo, hi, mat, smooth=False):
    """Axis-aligned box from its min and max corners."""
    lo, hi = Vector(lo), Vector(hi)
    return mk.box(part, (lo + hi) / 2, hi - lo, mat, smooth=smooth)


def quad(part, pts, mat, smooth=False):
    """One flat polygon (any vertex count) from world points, in the given winding order."""
    vs = [part.bm.verts.new(Vector(p)) for p in pts]
    return part.tag([part.bm.faces.new(vs)], mat, smooth)


def revolve_z(part, center, profile, mat_of, n=64, smooth=True, closed=False):
    """Revolve a (radius, z) profile around the vertical axis through `center`.
    mat_of: one material, or a list with one material per profile segment. r = 0 points collapse to the axis.
    closed=True joins the last profile point back to the first (tyres: a closed cross-section)."""
    bm = part.bm
    rings = []
    axis = {}
    for k in range(n):
        a = 2.0 * math.pi * k / n
        c, s = math.cos(a), math.sin(a)
        ring = []
        for i, (r, z) in enumerate(profile):
            if r < 1e-9:
                if i not in axis:
                    axis[i] = bm.verts.new(center + Vector((0.0, 0.0, z)))
                ring.append(axis[i])
            else:
                ring.append(bm.verts.new(center + Vector((r * c, r * s, z))))
        rings.append(ring)
    faces = []
    for k in range(n):
        A, B = rings[k], rings[(k + 1) % n]
        m_seg = len(profile) if closed else len(profile) - 1
        for i in range(m_seg):
            j = (i + 1) % len(profile)
            vs = [A[i], A[j], B[j], B[i]]
            uniq = []
            for v in vs:
                if v not in uniq:
                    uniq.append(v)
            if len(uniq) < 3:
                continue
            f = bm.faces.new(uniq)
            m = mat_of[i] if isinstance(mat_of, (list, tuple)) else mat_of
            part.tag([f], m, smooth)
            faces.append(f)
    return faces


def torus(part, center, normal, R, r, mat, nu=48, nv=8, smooth=True):
    """Torus around `normal` through `center` (major radius R, tube radius r)."""
    nrm = Vector(normal).normalized()
    u = nrm.cross(Z if abs(nrm.z) < 0.9 else X).normalized()
    w = nrm.cross(u)
    bm = part.bm
    rings = []
    for i in range(nu):
        a = 2 * math.pi * i / nu
        d = u * math.cos(a) + w * math.sin(a)
        c = Vector(center) + d * R
        rings.append([bm.verts.new(c + d * (r * math.cos(2 * math.pi * j / nv)) + nrm * (r * math.sin(2 * math.pi * j / nv)))
                      for j in range(nv)])
    faces = []
    for i in range(nu):
        A, B = rings[i], rings[(i + 1) % nu]
        for j in range(nv):
            k = (j + 1) % nv
            faces.append(bm.faces.new((A[j], B[j], B[k], A[k])))
    return part.tag(faces, mat, smooth)


def cyl_z(part, x, y, z0, z1, r, mat, n=16, smooth=True):
    return mk.cyl(part, Vector((x, y, z0)), Vector((x, y, z1)), r, mat, n=n)


def clip_poly(poly, rect):
    """Sutherland-Hodgman: clip a convex 2-D polygon to an axis-aligned rectangle (u0, v0, u1, v1)."""
    u0, v0, u1, v1 = rect
    edges = [(lambda p: p[0] >= u0, lambda a, b: _cut(a, b, 0, u0)),
             (lambda p: p[0] <= u1, lambda a, b: _cut(a, b, 0, u1)),
             (lambda p: p[1] >= v0, lambda a, b: _cut(a, b, 1, v0)),
             (lambda p: p[1] <= v1, lambda a, b: _cut(a, b, 1, v1))]
    out = list(poly)
    for inside, cut in edges:
        src, out = out, []
        for i, cur in enumerate(src):
            prev = src[i - 1]
            if inside(cur):
                if not inside(prev):
                    out.append(cut(prev, cur))
                out.append(cur)
            elif inside(prev):
                out.append(cut(prev, cur))
        if not out:
            return []
    return out


def _cut(a, b, axis, value):
    t = (value - a[axis]) / (b[axis] - a[axis])
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def ccw(outline):
    """mk.prism wants a counter-clockwise outline (its caps face +W / -W)."""
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(outline, outline[1:] + outline[:1]))
    return list(outline) if area > 0 else list(outline)[::-1]


def rot_z(angle):
    return Matrix.Rotation(angle, 3, 'Z')


def plate_yz(part, outline, x, mat, thickness=0.004, holes=()):
    """2-D outline (u = world y, v = world z) as a plate lying flat on a wall facing +X, centred at world x."""
    bm = mk.plate2d(outline, holes, thickness)
    mk.place(bm, Vector((x, 0.0, 0.0)), Y, Z, X)
    return part.add_bm(bm, mat, smooth=False)


def ring_yz(part, cy, cz, r_out, r_in, x0, x1, mat, n=20):
    """Flat ring in the YZ plane (wrench ring heads, tape rolls) between x0 and x1."""
    return mk.ring_prism(part, mk.circle2d(r_out, n), mk.circle2d(r_in, n), Vector((0.0, cy, cz)), Y, Z, X, x0, x1, mat)
