"""Build the NFS-style night garage around the bike (room, props, neon, turntable) and export it for the app.

Run (headless):
  blender --background --factory-startup --python 3d/blender/build_garage.py -- \
      --glb 3d/models/garage.glb --glb-draco android/app/src/main/assets/garage.glb [--blend out.blend] [--render PNG]

Same conventions as the bike (build_bike.py): Blender +X forward, +Y left (non-drive side), +Z up, metres,
ground z = 0; the glTF export converts to +Y up. Layout from the approved web prototype
(design/prototype/template.html). Node names are a contract with the app, see NODES and 3d/README.md.
"""
import argparse
import json
import os
import struct
import sys
import time

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from garagelib import materials, neon, preview, props, room  # noqa: E402

NODES = ["floor", "stripes", "walls", "shutter", "props", "turntable", "neon_ring", "neon_strips", "hex_lights", "sign"]
EMISSIVE_NODES = {"neon_ring", "neon_strips", "hex_lights", "sign"}

BUDGET_TOTAL = 60_000
BUDGET = {"floor": 200, "stripes": 2_000, "walls": 2_000, "shutter": 3_000, "props": 30_000, "turntable": 4_000,
          "neon_ring": 3_000, "neon_strips": 2_000, "hex_lights": 2_000, "sign": 10_000}


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.curves,
                 bpy.data.images):
        for item in list(coll):
            coll.remove(item)
    materials.reset()


def build():
    coll = bpy.data.collections.new("Garage")
    bpy.context.scene.collection.children.link(coll)
    for b in (room.build_floor, room.build_stripes, room.build_walls, room.build_shutter, props.build_props,
              room.build_turntable, room.build_neon_ring, neon.build_strips, neon.build_hex_lights, neon.build_sign):
        b(coll)
    missing = [n for n in NODES if n not in coll.objects]
    assert not missing, f"missing nodes: {missing}"
    return coll


def stats(coll):
    total = 0
    for name in NODES:
        ob = coll.objects[name]
        ob.data.calc_loop_triangles()
        tris = len(ob.data.loop_triangles)
        total += tris
        flag = "  OVER" if tris > BUDGET[name] * 1.10 else ""
        print(f"  {name:12s} {tris:7d} tris  / {BUDGET[name]:6d}{flag}")
    print(f"  {'TOTAL':12s} {total:7d} tris  / {BUDGET_TOTAL:6d}{'  OVER' if total > BUDGET_TOTAL else ''}")
    return total


def export_glb(coll, path, draco=False):
    """Textures as JPEG (no alpha needed; keeps the noisy concrete small). draco=True: phone copy with
    16-bit positions so the 12 mm neon tubes and 2 mm floor stripes stay exact."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in coll.objects:
        ob.select_set(True)
    kwargs = dict(filepath=path, export_format='GLB', use_selection=True, export_apply=True, export_extras=True,
                  export_yup=True, export_image_format='JPEG', export_jpeg_quality=88, export_cameras=False,
                  export_lights=False)
    if draco:
        kwargs.update(export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
                      export_draco_position_quantization=16, export_draco_normal_quantization=10,
                      export_draco_texcoord_quantization=14, export_draco_color_quantization=10,
                      export_draco_generic_quantization=12)
    bpy.ops.export_scene.gltf(**kwargs)
    print(f"exported {path} ({os.path.getsize(path) / 1e6:.2f} MB{', draco' if draco else ''})")


def validate(path):
    """Parse the GLB's JSON chunk: every contract node present, emissive set on the neon materials."""
    with open(path, "rb") as f:
        data = f.read()
    magic, _, _ = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67, "not a GLB"
    ln, kind = struct.unpack_from("<II", data, 12)
    gj = json.loads(data[20:20 + ln])
    nodes = {n["name"]: n for n in gj["nodes"]}
    ok = True
    for name in NODES:
        if name not in nodes:
            print(f"  MISSING node {name}")
            ok = False
    mats = gj.get("materials", [])
    for name in EMISSIVE_NODES:
        n = nodes.get(name)
        if not n or "mesh" not in n:
            continue
        prims = gj["meshes"][n["mesh"]]["primitives"]
        em = [mats[p["material"]] for p in prims if "material" in p and max(mats[p["material"]].get("emissiveFactor", [0])) > 0]
        if not em:
            print(f"  NO EMISSIVE material on {name}")
            ok = False
    print(f"  {path}: {os.path.getsize(path) / 1e6:.2f} MB, extensions used: {gj.get('extensionsUsed', [])}")
    for m in mats:
        ef = m.get("emissiveFactor")
        if ef:
            st = m.get("extensions", {}).get("KHR_materials_emissive_strength", {}).get("emissiveStrength", 1.0)
            print(f"    emissive material {m['name']:12s} factor {[round(c, 3) for c in ef]} strength {st}")
    for name in NODES:
        n = nodes.get(name, {})
        print(f"    node {name:12s} translation {[round(c, 4) for c in n.get('translation', [0, 0, 0])]}")
    for img in gj.get("images", []):
        print(f"    image {img.get('name')} {img.get('mimeType')}")
    print("  VALID" if ok else "  INVALID")
    return ok


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb")
    ap.add_argument("--glb-draco", help="also write a Draco-compressed copy (for the phone app)")
    ap.add_argument("--blend")
    ap.add_argument("--render", help="low-res sanity render (PNG path; keep it out of the repo)")
    ap.add_argument("--render-view", default="drive", help="drive (default) or corner")
    args = ap.parse_args(argv)

    t0 = time.time()
    clear_scene()
    coll = build()
    print(f"built {len(coll.objects)} garage nodes in {time.time() - t0:.1f}s")
    stats(coll)
    ok = True
    if args.glb:
        export_glb(coll, args.glb)
        ok &= validate(args.glb)
    if args.glb_draco:
        export_glb(coll, args.glb_draco, draco=True)
        ok &= validate(args.glb_draco)
    if args.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.blend))
    if args.render:
        preview.render(os.path.abspath(args.render), view=args.render_view)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
