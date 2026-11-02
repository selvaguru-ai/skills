"""Regression coverage: unknown-request handoff, validated promotion, versioning and reuse."""
import copy
import json
import zipfile
import pytest
from pathlib import Path

from machine3d.blueprints import blueprint, joint, part, save_blueprint
from machine3d.cli import NEEDS_BLUEPRINT, main
from machine3d.library import TemplateLibrary, normalize_request


def custom_fan():
    return blueprint("oscillating_desk_fan", "Oscillating desk fan", "desk fan", [
        part("Stand", "Stand", "Holds fan", "box", [0, 0, .08], {"x": .2, "y": .2, "z": .15}),
        part("Rotor", "Rotor", "Moves air", "cylinder", [0, .03, .3],
             {"radius": .1, "depth": .02, "axis": "Y"}, movable=True),
    ], [joint("Rotor", "rotate", [0, 1, 0])])


def synthesize_validated_outputs(out: Path, bp: dict):
    """Simulate successful artifact checks to unit-test promotion; not an actual Blender build."""
    save_blueprint(out, bp)
    (out / "machine.blend").write_bytes(b"BLENDER_FIXTURE" * 50)
    with zipfile.ZipFile(out / "machine.usdz", "w", compression=zipfile.ZIP_STORED) as z:
        z.writestr("machine.usda", "#usda 1.0\n" * 30)
    (out / "blender_validation.json").write_text(json.dumps({
        "passed": True, "components": len(bp["components"])}))
    (out / "export_validation.json").write_text(json.dumps({"passed": True}))


def test_unknown_request_automatically_enters_blueprint_mode_and_preserves_draft(tmp_path):
    out = tmp_path / "job"
    lib = tmp_path / "library"
    user_prompt = "Build an oscillating desk fan"
    assert main(["plan", "--prompt", user_prompt, "--out", str(out),
                 "--library", str(lib), "--offline"]) == NEEDS_BLUEPRINT
    assert (out / "AGENT_BLUEPRINT_TASK.md").exists()
    report = json.loads((out / "plan_report.json").read_text())
    assert report["status"] == "needs_agent_blueprint"
    bp = custom_fan()
    (out / "blueprint.json").write_text(json.dumps(bp))
    assert main(["plan", "--prompt", user_prompt, "--out", str(out),
                 "--library", str(lib), "--offline"]) == 0
    report = json.loads((out / "plan_report.json").read_text())
    assert report["templateSource"] == "agent_authored_blueprint"
    assert not TemplateLibrary(lib).entries()  # planning doesn't promote


def test_promotion_requires_actual_quality_evidence(tmp_path):
    bp = custom_fan()
    out = tmp_path / "out"
    save_blueprint(out, bp)
    library = TemplateLibrary(tmp_path / "library")
    with pytest.raises(ValueError, match="requires Blender"):
        library.promote(bp, out)
    assert not library.entries()
    synthesize_validated_outputs(out, bp)
    (out / "blender_validation.json").write_text('{"passed":false,"components":2}')
    with pytest.raises(ValueError, match="blocked"):
        library.promote(bp, out)
    assert not library.entries()


def test_promote_then_reuse_exact_machine_and_avoid_duplicate_versions(tmp_path):
    out = tmp_path / "out"
    bp = custom_fan()
    synthesize_validated_outputs(out, bp)
    library = TemplateLibrary(tmp_path / "registry")
    info = library.promote(bp, out, prompt="Build an oscillating desk fan")
    assert info["action"] == "created_version"
    assert info["engineeringVerified"] is False
    assert library.match("Create an oscillating desk fan with animated parts") is not None
    first_version = info["version"]
    other = tmp_path / "other"
    assert main(["plan", "--prompt", "Create an oscillating desk fan with animated parts",
                 "--out", str(other), "--library", str(library.root), "--offline"]) == 0
    plan = json.loads((other / "plan_report.json").read_text())
    assert plan["templateSource"] == "learned_template"
    assert plan["templateVersion"] == first_version
    again = library.promote(bp, out, prompt="Make an oscillating desk fan")
    assert again["action"] == "reused_existing_version"
    assert len(list((library.root / bp["id"] / "versions").iterdir())) == 1
    assert library.match("Make an oscillating desk fan") is not None


def test_new_validated_version_preserves_previous(tmp_path):
    out = tmp_path / "out"
    lib = TemplateLibrary(tmp_path / "library")
    bp = custom_fan()
    synthesize_validated_outputs(out, bp)
    prev = lib.promote(bp, out)
    modified = copy.deepcopy(bp)
    modified["components"][0]["dimensions"]["x"] = .35
    synthesize_validated_outputs(out, modified)
    curr = lib.promote(modified, out)
    assert curr["previousVersion"] == prev["version"]
    assert curr["version"] != prev["version"]
    assert len(list((lib.root / bp["id"] / "versions").iterdir())) == 2
    assert lib.load(lib.match("Oscillating desk fan"))["components"][0]["dimensions"]["x"] == .35


def test_corrupted_registry_not_reused(tmp_path):
    bp = custom_fan()
    out = tmp_path / "out"
    synthesize_validated_outputs(out, bp)
    lib = TemplateLibrary(tmp_path / "library")
    record = lib.promote(bp, out)
    path = lib.root / bp["id"] / "versions" / record["version"] / "blueprint.json"
    path.write_text("{}")
    assert lib.entries() == []
    assert lib.match("Oscillating desk fan") is None


def test_different_engine_variant_not_falsely_matched(tmp_path):
    bp = custom_fan()
    out = tmp_path / "out"
    synthesize_validated_outputs(out, bp)
    lib = TemplateLibrary(tmp_path / "library")
    lib.promote(bp, out)
    assert lib.match("oscillating desk fan") is not None
    assert lib.match("ceiling fan") is None
    assert lib.match("oscillating desk fan with solar charging") is not None
    assert normalize_request("Create a V12 gasoline engine with animations") == "v12 gasoline engine"
    assert normalize_request("Create a V10 gasoline engine") != "v12 gasoline engine"


def test_promotion_not_allowed_when_custom_code_dependencies_are_undeclared(tmp_path):
    bp = custom_fan()
    bp["generatorDependencies"] = ["custom_rotor.py"]
    out = tmp_path / "out"
    synthesize_validated_outputs(out, bp)
    lib = TemplateLibrary(tmp_path / "library")
    with pytest.raises(ValueError, match="Custom generator"):
        lib.promote(bp, out)


def test_build_auto_promotes_and_second_prompt_reuses(monkeypatch, tmp_path):
    """CLI integration with a synthetic Blender runner (real Blender requires a Mac)."""
    prompt = "Create an oscillating desk fan with animated parts"
    folder = tmp_path / "job"
    library_path = tmp_path / "learned"
    assert main(["build", "--prompt", prompt, "--out", str(folder), "--offline",
                 "--library", str(library_path)]) == NEEDS_BLUEPRINT
    (folder / "blueprint.json").write_text(json.dumps(custom_fan()))

    def fake_blender(out, executable, kind):
        assert executable == "fake-blender"
        assert kind == "generic"
        synthesize_validated_outputs(out, custom_fan())

    monkeypatch.setattr("machine3d.cli.run_blender", fake_blender)
    assert main(["build", "--prompt", prompt, "--out", str(folder), "--offline",
                 "--library", str(library_path), "--blender", "fake-blender"]) == 0
    promotion = json.loads((folder / "template_promotion.json").read_text())
    assert promotion["action"] == "created_version"
    second = tmp_path / "second"
    assert main(["plan", "--prompt", prompt, "--out", str(second), "--offline",
                 "--library", str(library_path)]) == 0
    assert json.loads((second / "plan_report.json").read_text())["templateSource"] == "learned_template"


def test_failed_build_does_not_promote_with_stale_outputs(monkeypatch, tmp_path):
    bp = custom_fan()
    library = tmp_path / "learned"
    out = tmp_path / "out"
    synthesize_validated_outputs(out, bp)  # stale files from previous attempt

    def broken_blender(out, blender, kind):
        raise RuntimeError("Deliberate build failure")

    monkeypatch.setattr("machine3d.cli.run_blender", broken_blender)
    assert main(["build", "--spec", str(out / "blueprint.json"), "--out", str(out),
                 "--offline", "--library", str(library), "--blender", "fake-blender"]) != 0
    assert not (out / "machine.usdz").exists()
    assert not TemplateLibrary(library).entries()
