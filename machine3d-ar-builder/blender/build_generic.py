"""Generic blueprint-based Blender assembly renderer and USDZ exporter.

Blender 4.x/5.x: blender --background --python-exit-code 2 --python blender/build_generic.py -- --out DIR
Blueprint JSON is authored by a template or by an AI agent using the skill rules.
"""
from __future__ import annotations
import argparse
import json
import math
import sys
import traceback
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from machine3d.blueprints import COLORS, validate_blueprint


def mat(name):
    color = COLORS[name]
    result = bpy.data.materials.get("M3D_" + name) or bpy.data.materials.new("M3D_" + name)
    result.diffuse_color = tuple(color)
    result.use_nodes = True
    bsdf = result.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = tuple(color)
        bsdf.inputs["Metallic"].default_value = 0.75 if name not in ("blue","green","cream") else .15
        bsdf.inputs["Roughness"].default_value = .37
    return result


def axis_rotate(obj, axis):
    if axis == "Y": obj.rotation_euler[0] = math.pi / 2
    elif axis == "X": obj.rotation_euler[1] = math.pi / 2


def add_mesh_of_part(p, parent):
    d = p["dimensions"]
    shape = p["primitive"]
    material = mat(p.get("material", "steel"))
    axis = d.get("axis", "Z")
    if shape == "box":
        bpy.ops.mesh.primitive_cube_add(size=1)
        obj = bpy.context.object
        obj.dimensions = (d["x"], d["y"], d["z"])
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    elif shape == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=d["radius"])
        obj = bpy.context.object
    elif shape == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=d["radius"], depth=d["depth"])
        obj = bpy.context.object
        axis_rotate(obj, axis)
    elif shape == "cone":
        bpy.ops.mesh.primitive_cone_add(vertices=48, radius1=d["radiusBottom"],
                                         radius2=d["radiusTop"], depth=d["depth"])
        obj = bpy.context.object
        axis_rotate(obj, axis)
    elif shape == "torus":
        bpy.ops.mesh.primitive_torus_add(major_segments=64, minor_segments=12,
                                         major_radius=d["majorRadius"], minor_radius=d["minorRadius"])
        obj = bpy.context.object
        axis_rotate(obj, axis)
    elif shape == "hollow_cylinder":
        # Actual annular surface, including end annuli and inner wall.
        inner, outer, half = d["innerRadius"], d["outerRadius"], d["depth"] / 2
        vertices, faces = [], []
        N = 64
        for radius in (inner, outer):
            for z in (-half, half):
                vertices.extend((radius*math.cos(i*2*math.pi/N), radius*math.sin(i*2*math.pi/N), z) for i in range(N))
        for i in range(N):
            j = (i+1)%N
            faces.extend([
                (N+i, N+j, j, i),               # inside
                (2*N+i, 3*N+i, 3*N+j, 2*N+j), # outside
                (i, j, 2*N+j, 2*N+i),         # lower rim
                (N+i, 3*N+i, 3*N+j, N+j),     # upper rim
            ])
        mesh = bpy.data.meshes.new(p["id"] + "_annular_mesh")
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        obj = bpy.data.objects.new(p["id"] + "_mesh", mesh)
        bpy.context.collection.objects.link(obj)
        axis_rotate(obj, axis)
    elif shape == "gear":
        bpy.ops.mesh.primitive_cylinder_add(vertices=max(48, 4*d["teeth"]),
                                             radius=d["radius"]*.88, depth=d["depth"])
        obj = bpy.context.object
        axis_rotate(obj, axis)
        # Separate simple boxes for teeth; educational schematic, not involute teeth.
        for i in range(d["teeth"]):
            theta = 2*math.pi*i/d["teeth"]
            bpy.ops.mesh.primitive_cube_add(size=1)
            tooth = bpy.context.object
            tooth.name = p["id"] + "_Tooth_%02d" % i
            tooth.dimensions = (d["radius"]*.25, d["radius"]*.20, d["depth"])
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            tooth.location = (d["radius"]*.90*math.cos(theta), d["radius"]*.90*math.sin(theta), 0)
            tooth.rotation_euler.z = theta
            tooth.parent = obj
            tooth.data.materials.append(material)
        # Rotate the gear parent (and its teeth) as a unit.
    elif shape == "tube":
        bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=d["radius"], depth=d["length"])
        obj = bpy.context.object
        axis_rotate(obj, axis)
    else:
        raise ValueError("Unsupported shape " + shape)
    obj.name = p["id"] + "_mesh"
    obj.parent = parent
    obj.data.materials.append(material)
    if shape not in ("sphere", "gear"):
        bevel = obj.modifiers.new("EdgeBevel", "BEVEL")
        bevel.width = min(.001, min(d.values() if not any(isinstance(v,str) for v in d.values()) else [0.01]) / 12)
        bevel.segments = 2
    return obj


def build_scene(spec):
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system = "METRIC"
    bpy.context.scene.frame_start = 1
    bpy.context.scene.render.fps = 30
    bpy.context.scene.render.resolution_x = 1000
    bpy.context.scene.render.resolution_y = 1000
    bpy.context.scene.render.resolution_percentage = 100
    try: bpy.context.scene.render.engine = "BLENDER_EEVEE_NEXT"
    except (TypeError, ValueError):
        try: bpy.context.scene.render.engine = "BLENDER_EEVEE"
        except (TypeError, ValueError):
            bpy.context.scene.render.engine = "CYCLES"
            bpy.context.scene.cycles.samples = 16
    root = bpy.data.objects.new("MachineRoot", None)
    bpy.context.collection.objects.link(root)
    entities = {}
    for p in spec["components"]:
        component = bpy.data.objects.new(p["id"], None)
        bpy.context.collection.objects.link(component)
        component["component_id"] = p["id"]
        component.location = p["position"]
        component.rotation_euler = [math.radians(x) for x in p.get("rotationDegrees", [0,0,0])]
        entities[p["id"]] = component
    for p in spec["components"]:
        component = entities[p["id"]]
        # Positions are local to parent, if set.
        component.parent = entities[p["parent"]] if p.get("parent") else root
        add_mesh_of_part(p, component)
    return root, entities


def animate(spec, entities):
    scene = bpy.context.scene
    frame_count = 121
    scene.frame_end = frame_count
    baseline = {name: (tuple(o.location), tuple(o.rotation_euler)) for name,o in entities.items()}
    for frame in range(1, frame_count + 1):
        theta = (frame-1) * 2*math.pi/(frame_count-1)
        for j in spec["animation"]["joints"]:
            component = entities[j["entity"]]
            loc, rot = baseline[j["entity"]]
            ratio, phase = j.get("ratio",1),j.get("phase",0)
            norm = math.sqrt(sum(a*a for a in j["axis"]))
            axis = [a/norm for a in j["axis"]]
            value = ratio*theta + phase
            if j["type"] == "rotate":
                component.rotation_euler = [r + ax*value for r,ax in zip(rot,axis)]
                component.keyframe_insert(data_path="rotation_euler", frame=frame)
            elif j["type"] == "oscillate":
                angle = j.get("offset",0) + j.get("amplitude",0)*math.sin(value)
                component.rotation_euler = [r + ax*angle for r,ax in zip(rot,axis)]
                component.keyframe_insert(data_path="rotation_euler", frame=frame)
            elif j["type"] == "slide":
                shift = j.get("offset",0) + j.get("amplitude",0)*math.sin(value)
                component.location = [v + ax*shift for v,ax in zip(loc,axis)]
                component.keyframe_insert(data_path="location", frame=frame)
    scene.frame_set(1)


def setup_camera(spec):
    points = [p["position"] for p in spec["components"]]
    mins = [min(p[i] for p in points) for i in range(3)]
    maxs = [max(p[i] for p in points) for i in range(3)]
    center = Vector([(mins[i]+maxs[i])/2 for i in range(3)])
    extent = max(maxs[i]-mins[i] for i in range(3)) + .25
    extent = max(.30,extent)
    bpy.ops.object.camera_add(location=(center + Vector((extent*1.5, -extent*2, extent*1.25))))
    camera = bpy.context.object
    camera.name = "PreviewCamera"
    camera.rotation_euler = (center-camera.location).to_track_quat("-Z","Y").to_euler()
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = extent * 2.25
    bpy.context.scene.camera = camera
    world = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (.06,.08,.10,1)
        bg.inputs["Strength"].default_value = .7
    for idx, ofs in enumerate(((1, -2, 2),(-1,1,2))):
        bpy.ops.object.light_add(type="AREA", location=center + Vector(ofs)*extent)
        o = bpy.context.object
        o.name = "StudioLight_%d" % idx
        o.data.energy = 500
        o.data.size = extent*1.5
        o.rotation_euler = (center-o.location).to_track_quat("-Z","Y").to_euler()


def export_usdz(output):
    bpy.context.scene.frame_set(1)
    props = set(bpy.ops.wm.usd_export.get_rna_type().properties.keys())
    options = {
        "filepath":str(output), "export_animation":False, "export_materials":True,
        "export_cameras":False,"export_lights":False,"convert_orientation":True,
        "export_global_up_selection":"Y","export_global_forward_selection":"NEGATIVE_Z",
        "export_meshes":True,"generate_preview_surface":True,"check_existing":False,
    }
    result = bpy.ops.wm.usd_export(**{k:v for k,v in options.items() if k in props})
    if "FINISHED" not in result or not output.is_file():
        raise RuntimeError("USDZ export failed: " + str(output))


def main():
    argparser = argparse.ArgumentParser()
    argparser.add_argument("--out", required=True)
    cli = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    opts = argparser.parse_args(cli)
    out = Path(opts.out).resolve()
    spec = json.loads((out / "blueprint.json").read_text(encoding="utf-8"))
    validate_blueprint(spec)
    _, entities = build_scene(spec)
    animate(spec, entities)
    setup_camera(spec)
    missing = [p["id"] for p in spec["components"] if p["id"] not in bpy.data.objects]
    report = {
        "passed":not missing,"missing":missing,"components":len(entities),
        "meshCount":sum(o.type == "MESH" for o in bpy.data.objects),
        "animationJoints":len(spec["animation"]["joints"]),
        "blenderVersion":bpy.app.version_string,
    }
    (out / "blender_validation.json").write_text(json.dumps(report,indent=2)+"\n")
    if missing: raise RuntimeError("Generated scene missing components: " + str(missing))
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "machine.blend"))
    export_usdz(out / "machine.usdz")
    try:
        bpy.context.scene.render.filepath = str(out / "preview.png")
        bpy.ops.render.render(write_still=True)
    except Exception as error:
        (out / "preview_error.txt").write_text(str(error) + "\n")
        print("WARNING: preview render failed:",error)
    print("BUILT", out)


if __name__ == "__main__":
    try: main()
    except Exception:
        traceback.print_exc()
        raise
