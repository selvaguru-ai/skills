import ast
from pathlib import Path


def test_blender_generator_is_syntactically_valid():
    script = Path(__file__).resolve().parents[1] / "blender" / "build_engine.py"
    ast.parse(script.read_text(encoding="utf-8"))


def test_skill_has_real_executables_and_swift_package():
    root = Path(__file__).resolve().parents[1]
    assert (root / "SKILL.md").is_file()
    assert (root / "machine3d" / "cli.py").is_file()
    assert (root / "ios" / "Package.swift").is_file()
    assert (root / "ios" / "Sources" / "MachineARKit" / "MachineARView.swift").is_file()
