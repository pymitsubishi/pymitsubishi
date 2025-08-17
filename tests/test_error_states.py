import pytest

from pymitsubishi import ErrorStates


@pytest.mark.parametrize(
    "data_hex",
    [
        "fc6201301004000000800000000000000000000000d9",
    ],
)
def test_error_states(data_hex):
    state = ErrorStates.parse_error_states(data_hex)
    assert state.error_code == format(0x8000, "04x")
    assert not state.is_abnormal_state
