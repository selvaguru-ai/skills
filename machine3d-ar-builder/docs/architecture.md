# Machine3D general architecture (v0.3)

`Natural-language request` → `Cursor AI research & planning` → `registered template OR agent-authored blueprint` → `automatic licensed reference search, optional` → `Blender procedural assembly` → `validation/render` → `.blend`, `.usdz`, metadata → `Swift MachineARKit runtime`.

The reusable generic pipeline uses v2 `blueprint.json`. The optimized v1 two-stroke reference builder and mathematically validated crank-slider are retained. New machines do **not** need to be implemented by editing `cli.py` each time: Cursor can author a new blueprint and invoke `--spec`, adding geometry primitives and kinematics only if required.

**CLI limitation:** the CLI is deterministic Python, not a multimodal foundation model. The Cursor agent performs open-ended understanding and blueprint design. If that agent cannot research/author the geometry, the program should report that limit instead of generating a misleading model.

## Generic geometry

See `docs/blueprint-authoring.md` and `schemas/blueprint.schema.json`. Blender works in meters, Z-up, stable component names, parent entities with local pivots. The generic builder supports simple CSG-like primitives and approximate gears. Detailed specialized geometries must be implemented and reviewed. USD exporter requests Y-up conversion.

## Animation ownership

Blender produces the reference/preview; exported USDZ is a static pose. RealityKit drives dynamic animation from the same JSON specification. v2 supports rotate/slide/oscillate with gear ratios and phases. v1 two-stroke runs analytic crank-slider. Complex valvetrains, turbine flow simulation, ATM banknote physics and cam/linkage motion require dedicated mechanisms.

## Validation

- Pure Python: blueprint structural integrity, parent-cycle detection, unique IDs, required geometry dimensions, joint targets, source metadata.
- v1 engine: piston stroke, head clearance, rod-length conservation, periodicity.
- Blender (when installed): named entity presence, mesh count, basic motion existence, preview attempt.
- Export: USDZ archive and main USD layer.
- Device release: USD mesh hierarchy, pivot coordinate calibration, ARKit placement, collision/taps, graphics performance on real iPhone. These device tests have not run inside the packaging environment.

## Real engineering accuracy

Manufacturer-accurate assembly requires dimensioned CAD drawings, verified part measurements, tolerances, and potentially simulation. A conceptual model should not be called a physically validated motor/ATM/turbine just because its animations play.

## New v0.3 lifecycle

A natural-language `build --prompt` request is resolved against learned and
built-in templates, else it creates an agent handoff. The agent completes an
unknown machine blueprint and re-enters the same pipeline. A passing Blender
build auto-promotes a versioned, self-contained blueprint into a persistent
registry outside the installed skill folder. See `template-learning.md`.
