---
name: machine3d-ar-builder
description: Build component-based, educational interactive 3D models of ANY requested engine, machine, or device for Blender and iOS RealityKit. From a text-only prompt, automatically research the mechanism, acquire appropriate reference sources, automatically route unknown requests into a machine blueprint or specialized Blender Python generator, render/test, export USDZ and part metadata, and integrate with a reusable AR viewer. Includes built-in templates plus a general AI-authoring path for new machines; never claim unsourced geometry is engineering-accurate.
---

# Machine3D AR Builder — General-Purpose Agent Skill (v0.3)

## User input contract

The user supplies **only a natural-language request**, for example:

- "Build an interactive two-stroke engine with working piston, crank and labels."
- "Build a four-stroke diesel engine with valves and a combustion cycle."
- "Build an ATM and show the banknote dispensing mechanism."
- "Build a hydraulic excavator and animate the boom linkage."
- "Build a washing machine whose drum spins and users can inspect parts."

**Reference images, CAD assets and engineering dimensions are OPTIONAL user inputs.** Research/acquisition is the agent's responsibility. If the user provides them, preferentially incorporate them with proper authorization. A machine unknown to the built-in registry is **not** a reason to stop or ask the user for pictures: use the custom-blueprint pathway below. If critical physical details cannot be confirmed, label approximations and avoid claiming manufacturer fidelity.

## Mandatory autonomous routing and self-learning rules (v0.3)

**Users must ONLY describe a machine.** NEVER ask them to select template versus
blueprint mode or to supply reference images as a prerequisite. NEVER tell the
user to run `scaffold` or write JSON themselves.

1. Start with **the identical workflow for every request**:
   `python3 -m machine3d build --prompt "<full user request>" --out output/<unique-machine-id>`.
   Use `--offline` only when reference acquisition is unavailable or explicitly disabled.
2. The CLI checks the persistent learned template registry first, then built-in
   generators. An exact compatible match goes directly to the shared Blender build.
3. If the CLI returns exit code **5** and JSON `status: needs_agent_blueprint`,
   this is an **internal agent handoff**, not a reason to stop. Read the generated
   `AGENT_BLUEPRINT_TASK.md` and `docs/blueprint-authoring.md`. Research the machine,
   create/complete its blueprint, implement missing geometry or kinematic code
   and tests when needed, and rerun the **same build command with `--prompt`**.
   Do NOT pass an incomplete scaffold to Blender or treat it as a finished model.
4. The skill/agent must run the remaining shared generation, preview, validation
   and export stages, fixing errors where possible. If Blender is missing, report
   that no model was built; never fake success.
5. After a **real successful build** of an agent-authored generic blueprint,
   the CLI **automatically promotes** it into a reusable versioned template.
   This never happens on a mere plan, incomplete blueprint or failed build.
   The CLI reuses the same validated template on future compatible requests.
6. Auto-promotion is limited to self-contained blueprints supported by the
   packaged generic builder. If the new model requires special Python geometry
   or Swift motion code, the agent must version and register those dependencies
   before treating the template as portable; `generatorDependencies` blocks
   automatic blueprint-only promotion rather than silently saving a broken model.
7. When a template exists but does not represent an important subtype or variant,
   research the differences and make a new version or new machine blueprint.
   Do not pretend that a schematic generic shape is manufacturer-accurate.
8. Treat learned templates as **pipeline-validated**, not engineering-certified:
   Blender and USDZ structure checks are not CAD accuracy checks or physical
   iPhone RealityKit validation.

**Persistence:** The default registry lives in `<project>/.machine3d/templates`
when installed under `.cursor/skills/`, or `~/.machine3d/templates` otherwise.
It is kept outside the replaceable skill folder. Set
`MACHINE3D_TEMPLATE_LIBRARY` to choose a shared path. Read
`docs/template-learning.md` for the registry, versioning and validation rules.

## What this package actually executes

- CLI: `python3 -m machine3d` (run commands from the skill folder).
- **Built-in template library:** detailed two-stroke engine (v1 optimized generator), electric motor, gas turbine, two-gear gearbox, centrifugal pump, ATM, front-load washing machine (v2 generic builder).
- **Open-ended path:** CLI automatically issues agent handoff status 5; the AI agent researches a requested new machine, creates `blueprint.json` following `schemas/blueprint.schema.json` and `docs/blueprint-authoring.md`, then the same general Blender generator builds its components and animation. The CLI alone is **NOT an AI text-to-CAD model**: outside built-in template families, an AI agent must write/verify a blueprint.
- Generic geometry primitives: box, cylinder, hollow cylinder, sphere, torus, cone, simplified gear and tube. For geometries this cannot describe, the agent must write reviewed Blender Python geometry functions, or import an appropriately licensed CAD asset; **do not** substitute a random block and claim a realistic model.
- Generic animation: rotation, slide, and oscillation joints, supported in Blender and the Swift RealityKit runtime. The optimized two-stroke builder uses a validated analytical crank-slider motion model. More complex mechanisms require new motion models and tests.
- USDZ export, metadata validation, preview, and RealityKit part selection, labels, RPM/cycle slider and exploded view starter.

## Full agent workflow — AUTOMATIC without user images

1. Parse the prompt and identify a **specific machine subtype** (e.g. axial compressor versus centrifugal compressor, 4-stroke gasoline versus 2-stroke diesel). Document assumption where the prompt is ambiguous.
2. **Research** manufacturer drawings, properly licensed CAD, technical diagrams and authoritative mechanism descriptions using the research tools and network available to the agent. This package's optional `machine3d.references` downloader provides Wikimedia Commons visual references with attribution and license filtering. Do not mistake web images for dimensioned drawings, and never imply external sources were found when offline.
3. Build a **component graph**: stationary and moving components, placement, parent/child associations, pivot axes, and physical relationships. Keep physically meaningful names stable across Blender/JSON/Swift.
4. Check built-in templates using `python3 -m machine3d templates`.
5. **If a matching template exists**, generate a plan:
   ```bash
   python3 -m machine3d plan --prompt "Build an electric motor" --out output/electric_motor
   ```
6. **If NO matching template exists**, the CLI has already created an incomplete
   scaffold and an `AGENT_BLUEPRINT_TASK.md` as part of the first `build --prompt`
   call. **DO NOT stop**, ask the user, or create a new duplicate request. You may
   inspect the equivalent explicit scaffold command for debugging:
   ```bash
   python3 -m machine3d scaffold --prompt "Build a hydraulic excavator" --out output/excavator
   ```
   Use your model reasoning and available research/image tools to **replace the scaffold** with an actual engineered educational assembly: research components and dimensions, assign geometry, materials and joints; do not fabricate measurements as verified. Fill `output/excavator/blueprint.json` according to `schemas/blueprint.schema.json`. Invoke:
   ```bash
   python3 -m machine3d plan --spec output/excavator/blueprint.json --out output/excavator
   ```
   If advanced shapes/kinematics are needed, implement them under `blender/` as
   reusable functions, update schema/Swift motion controller where needed, add
   tests, then run build. Prefer **rerunning the same `build --prompt` command**
   after completing the scaffold rather than asking the user to invoke `--spec`.
   Failure to model needed components is a documented limitation, not a reason
   to silently omit them.
7. **Geometry and motion validation:** run the pure-Python test suite and per-machine metadata checks; validate pivots, component bounds, clearance, motion periodicity, power transfer, gear ratios/phase, and relative movements. General schema validation does NOT prove physical accuracy.
8. **Build in Blender** (Blender 4.x/5.x):
   ```bash
   python3 -m machine3d build --prompt "Build an electric motor" --out output/electric_motor
   # OR (for a custom blueprint)
   python3 -m machine3d build --spec output/excavator/blueprint.json --out output/excavator
   ```
   If Blender is not found, the command exits non-zero; NEVER claim a `.blend`/`.usdz` exists.
9. **Visual QC:** render from several angles, compare to source references, test animations in Blender. Any part intersections or inaccurate mechanism require correction. The built-in export validator confirms container structure, not real-world mechanical correctness or iOS compatibility.
10. **AR export and integration:** load `machine.usdz`, `machine.json`, `animation_spec.json` into the shared `ios` Swift package. Validate entities, coordinate conversion and interactions on a physical ARKit-compatible iPhone. For production, confirm the exported USD prim hierarchy is retained as names in RealityKit.
11. **Template learning:** after successful generic build the CLI promotes a
    self-contained v2 blueprint into a versioned reusable template. Check
    `template_promotion.json`; review the saved library in
    `python3 -m machine3d templates`. Never promote unvalidated assets.
12. Report what actually ran: research sources, part count, accuracy level, tests, exported files, limitations, and iOS verification status.

## Files/contract

- **v1 dedicated engine** (optimized two-stroke): `blender/build_engine.py`, `machine3d/spec.py`, `machine3d/kinematics.py`; `machine.json` and `animation_spec.json` have schemaVersion 1.
- **v2 generic machines**: `machine3d/blueprints.py`, `blender/build_generic.py`, optional agent-authored `blueprint.json`; `machine.json` and `animation_spec.json` have schemaVersion 2.
- **iOS runtime**: `ios/Sources/MachineARKit/MachineAsset.swift`, `MachineSession.swift`, `GenericJointController` in `MachineMotionController.swift`, and legacy `CrankSliderController.swift`.
- Expected generated files: `machine.blend`, `machine.usdz`, `machine.json`, `animation_spec.json`, `geometry_spec.json`, `plan_report.json`, `references/reference_manifest.json`, `blender_validation.json`, `export_validation.json`, and preview if render succeeds.

## Animation ownership

- **Blender:** create parts, exact pivots, exported rest pose and preview clip; optimize topology.
- **RealityKit:** real-time interactive movement, RPM, manual cycle scrubbing, joint simulation, part-selection and exploded view. ARKit tracks the physical environment.
- A v2 generic mechanism's `rotate`/`slide`/`oscillate` commands run in both Blender and RealityKit. A camshaft or four-stroke valve system needs additional **specific mechanism logic** (do not treat a simple sine wave as physically accurate).
- Avoid simultaneously playing Blender clips and runtime-controlled transformations for the same parts.

## Reference source/fidelity policy

Source priority: licensed CAD/engineering drawings with dimensions > manufacturer manuals/technical cross sections > multi-view photographs > procedurally derived mechanism geometry > AI-generated conceptual images. Sources must be recorded with provenance, attribution and license; CAD reuse must be authorized. AI-generated reference images are never dimensionally authoritative. When missing precision, use labels such as **conceptual-educational**, **approximate**, and list assumptions.

## Reliability gates

- `python3 -m pytest -q` must pass.
- Unknown machine handoff must be completed by the AGENT, not delegated to the user.
- Template promotion requires a real Blender validation report and passing USDZ structural checks; it never certifies mechanical correctness.
- Every component has a unique stable ID, sensible bounds, targetable entity name, description and parent relationship.
- No component or animation is reported working if it hasn't actually been exercised.
- Never execute third-party Blender Python scripts obtained online without review; code execution is local and trusted-agent authored.
- Avoid claims of engineering-grade geometry, CFD, manufacturer-specific dimensions or real-device compatibility without evidence.

## Skill response style

For a new machine: proceed with best-effort automatic research, blueprint generation, Blender build and verification. If an environment lacks Blender, report exactly what was planned versus generated; do not ask user to supply reference images unless essential information is genuinely unavailable.
