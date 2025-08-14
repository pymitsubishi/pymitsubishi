import pytest

from pymitsubishi import EnergyStates


@pytest.mark.parametrize(
    "data_hex, this_unit, other_units",
    [  #  0 1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6 7 8 9 0 1
        ("fc6201301006000000000001004700004200000000cd", False, False),
        ("fc620130100600000000001a52280000420000000081", False, False),
        ("fc6201301006000000010004004700004200000000c9", True, False),
        ("fc620130100600000000016652280000420000000034", False, True),
        ("fc620130100600000001025552290000420000000042", True, True),
        ("fc620130100600000001000e004700004200000000bf", True, True),
        ("fc620130100600000000000a004700004200000000c4", False, True),
        ("fc62013010060000000102095229000042000000008e", True, False),
    ],
)
def test_operating(data_hex, this_unit, other_units):
    state = EnergyStates.parse_energy_states(data_hex)
    assert state.operating == this_unit


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
