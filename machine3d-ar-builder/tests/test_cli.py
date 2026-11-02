import json
import shutil
import zipfile
import pytest
from machine3d.cli import main, parse_machine
from machine3d.spec import TwoStrokeSpec
from machine3d.validation import validate_export, validate_metadata


def test_prompt_to_engine():
    assert isinstance(parse_machine("Create a two-stroke motorcycle engine with ARKit integration"), TwoStrokeSpec)
    assert isinstance(parse_machine("A 2 stroke engine"), TwoStrokeSpec)


def test_prompt_rejects_unimplemented_machine():
    with pytest.raises(ValueError, match="No generator"):
        parse_machine("Make a jet engine")


def test_plan_offline(tmp_path):
    out = tmp_path / "machine"
    status = main(["plan", "--prompt", "2-stroke engine", "--out", str(out), "--offline"])
    assert status == 0
    manifest = json.loads((out / "references" / "reference_manifest.json").read_text())
    assert manifest["mode"] == "offline"
    assert manifest["status"] == "fallback-geometry-without-external-images"
    machine = json.loads((out / "machine.json").read_text())
    assert machine["accuracy"] == "conceptual-educational"
    assert len(machine["components"]) >= 15
    assert validate_metadata(out)["passed"]
    assert not validate_export(out)["passed"]


def test_blender_missing_returns_nonzero_and_no_fabricated_files(tmp_path):
    out = tmp_path / "engine"
    status = main(["build", "--prompt", "two stroke engine", "--out", str(out),
                   "--offline", "--blender", "/not/a/real/blender"])
    assert status != 0
    assert not (out / "machine.blend").exists()
    assert not (out / "machine.usdz").exists()


def test_export_rejects_corrupt_usdz(tmp_path):
    (tmp_path / "machine.blend").write_bytes(b"A" * 200)
    (tmp_path / "machine.usdz").write_bytes(b"not a zip" * 20)
    result = validate_export(tmp_path)
    assert not result["passed"]
    assert "USDZ is not a valid ZIP archive" in result["errors"]


def test_export_accepts_usd_zip_structure(tmp_path):
    (tmp_path / "machine.blend").write_bytes(b"A" * 200)
    with zipfile.ZipFile(tmp_path / "machine.usdz", "w", compression=zipfile.ZIP_STORED) as z:
        z.writestr("engine.usda", "#usda 1.0\n" * 30)
    assert validate_export(tmp_path)["passed"]
