from unittest.mock import Mock

import pytest

from pymitsubishi import DriveMode, MitsubishiController, RemoteLock
from tests.test_fixtures import REAL_DEVICE_XML_RESPONSE


def test_set_power_on():
    """Test a complete cycle of status fetch and device control."""
    mock_api = Mock()
    controller = MitsubishiController(mock_api)
    mock_api.send_status_request.return_value = REAL_DEVICE_XML_RESPONSE
    mock_api.send_hex_command = Mock(return_value=REAL_DEVICE_XML_RESPONSE)

    controller.set_power(True)

    mock_api.send_hex_command.assert_called_once_with("fc410130100101020100090000000000000000ac4183")


@pytest.mark.parametrize(
    "mode, hex_cmd",
    [
        (DriveMode.AUTO, "fc410130100102020008090000000000000000ac417b"),
        (DriveMode.FAN, "fc410130100102020007090000000000000000ac417c"),
        (DriveMode.COOLER, "fc410130100102020003090000000000000000ac4180"),
        (DriveMode.HEATER, "fc410130100102020001090000000000000000ac4182"),
    ],
)
def test_set_auto(mode, hex_cmd):
    """Test a complete cycle of status fetch and device control."""
    mock_api = Mock()
    controller = MitsubishiController(mock_api)
    mock_api.send_status_request.return_value = REAL_DEVICE_XML_RESPONSE
    mock_api.send_hex_command = Mock(return_value=REAL_DEVICE_XML_RESPONSE)

    controller.set_mode(mode)

    mock_api.send_hex_command.assert_called_once_with(hex_cmd)


@pytest.mark.parametrize(
    "lock, hex_cmd",
    [
        (RemoteLock.PowerLocked, "fc410130100140020000090000000000010000ac4144"),
    ],
)
def test_set_remote_lock(lock, hex_cmd):
    """Test a complete cycle of status fetch and device control."""
    mock_api = Mock()
    controller = MitsubishiController(mock_api)
    mock_api.send_status_request.return_value = REAL_DEVICE_XML_RESPONSE
    mock_api.send_hex_command = Mock(return_value=REAL_DEVICE_XML_RESPONSE)

    controller.set_remote_lock(lock)

    mock_api.send_hex_command.assert_called_once_with(hex_cmd)


@pytest.mark.parametrize(
    "temp, hex_cmd",
    [
        (22.0, "fc410130100104020000090000000000000000ac4181"),
        (22.5, "fc410130100104020000190000000000000000ad4170"),
        (16.0, "fc4101301001040200000f0000000000000000a04187"),
        (12.0, "fc4101301001040200000f000000000000000098418f"),
    ],
)
def test_set_temperature(temp, hex_cmd):
    """Test a complete cycle of status fetch and device control."""
    mock_api = Mock()
    controller = MitsubishiController(mock_api)
    mock_api.send_status_request.return_value = REAL_DEVICE_XML_RESPONSE
    mock_api.send_hex_command = Mock(return_value=REAL_DEVICE_XML_RESPONSE)

    controller.set_temperature(temp)

    mock_api.send_hex_command.assert_called_once_with(hex_cmd)
