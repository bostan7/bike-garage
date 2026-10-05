"""Build a single-file HTML viewer for 3d/models/bike.glb (model embedded, part info from the app's SeedData).

  python 3d/viewer/make_viewer.py OUT.html
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
    data = open(GLB, "rb").read()
    parts = parts_from_seed()
    html = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    html = (html.replace("__PARTS_JSON__", json.dumps(parts, ensure_ascii=False).replace("</", "<\\/"))
                .replace("__GLB_BASE64__", base64.b64encode(data).decode("ascii"))
                .replace("__TRIS__", f"{triangle_count(data):,}")
                .replace("__MB__", f"{len(data) / 1e6:.1f}"))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    open(out, "w", encoding="utf-8").write(html)
    print(f"{out}: {os.path.getsize(out) / 1e6:.2f} MB, {len(parts)} parts")


if __name__ == "__main__":
    main()
