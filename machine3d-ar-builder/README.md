# Machine3D AR Builder v0.3 — reusable AI 3D machine-generation skill

**Goal:** Give Cursor one prompt such as **"Build an interactive hydraulic excavator"**, **"Build an ATM"**, or **"Build an electric motor"**. The agent automatically researches the mechanism, collects available references (optional), authors or selects a machine blueprint, writes/executes Blender geometry generation, creates animation specs, and exports component-separated assets for an iOS RealityKit app.

**Important distinction:** This is an executable **extensible skill**, not a universal text-to-accurate-CAD model. It has seven working blueprint paths (one optimized two-stroke model + six generic templates). For all other machines the CLI **automatically hands off** blueprint authoring to the AI coding agent (exit code 5). The agent must research/complete `blueprint.json`, and potentially implement new geometry/kinematics, then rerun the same `build --prompt` command. **Validated custom blueprints are automatically saved as versioned reusable templates.** The raw CLI cannot independently invent accurate models from arbitrary text. Models in the generic starter library are simplified educational concepts.

## Install in Cursor (Mac)

1. Install Blender 4.x/5.x: https://www.blender.org/download/ and Python 3.10+.
2. Unzip the package and copy the **entire folder**, not just `SKILL.md`, to your Cursor project's `.cursor/skills/machine3d-ar-builder/`.
3. Open the project in Cursor. Tell the agent:
   > Use the machine3d-ar-builder skill. Create a detailed four-stroke gasoline engine with independently selectable parts and full RealityKit integration. Research reference sources yourself; no user images are supplied. Use a custom blueprint or additional procedural geometry as needed, generate assets, run validations, and clearly identify unverified steps.
4. Ensure the agent reads `SKILL.md`, `docs/blueprint-authoring.md`, and the existing test suite before editing generators.

## Commands (run inside the skill folder)

List built-in templates:

```bash
python3 -m machine3d templates
```

Build a device from a known template:

```bash
python3 -m machine3d plan --prompt "Create an interactive ATM" --out output/atm_machine --offline
python3 -m machine3d build --prompt "Create an interactive ATM" --out output/atm_machine --offline
```

**For any machine, including unknown ones, use the SAME command:**

```bash
python3 -m machine3d build --prompt "Build a realistic V12 gasoline engine with animated pistons" --out output/v12_engine
```

If a template is unavailable, the CLI writes `blueprint.json`, `request.json`
and `AGENT_BLUEPRINT_TASK.md`, and returns **exit code 5**. This is an **agent
handoff**: Cursor reads the generated task, researches references, completes
`blueprint.json`, implements missing builders/controllers if necessary, and
runs the **same command again**. The user is not asked to supply JSON or images.

On successful generic Blender build and export validation, the blueprint is
**automatically promoted** to the persistent template registry. Future matching
prompts reuse the saved template. To inspect learned templates:

```bash
python3 -m machine3d templates
```

Default library storage: `<project>/.machine3d/templates/` when installed in
Cursor, otherwise `~/.machine3d/templates/`. This is outside the skill folder,
so reinstalling/updating the skill does not delete learned templates. Override
with `MACHINE3D_TEMPLATE_LIBRARY` or `--library /path/to/templates`.
See [Automatic routing and template learning](docs/template-learning.md).

The scaffold is intentionally **not buildable until the agent fills its parts**. Blender is needed to generate `.blend`, `.usdz`, and preview files; the `plan` step works without Blender. `--offline` skips automatic reference downloading and still generates metadata. Running the real build without Blender exits nonzero rather than fabricating completed assets.

## Template library

| Prompt example | Template / mode | Motion | Accuracy |
|---|---|---|---|
| "Two-stroke motorcycle engine" | Dedicated detailed engine v1 | Analytic crank-slider | Conceptual educational |
| "Electric motor" | Generic v2 | Rotor/shaft rotation | Simplified |
| "Gas turbine / jet engine" | Generic v2 | Linked compressor/turbine rotation | Simplified blade/stage geometry |
| "Gearbox" | Generic v2 | Coupled counterrotation | Schematic teeth |
| "Centrifugal pump" | Generic v2 | Impeller rotation | Simplified/no CFD |
| "ATM" | Generic v2 | Feed roller rotation | Simplified/nonmanufacturer |
| "Washing machine" | Generic v2 | Drum rotation | Simplified |
| **Any other engine/device** | **Automatic handoff → AI-created v2 blueprint → saved after validation** | Generic joints or custom math | Depends on documented sources and authored geometry |

## Generated files

| File | Purpose |
|---|---|
| `blueprint.json` (v2) | Editable structured 3D assembly and joint specification |
| `machine.blend` | Native Blender assembly and preview animation |
| `machine.usdz` | Static-pose separated part asset for RealityKit |
| `machine.json` | Component names, selection IDs, descriptions |
| `animation_spec.json` | Cross-platform runtime animation contract |
| `geometry_spec.json` | Original dimensions or structured blueprint pointer |
| `references/reference_manifest.json` | Attribution and source/fallback status |
| `preview.png` | Rendered Blender preview if available |
| `plan_report.json` | Plan checks |
| `blender_validation.json` | Checks run inside Blender |
| `export_validation.json` | USDZ archive validation |

## RealityKit integration

Import `ios/` as a local Swift package in Xcode (iOS 17+). Copy `.usdz` + two JSON metadata files to the app bundle. `MachineSession` selects between dedicated crank-slider and general-purpose joint animation controllers based on the animation spec. See `docs/ios-integration.md`. A local Swift package handles selection, tap labels, play/pause, timeline scrubbing and simplified exploded views; the actual app remains yours.

**Quality gates:** Run `python3 -m pytest -q`. Blender export and actual iPhone load require local testing. The built-in Python checks verify schemas and mathematical correctness of the reference engine; generic template checks do **not** prove manufacturer CAD fidelity or collision-free operation.

## Automatic template learning: scope

Promotion requires passing Blender, metadata and export **structural** checks.
Drafts, failed builds and builds without Blender are **not** reusable templates.
A newly authored machine needing extra generator Python/Swift must register and
version that supporting implementation separately; v0.3 does not auto-package
custom code. Learn more in `docs/template-learning.md`.

## Next capabilities needed for full production

Add specialized geometry tools (loft/extrude/boolean/CAD import), motion solvers (cams, linkages, complex gear trains), visually validated image-to-geometry reconstruction, licensing governance, materials/LOD, USD hierarchy round-trip tests, iPhone profiling and AR placement UX. These are extensibility work items, not finished capabilities.
