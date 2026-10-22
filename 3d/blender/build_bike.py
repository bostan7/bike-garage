"""Build Toni's SCOTT Scale 980 (Dark Grey, L) in Blender and export it for the app.

Run (headless):
  blender --background --factory-startup --python 3d/blender/build_bike.py -- \
      --glb 3d/models/bike.glb [--glb-draco android/app/src/main/assets/bike.glb] [--no-accessories] \
      [--blend out.blend] [--render DIR] [--views side_photo,front34]

Every part is one object named after its app slot (frame, fork, chain, ...); see "Part slots" in the root README.
Toni's accessories (mudguards, lights, bell, lock, reflectors) are extra objects named acc_* (bikelib/accessories.py),
built by default; --no-accessories leaves them out.
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

from bikelib import accessories, brakes, cockpit, drivetrain, fork, frame, materials, preview, seat, wheels  # noqa: E402

SLOTS = ["frame", "fork", "headset", "stem", "handlebar", "grips", "shifter", "brake_front", "brake_rear",
         "rotor_front", "rotor_rear", "crankset", "bottom_bracket", "chain", "cassette", "derailleur", "pedals",
         "wheel_front", "wheel_rear", "tire_front", "tire_rear", "seatpost", "saddle"]


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.curves):
        for item in list(coll):
            coll.remove(item)
    materials.reset()


def build(with_accessories=True):
    coll = bpy.data.collections.new("ScaleBike")
    bpy.context.scene.collection.children.link(coll)
    remote_anchor = lambda side: cockpit.bar_point(side * (0.370 - 0.130 - 0.050))  # noqa: E731
    builders = [
        lambda: frame.build(coll),
        lambda: fork.build(coll, remote_anchor),
        lambda: fork.build_headset(coll),
        lambda: cockpit.build_stem(coll),
        lambda: cockpit.build_handlebar(coll),
        lambda: cockpit.build_grips(coll),
        lambda: cockpit.build_shifter(coll),
        lambda: brakes.build_brake(coll, True),
        lambda: brakes.build_brake(coll, False),
        lambda: brakes.build_rotor(coll, True),
        lambda: brakes.build_rotor(coll, False),
        lambda: drivetrain.build_crankset(coll),
        lambda: drivetrain.build_bottom_bracket(coll),
        lambda: drivetrain.build_chain(coll),
        lambda: drivetrain.build_cassette(coll),
        lambda: drivetrain.build_derailleur(coll),
        lambda: drivetrain.build_pedals(coll),
        lambda: wheels.build_wheel(coll, True),
        lambda: wheels.build_wheel(coll, False),
        lambda: wheels.build_tyre(coll, True),
        lambda: wheels.build_tyre(coll, False),
        lambda: seat.build_seatpost(coll),
        lambda: seat.build_saddle(coll),
    ]
    if with_accessories:
        builders.append(lambda: accessories.build_all(coll))
    for b in builders:
        b()
    expected = SLOTS + (accessories.NAMES if with_accessories else [])
    missing = [s for s in expected if s not in coll.objects]
    assert not missing, f"missing slots: {missing}"
    return coll


# Model v3 triangle budget per part (agreed with Toni 2026-10-05: ~580k; tyres raised to 62k each for the
# accurate Rekon Race Tan Wall tread and sidewall graphics)
BUDGET = {"frame": 110_000, "fork": 60_000, "tire_front": 62_000, "tire_rear": 62_000, "wheel_front": 30_000,
          "wheel_rear": 30_000, "chain": 40_000, "cassette": 45_000, "crankset": 18_000, "derailleur": 22_000,
          "brake_front": 15_000, "brake_rear": 15_000, "rotor_front": 10_000, "rotor_rear": 10_000,
          "saddle": 26_000, "pedals": 15_000, "grips": 10_000, "handlebar": 8_000, "stem": 8_000,
          "shifter": 8_000, "seatpost": 6_000, "headset": 4_000, "bottom_bracket": 3_000,
          # Toni's accessories (v2 2026-10-22, rebuilt from product photos): a few thousand each
          "acc_mudguard_front": 8_000, "acc_mudguard_rear": 10_000, "acc_light_rear": 4_000,
          "acc_light_front": 4_000, "acc_light_clip": 3_000, "acc_bell": 4_000, "acc_lock": 7_500,
          "acc_reflectors": 4_500}


def stats(coll):
    total = 0
    rows = []
    for ob in coll.objects:
        ob.data.calc_loop_triangles()
        tris = len(ob.data.loop_triangles)
        total += tris
        rows.append((ob.name, tris))
    for name, tris in sorted(rows, key=lambda r: -r[1]):
        budget = BUDGET.get(name, 0)
        flag = "  OVER" if tris > budget * 1.10 else ""
        print(f"  {name:16s} {tris:7d} tris  / {budget:7d}{flag}")
    print(f"  {'TOTAL':16s} {total:7d} tris  / {sum(BUDGET.values()):7d}")
    return total


def export_glb(coll, path, draco=False):
    """draco=True: Draco-compressed copy for the phone app (Filament's full gltfio decodes it).
    Positions keep 16 bits (~0.03 mm steps) so the 0.3-0.5 mm decal layers stay apart."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in coll.objects:
        ob.select_set(True)
    kwargs = dict(filepath=path, export_format='GLB', use_selection=True, export_apply=True,
                  export_extras=True, export_yup=True)
    if draco:
        kwargs.update(export_draco_mesh_compression_enable=True, export_draco_mesh_compression_level=6,
                      export_draco_position_quantization=16, export_draco_normal_quantization=10,
                      export_draco_texcoord_quantization=12, export_draco_color_quantization=10,
                      export_draco_generic_quantization=12)
        bpy.ops.export_scene.gltf(**kwargs)          # no silent fallback: an uncompressed phone model is a bug
    else:
        try:
            bpy.ops.export_scene.gltf(**kwargs)
        except TypeError:
            bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', use_selection=True)
    print(f"exported {path} ({os.path.getsize(path) / 1e6:.2f} MB{', draco' if draco else ''})")


def check_glb(path, expected):
    """Read the glb's JSON chunk and check that every expected node name is there."""
    with open(path, "rb") as fh:
        data = fh.read()
    magic, _, _ = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67, "not a glb"
    length, _ = struct.unpack_from("<II", data, 12)
    gltf = json.loads(data[20:20 + length].decode("utf-8"))
    names = [n.get("name", "") for n in gltf.get("nodes", [])]
    missing = [n for n in expected if n not in names]
    acc = sorted(n for n in names if n.startswith("acc_"))
    print(f"check {path}: {len(names)} nodes, {len([n for n in expected if n in names])}/{len(expected)} expected "
          f"names present; accessories: {', '.join(acc) or '-'}; draco: "
          f"{'KHR_draco_mesh_compression' in gltf.get('extensionsUsed', [])}")
    assert not missing, f"{path}: missing nodes {missing}"


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--glb")
    ap.add_argument("--glb-draco", help="also write a Draco-compressed copy (for the phone app)")
    ap.add_argument("--no-accessories", action="store_true", help="leave out Toni's acc_* accessories")
    ap.add_argument("--blend")
    ap.add_argument("--render")
    ap.add_argument("--views", default="")
    args = ap.parse_args(argv)

    t0 = time.time()
    clear_scene()
    coll = build(with_accessories=not args.no_accessories)
    expected = SLOTS + ([] if args.no_accessories else accessories.NAMES)
    print(f"built {len(coll.objects)} parts in {time.time() - t0:.1f}s")
    stats(coll)
    if args.glb:
        export_glb(coll, args.glb)
        check_glb(args.glb, expected)
    if args.glb_draco:
        export_glb(coll, args.glb_draco, draco=True)
        check_glb(args.glb_draco, expected)
    if args.blend:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args.blend))
    if args.render:
        eng = preview.setup(bpy.context.scene)
        print("render engine:", eng)
        preview.render_views(args.render, [v for v in args.views.split(",") if v] or None)


if __name__ == "__main__":
    main()
