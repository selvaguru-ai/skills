"""Crank-slider equations; units are meters and radians throughout.

Coordinate frame in Blender: X horizontal, Y crankshaft axis, Z cylinder axis.
The crank pin rotates around Y from +Z toward +X for increasing crank angle.
One crankshaft revolution is one cycle in the reference 2-stroke engine.
"""
from __future__ import annotations
from dataclasses import dataclass
from math import atan2, cos, pi, sin, sqrt, isfinite


@dataclass(frozen=True)
class Pose:
    theta: float
    crank_x: float
    crank_z: float
    wrist_z: float
    rod_x: float
    rod_z: float
    rod_tilt_y: float
    piston_velocity_per_radian: float


def crank_slider(theta: float, crank_radius: float, rod_length: float) -> Pose:
    """Exact slider-crank kinematics with zero pin offset.

    Wrist center is constrained to x=0; crankshaft center at x=z=0.
    `rod_tilt_y` rotates a rod initially aligned with local +Z.
    """
    if not all(isfinite(v) for v in (theta, crank_radius, rod_length)):
        raise ValueError("Non-finite mechanism parameter")
    if crank_radius <= 0 or rod_length <= crank_radius:
        raise ValueError("Require crank_radius > 0 and rod_length > crank_radius")
    sx = crank_radius * sin(theta)
    cz = crank_radius * cos(theta)
    vertical = sqrt(rod_length * rod_length - sx * sx)
    wrist_z = cz + vertical
    tilt = atan2(-sx, vertical)
    velocity = -crank_radius * sin(theta) - (crank_radius ** 2 * sin(theta) * cos(theta)) / vertical
    return Pose(
        theta=theta,
        crank_x=sx,
        crank_z=cz,
        wrist_z=wrist_z,
        rod_x=sx / 2,
        rod_z=(cz + wrist_z) / 2,
        rod_tilt_y=tilt,
        piston_velocity_per_radian=velocity,
    )


def degrees_of_crank(revolutions: float) -> float:
    return revolutions * 2 * pi


def piston_crown_z(theta: float, radius: float, length: float, crown_offset: float) -> float:
    return crank_slider(theta, radius, length).wrist_z + crown_offset


def port_uncovered_by_crown(theta: float, port_top: float, radius: float, length: float, crown_offset: float) -> bool:
    """Simplified exhaust/transfer opening approximation based on piston crown position."""
    return piston_crown_z(theta, radius, length, crown_offset) <= port_top
