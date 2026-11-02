# Example machine plans

`two_stroke_engine/` — detailed legacy reference (v1), analytical crank-slider animation.

`electric_motor/`, `gas_turbine/`, `spur_gearbox/`, `centrifugal_pump/`, `atm_machine/`, `washing_machine/` — reusable generic-blueprint examples (v2).

The examples contain metadata, blueprint and planning reports; **they are not verified Blender exports**. On a Mac with Blender, run `python3 -m machine3d build --spec examples/<machine>/blueprint.json --out output/<machine>` to generate `.blend`, `.usdz` and preview.

For a request that isn't a built-in example, Cursor should follow `SKILL.md` to research and author a complete new v2 blueprint and implement any nonprimitive shapes/complex mechanisms.
