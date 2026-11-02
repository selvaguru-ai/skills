#!/bin/zsh
# Double-click to generate one of the built-in machines, no user reference images required.
cd "$(dirname "$0")" || exit 1
PYTHON="$(command -v python3)"
if [ -z "$PYTHON" ]; then
  echo "Python 3.10+ is required."
  read "_?Press Enter to close..."
  exit 1
fi
echo "Examples: two-stroke engine, electric motor, gearbox, ATM, centrifugal pump, washing machine"
read "MACHINE_PROMPT?Describe the machine you want to build: "
if [ -z "$MACHINE_PROMPT" ]; then
  MACHINE_PROMPT="Create a two-stroke motorcycle engine"
fi
FOLDER="output/machine_$(date +%Y%m%d_%H%M%S)"
"$PYTHON" -m machine3d build --prompt "$MACHINE_PROMPT" --out "$FOLDER"
status=$?
if [ "$status" -eq 0 ]; then
  echo "Success! Open $FOLDER/machine.blend in Blender."
else
  echo "Build incomplete. For a NEW machine, open Cursor and ask its agent to use"
  echo "the skill to complete AGENT_BLUEPRINT_TASK.md and rerun the same build command."
  echo "Blender must be installed to generate .blend and .usdz."
fi
read "_?Press Enter to close..."
exit "$status"
