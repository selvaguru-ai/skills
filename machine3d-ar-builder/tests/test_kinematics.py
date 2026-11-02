import math
import pytest
from machine3d.kinematics import crank_slider, port_uncovered_by_crown
from machine3d.spec import TwoStrokeSpec
from machine3d.validation import validate_kinematics

S = TwoStrokeSpec()


def test_tdc_and_bdc_exact():
    top = crank_slider(0, S.crank_radius_m, S.rod_length_m)
    bottom = crank_slider(math.pi, S.crank_radius_m, S.rod_length_m)
    assert top.wrist_z == pytest.approx(S.rod_length_m + S.crank_radius_m)
    assert bottom.wrist_z == pytest.approx(S.rod_length_m - S.crank_radius_m)
    assert top.wrist_z - bottom.wrist_z == pytest.approx(S.stroke_m)


def test_rod_length_constant():
    for i in range(1440):
        p = crank_slider(i * math.pi / 720, S.crank_radius_m, S.rod_length_m)
        length = math.hypot(p.crank_x, p.wrist_z - p.crank_z)
        assert length == pytest.approx(S.rod_length_m, abs=1e-10)


def test_full_cycle_periodic():
    for theta in [0.1, 0.5, 2.0, 5.0]:
        a = crank_slider(theta, S.crank_radius_m, S.rod_length_m)
        b = crank_slider(theta + 2 * math.pi, S.crank_radius_m, S.rod_length_m)
        assert a.wrist_z == pytest.approx(b.wrist_z)
        assert a.crank_x == pytest.approx(b.crank_x)


def test_ports_closed_tdc_open_bdc():
    args = (S.crank_radius_m, S.rod_length_m, S.wrist_to_crown_m)
    assert not port_uncovered_by_crown(0, S.exhaust_top_z_m, *args)
    assert port_uncovered_by_crown(math.pi, S.exhaust_top_z_m, *args)
    assert not port_uncovered_by_crown(0, S.transfer_top_z_m, *args)
    assert port_uncovered_by_crown(math.pi, S.transfer_top_z_m, *args)


def test_kinematics_report():
    report = validate_kinematics(S)
    assert report["passed"], report
    assert report["minHeadClearanceM"] > 0


@pytest.mark.parametrize("radius,length", [(0, 0.1), (0.1, 0.1), (0.3, 0.1), (-1, 0.1)])
def test_invalid_rod_geometry(radius, length):
    with pytest.raises(ValueError):
        crank_slider(0, radius, length)


def test_spec_rejects_head_collision():
    from dataclasses import replace
    with pytest.raises(ValueError):
        replace(S, cylinder_top_z_m=0.13).validate()
