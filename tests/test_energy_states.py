import pytest

from pymitsubishi import EnergyStates


@pytest.mark.parametrize(
    "data_hex, operating",
    [  #  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        ("fc6201301006000000000001004100004200000000d3", False),  # all units off
        ("fc6201301006000000000001004100004200000000d3", False),  # this indoor unit off, other on
        ("fc62013010060000000102b951e50000420000000023", True),  # only this indoor unit on, others off
        ("fc6201301006000000010014004100004200000000bf", True),  # all indoor units on
        ("fc620130100600000000073851ec0000420000000099", True),  # all indoor units on
        ("fc62013010060000000106e451ed00004200000000ec", True),  # all indoor units on
    ],
)
def test_operating(data_hex, operating):
    state = EnergyStates.parse_energy_states(data_hex)
    assert state.operating == operating


@pytest.mark.parametrize(
    "data_hex, freq",
    [  #  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        ("fc6201301006000000000001004100004200000000d3", 0),  # all units off
        ("fc6201301006000000000001004100004200000000d3", 0),  # this indoor unit off, other on
        ("fc62013010060000000102b951e50000420000000023", 1),  # this indoor unit on, ~700W electrical consumption
        ("fc6201301006000000010014004100004200000000bf", 2),  # all indoor units on, ~1.9kW electrical consumption
        ("fc620130100600000000073851ec0000420000000099", 2),  # all indoor units on, ~1.8kW electrical consumption
    ],
)
def test_compressor_frequency(data_hex, freq):
    state = EnergyStates.parse_energy_states(data_hex)
    assert state.compressor_frequency == freq
