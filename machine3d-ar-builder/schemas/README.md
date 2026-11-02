# Model schemas

- `blueprint.schema.json` — generic version 2 authoring contract for any new machine (AI-authored geometry and joints).
- `machine.schema.json`, `animation.schema.json` — legacy v1 reference engine schema; these are retained for backwards compatibility.

The Python blueprint validator performs additional cross-file/semantic checks (unique names, animation targets, valid dimensions, parent cycles) beyond the JSON Schema file. See `docs/blueprint-authoring.md`.
