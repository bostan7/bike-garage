"""Compare a 'side_photo' render with SCOTT's official studio photo (same scale and framing).

  python 3d/blender/compare_photo.py RENDER.png OUT_DIR [--crop x0,y0,x1,y1]

Writes side_by_side.jpg, overlay.jpg (50/50 blend) and edges.jpg (photo edges red, render edges cyan).
"""
import argparse
import os

import numpy as np
from PIL import Image, ImageFilter, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
PHOTO = os.path.join(HERE, "..", "..", "photos", "online-reference", "scott-official", "280483_1699164_png_zoom_11.jpg")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("render")
    ap.add_argument("out")
    ap.add_argument("--crop", default="0,380,2000,1620")
    ap.add_argument("--scale", type=float, default=0.5)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    crop = tuple(int(v) for v in a.crop.split(","))

    photo = Image.open(PHOTO).convert("RGB")
    rnd = Image.open(a.render).convert("RGBA")
    white = Image.new("RGBA", rnd.size, (255, 255, 255, 255))
    rnd = Image.alpha_composite(white, rnd).convert("RGB")

    def shrink(im):
        im = im.crop(crop)
        return im.resize((int(im.width * a.scale), int(im.height * a.scale)), Image.LANCZOS)

    p, r = shrink(photo), shrink(rnd)
    sbs = Image.new("RGB", (p.width, p.height * 2), "white")
    sbs.paste(p, (0, 0))
    sbs.paste(r, (0, p.height))
    sbs.save(os.path.join(a.out, "side_by_side.jpg"), quality=88)
    Image.blend(p, r, 0.5).save(os.path.join(a.out, "overlay.jpg"), quality=88)

    def edges(im):
        g = ImageOps.grayscale(im).filter(ImageFilter.FIND_EDGES)
        return np.asarray(g) > 40
    ep, er = edges(p), edges(r)
    out = np.full((p.height, p.width, 3), 255, np.uint8)
    out[ep] = (220, 30, 30)
    out[er] = (0, 160, 220)
    out[ep & er] = (20, 20, 20)
    Image.fromarray(out).save(os.path.join(a.out, "edges.jpg"), quality=88)
    print("written to", a.out)


if __name__ == "__main__":
    main()
