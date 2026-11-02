import copy
import json
from pathlib import Path
import pytest
from machine3d.blueprints import (
    TEMPLATES, from_template, validate_blueprint, save_blueprint, scaffold,
    part, joint, blueprint,
)
from machine3d.cli import main
from machine3d.validation import validate_metadata

@pytest.mark.parametrize("template", sorted(TEMPLATES))
def test_each_machine_family_has_valid_components_and_joints(template):
    data = from_template(template)
    assert len(data["components"]) >= 6
    assert data["animation"]["joints"]
    assert {x["primitive"] for x in data["components"]}
    assert data["schemaVersion"] == 2
    assert all(x["entity"] in {c["id"] for c in data["components"]}
               for x in data["animation"]["joints"])

@pytest.mark.parametrize("machine_request", [
    "Build an electric motor", "A two gear gearbox", "Interactive ATM machine",
    "Centrifugal water pump", "front load washing machine", "jet engine",
])
def test_prompt_generates_different_models(machine_request, tmp_path):
    dest = tmp_path / "sample"
    assert main(["plan", "--prompt", machine_request, "--offline", "--out", str(dest)]) == 0
    assert (dest / "blueprint.json").exists()
    assert validate_metadata(dest)["passed"]
    assert json.loads((dest / "plan_report.json").read_text())["buildKind"] == "generic"


def test_agent_authored_unregistered_machine_blueprint(tmp_path):
    fan = blueprint("desk_fan", "Desk fan", "oscillating fan", [
        part("Motor", "Motor", "Creates shaft torque", "cylinder", [0,0,.20],
             {"radius":.06,"depth":.09,"axis":"Y"}),
        part("Blades", "Blade wheel", "Moves air", "gear", [0,-.08,.20],
             {"radius":.13,"depth":.01,"teeth":6,"axis":"Y"}, movable=True),
        part("Foot", "Fan base", "Supports fan", "box", [0,0,.02],
             {"x":.25,"y":.20,"z":.04}),
    ], [joint("Blades", "rotate", [0,1,0])])
    custom = tmp_path / "custom.json"
    custom.write_text(json.dumps(fan))
    out = tmp_path / "built"
    assert main(["plan", "--spec", str(custom), "--offline", "--out", str(out)]) == 0
    assert validate_metadata(out)["passed"]
    assert json.loads((out / "machine.json").read_text())["id"] == "desk_fan"


def test_unknown_prompt_prepares_incomplete_scaffold(tmp_path):
    out = tmp_path / "out"
    assert main(["scaffold", "--prompt", "Build an orbital cheese slicer", "--out", str(out)]) == 0
    assert (out / "blueprint.json").exists()
    assert main(["plan", "--prompt", "Build an orbital cheese slicer", "--offline", "--out", str(out)]) != 0
    with pytest.raises(ValueError):
        validate_blueprint(json.loads((out / "blueprint.json").read_text()))


def test_invalid_gear_teeth_and_parent_cycle_are_rejected():
    data = from_template("spur_gearbox")
    p = next(x for x in data["components"] if x["primitive"] == "gear")
    p["dimensions"]["teeth"] = 0
    with pytest.raises(ValueError, match="teeth"):
        validate_blueprint(data)
    data = from_template("atm_machine")
    data["components"][0]["parent"] = data["components"][1]["id"]
    data["components"][1]["parent"] = data["components"][0]["id"]
    with pytest.raises(ValueError, match="cycle"):
        validate_blueprint(data)


def test_missing_joint_entity_rejected():
    data = from_template("electric_motor")
    data["animation"]["joints"][0]["entity"] = "NonexistentPart"
    with pytest.raises(ValueError, match="invalid entity"):
        validate_blueprint(data)


def test_no_blender_do_not_claim_files(tmp_path):
    out = tmp_path / "motor"
    assert main(["build", "--prompt", "electric motor", "--offline", "--out",str(out),
                 "--blender", "/missing/blender"]) != 0
    assert not (out / "machine.blend").exists()
    assert not (out / "machine.usdz").exists()
