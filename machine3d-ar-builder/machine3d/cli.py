"""Machine3D CLI: template lookup -> agent blueprint handoff -> shared build -> safe promotion.

No arbitrary language model is embedded in this pure-Python CLI. For unknown
machines the CLI writes a concrete agent task and returns code 5. The installed
Cursor skill automatically completes that task and resumes the SAME build path.
"""
from __future__ import annotations
from pathlib import Path
from shutil import which
import argparse
import json
import subprocess
import sys

from .blueprints import TEMPLATES, from_template, match_template, save_blueprint, scaffold, validate_blueprint
from .library import TemplateLibrary, normalize_request
from .references import collect_references
from .spec import TwoStrokeSpec, save_spec_bundle
from .validation import validate_kinematics, validate_metadata, validate_export

NEEDS_BLUEPRINT = 5


def parse_machine(prompt: str) -> TwoStrokeSpec:
    """Deprecated v1 compatibility: explicit two-stroke reference model."""
    if is_two_stroke(prompt):
        return TwoStrokeSpec()
    raise ValueError("No generator in legacy v1 parser. Use v2 templates or --spec blueprint.json")


def is_two_stroke(prompt: str) -> bool:
    text = prompt.casefold().replace("-", " ")
    return ("two stroke" in text or "2 stroke" in text) and any(
        s in text for s in ["engine", "motorcycle", "motor", "moped"]
    )


def prepare_blueprint_handoff(folder: Path, prompt: str) -> dict:
    """Automatically scaffold, preserving an existing agent-authored blueprint."""
    folder.mkdir(parents=True, exist_ok=True)
    request_path = folder / "request.json"
    target = folder / "blueprint.json"
    if request_path.exists() and target.exists():
        try:
            original = json.loads(request_path.read_text(encoding="utf-8"))
            if normalize_request(original["prompt"]) == normalize_request(prompt):
                candidate = json.loads(target.read_text(encoding="utf-8"))
                validate_blueprint(candidate)
                return {"status": "ready", "blueprint": candidate}
        except (ValueError, KeyError, TypeError, OSError, json.JSONDecodeError):
            pass
    # Do not clobber a different, potentially user-authored blueprint.
    if target.exists() and request_path.exists():
        try:
            original = json.loads(request_path.read_text(encoding="utf-8"))["prompt"]
        except (KeyError, OSError, ValueError, json.JSONDecodeError):
            original = None
        if original and normalize_request(original) != normalize_request(prompt):
            raise ValueError("Output folder belongs to a different request. Use a new --out directory.")
    if target.exists() and not request_path.exists():
        raise ValueError("Output folder already contains an untracked blueprint. Use --spec or a new --out directory.")
    target.write_text(json.dumps(scaffold(prompt), indent=2) + "\n", encoding="utf-8")
    request_path.write_text(json.dumps({"prompt": prompt, "status": "needs_agent_blueprint"}, indent=2) + "\n", encoding="utf-8")
    task = f"""# Agent handoff — complete this automatically (no user action required)

Request: {prompt}

The requested machine has no trustworthy matching template. DO NOT stop and
ask the user for a blueprint or reference images. You are the AI coding agent.

1. Research reliable diagrams, mechanisms, part lists and usable licensed CAD/images.
2. Read SKILL.md, docs/blueprint-authoring.md and schemas/blueprint.schema.json.
3. Replace {target.name} with a COMPLETE v2 blueprint: separate named parts,
   meaningful dimensions/pivots, educational descriptions, valid joints.
4. Where primitives or generic joints are insufficient, implement and test
   geometry / mechanism extensions; document limitations honestly.
5. Run `python3 -m machine3d plan --prompt {json.dumps(prompt)} --out {folder}`.
6. Fix all validation errors and run `python3 -m machine3d build --prompt {json.dumps(prompt)} --out {folder}`.
7. Successful Blender + export validation automatically promotes a new version
   to the learned template registry. Failed, incomplete or unverified builds
   must never be promoted. Review preview and check RealityKit on device.

The raw Python CLI cannot call an LLM itself. This handoff is executed by the
hosting Cursor/Codex agent when the skill is active, not by Blender or argparse.
"""
    (folder / "AGENT_BLUEPRINT_TASK.md").write_text(task, encoding="utf-8")
    return {"status": "needs_agent_blueprint", "blueprintPath": str(target),
            "agentTask": str(folder / "AGENT_BLUEPRINT_TASK.md"),
            "message": "AI coding agent must complete blueprint and rerun the SAME --prompt command."}


def plan(prompt: str | None, folder: Path, offline: bool,
         blueprint_file: Path | None = None, library: TemplateLibrary | None = None) -> dict:
    folder.mkdir(parents=True, exist_ok=True)
    library = library or TemplateLibrary()
    source = "provided_spec"
    template_version = None
    if blueprint_file is not None:
        bp = json.loads(blueprint_file.expanduser().resolve().read_text(encoding="utf-8"))
        validate_blueprint(bp)
        kind = "generic"
        save_blueprint(folder, bp)
        machine_id = bp["id"]
    elif prompt and (saved := library.match(prompt)):
        bp = library.load(saved)
        kind = "generic"
        source = "learned_template"
        template_version = saved["version"]
        save_blueprint(folder, bp)
        machine_id = bp["id"]
    elif prompt and is_two_stroke(prompt):
        spec = TwoStrokeSpec()
        spec.validate()
        save_spec_bundle(folder, spec)
        kind = "legacy_two_stroke"
        source = "built_in_two_stroke"
        machine_id = spec.machine_id
    elif prompt and (name := match_template(prompt)):
        bp = from_template(name)
        kind = "generic"
        source = "built_in_template"
        save_blueprint(folder, bp)
        machine_id = bp["id"]
    elif prompt:
        handoff = prepare_blueprint_handoff(folder, prompt)
        if handoff["status"] == "needs_agent_blueprint":
            report = {**handoff, "prompt": prompt, "buildKind": "pending", "machineId": None}
            (folder / "plan_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            return report
        bp = handoff["blueprint"]
        kind = "generic"
        source = "agent_authored_blueprint"
        save_blueprint(folder, bp)
        machine_id = bp["id"]
    else:
        raise ValueError("Either --prompt or --spec is required")
    refs = collect_references(folder / "references", offline=offline,
                              queries=[prompt or bp["displayName"]] if kind == "generic" else None)
    kin = (validate_kinematics(TwoStrokeSpec()) if kind == "legacy_two_stroke"
           else {"passed": True, "mechanism": "generic_joints", "joints": len(bp["animation"]["joints"]),
                 "note": "Schema checks only; physical collision/engineering checks require review."})
    results = {"status": "planned", "prompt": prompt, "machineId": machine_id, "buildKind": kind,
               "templateSource": source, "templateVersion": template_version,
               "accuracy": "conceptual-educational", "referenceStatus": refs["status"],
               "kinematics": kin, "metadata": validate_metadata(folder)}
    (folder / "plan_report.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return results


def find_blender(user_path: str | None) -> str | None:
    if user_path:
        return str(Path(user_path).expanduser())
    found = which("blender")
    if found:
        return found
    mac = Path("/Applications/Blender.app/Contents/MacOS/Blender")
    return str(mac) if mac.is_file() else None


def run_blender(folder: Path, blender: str, kind: str) -> None:
    script_name = "build_engine.py" if kind == "legacy_two_stroke" else "build_generic.py"
    script = Path(__file__).resolve().parent.parent / "blender" / script_name
    cmd = [blender, "--background", "--python-exit-code", "2", "--python", str(script),
           "--", "--out", str(folder.resolve())]
    result = subprocess.run(cmd, check=False)
    if result.returncode:
        raise RuntimeError(f"Blender build failed ({result.returncode}); see logs above")


def validate_plan(folder: Path) -> dict:
    metadata = validate_metadata(folder)
    if (folder / "blueprint.json").exists():
        try:
            bp = json.loads((folder / "blueprint.json").read_text())
            validate_blueprint(bp)
            kinematics = {"passed": True, "joints": len(bp["animation"]["joints"]),
                          "note": "Schema checked, engineering fidelity unverified."}
        except (ValueError, KeyError) as error:
            kinematics = {"passed": False, "errors": [str(error)]}
    elif (folder / "geometry_spec.json").exists():
        raw = json.loads((folder / "geometry_spec.json").read_text())
        spec = TwoStrokeSpec(**{k: v for k, v in raw.items() if k in TwoStrokeSpec.__dataclass_fields__})
        kinematics = validate_kinematics(spec)
    else:
        kinematics = {"passed": False, "errors": ["Missing blueprint.json or geometry_spec.json"]}
    return {"metadata": metadata, "kinematics": kinematics, "export": validate_export(folder)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate educational machine assemblies for Blender and RealityKit")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "build"):
        p = commands.add_parser(name)
        p.add_argument("--prompt", help="Natural-language request; automatically routes to template or agent blueprint")
        p.add_argument("--spec", type=Path, help="Supplied v2 blueprint JSON")
        p.add_argument("--out", default="output/machine", help="Output directory")
        p.add_argument("--offline", action="store_true", help="Skip online image acquisition")
        p.add_argument("--library", type=Path, help="Override persistent learned-template library path")
        if name == "build":
            p.add_argument("--blender", help="Blender executable path")
            p.add_argument("--no-promote", action="store_true", help="Do not save validated custom blueprint as a template")
    p = commands.add_parser("scaffold", help="Prepare incomplete blueprint plus agent design task")
    p.add_argument("--prompt", required=True)
    p.add_argument("--out", default="output/custom_machine")
    p = commands.add_parser("validate")
    p.add_argument("--out", default="output/machine")
    p = commands.add_parser("templates")
    p.add_argument("--library", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "templates":
            registry = TemplateLibrary(args.library)
            print("Built-in: two-stroke gasoline engine (specialized)")
            for name in sorted(TEMPLATES):
                print("Built-in:", name)
            for saved in registry.entries():
                print("Learned:", saved["id"], "version:", saved["version"],
                      "aliases:", ", ".join(saved["aliases"]))
            return 0
        out = Path(args.out).expanduser().resolve()
        if args.command == "scaffold":
            result = prepare_blueprint_handoff(out, args.prompt)
            print(json.dumps(result, indent=2))
            return 0
        if args.command in ("plan", "build"):
            if bool(args.prompt) == bool(args.spec):
                raise ValueError("Choose exactly one: --prompt OR --spec")
            registry = TemplateLibrary(args.library)
            report = plan(args.prompt, out, args.offline, args.spec, registry)
            print(json.dumps(report, indent=2))
            if report["status"] == "needs_agent_blueprint":
                return NEEDS_BLUEPRINT
            if not report["kinematics"]["passed"] or not report["metadata"]["passed"]:
                return 2
            if args.command == "build":
                blender = find_blender(args.blender)
                if not blender:
                    print("BLENDER_MISSING: plan generated but no .blend/.usdz. Install Blender and rerun.", file=sys.stderr)
                    return 3
                # Never allow stale successful outputs to authorize promotion.
                for filename in ("machine.blend", "machine.usdz", "blender_validation.json", "export_validation.json"):
                    (out / filename).unlink(missing_ok=True)
                run_blender(out, blender, report["buildKind"])
                export_result = validate_export(out)
                (out / "export_validation.json").write_text(json.dumps(export_result, indent=2) + "\n")
                print("Export checks:", json.dumps(export_result, indent=2))
                if not export_result["passed"]:
                    return 4
                should_promote = report["buildKind"] == "generic" and report["templateSource"] in (
                    "agent_authored_blueprint", "provided_spec", "learned_template")
                if should_promote and not args.no_promote:
                    bp = json.loads((out / "blueprint.json").read_text())
                    try:
                        promoted = registry.promote(bp, out, prompt=args.prompt)
                    except ValueError as error:
                        print("TEMPLATE_NOT_PROMOTED:", error, file=sys.stderr)
                        return 6
                    (out / "template_promotion.json").write_text(json.dumps(promoted, indent=2) + "\n")
                    print("Template library:", json.dumps(promoted, indent=2))
                return 0
            return 0
        if args.command == "validate":
            checks = validate_plan(out)
            print(json.dumps(checks, indent=2))
            return 0 if all(v["passed"] for v in checks.values()) else 4
    except (ValueError, RuntimeError, OSError, KeyError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 1


if __name__ == "__main__":
    sys.exit(main())
