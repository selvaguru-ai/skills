"""Reference-engine specifications, validation, and metadata generation."""
from __future__ import annotations
from dataclasses import asdict, dataclass
from math import pi
from pathlib import Path
import json


@dataclass(frozen=True)
class TwoStrokeSpec:
    machine_id: str = "two_stroke_engine"
    display_name: str = "Educational single-cylinder two-stroke gasoline engine"
    bore_m: float = 0.064
    stroke_m: float = 0.054
    rod_length_m: float = 0.105
    piston_height_m: float = 0.038
    wrist_to_crown_m: float = 0.018
    crank_web_radius_m: float = 0.042
    cylinder_base_z_m: float = 0.071
    cylinder_top_z_m: float = 0.153
    cylinder_wall_m: float = 0.004
    exhaust_top_z_m: float = 0.116
    exhaust_bottom_z_m: float = 0.096
    transfer_top_z_m: float = 0.103
    transfer_bottom_z_m: float = 0.086
    intake_top_z_m: float = 0.089
    intake_bottom_z_m: float = 0.075
    render_samples: int = 120
    approximate: bool = True

    @property
    def crank_radius_m(self) -> float:
        return self.stroke_m / 2

    @property
    def displacement_cc(self) -> float:
        return (pi / 4) * self.bore_m ** 2 * self.stroke_m * 1_000_000

    def validate(self) -> None:
        measurements = [
            self.bore_m, self.stroke_m, self.rod_length_m, self.piston_height_m,
            self.wrist_to_crown_m, self.cylinder_wall_m,
        ]
        if min(measurements) <= 0:
            raise ValueError("All mechanical dimensions must be positive")
        if self.rod_length_m <= self.crank_radius_m:
            raise ValueError("Connecting rod must exceed crank radius")
        if self.wrist_to_crown_m >= self.piston_height_m:
            raise ValueError("Wrist-to-crown offset exceeds piston height")
        crown_tdc = self.rod_length_m + self.crank_radius_m + self.wrist_to_crown_m
        if crown_tdc > self.cylinder_top_z_m:
            raise ValueError("Piston collides with cylinder head at TDC")
        if not self.cylinder_base_z_m < self.intake_bottom_z_m < self.intake_top_z_m < self.cylinder_top_z_m:
            raise ValueError("Invalid intake port limits")
        if not self.cylinder_base_z_m < self.transfer_bottom_z_m < self.transfer_top_z_m < self.cylinder_top_z_m:
            raise ValueError("Invalid transfer port limits")
        if not self.cylinder_base_z_m < self.exhaust_bottom_z_m < self.exhaust_top_z_m < self.cylinder_top_z_m:
            raise ValueError("Invalid exhaust port limits")
        if self.render_samples < 12 or self.render_samples > 720:
            raise ValueError("render_samples must be 12..720")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["crank_radius_m"] = self.crank_radius_m
        d["displacement_cc"] = round(self.displacement_cc, 2)
        return d


COMPONENTS = [
    ("CylinderBlock", "Cylinder block", "Guides piston motion and contains exhaust, transfer, and intake ports.", False),
    ("CylinderHead", "Cylinder head", "Seals combustion chamber and carries the spark plug.", False),
    ("PistonAssembly", "Piston", "Receives combustion pressure and moves along the cylinder.", True),
    ("PistonRing_01", "Top piston ring", "Helps seal gases against cylinder wall.", True),
    ("PistonRing_02", "Second piston ring", "Supports sealing and heat transfer.", True),
    ("WristPin", "Wrist pin", "Connects piston and small connecting-rod end.", True),
    ("ConnectingRodAssembly", "Connecting rod", "Transfers piston force to crankshaft and oscillates.", True),
    ("CrankshaftAssembly", "Crankshaft", "Converts reciprocating motion to rotation.", True),
    ("CrankWeb_Left", "Left crank web", "Supports offset crank pin.", True),
    ("CrankWeb_Right", "Right crank web", "Supports offset crank pin.", True),
    ("CrankPin", "Crank pin", "Connects the rod big end to the crank throw.", True),
    ("Flywheel", "Flywheel", "Stores rotational energy to smooth crank rotation.", True),
    ("Crankcase", "Crankcase", "Encloses crankshaft and precompresses incoming mixture.", False),
    ("SparkPlug", "Spark plug", "Ignites compressed air-fuel mixture near top dead center.", False),
    ("ExhaustPort", "Exhaust port", "Allows burnt exhaust gases to escape when uncovered.", False),
    ("TransferPort", "Transfer ports", "Connect crankcase to cylinder during scavenging.", False),
    ("IntakePort", "Intake port", "Admits fresh mixture into crankcase during the induction phase.", False),
]


def component_manifest() -> list[dict]:
    return [dict(id=key, name=title, description=description, movable=moving, entityName=key)
            for key, title, description, moving in COMPONENTS]


def animation_spec(spec: TwoStrokeSpec) -> dict:
    return {
        "schemaVersion": 1,
        "machineId": spec.machine_id,
        "mechanism": "crank_slider",
        "units": "meters",
        "twoStrokeRevolutionsPerCycle": 1,
        "crankRadius": spec.crank_radius_m,
        "connectingRodLength": spec.rod_length_m,
        "wristToCrown": spec.wrist_to_crown_m,
        "defaultRPM": 600,
        "maxRPM": 6000,
        "coordinateSystem": {
            "blender": "Z_UP, crankshaft axis Y",
            "runtime": "Y_UP, crankshaft axis -Z; assumes Blender USD axis conversion",
        },
        "entities": {
            "piston": "PistonAssembly",
            "crankshaft": "CrankshaftAssembly",
            "connectingRod": "ConnectingRodAssembly",
        },
        "notes": [
            "Runtime uses the analytical crank-slider mechanism; exported preview animation is not required.",
            "Review coordinate conversion on an iPhone before publishing other machines.",
        ],
    }


def machine_metadata(spec: TwoStrokeSpec) -> dict:
    return {
        "schemaVersion": 1,
        "id": spec.machine_id,
        "displayName": spec.display_name,
        "machineType": "single-cylinder, piston-port, crankcase-scavenged two-stroke spark-ignition",
        "accuracy": "conceptual-educational",
        "dimensions": spec.to_dict(),
        "components": component_manifest(),
        "stages": [
            {"id": "compression", "label": "Upstroke: compression and crankcase intake", "degrees": [180, 360]},
            {"id": "power", "label": "Downstroke: combustion, exhaust, and scavenging", "degrees": [0, 180]},
        ],
        "warnings": [
            "All dimensions are illustrative, not sourced from a manufacturer.",
            "Simplified port shapes and gas flows; no fluid dynamics or structural safety certification.",
            "For real engineering accuracy, replace with manufacturer drawings and verify port timing.",
        ],
    }


def save_spec_bundle(folder: Path, spec: TwoStrokeSpec) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    bundle = {
        "machine.json": machine_metadata(spec),
        "animation_spec.json": animation_spec(spec),
        "geometry_spec.json": spec.to_dict(),
    }
    for name, data in bundle.items():
        (folder / name).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
