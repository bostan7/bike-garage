"""Build the clickable garage UI prototype (landscape game screen) as one HTML page.

  python design/prototype/make_prototype.py OUT_DIR

Embeds the phone model (android/app/src/main/assets/bike.glb, Draco) and the app's part list.
Publish OUT_DIR/garage-prototype.html with draco_decoder.js next to it (three@0.147.0 examples/js/libs/draco).
"""
import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "3d", "viewer"))
from make_viewer import MODIFICATIONS, parts_from_seed  # noqa: E402

GLB = os.path.join(ROOT, "android", "app", "src", "main", "assets", "bike.glb")


def main():
    out_dir = sys.argv[1]
    os.makedirs(out_dir, exist_ok=True)
    parts = parts_from_seed()
    for slot, changes in MODIFICATIONS.items():
        parts[slot].update(changes)
    html = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    html = (html.replace("__PARTS_JSON__", json.dumps(parts, ensure_ascii=False).replace("</", "<\\/"))
                .replace("__GLB_BASE64__", base64.b64encode(open(GLB, "rb").read()).decode("ascii")))
    out = os.path.join(out_dir, "garage-prototype.html")
    open(out, "w", encoding="utf-8").write(html)
    print(f"{out}: {os.path.getsize(out) / 1e6:.2f} MB, {len(parts)} parts")


if __name__ == "__main__":
    main()
