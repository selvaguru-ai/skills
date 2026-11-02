# Automatic blueprint routing and persistent template learning (v0.3)

The **Cursor/Codex agent** reads SKILL.md. The local Python CLI is an orchestrator,
not a language model or web research agent. The user never needs to specify a
mode, blueprint, or reference image. The agent finishes the work after the CLI
returns a structured handoff, using its available tools.

## User's only prompt

> Build a V12 gasoline engine with animated pistons for my AR app.

The agent calls `python3 -m machine3d build --prompt "Build a V12 gasoline engine with animated pistons for my AR app" --out output/v12 --offline`.

Pipeline:

1. Search saved validated templates, then built-in templates.
2. If no exact compatible match, write `output/v12/blueprint.json`,
   `request.json`, and `AGENT_BLUEPRINT_TASK.md`. The command returns exit
   code **5** (`needs_agent_blueprint`), which is a **handoff**, not a fatal stop.
3. Agent reads the task, researches references, replaces the incomplete blueprint
   with a real, valid specification, and extends Blender geometry and motion
   capabilities as necessary. It then **reruns the same build command**.
4. Blender generates separate component entities and the USDZ. Python validates
   the metadata and package. Every generated component must remain targetable.
5. A machine with all required checks passing gets a versioned record in the
   learned template library. A model failing checks **cannot** be promoted.
6. Next matching request loads the validated blueprint directly. It can still
   be customized by the agent; an exact template does not prove that every
   variant is supported.

## Template library storage

Default library location on an installed Cursor project:

`<your-project>/.machine3d/templates/`

When running standalone: `~/.machine3d/templates/`. The directory is deliberately
**outside** `.cursor/skills/machine3d-ar-builder/` so replacing the skill on
upgrades does not erase saved machines.

Override for portable/team storage:

```bash
export MACHINE3D_TEMPLATE_LIBRARY="$PWD/.machine3d/templates"
python3 -m machine3d templates
```

Or specify `--library /your/path` on `templates`, `plan`, and `build`. Commit
reviewed template JSON to Git if your team needs shared versioning. Do not
commit unlicensed source assets or sensitive reference material.

Each template stores `latest.json` plus immutable-ish version directories:

```text
.machine3d/templates/
└── v12_engine/
    ├── latest.json
    └── versions/
        └── 20261101T152900Z_0123456789ab/
            ├── blueprint.json
            ├── manifest.json
            ├── machine.json
            ├── animation_spec.json
            ├── blender_validation.json
            └── export_validation.json
```

Version ID includes UTC timestamp and blueprint SHA-256 digest. Identical
blueprints reuse the same version without duplicates; changed blueprints create
new versions and keep the previous one. `latest.json` is written atomically.
Checksum mismatches prevent loading corrupted templates.

## Matching rules

A learned template is chosen for a **conservative normalized exact request**.
The matcher strips presentation phrases such as "create", "build", "with
animations", but retains machine subtype details such as `V8` vs `V12`. This
reduces false matches. The agent may separately reason about adapting a
similar template, but should verify subtype differences before reuse.

## Promotion gates

Auto-promotion occurs after a successful `build`, not after `plan` or after
merely writing a blueprint. This requires:

- Valid v2 blueprint and matching machine/animation metadata.
- `blender_validation.json` with `passed=true` and expected component count.
- `machine.blend` and a structurally valid USDZ containing a USD layer.
- `export_validation.json` with `passed=true`.
- The built blueprint exactly matches the blueprint being promoted.

The library labels this `blender-and-export-pipeline-validated` and explicitly
sets `engineeringVerified=false` and `realityKitDeviceVerified=false`.
Structural checks **do not guarantee** accurate CAD, collision-free motion, or
successful ARKit behavior on a physical iPhone. Those require further work.

Use `--no-promote` to build without teaching the library. Built-in templates
are not redundantly promoted. If specialized custom generator code is needed,
package and version that dependency before treating the model as reusable;
blueprint-only reuse cannot guarantee custom code portability. The v0.3
promoter rejects `generatorDependencies` rather than storing a broken template.

## Important capabilities / limitations

- Automatic **mode selection, handoff and retry** is implemented. The host AI
  coding agent still must actually author a blueprint for an unknown machine.
- Auto-saving and versioned reuse of **validated generic blueprints** is
  implemented. A two-stroke legacy engine remains an existing built-in model.
- There is no universal autonomous text-to-CAD backend in the Python CLI.
- The default generic geometry vocabulary and joint controllers are deliberately
  small. Mechanical fidelity and model aesthetics are not guaranteed.
- Real Blender/USDZ export and iPhone device tests must run on your hardware.
