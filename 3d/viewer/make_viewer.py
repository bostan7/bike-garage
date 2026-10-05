"""Build an HTML viewer for 3d/models/bike.glb (part info from the app's SeedData).

  python 3d/viewer/make_viewer.py OUT.html              # single file, model embedded
  python 3d/viewer/make_viewer.py OUT.html --external   # model written next to the page as base64 text
                                                        # chunks bike-glb-N.txt (for models too big to embed;
                                                        # artifacts serve .txt but not .glb)
"""
import base64
import json
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
GLB = os.path.join(ROOT, "3d", "models", "bike.glb")
SEED = os.path.join(ROOT, "android", "app", "src", "main", "java", "dev", "toni", "scalebike", "data", "SeedData.kt")
CATEGORY = {"FRAME": "Frame & fork", "COCKPIT": "Cockpit", "BRAKES": "Brakes", "DRIVETRAIN": "Drivetrain",
            "WHEELS": "Wheels & tyres", "CONTACT": "Saddle & seatpost"}
# Toni's changes to the stock bike that are already in the 3D model but not yet in the app's SeedData
MODIFICATIONS = {
    "tire_front": {"model": "Rekon Race EXO TR Tan Wall", "spec": "29 × 2.35\" (60-622) · 60 TPI · Dual · TB00219800 · Toni's upgrade from the stock 2.25 · inner tube"},
    "tire_rear": {"model": "Rekon Race EXO TR Tan Wall", "spec": "29 × 2.35\" (60-622) · 60 TPI · Dual · TB00219800 · Toni's upgrade from the stock 2.25 · inner tube"},
}


def parts_from_seed():
    src = open(SEED, encoding="utf-8").read()
    pat = re.compile(r'part\(\s*"(?P<slot>[a-z_]+)",\s*(?P<cat>[A-Z]+),\s*"(?P<name>[^"]*)",\s*"(?P<brand>[^"]*)",'
                     r'\s*"(?P<model>[^"]*)",\s*"(?P<spec>(?:[^"\\]|\\.)*)"', re.S)
    out = {}
    for m in pat.finditer(src):
        out[m["slot"]] = {"name": m["name"], "brand": m["brand"], "model": m["model"],
                          "spec": m["spec"].replace('\\"', '"'), "category": CATEGORY[m["cat"]]}
    return out


def triangle_count(data):
    clen = struct.unpack_from("<I", data, 12)[0]
    gltf = json.loads(data[20:20 + clen])
    acc = gltf["accessors"]
    return sum(acc[p["indices"]]["count"] // 3 for m in gltf["meshes"] for p in m["primitives"] if "indices" in p)


def main():
    out = sys.argv[1]
    external = "--external" in sys.argv[2:]
    data = open(GLB, "rb").read()
    parts = parts_from_seed()
    for slot, changes in MODIFICATIONS.items():
        parts[slot].update(changes)
    html = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    b64 = base64.b64encode(data).decode("ascii")
    chunks = []
    if external:
        size = 8_000_000                     # keep every chunk well under the 16 MB per-file limit
        for i in range(0, len(b64), size):
            name = f"bike-glb-{len(chunks)}.txt"
            open(os.path.join(os.path.dirname(os.path.abspath(out)), name), "w", encoding="ascii").write(b64[i:i + size])
            chunks.append(name)
    html = (html.replace("__PARTS_JSON__", json.dumps(parts, ensure_ascii=False).replace("</", "<\\/"))
                .replace("__GLB_BASE64__", "" if external else b64)
                .replace("__GLB_CHUNKS__", json.dumps(chunks))
                .replace("__TRIS__", f"{triangle_count(data):,}")
                .replace("__MB__", f"{len(data) / 1e6:.1f}"))
    open(out, "w", encoding="utf-8").write(html)
    print(f"{out}: {os.path.getsize(out) / 1e6:.2f} MB, {len(parts)} parts")


if __name__ == "__main__":
    main()
