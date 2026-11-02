"""Executable Blender 4.x/5.x engine builder.

Run through:
  blender --background --python-exit-code 2 --python blender/build_engine.py -- --out /path/to/output

Creates machine.blend, machine.usdz, preview.png and a Blender validation report.
Requires Blender's bundled bpy; deliberately does not depend on pip-installed bpy.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
import sys
import traceback

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from machine3d.spec import TwoStrokeSpec, COMPONENTS
from machine3d.kinematics import crank_slider


MAT = {}


def material(name, color, metallic=0.0, roughness=0.45, alpha=1.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, alpha)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Alpha"].default_value = alpha
    return mat


def empty(name, parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    if parent:
        o.parent = parent
    o["component_id"] = name
    return o


def set_material(obj, mat):
    obj.data.materials.append(mat)
    return obj


def cylinder(name, radius, depth, loc=(0, 0, 0), *, parent=None, mat=None, axis="Z", vertices=64):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=loc)
    o = bpy.context.object
    o.name = name
    if axis == "Y":
        o.rotation_euler[0] = math.pi / 2
    if mat:
        set_material(o, mat)
    if parent:
        o.parent = parent
    bevel = o.modifiers.new(name="MachinedEdge", type="BEVEL")
    bevel.width = min(0.00055, depth / 12)
    bevel.segments = 2
    o.modifiers.new(name="WeightedNormals", type="WEIGHTED_NORMAL")
    return o


def torus(name, major, minor, loc=(0, 0, 0), *, parent=None, mat=None, axis="Z"):
    bpy.ops.mesh.primitive_torus_add(major_segments=64, minor_segments=12,
                                     location=loc, major_radius=major, minor_radius=minor)
    o = bpy.context.object
    o.name = name
    if axis == "Y":
        o.rotation_euler[0] = math.pi / 2
    if parent:
        o.parent = parent
    if mat:
        set_material(o, mat)
    return o


def box(name, scale, loc, *, parent=None, mat=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if parent:
        o.parent = parent
    if mat:
        set_material(o, mat)
    return o


def barrel_with_ports(spec, parent, mat):
    """Visible cutaway cylinder wall with actual rectangular gaps for three port types.

    A grid of small annular wall patches is generated as one mesh. The holes
    are schematic (not manufacturable port/duct geometry).
    """
    angular = 96
    vertical = 65
    zmin, zmax = spec.cylinder_base_z_m, spec.cylinder_top_z_m
    r_in = spec.bore_m / 2 + 0.00045
    r_out = r_in + spec.cylinder_wall_m
    vertices, faces = [], []

    def wrap(a):
        return (a + math.pi) % (2 * math.pi) - math.pi

    def occupied(angle, z):
        # Missing front sector exposes the piston and rod to AR users.
        if abs(wrap(angle + math.pi / 2)) < 0.42:
            return False
        openings = [
            (0.0, 0.37, spec.exhaust_bottom_z_m, spec.exhaust_top_z_m),
            (2.12, 0.31, spec.transfer_bottom_z_m, spec.transfer_top_z_m),
            (-2.37, 0.31, spec.transfer_bottom_z_m, spec.transfer_top_z_m),
            (math.pi, 0.40, spec.intake_bottom_z_m, spec.intake_top_z_m),
        ]
        return not any(abs(wrap(angle - center)) < width and low < z < high
                       for center, width, low, high in openings)

    for i in range(angular):
        angle0 = 2 * math.pi * i / angular
        angle1 = 2 * math.pi * (i + 1) / angular
        mid_angle = (angle0 + angle1) / 2
        for j in range(vertical):
            z0 = zmin + (zmax - zmin) * j / vertical
            z1 = zmin + (zmax - zmin) * (j + 1) / vertical
            if not occupied(mid_angle, (z0 + z1) / 2):
                continue
            base = len(vertices)
            for r in (r_in, r_out):
                for z in (z0, z1):
                    for a in (angle0, angle1):
                        vertices.append((r * math.cos(a), r * math.sin(a), z))
            # Inner/outer surfaces plus four side caps; contiguous patch walls
            # are intentionally not welded, but mesh remains manifold per cell.
            faces.extend(tuple(base + k for k in quad) for quad in (
                (0, 1, 3, 2), (4, 6, 7, 5),
                (0, 4, 5, 1), (2, 3, 7, 6),
                (0, 2, 6, 4), (1, 5, 7, 3),
            ))
    mesh = bpy.data.meshes.new("CylinderWallMesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    o = bpy.data.objects.new("CylinderWall", mesh)
    bpy.context.collection.objects.link(o)
    o.parent = parent
    set_material(o, mat)
    return o


def add_crank(spec, root):
    crank = empty("CrankshaftAssembly", root)
    r = spec.crank_radius_m
    cylinder("MainJournal_Left", 0.010, 0.034, (0, -0.044, 0), parent=crank, mat=MAT["steel"], axis="Y")
    cylinder("MainJournal_Right", 0.010, 0.034, (0, 0.044, 0), parent=crank, mat=MAT["steel"], axis="Y")
    cylinder("CrankWeb_Left", spec.crank_web_radius_m, 0.009, (0, -0.017, 0), parent=crank, mat=MAT["steel"], axis="Y")
    cylinder("CrankWeb_Right", spec.crank_web_radius_m, 0.009, (0, 0.017, 0), parent=crank, mat=MAT["steel"], axis="Y")
    cylinder("CrankPin", 0.009, 0.046, (0, 0, r), parent=crank, mat=MAT["copper"], axis="Y")
    cylinder("Flywheel", 0.049, 0.009, (0, 0.071, 0), parent=crank, mat=MAT["darksteel"], axis="Y")
    return crank


def add_piston(spec, root):
    piston = empty("PistonAssembly", root)
    rad = spec.bore_m / 2 - 0.0007
    center_z = spec.wrist_to_crown_m - spec.piston_height_m / 2
    cylinder("PistonBody", rad, spec.piston_height_m, (0, 0, center_z), parent=piston, mat=MAT["aluminum"])
    torus("PistonRing_01", rad - 0.0001, 0.0012,
          (0, 0, spec.wrist_to_crown_m - 0.004), parent=piston, mat=MAT["darksteel"])
    torus("PistonRing_02", rad - 0.0001, 0.0012,
          (0, 0, spec.wrist_to_crown_m - 0.008), parent=piston, mat=MAT["darksteel"])
    cylinder("WristPin", 0.006, 0.066, (0, 0, 0), parent=piston, mat=MAT["copper"], axis="Y")
    torus("WristPinClip_Left", 0.0067, 0.0008, (0, -0.033, 0), parent=piston, mat=MAT["darksteel"], axis="Y")
    torus("WristPinClip_Right", 0.0067, 0.0008, (0, 0.033, 0), parent=piston, mat=MAT["darksteel"], axis="Y")
    return piston


def add_connecting_rod(spec, root):
    rod = empty("ConnectingRodAssembly", root)
    length = spec.rod_length_m
    # Rod local +Z points from crank pin to wrist pin.
    body = box("RodShank", (0.014, 0.012, length - 0.024), (0, 0, 0), parent=rod, mat=MAT["steel"])
    bevel = body.modifiers.new("RodEdgeBevel", "BEVEL")
    bevel.width = 0.003
    bevel.segments = 3
    torus("BigEndBearing", 0.012, 0.004, (0, 0, -length / 2), parent=rod, mat=MAT["darksteel"], axis="Y")
    torus("SmallEndBearing", 0.009, 0.003, (0, 0, length / 2), parent=rod, mat=MAT["copper"], axis="Y")
    return rod


def add_stationary(spec, root):
    block = empty("CylinderBlock", root)
    barrel_with_ports(spec, block, MAT["aluminum"])
    cylinder("CylinderBaseFlange", spec.bore_m / 2 + 0.008, 0.003,
             (0, 0, spec.cylinder_base_z_m - 0.002), parent=block, mat=MAT["darksteel"])
    head = empty("CylinderHead", root)
    cylinder("HeadBody", spec.bore_m / 2 + 0.010, 0.008,
             (0, 0, spec.cylinder_top_z_m + 0.004), parent=head, mat=MAT["darksteel"])
    for n in range(5):
        cylinder("CoolingFin_%02d" % n, spec.bore_m / 2 + 0.010 + 0.002 * n, 0.001,
                 (0, 0, spec.cylinder_top_z_m + 0.009 + 0.004 * n), parent=head, mat=MAT["aluminum"])
    plug = empty("SparkPlug", root)
    cylinder("PlugCeramic", 0.005, 0.018, (0, 0, spec.cylinder_top_z_m + 0.019), parent=plug, mat=MAT["ceramic"])
    cylinder("PlugElectrode", 0.0015, 0.010, (0, 0, spec.cylinder_top_z_m + 0.004), parent=plug, mat=MAT["copper"])
    # Named part markers sit next to the corresponding cut-through openings.
    exhaust = empty("ExhaustPort", root)
    box("ExhaustDuct", (0.022, 0.018, 0.018), (0.046, 0, 0.107), parent=exhaust, mat=MAT["exhaust"])
    transfer = empty("TransferPort", root)
    for i, ang in enumerate((2.12, -2.37)):
        box("TransferDuct_%d" % i, (0.010, 0.010, 0.014),
            (0.042 * math.cos(ang), 0.042 * math.sin(ang), 0.095),
            parent=transfer, mat=MAT["intake"])
    intake = empty("IntakePort", root)
    box("IntakeDuct", (0.024, 0.014, 0.014), (-0.044, 0, 0.083), parent=intake, mat=MAT["intake"])
    case = empty("Crankcase", root)
    torus("CrankcaseRim", 0.060, 0.005, (0, 0.034, 0), parent=case, mat=MAT["aluminum"], axis="Y")
    cylinder("RearCrankcaseCover", 0.059, 0.005, (0, 0.039, 0), parent=case,
             mat=MAT["darksteel"], axis="Y")
    # Discrete stand foot helps users place the mechanical model on a table.
    box("BaseStand", (0.12, 0.10, 0.008), (0, 0, -0.064), parent=root, mat=MAT["darksteel"])


def setup_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.render.film_transparent = False
    bpy.context.scene.render.resolution_x = 900
    bpy.context.scene.render.resolution_y = 900
    bpy.context.scene.render.resolution_percentage = 100
    bpy.context.scene.render.image_settings.file_format = "PNG"
    bpy.context.scene.render.fps = 30
    bpy.context.scene.frame_start = 1
    try:
        bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"
    except (TypeError, ValueError):
        try:
            bpy.context.scene.render.engine = "BLENDER_EEVEE"
        except (TypeError, ValueError):
            bpy.context.scene.render.engine = "CYCLES"
            bpy.context.scene.cycles.samples = 16
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.035, 0.055, 0.08, 1)
        bg.inputs["Strength"].default_value = 0.7
    MAT.update({
        "aluminum": material("Satin Aluminum", (0.58, 0.65, 0.72), metallic=0.8),
        "steel": material("Machined Steel", (0.37, 0.43, 0.50), metallic=0.88),
        "darksteel": material("Dark Steel", (0.12, 0.17, 0.21), metallic=0.85),
        "copper": material("Copper Bearings", (0.73, 0.37, 0.16), metallic=0.7),
        "ceramic": material("Spark Plug Ceramic", (0.93, 0.88, 0.72)),
        "intake": material("Intake Blue", (0.08, 0.50, 0.85), metallic=0.35),
        "exhaust": material("Exhaust Orange", (0.82, 0.30, 0.10), metallic=0.35),
    })


def create_camera_and_lights():
    bpy.ops.object.camera_add(location=(0.24, -0.32, 0.21))
    camera = bpy.context.object
    camera.name = "PreviewCamera"
    direction = Vector((0, 0, 0.08)) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 0.34
    bpy.context.scene.camera = camera
    for idx, (loc, power) in enumerate([((0.13, -0.15, 0.33), 450), ((-0.15, 0.05, 0.25), 350)]):
        bpy.ops.object.light_add(type="AREA", location=loc)
        light = bpy.context.object
        light.name = "StudioLight_%d" % idx
        light.data.energy = power
        light.data.shape = "DISK"
        light.data.size = 0.20
        light.rotation_euler = (Vector((0, 0, 0.08)) - light.location).to_track_quat("-Z", "Y").to_euler()


def animate_mechanism(spec, piston, crank, rod):
    frames = spec.render_samples
    bpy.context.scene.frame_end = frames + 1
    for frame in range(1, frames + 2):
        theta = 2 * math.pi * (frame - 1) / frames
        pose = crank_slider(theta, spec.crank_radius_m, spec.rod_length_m)
        crank.rotation_euler = (0, theta, 0)
        crank.keyframe_insert(data_path="rotation_euler", frame=frame)
        piston.location = (0, 0, pose.wrist_z)
        piston.keyframe_insert(data_path="location", frame=frame)
        rod.location = (pose.rod_x, 0, pose.rod_z)
        rod.rotation_euler = (0, pose.rod_tilt_y, 0)
        rod.keyframe_insert(data_path="location", frame=frame)
        rod.keyframe_insert(data_path="rotation_euler", frame=frame)
    for obj in (piston, crank, rod):
        if obj.animation_data and obj.animation_data.action:
            try:
                for fc in obj.animation_data.action.fcurves:
                    for key in fc.keyframe_points:
                        key.interpolation = "LINEAR"
            except AttributeError:
                # Blender >= 4.4 layered actions expose animation through slots.
                pass
    bpy.context.scene.frame_set(1)


def validate_blender_scene(spec):
    required = {component[0] for component in COMPONENTS}
    present = {o.name for o in bpy.data.objects}
    missing = sorted(required - present)
    failures = []
    if missing:
        failures.append("Missing entities: " + ", ".join(missing))
    for name in ("PistonAssembly", "CrankshaftAssembly", "ConnectingRodAssembly"):
        obj = bpy.data.objects.get(name)
        if obj is None or not obj.animation_data:
            failures.append("No animation for " + name)
    for obj in bpy.data.objects:
        if obj.type == "MESH" and len(obj.data.vertices) == 0:
            failures.append("Empty mesh: " + obj.name)
    return {"passed": not failures, "errors": failures,
            "entitiesFound": len(required - set(missing)),
            "sceneMeshCount": sum(1 for obj in bpy.data.objects if obj.type == "MESH"),
            "blenderVersion": bpy.app.version_string}


def export_usdz(output_path):
    bpy.context.scene.frame_set(1)
    props = set(bpy.ops.wm.usd_export.get_rna_type().properties.keys())
    desired = {
        "filepath": str(output_path), "export_animation": False,
        "export_materials": True, "export_cameras": False, "export_lights": False,
        "convert_orientation": True, "export_global_up_selection": "Y",
        "export_global_forward_selection": "NEGATIVE_Z",
        "export_meshes": True, "generate_preview_surface": True,
        "check_existing": False,
    }
    options = {k: v for k, v in desired.items() if k in props}
    if "convert_orientation" not in props:
        print("WARNING: Blender USD operator lacks convert_orientation; verify axes in RealityKit")
    result = bpy.ops.wm.usd_export(**options)
    if "FINISHED" not in result or not output_path.is_file():
        raise RuntimeError("Blender USDZ export failed: " + str(result))


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--out", required=True)
    cli = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = argparser.parse_args(cli)
    out = Path(opts.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    d = json.loads((out / "geometry_spec.json").read_text())
    spec = TwoStrokeSpec(**{k: v for k, v in d.items() if k in TwoStrokeSpec.__dataclass_fields__})
    spec.validate()
    setup_scene()
    root = empty("TwoStrokeEngine")
    piston = add_piston(spec, root)
    crank = add_crank(spec, root)
    rod = add_connecting_rod(spec, root)
    add_stationary(spec, root)
    animate_mechanism(spec, piston, crank, rod)
    create_camera_and_lights()
    check = validate_blender_scene(spec)
    (out / "blender_validation.json").write_text(json.dumps(check, indent=2) + "\n")
    if not check["passed"]:
        raise RuntimeError("Blender scene validation failed: " + str(check["errors"]))
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "machine.blend"))
    export_usdz(out / "machine.usdz")
    try:
        bpy.context.scene.render.filepath = str(out / "preview.png")
        bpy.ops.render.render(write_still=True)
    except Exception as e:
        (out / "preview_error.txt").write_text(str(e) + "\n")
        print("WARNING preview render failed:", e)
    print("BUILT:", out)
    print("VALIDATED COMPONENTS:", check["entitiesFound"])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise
