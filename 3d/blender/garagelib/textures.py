"""Small procedural textures (numpy), generated at build time and embedded in the glb.

Every texture tiles seamlessly (periodic noise) and is at most 1024 px. Values are sRGB.
"""
import bpy
import numpy as np

SEED = 980


def _hex(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)], dtype=np.float32)


def _periodic(n, cells, rng):
    """Smooth value noise that wraps around (n x n, `cells` random values per side)."""
    g = rng.random((cells, cells)).astype(np.float32)
    t = np.arange(n, dtype=np.float32) * cells / n
    i0 = np.floor(t).astype(int)
    f = t - i0
    f = f * f * (3 - 2 * f)
    i1 = (i0 + 1) % cells
    a, b = g[np.ix_(i0, i0)], g[np.ix_(i0, i1)]
    c, d = g[np.ix_(i1, i0)], g[np.ix_(i1, i1)]
    fx, fy = f[None, :], f[:, None]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


def _fbm(n, rng, octaves=((4, 1.0), (8, 0.5), (16, 0.25), (32, 0.125))):
    out = sum(_periodic(n, c, rng) * w for c, w in octaves)
    out -= out.min()
    return out / max(out.max(), 1e-6)


def _image(name, rgb):
    """rgb: (h, w, 3) float sRGB -> packed Blender image (PNG inside the .blend; the exporter re-encodes)."""
    h, w, _ = rgb.shape
    img = bpy.data.images.get(name) or bpy.data.images.new(name, w, h, alpha=False)
    # colour space and format first: changing them later reloads the generated image and wipes the pixels
    img.colorspace_settings.name = 'sRGB'
    img.file_format = 'PNG'
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :3] = np.clip(rgb, 0.0, 1.0)
    img.pixels.foreach_set(rgba.ravel())
    img.update()                     # without this, pack() silently stores nothing (black texture)
    img.pack()
    assert img.packed_file is not None, f"texture {name} was not packed"
    return img


def concrete_floor(n=1024):
    """Polished concrete slab (one 3.2 m slab per tile): mottled grey, fine aggregate, dark saw-cut joint
    along the tile border (the joint grid lines up with the slab grid on the floor)."""
    rng = np.random.default_rng(SEED)
    base = _hex("#2c2f33")
    mottle = _fbm(n, rng)
    blotch = _fbm(n, rng, ((3, 1.0), (6, 0.6), (12, 0.2)))
    fine = _periodic(n, 256, rng)
    v = 0.88 + 0.18 * mottle - 0.14 * np.clip(blotch - 0.55, 0, 1) * 2.0 + 0.06 * (fine - 0.5)
    rgb = base[None, None, :] * v[..., None]
    # sparse light aggregate specks (1-2 px)
    k = int(n * n * 0.004)
    ys, xs = rng.integers(0, n, k), rng.integers(0, n, k)
    rgb[ys, xs] *= rng.uniform(1.15, 1.45, (k, 1)).astype(np.float32)
    # saw-cut joint: 2 px dark core + 1 px half-dark edge on each side of the tile seam
    joint = np.ones(n, dtype=np.float32)
    joint[[0, n - 1]] = 0.18
    joint[[1, n - 2]] = 0.55
    rgb *= joint[None, :, None]
    rgb *= joint[:, None, None]
    return _image("tex_concrete_floor", rgb)


def concrete_blocks(n=512, rows=8, cols=4):
    """Painted concrete block wall (one tile = 1.6 m x 1.6 m: 8 rows of 0.2 m, 0.4 m blocks, running bond)."""
    rng = np.random.default_rng(SEED + 1)
    base = _hex("#26292d")
    v = 0.88 + 0.16 * _fbm(n, rng) + 0.08 * (_periodic(n, 128, rng) - 0.5)
    rgb = base[None, None, :] * v[..., None]
    rh, bw = n // rows, n // cols
    yy, xx = np.mgrid[0:n, 0:n]
    row = yy // rh
    shift = (row % 2) * (bw // 2)
    col = ((xx + shift) // bw) % cols
    tone = rng.uniform(0.92, 1.08, (rows, cols)).astype(np.float32)
    rgb *= tone[row, col][..., None]
    # mortar joints (4 px = 12 mm), slightly darker and flatter
    my = (yy % rh) < 2
    my |= (yy % rh) >= rh - 2
    mx = ((xx + shift) % bw) < 2
    mx |= ((xx + shift) % bw) >= bw - 2
    mortar = my | mx
    rgb[mortar] = base * 0.45
    return _image("tex_concrete_blocks", rgb)


def pegboard(n=256, holes=16):
    """Dark painted pegboard (one tile = 0.4 m: 16 x 16 holes at 25 mm)."""
    rng = np.random.default_rng(SEED + 2)
    base = _hex("#1c1f23")
    v = 0.92 + 0.12 * _fbm(n, rng, ((8, 1.0), (32, 0.4)))
    rgb = base[None, None, :] * v[..., None]
    step = n // holes
    yy, xx = np.mgrid[0:n, 0:n]
    dy = (yy % step) - step / 2 + 0.5
    dx = (xx % step) - step / 2 + 0.5
    d = np.sqrt(dx * dx + dy * dy)
    hole = np.clip((d - 1.6) / 1.0, 0.0, 1.0)          # anti-aliased hole edge, r ~ 2 px (3 mm)
    rgb *= (0.12 + 0.88 * hole)[..., None]
    return _image("tex_pegboard", rgb)
