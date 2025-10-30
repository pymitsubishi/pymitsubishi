import pytest

from pymitsubishi import RemoteTemperatureMode, RemoteTemperatureStates


# These commands are not gathered from real thermostats. These were generated, but are working on at least MSZ-LN35VG2V produced date 2023.03
@pytest.mark.parametrize(
    "data_hex, mode, temperature",
    [
        ("fc4101301007000f81000000000000000000000000e7", RemoteTemperatureMode.UseInternal, 0.5),
        ("fc4101301007000aaa000000000000000000000000c3", RemoteTemperatureMode.UseInternal, 21),
        ("fc41013010070104b6000000000000000000000000bc", RemoteTemperatureMode.RemoteTemp, 27),
        ("fc41013010070110c70000000000000000000000009f", RemoteTemperatureMode.RemoteTemp, 35.5),
    ],
)
def test_remote_temperature_states(data_hex, mode, temperature):
    command = RemoteTemperatureStates.generate_remote_temperature_command(mode, temperature)
    assert command.hex() == data_hex
