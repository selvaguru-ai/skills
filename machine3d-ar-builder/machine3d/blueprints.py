"""Generic, reusable machine blueprints for procedural educational AR assemblies.

A blueprint describes WHAT to model. A Blender generator interprets it. Machine
families here are exemplars, not manufacturer-verified CAD. An AI agent can author
new blueprints for arbitrary machine types with the same documented contract.
"""
from __future__ import annotations
import copy
import json
import math
import re
from pathlib import Path

SUPPORTED_SHAPES = {"box", "cylinder", "hollow_cylinder", "sphere", "torus", "cone", "gear", "tube"}
SUPPORTED_JOINTS = {"rotate", "slide", "oscillate"}
COLORS = {
    "aluminum": [0.65, 0.70, 0.75, 1], "steel": [0.36, 0.44, 0.52, 1],
    "dark": [0.15, 0.19, 0.25, 1], "copper": [0.77, 0.43, 0.21, 1],
    "blue": [0.13, 0.45, 0.85, 1], "orange": [0.91, 0.41, 0.12, 1],
    "green": [0.17, 0.68, 0.40, 1], "cream": [0.86, 0.82, 0.72, 1],
}


def part(pid: str, name: str, desc: str, primitive: str, position, dimensions, *,
         material="steel", movable=False, rotation=None, **extra):
    result = {
        "id": pid, "name": name, "description": desc, "primitive": primitive,
        "position": list(position), "dimensions": dict(dimensions),
        "material": material, "movable": movable,
        "rotationDegrees": list(rotation or [0, 0, 0]),
    }
    result.update(extra)
    return result


def joint(entity: str, kind: str, axis, *, ratio=1.0, phase=0.0, amplitude=0.0, offset=0.0):
    return dict(entity=entity, type=kind, axis=list(axis), ratio=ratio,
                phase=phase, amplitude=amplitude, offset=offset)


def blueprint(machine_id: str, name: str, machine_type: str, components: list,
              joints: list, *, rpm=120, max_rpm=3000, notes=None, accuracy="conceptual-educational"):
    return {
        "schemaVersion": 2, "id": machine_id, "displayName": name,
        "machineType": machine_type, "accuracy": accuracy, "units": "meters",
        "coordinateSystem": "Z_UP", "components": components,
        "animation": {"schemaVersion": 2, "machineId": machine_id,
                      "mechanism": "generic_joints", "defaultRPM": rpm,
                      "maxRPM": max_rpm, "joints": joints},
        "warnings": notes or ["Educational conceptual geometry. Not manufacturer-verified or suitable for fabrication."],
    }


def electric_motor() -> dict:
    c = [
        part("Housing", "Motor housing", "Protective stationary cylindrical enclosure.", "hollow_cylinder", [0,0,0], {"outerRadius":.077,"innerRadius":.067,"depth":.19,"axis":"Y"}, material="aluminum"),
        part("RearCap", "Rear end cap", "Supports the rear shaft bearing.", "cylinder", [0,-.10,0], {"radius":.075,"depth":.012,"axis":"Y"}, material="dark"),
        part("FrontCap", "Front end cap", "Supports the front shaft bearing.", "hollow_cylinder", [0,.10,0], {"outerRadius":.075,"innerRadius":.010,"depth":.012,"axis":"Y"}, material="dark"),
        part("Stator", "Stator core", "Stationary magnetic core around the rotor.", "hollow_cylinder", [0,0,0], {"outerRadius":.066,"innerRadius":.044,"depth":.15,"axis":"Y"}, material="steel"),
        part("Rotor", "Rotor", "Rotating electromagnetic component.", "cylinder", [0,0,0], {"radius":.040,"depth":.145,"axis":"Y"}, material="copper", movable=True),
        part("Shaft", "Output shaft", "Carries motor torque to an external load.", "cylinder", [0,0,0], {"radius":.009,"depth":.29,"axis":"Y"}, material="dark", movable=True),
        part("TerminalBox", "Terminal housing", "Connection point for electrical power.", "box", [0,0,.092], {"x":.067,"y":.07,"z":.038}, material="blue"),
        part("BearingFront", "Front bearing", "Supports the rotating shaft.", "torus", [0,.105,0], {"majorRadius":.017,"minorRadius":.005,"axis":"Y"}, material="steel"),
    ]
    return blueprint("electric_motor", "Electric motor (cutaway concept)", "electric motor", c,
                     [joint("Rotor","rotate",[0,1,0]), joint("Shaft","rotate",[0,1,0])], rpm=900, max_rpm=6000,
                     notes=["Conceptual motor: windings and electromagnetic fields are illustrative, not simulated.", "Casing is an unsectioned hollow shell; hide parts in AR to inspect inside."])


def gearbox() -> dict:
    c = [
        part("Housing", "Gearbox housing", "Supports the shafts and encloses the gear train.", "box", [0,0,-.065], {"x":.33,"y":.24,"z":.015}, material="dark"),
        part("InputShaft", "Input shaft", "Receives input torque.", "cylinder", [-.072,0,.015], {"radius":.010,"depth":.25,"axis":"Y"}, material="steel", movable=True),
        part("InputGear", "Small driving gear", "Rotates faster than the driven gear.", "gear", [-.072,0,.015], {"radius":.036,"depth":.024,"teeth":16,"axis":"Y"}, material="blue", movable=True),
        part("OutputShaft", "Output shaft", "Transmits reduced speed and increased ideal torque.", "cylinder", [.035,0,.015], {"radius":.012,"depth":.25,"axis":"Y"}, material="steel", movable=True),
        part("OutputGear", "Large driven gear", "Receives power from the input gear.", "gear", [.035,0,.015], {"radius":.071,"depth":.024,"teeth":32,"axis":"Y"}, material="copper", movable=True),
        part("InputBearing", "Input bearing", "Supports input shaft rotation.", "torus", [-.072,-.11,.015], {"majorRadius":.016,"minorRadius":.005,"axis":"Y"}, material="dark"),
        part("OutputBearing", "Output bearing", "Supports output shaft rotation.", "torus", [.035,-.11,.015], {"majorRadius":.018,"minorRadius":.005,"axis":"Y"}, material="dark"),
    ]
    return blueprint("spur_gearbox", "Two-gear reduction gearbox", "gearbox", c,
                     [joint("InputGear","rotate",[0,1,0]), joint("InputShaft","rotate",[0,1,0]),
                      joint("OutputGear","rotate",[0,1,0],ratio=-0.5), joint("OutputShaft","rotate",[0,1,0],ratio=-0.5)],rpm=180,max_rpm=2400,
                     notes=["Schematic involute approximation; not a verified tooth-contact or tolerance design.", "Assumes a 2:1 ideal reduction, no backlash or losses."])


def pump() -> dict:
    c = [
        part("PumpHousing", "Volute housing", "Contains the impeller and channels liquid toward the outlet.", "hollow_cylinder", [0,0,0], {"outerRadius":.11,"innerRadius":.085,"depth":.055,"axis":"Y"}, material="aluminum"),
        part("Impeller", "Impeller", "Transfers rotating shaft energy into liquid flow.", "gear", [0,0,0], {"radius":.072,"depth":.018,"teeth":8,"axis":"Y"}, material="copper", movable=True),
        part("Shaft", "Drive shaft", "Turns the impeller.", "cylinder", [0,0,0], {"radius":.009,"depth":.20,"axis":"Y"}, material="steel", movable=True),
        part("Inlet", "Suction inlet", "Fluid enters axially near the impeller eye.", "hollow_cylinder", [0,-.056,0], {"outerRadius":.031,"innerRadius":.024,"depth":.080,"axis":"Y"}, material="blue"),
        part("Outlet", "Discharge outlet", "Fluid exits the pump casing.", "hollow_cylinder", [.094,.02,.060], {"outerRadius":.026,"innerRadius":.020,"depth":.085,"axis":"Z"}, material="blue"),
        part("Base", "Pump mount", "Supports the housing.", "box", [0,0,-.137], {"x":.22,"y":.17,"z":.017}, material="dark"),
    ]
    return blueprint("centrifugal_pump", "Centrifugal pump (conceptual cutaway)", "centrifugal pump", c,
                     [joint("Impeller","rotate",[0,1,0]), joint("Shaft","rotate",[0,1,0])],rpm=900,max_rpm=5000,
                     notes=["Impeller blade and casing are simplified visualizations; no CFD or flow accuracy."])


def atm() -> dict:
    c = [
        part("Cabinet", "ATM cabinet", "Encloses computing, banking, and cash transport modules.", "box", [0,0,.75], {"x":.56,"y":.40,"z":1.5}, material="aluminum"),
        part("Screen", "Display", "Shows transaction instructions.", "box", [0,-.207,1.22], {"x":.34,"y":.012,"z":.24}, material="dark"),
        part("Keypad", "Keypad", "Accepts PIN entry and commands.", "box", [0,-.23,.91], {"x":.23,"y":.027,"z":.13}, material="steel"),
        part("CardSlot", "Card reader", "Guides cards through the reader mechanism.", "box", [.15,-.219,1.04], {"x":.12,"y":.022,"z":.03}, material="blue"),
        part("CashSlot", "Cash dispensing slot", "Opening for dispensed banknotes.", "box", [0,-.219,.65], {"x":.34,"y":.025,"z":.045}, material="dark"),
        part("CashCassette", "Cash cassette", "Removable internal banknote storage.", "box", [0,.0,.40], {"x":.39,"y":.22,"z":.16}, material="green",movable=True),
        part("TransportRoller1", "Feed roller", "Moves banknotes along the dispensing path.", "cylinder", [-.08,-.07,.66], {"radius":.017,"depth":.26,"axis":"X"},material="copper",movable=True),
        part("TransportRoller2", "Output roller", "Transfers banknotes toward the exit.", "cylinder", [.08,-.07,.66], {"radius":.017,"depth":.26,"axis":"X"},material="copper",movable=True),
    ]
    return blueprint("atm_machine", "ATM with dispensing mechanism (concept)", "ATM", c,
                     [joint("TransportRoller1","rotate",[1,0,0]),joint("TransportRoller2","rotate",[1,0,0],ratio=-1)],rpm=60,max_rpm=600,
                     notes=["Conceptual teaching model, not a specific manufacturer's secure ATM architecture.", "Actual dispenser timing, sensors and banknote path require a verified design."])


def washing_machine() -> dict:
    c = [
        part("Cabinet", "Washing machine cabinet", "Outer enclosure and structural support.", "box", [0,0,.46], {"x":.64,"y":.61,"z":.92}, material="aluminum"),
        part("OuterTub", "Outer tub", "Stationary water-containing tub.", "hollow_cylinder", [0,-.04,.49], {"outerRadius":.265,"innerRadius":.24,"depth":.40,"axis":"Y"}, material="blue"),
        part("Drum", "Inner drum", "Rotates clothing during wash and spin cycles.", "hollow_cylinder", [0,-.04,.49], {"outerRadius":.225,"innerRadius":.211,"depth":.35,"axis":"Y"}, material="steel",movable=True),
        part("DriveShaft", "Drum shaft", "Transfers motor torque to drum.", "cylinder", [0,.17,.49], {"radius":.018,"depth":.20,"axis":"Y"},material="dark",movable=True),
        part("Door", "Door ring", "Front access opening.", "torus", [0,-.342,.49], {"majorRadius":.238,"minorRadius":.021,"axis":"Y"}, material="dark"),
        part("ControlPanel", "Control panel", "Selects operating cycles.", "box", [0,-.313,.82], {"x":.55,"y":.02,"z":.10},material="cream"),
    ]
    return blueprint("washing_machine", "Front-load washing machine (concept)", "washing machine",c,
                     [joint("Drum","rotate",[0,1,0]),joint("DriveShaft","rotate",[0,1,0])],rpm=70,max_rpm=1400,
                     notes=["Conceptual arrangement; cabinet obscures interior unless isolated or hidden in viewer."])


def gas_turbine() -> dict:
    """Schematic single-spool gas-turbine cutaway, not performance simulation."""
    c = [
        part("OuterCase", "Engine casing", "Encloses compression, combustion and turbine stages.",
             "hollow_cylinder", [0,0,0], {"outerRadius":.17,"innerRadius":.15,"depth":.75,"axis":"Y"}, material="aluminum"),
        part("Intake", "Air intake", "Guides incoming air toward the compressor.",
             "hollow_cylinder", [0,-.44,0], {"outerRadius":.18,"innerRadius":.15,"depth":.12,"axis":"Y"}, material="blue"),
        part("CompressorRotor", "Compressor rotor", "Accelerates incoming air before combustion.",
             "gear", [0,-.22,0], {"radius":.13,"depth":.036,"teeth":18,"axis":"Y"}, material="steel",movable=True),
        part("CompressorStator", "Stationary compressor guide", "Guides compressed airflow through the engine core.",
             "hollow_cylinder", [0,-.10,0], {"outerRadius":.148,"innerRadius":.105,"depth":.04,"axis":"Y"}, material="dark"),
        part("CombustionChamber", "Combustion chamber", "Mixes fuel and pressurized air, releasing heat during combustion.",
             "hollow_cylinder", [0,.06,0], {"outerRadius":.144,"innerRadius":.085,"depth":.19,"axis":"Y"}, material="orange"),
        part("TurbineRotor", "Turbine rotor", "Extracts work from hot gas to drive the compressor shaft.",
             "gear", [0,.24,0], {"radius":.128,"depth":.038,"teeth":14,"axis":"Y"}, material="copper",movable=True),
        part("MainShaft", "Central shaft", "Couples turbine torque to the compressor rotor.",
             "cylinder", [0,0,0], {"radius":.016,"depth":.80,"axis":"Y"},material="dark",movable=True),
        part("Nozzle", "Exhaust nozzle", "Channels hot exhaust gas rearward.",
             "cone", [0,.44,0], {"radiusBottom":.14,"radiusTop":.10,"depth":.16,"axis":"Y"},material="aluminum"),
    ]
    return blueprint("gas_turbine", "Single-spool gas turbine (cutaway concept)", "gas turbine / jet engine",c,
                     [joint("CompressorRotor","rotate",[0,1,0]),joint("TurbineRotor","rotate",[0,1,0]),
                      joint("MainShaft","rotate",[0,1,0])],rpm=600,max_rpm=12000,
                     notes=["Schematic compressor and turbine discs, not true aerodynamically designed blades.",
                            "No air thermodynamics, fuel injection, thermal stress, thrust or fluid simulation."])


TEMPLATES = {
    "electric_motor": electric_motor,
    "gas_turbine": gas_turbine,
    "spur_gearbox": gearbox,
    "centrifugal_pump": pump,
    "atm_machine": atm,
    "washing_machine": washing_machine,
}


def match_template(prompt: str) -> str | None:
    p = re.sub(r"\s+", " ", prompt.casefold().replace("-", " "))
    if "jet engine" in p or "gas turbine" in p or "turbine engine" in p: return "gas_turbine"
    if re.search(r"\b(atm|cash machine|cash dispenser)\b", p): return "atm_machine"
    if "washing machine" in p or "washer machine" in p: return "washing_machine"
    if "centrifugal pump" in p or "water pump" in p: return "centrifugal_pump"
    if "gearbox" in p or "gear train" in p or "gear reducer" in p: return "spur_gearbox"
    if "electric motor" in p or "induction motor" in p or "dc motor" in p: return "electric_motor"
    return None


def from_template(template: str) -> dict:
    if template not in TEMPLATES:
        raise ValueError(f"Unknown template '{template}'. Available: {', '.join(TEMPLATES)}")
    result = TEMPLATES[template]()
    validate_blueprint(result)
    return copy.deepcopy(result)


def _finite_number(value, name, *, positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    if positive and value <= 0:
        raise ValueError(f"{name} must be positive")


def _vector(value, name, *, nonzero=False):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{name} must be a 3-number array")
    for n in value: _finite_number(n, name)
    if nonzero and sum(x*x for x in value) < 1e-10:
        raise ValueError(f"{name} cannot be the zero vector")


def validate_blueprint(data: dict) -> None:
    if not isinstance(data, dict) or data.get("schemaVersion") != 2:
        raise ValueError("Expected blueprint schemaVersion 2")
    for field in ("id", "displayName", "machineType"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ValueError(f"Missing {field}")
    if not re.fullmatch(r"[a-z][a-z0-9_]*", data["id"]):
        raise ValueError("Machine id must be lowercase snake_case")
    if data.get("units") != "meters" or data.get("coordinateSystem") != "Z_UP":
        raise ValueError("Blueprint requires meters and Z_UP")
    components = data.get("components")
    if not isinstance(components, list) or not 1 <= len(components) <= 300:
        raise ValueError("Components must have 1..300 items")
    seen = set()
    for i, p in enumerate(components):
        label = f"components[{i}]"
        if not isinstance(p, dict): raise ValueError(label + " must be object")
        ident = p.get("id")
        if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", ident) or ident in seen:
            raise ValueError(label + ".id invalid or duplicate")
        seen.add(ident)
        for field in ("name", "description"):
            if not isinstance(p.get(field), str) or not p[field]: raise ValueError(f"{label}.{field} missing")
        shape = p.get("primitive")
        if shape not in SUPPORTED_SHAPES: raise ValueError(f"{label}.primitive unsupported: {shape}")
        _vector(p.get("position"), f"{label}.position")
        _vector(p.get("rotationDegrees", [0,0,0]), f"{label}.rotationDegrees")
        dimensions = p.get("dimensions")
        if not isinstance(dimensions, dict): raise ValueError(f"{label}.dimensions missing")
        numeric_required = {
            "box": ["x","y","z"], "cylinder": ["radius","depth"],
            "hollow_cylinder": ["innerRadius","outerRadius","depth"],
            "sphere": ["radius"], "torus": ["majorRadius","minorRadius"],
            "cone": ["radiusTop","radiusBottom","depth"],
            "gear": ["radius","depth","teeth"], "tube": ["radius","length"],
        }[shape]
        for field in numeric_required:
            _finite_number(dimensions.get(field), f"{label}.dimensions.{field}", positive=field != "radiusTop")
        if shape == "cone" and dimensions["radiusTop"] < 0:
            raise ValueError(label + " radiusTop cannot be negative")
        if shape == "hollow_cylinder" and dimensions["innerRadius"] >= dimensions["outerRadius"]:
            raise ValueError(label + " innerRadius must be smaller than outerRadius")
        if shape == "gear" and (not isinstance(dimensions["teeth"], int) or not 6 <= dimensions["teeth"] <= 120):
            raise ValueError(label + " teeth must be integer 6..120")
        if "axis" in dimensions and dimensions["axis"] not in ("X", "Y", "Z"):
            raise ValueError(label + ".dimensions.axis invalid")
        if "parent" in p and (p["parent"] == ident or p["parent"] not in {c.get("id") for c in components}):
            raise ValueError(label + " parent invalid")
        if p.get("material", "steel") not in COLORS: raise ValueError(label + " unknown material")
    # Catch parent cycles before Blender is invoked.
    parents = {p["id"]: p.get("parent") for p in components}
    for key in parents:
        encountered = set()
        cursor = key
        while cursor:
            if cursor in encountered: raise ValueError("Parent cycle at " + cursor)
            encountered.add(cursor)
            cursor = parents[cursor]
    animation = data.get("animation")
    if not isinstance(animation, dict) or animation.get("schemaVersion") != 2 or animation.get("mechanism") != "generic_joints":
        raise ValueError("Requires v2 generic_joints animation")
    if animation.get("machineId") != data["id"]: raise ValueError("Animation machineId mismatch")
    for field in ("defaultRPM", "maxRPM"):
        _finite_number(animation.get(field), field, positive=True)
    if animation["defaultRPM"] > animation["maxRPM"]: raise ValueError("defaultRPM exceeds maxRPM")
    joints = animation.get("joints")
    if not isinstance(joints, list) or len(joints) > 500: raise ValueError("joints must be array <= 500")
    animated_entities = set()
    for i, j in enumerate(joints):
        name = f"joints[{i}]"
        if not isinstance(j, dict) or j.get("entity") not in seen or j.get("type") not in SUPPORTED_JOINTS:
            raise ValueError(name + " invalid entity or type")
        if j["entity"] in animated_entities:
            raise ValueError(name + " duplicates target; combine motion into a single mechanism controller")
        animated_entities.add(j["entity"])
        if not next(p for p in components if p["id"] == j["entity"]).get("movable"):
            raise ValueError(name + " targets non-movable component")
        _vector(j.get("axis"), name + ".axis", nonzero=True)
        for field in ("ratio", "phase", "amplitude", "offset"):
            _finite_number(j.get(field, 0), name + "." + field)


def save_blueprint(out: Path, data: dict) -> None:
    validate_blueprint(data)
    out.mkdir(parents=True, exist_ok=True)
    (out / "blueprint.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    meta = {k: data[k] for k in ("schemaVersion", "id", "displayName", "machineType", "accuracy")}
    meta["components"] = [dict(id=p["id"], name=p["name"], description=p["description"],
                                entityName=p["id"], movable=p.get("movable", False)) for p in data["components"]]
    meta["warnings"] = data.get("warnings", [])
    (out / "machine.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    (out / "animation_spec.json").write_text(json.dumps(data["animation"], indent=2) + "\n", encoding="utf-8")
    (out / "geometry_spec.json").write_text(json.dumps({"source":"blueprint.json", "units":"meters", "components": len(data["components"])}, indent=2) + "\n", encoding="utf-8")


def scaffold(prompt: str) -> dict:
    """Return an intentionally INCOMPLETE scaffold for AI to fill; never fabricate geometry."""
    slug = re.sub(r"[^a-z0-9]+", "_", prompt.casefold()).strip("_")[:65] or "unknown_machine"
    if not slug[0].isalpha(): slug = "machine_" + slug
    return {
        "schemaVersion": 2, "id": slug, "displayName": prompt,
        "machineType": "NEEDS_RESEARCH", "accuracy": "unverified",
        "units": "meters", "coordinateSystem": "Z_UP", "components": [],
        "animation": {"schemaVersion": 2, "machineId": slug,
                      "mechanism": "generic_joints", "defaultRPM": 60,
                      "maxRPM": 1000, "joints": []},
        "warnings": ["INCOMPLETE: agent must research and fill real components/dimensions before build."],
    }
