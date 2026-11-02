"""Executable pure-Python kinematic, metadata, and export checks."""
from __future__ import annotations
from math import cos, hypot, isclose, pi, sin
from pathlib import Path
import json
import zipfile
from .kinematics import crank_slider, piston_crown_z
from .spec import TwoStrokeSpec, COMPONENTS


def validate_kinematics(spec: TwoStrokeSpec, samples: int = 361) -> dict:
    spec.validate()
    r, length = spec.crank_radius_m, spec.rod_length_m
    max_error = 0.0
    wrist_extrema = []
    min_crown_clearance = float("inf")
    for i in range(samples):
        theta = i * 2 * pi / (samples - 1)
        p = crank_slider(theta, r, length)
        rod_error = abs(hypot(p.crank_x, p.wrist_z - p.crank_z) - length)
        max_error = max(max_error, rod_error)
        wrist_extrema.append(p.wrist_z)
        min_crown_clearance = min(min_crown_clearance, spec.cylinder_top_z_m - piston_crown_z(theta, r, length, spec.wrist_to_crown_m))
    initial = crank_slider(0, r, length)
    final = crank_slider(2 * pi, r, length)
    errors = []
    if max_error > 1e-7:
        errors.append("Connecting rod length is not conserved")
    if abs((max(wrist_extrema) - min(wrist_extrema)) - spec.stroke_m) > 2e-6:
        errors.append("Piston stroke differs from specification")
    if not isclose(initial.wrist_z, final.wrist_z, abs_tol=1e-9):
        errors.append("Cycle position is not continuous")
    if min_crown_clearance < 0:
        errors.append("Piston crown collides with cylinder head")
    return {
        "passed": not errors, "errors": errors,
        "samples": samples, "maxRodLengthErrorM": max_error,
        "observedStrokeM": max(wrist_extrema) - min(wrist_extrema),
        "minHeadClearanceM": min_crown_clearance,
    }


def validate_metadata(folder: Path) -> dict:
    errors = []
    try:
        machine = json.loads((folder / "machine.json").read_text())
        anim = json.loads((folder / "animation_spec.json").read_text())
        components = machine["components"]
        component_ids = [c["id"] for c in components]
        if not component_ids or len(component_ids) != len(set(component_ids)):
            errors.append("Empty or duplicate component IDs")
        if machine.get("id") != anim.get("machineId"):
            errors.append("Machine ID and animation machineId mismatch")
        if machine.get("schemaVersion") == 2:
            from .blueprints import validate_blueprint
            blueprint_path = folder / "blueprint.json"
            if not blueprint_path.exists():
                errors.append("Missing v2 blueprint.json")
            else:
                validate_blueprint(json.loads(blueprint_path.read_text()))
            for item in anim["joints"]:
                if item["entity"] not in component_ids:
                    errors.append("Animation target missing: " + item["entity"])
        elif machine.get("schemaVersion") == 1:
            for component in COMPONENTS:
                if component[0] not in component_ids:
                    errors.append("Missing component " + component[0])
            for entity in anim["entities"].values():
                if entity not in component_ids:
                    errors.append("Animation target missing: " + entity)
            if anim["crankRadius"] <= 0 or anim["connectingRodLength"] <= anim["crankRadius"]:
                errors.append("Invalid mechanism dimensions")
        else:
            errors.append("Unsupported metadata schemaVersion")
    except (OSError, ValueError, KeyError, TypeError) as e:
        errors.append(str(e))
    return {"passed": not errors, "errors": errors}


def validate_export(folder: Path) -> dict:
    errors = []
    checks = {}
    blend = folder / "machine.blend"
    asset = folder / "machine.usdz"
    checks["blendExists"] = blend.is_file() and blend.stat().st_size > 128
    checks["usdzExists"] = asset.is_file() and asset.stat().st_size > 128
    if not checks["blendExists"]:
        errors.append("Missing or empty machine.blend")
    if not checks["usdzExists"]:
        errors.append("Missing or empty machine.usdz")
    else:
        checks["usdzArchiveValid"] = zipfile.is_zipfile(asset)
        if not checks["usdzArchiveValid"]:
            errors.append("USDZ is not a valid ZIP archive")
        else:
            with zipfile.ZipFile(asset) as z:
                roots = [name for name in z.namelist() if name.endswith((".usd", ".usda", ".usdc"))]
                checks["usdLayerPresent"] = bool(roots)
                if not roots:
                    errors.append("USDZ contains no USD layer")
    return {"passed": not errors, "errors": errors, "checks": checks,
            "note": "Package checks do not prove RealityKit runtime compatibility; load on an iPhone."}
