import pytest

from pymitsubishi import DriveMode, GeneralStates, HorizontalWindDirection, PowerOnOff, VerticalWindDirection


@pytest.mark.parametrize(
    "data_hex, power, mode",
    [  #  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        ("fc62013010020000000b070000000083b046000000d0", PowerOnOff.OFF, DriveMode.COOLER),
        ("fc62013010020000010b070000000083b046000000cf", PowerOnOff.ON, DriveMode.COOLER),
        ("fc62013010020000010a070000000083b032000000e4", PowerOnOff.ON, DriveMode.DEHUM),
        ("fc620130100200000109090000000083ac28000000f1", PowerOnOff.ON, DriveMode.HEATER),
        ("fc620130100200000107070000000083b028000000f1", PowerOnOff.ON, DriveMode.FAN),
        ("fc620130100200000108080000000083ae46000000d3", PowerOnOff.ON, DriveMode.AUTO),
        ("fc6201301002000001080b0000000083a846000000d6", PowerOnOff.ON, DriveMode.AUTO),  # auto, 20º => cooling
        ("fc620130100200000108010000000083bc46000000cc", PowerOnOff.ON, DriveMode.AUTO),  # auto, 30º => heating
    ],
)
def test_parse_general_states_mode(data_hex, power, mode):
    states = GeneralStates.parse_general_states(bytes.fromhex(data_hex))
    assert states.power_on_off == power
    assert states.drive_mode == mode


@pytest.mark.parametrize(
    "data_hex, mode, off, home, isee",
    [
        # 0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        ("fc620130100200000108070000000083b046000000d2", DriveMode.AUTO, False, False, True),  # sensor
        ("fc620130100200000108070000000083b046000000d2", DriveMode.AUTO, False, True, True),  # home, sensor
        ("fc620130100200000108070000000083b046000000d2", DriveMode.AUTO, True, False, True),  # off, sensor
        ("fc620130100200000108070000000083b046000000d2", DriveMode.AUTO, False, False, False),  # nothing
        # ^^ isee bit seems to be always set in auto mode?
        ("fc62013010020000010b070000000083b046000000cf", DriveMode.COOLER, False, False, True),  # sensor
        ("fc62013010020000010b070000000083b046000000cf", DriveMode.COOLER, False, True, True),  # home, sensor
        ("fc62013010020000010b070000000083b046000000cf", DriveMode.COOLER, True, False, True),  # off, sensor
        ("fc620130100200000103070000000083b046000000d7", DriveMode.COOLER, False, False, False),  # nothing
        #                   ^^
    ],
)
def test_parse_general_states_drive_mode_isee(data_hex, mode, off, home, isee):
    states = GeneralStates.parse_general_states(bytes.fromhex(data_hex))
    assert states.drive_mode == mode
    # isee bit seems to be always set in auto mode
    assert states.i_see_sensor == (isee or mode == DriveMode.AUTO)


@pytest.mark.parametrize(
    "data_hex, temp",
    [
        ("fc62013010020000010b070000000083b046000000cf", 24.0),
        ("fc62013010020000010b090000000083ac46000000d1", 22.0),
    ],
)
def test_parse_general_states_temp(data_hex, temp):
    states = GeneralStates.parse_general_states(bytes.fromhex(data_hex))
    assert states.coarse_temperature == temp
    assert states.fine_temperature == temp
    assert states.temperature == temp


@pytest.mark.parametrize(
    "data_hex, wind_speed",
    [  #  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        ("fc62013010020000010b070000000083b046000000cf", 0),  # auto
        ("fc62013010020000010b070100000083b046000000ce", 1),  # "silent"
        ("fc620130100200000107070200000083b028000000ef", 2),  # 1 bar
        ("fc620130100200000107070300000083b028000000ee", 3),  # 2 bars
        # no 4 from my remote
        ("fc620130100200000107070500000083b028000000ec", 5),  # 3 bars
        ("fc620130100200000107070600000083b028000000eb", 6),  # 4 bars, max
    ],
)
def test_parse_general_states_wind_speed(data_hex, wind_speed):
    states = GeneralStates.parse_general_states(bytes.fromhex(data_hex))
    assert states.wind_speed.value == wind_speed


@pytest.mark.parametrize(
    "data_hex, v_vane_l, v_vane_r",
    [  #  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        ("fc62013010020000010b070000000083b046000000cf", VerticalWindDirection.AUTO, VerticalWindDirection.AUTO),
        ("fc62013010020000010b070001000083b046000000ce", VerticalWindDirection.V1, VerticalWindDirection.AUTO),
        ("fc62013010020000010b070002000083b046000000cd", VerticalWindDirection.V2, VerticalWindDirection.AUTO),
        ("fc62013010020000010b070003000083b046000000cc", VerticalWindDirection.V3, VerticalWindDirection.AUTO),
        ("fc62013010020000010b070004000083b046000000cb", VerticalWindDirection.V4, VerticalWindDirection.AUTO),
        ("fc62013010020000010b070005000083b046000000ca", VerticalWindDirection.V5, VerticalWindDirection.AUTO),
        ("fc62013010020000010b070007000083b046000000c8", VerticalWindDirection.SWING, VerticalWindDirection.AUTO),
        ("fc62013010020000010b070001000083b046000000ce", VerticalWindDirection.AUTO, VerticalWindDirection.V1),
        ("fc62013010020000010b070002000083b046000000cd", VerticalWindDirection.AUTO, VerticalWindDirection.V2),
        ("fc62013010020000010b070005000083b046000000ca", VerticalWindDirection.AUTO, VerticalWindDirection.V5),
        ("fc62013010020000010b070007000083b046000000c8", VerticalWindDirection.AUTO, VerticalWindDirection.SWING),
        ("fc62013010020000010b070005000083b046000000ca", VerticalWindDirection.V1, VerticalWindDirection.V5),
        ("fc62013010020000010b070005000083b046000000ca", VerticalWindDirection.V5, VerticalWindDirection.V1),
    ],
)
def test_parse_general_states_vertical_vane(data_hex, v_vane_l: VerticalWindDirection, v_vane_r: VerticalWindDirection):
    states = GeneralStates.parse_general_states(bytes.fromhex(data_hex))

    # My system has a left & right vertical vane, but I can't find the bits to see them separately
    # The "right" vane bits seem to report the "highest" one
    # The "left" vane stays "auto"
    v_vane = VerticalWindDirection(max(v_vane_l.value, v_vane_r.value))
    assert states.vertical_wind_direction == v_vane


@pytest.mark.parametrize(
    "data_hex, vane",
    [  #  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        ("fc62013010020000010b070000000081b046000000d1", HorizontalWindDirection.FAR_LEFT),
        ("fc62013010020000010b070000000082b046000000d0", HorizontalWindDirection.LEFT),
        ("fc62013010020000010b070000000083b046000000cf", HorizontalWindDirection.CENTER),
        ("fc62013010020000010b070000000084b046000000ce", HorizontalWindDirection.RIGHT),
        ("fc62013010020000010b070000000085b046000000cd", HorizontalWindDirection.FAR_RIGHT),
        ("fc62013010020000010b070000000088b046000000ca", HorizontalWindDirection.LEFT_RIGHT),  # split
        ("fc62013010020000010b07000000008cb046000000c6", HorizontalWindDirection.SWING),  # sweep
    ],
)
def test_parse_general_states_horizontal_vane(data_hex, vane):
    states = GeneralStates.parse_general_states(bytes.fromhex(data_hex))
    assert states.horizontal_wind_direction == vane


@pytest.mark.parametrize(
    "data_hex, h_vane, isee_h_vane",
    [  #  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        ("fc62013010020000010b070000000083b046000000cf", HorizontalWindDirection.CENTER, 0),  # off
        ("fc62013010020000010b070000000080b046000100d1", HorizontalWindDirection.AUTO, 1),  # avoid person
        ("fc62013010020000010b070000000080b046000200d0", HorizontalWindDirection.AUTO, 2),  # aim at person
        ("fc62013010020000010b070000000080b046000000d2", HorizontalWindDirection.AUTO, 0),  # wide
    ],
)
def test_parse_general_states_h_vane_isee(data_hex, h_vane, isee_h_vane):
    states = GeneralStates.parse_general_states(bytes.fromhex(data_hex))
    assert states.horizontal_wind_direction == h_vane
    assert states.wind_and_wind_break_direct == isee_h_vane


# Based on my tests, these settings available on my remote are not visible in the data:
#  - Purifier on/off
#  - Night mode on/off
#  - iSee modes (partially visible in non-auto mode)
