import pytest

from pymitsubishi import SensorStates


@pytest.mark.parametrize(
    "data_hex, room_temperature",
    [
        ("fc620130100300000e00c0b0affe42000114a7000031", 23.5),
        ("fc620130100300000b00baabaafe4200009a33000033", 21.0),
    ],
)
def test_room_temperature(data_hex, room_temperature):
    state = SensorStates.parse_sensor_states(bytes.fromhex(data_hex))
    assert state.inside_temperature_2 == room_temperature


@pytest.mark.parametrize(
    "data_hex, outside_temperature",
    [
        ("fc620130100300000e00c0b0affe42000114a7000031", 32.0),
        ("fc620130100300000b00baabaafe4200009a33000033", 29.0),
    ],
)
def test_outside_temperature(data_hex, outside_temperature):
    state = SensorStates.parse_sensor_states(bytes.fromhex(data_hex))
    assert state.outside_temperature == outside_temperature
