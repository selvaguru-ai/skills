# Generic machine blueprint authoring (v2)

The AI coding agent should **automatically design a blueprint** when a text-only machine request has no built-in template. The tool does not contain a universal pretrained CAD generator. An unrecognized `build --prompt` automatically enters blueprint handoff mode (exit code 5), writing an incomplete `blueprint.json` plus `AGENT_BLUEPRINT_TASK.md` that the agent must complete. This prevents presenting made-up geometry as a completed device.

## Machine specification

Use `schemas/blueprint.schema.json` as the machine-level contract. A working example appears in `examples/electric_motor/blueprint.json` and `examples/atm_machine/blueprint.json`. The simplified generic builder accepts up to 300 components; coordinates are **meters**, right-handed, Blender **Z-up**, each component's position is relative to its parent if one is assigned. Place the pivot at the component's `position`, with the primitive centered there; for noncentral pivots write a specialized builder.

## Component design

Each component needs `id`, `name`, `description`, `position:[x,y,z]`, `primitive`, `dimensions`, `material`, `movable` and optional `parent`, `rotationDegrees:[x,y,z]`.

Shapes and dimensions:

| primitive | required dimensions | note |
|---|---|---|
| box | x, y, z | rectangular volume |
| cylinder | radius, depth | axis X/Y/Z optional |
| hollow_cylinder | innerRadius, outerRadius, depth | real annular wall |
| sphere | radius | round primitive |
| torus | majorRadius, minorRadius | ring |
| cone | radiusTop (may be zero), radiusBottom, depth | frustum |
| gear | radius, depth, teeth | schematic tooth boxes; not an involute gear |
| tube | radius, length | currently solid round rod, not a hollow pipe |

`material`: aluminum, steel, dark, copper, blue, orange, green, cream.

More specialized parts (turbine blades, cast crankcases, helical gears, ATM belts, complex valves) require additional Blender geometry helpers. Write them in `blender` and add an explicit schema/type plus automated tests, **not** an inaccurate substitute primitive.

## Animation joint design

`animation` includes `schemaVersion:2`, `machineId`, `mechanism:"generic_joints"`, `defaultRPM`, `maxRPM` and `joints`.

Each joint has:

- `entity`: component `id`.
- `type`: `rotate`, `slide`, or `oscillate`.
- `axis`: local XYZ axis in Blender Z-up (must be nonzero).
- `ratio`: machine-cycle multiplier (negative reverses motion; e.g. counterrotating gears).
- `phase`: phase angle in radians.
- `amplitude`: displacement in meters for slides, radians for oscillating rotation.
- `offset`: base displacement/angle for slide and oscillation.

`rotate` uses `angle = ratio * cycleAngle + phase`. `oscillate` uses `angle = offset + amplitude*sin(ratio*cycleAngle + phase)`. `slide` uses `distance = offset + amplitude*sin(ratio*cycleAngle + phase)`. The AR runtime applies these to saved rest transforms, and rotation can be reversed or synchronized by gear ratio. The Blender preview uses the same formulas for compatible joint types. This is a **kinematic illustration**, not a force or collision dynamics simulator.

For connected complex linkages where a sine wave is incorrect, implement a custom tested motion controller in Python and Swift. For example, the two-stroke reference uses the analytic slider-crank equations rather than simple sine translation.

## Example: fan not in built-in registry

```json
{
  "schemaVersion": 2,
  "id": "desk_fan",
  "displayName": "Educational desk fan",
  "machineType": "fan",
  "accuracy": "conceptual-educational",
  "units": "meters",
  "coordinateSystem": "Z_UP",
  "components": [
    {"id":"Motor","name":"Motor","description":"Drives the shaft","primitive":"cylinder","position":[0,0,0.20],"rotationDegrees":[0,0,0],"dimensions":{"radius":0.06,"depth":0.09,"axis":"Y"},"material":"steel","movable":false},
    {"id":"BladeWheel","name":"Blade wheel","description":"Moves air","primitive":"gear","position":[0,-0.08,0.20],"rotationDegrees":[0,0,0],"dimensions":{"radius":0.13,"depth":0.01,"teeth":6,"axis":"Y"},"material":"blue","movable":true}
  ],
  "animation": {"schemaVersion":2,"machineId":"desk_fan","mechanism":"generic_joints","defaultRPM":200,"maxRPM":2500,"joints":[{"entity":"BladeWheel","type":"rotate","axis":[0,1,0],"ratio":1,"phase":0}]},
  "warnings": ["Fan blades are represented by schematic gear-shaped paddles. Not a production fan model."]
}
```

For a realistic fan, write actual blade mesh geometry instead of the gear placeholder. The data example demonstrates the workflow, not aesthetic fidelity.

```
python3 -m machine3d plan --spec output/desk_fan/blueprint.json --out output/desk_fan --offline
python3 -m machine3d build --spec output/desk_fan/blueprint.json --out output/desk_fan --offline
python3 -m machine3d validate --out output/desk_fan
```

## How the agent should approach arbitrary requests

1. Determine specific mechanism and educational objectives.
2. Search for documented components, diagrams, dimensions and movement descriptions; log licenses.
3. Create assembly graph in JSON and assign physically plausible units and pivots.
4. Decide whether the generic primitives can represent the geometry. If **not**, implement Blender geometry extensions using `bpy` rather than falsely claiming realism.
5. Derive joint kinematics; when generic joints are insufficient, add a **new versioned motion controller** for RealityKit and test it against Blender output.
6. Run `plan --spec`, correct validation, then `build --spec` on a machine with Blender installed.
7. Review Blender preview and animations, check USD entities and import into iOS, run device tests.
8. Report approximation and completeness honestly.

## Built-in automatic routing / promotion

Run `build --prompt "..."` for any machine, including one not found in the
registry. An unknown machine creates an agent handoff; the AI coding agent
authors the blueprint, then reruns the same command. After a passing Blender
build and export validation, the blueprint is automatically saved to the
persistent learned-template library. See `docs/template-learning.md`.
