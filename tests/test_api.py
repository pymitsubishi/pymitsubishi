from unittest.mock import patch

import pytest

from pymitsubishi import MitsubishiAPI
from tests.test_fixtures import REAL_DEVICE_XML_RESPONSE

HEX = "fc410130100108020107070101000000000001b04170"


@pytest.fixture
def api():
    return MitsubishiAPI(device_host_port="192.0.2.1")


def test_send_hex_command_omits_connect_by_default(api):
    """A control command must not carry the CONNECT element unless asked to."""
    with patch.object(api, "make_request", return_value=REAL_DEVICE_XML_RESPONSE) as req:
        api.send_hex_command(HEX)

    req.assert_called_once_with(f"<CSV><CODE><VALUE>{HEX}</VALUE></CODE></CSV>")


@pytest.mark.parametrize(("connect", "tag"), [(True, "ON"), (False, "OFF")])
def test_send_hex_command_writes_connect_when_asked(api, connect, tag):
    with patch.object(api, "make_request", return_value=REAL_DEVICE_XML_RESPONSE) as req:
        api.send_hex_command(HEX, connect=connect)

    req.assert_called_once_with(f"<CSV><CONNECT>{tag}</CONNECT><CODE><VALUE>{HEX}</VALUE></CODE></CSV>")


def test_send_command_passes_connect_through(api):
    with patch.object(api, "send_hex_command", return_value=REAL_DEVICE_XML_RESPONSE) as hex_cmd:
        api.send_command(bytes.fromhex(HEX), connect=False)

    hex_cmd.assert_called_once_with(HEX, connect=False)


def test_send_status_request_omits_connect_by_default(api):
    with patch.object(api, "make_request", return_value=REAL_DEVICE_XML_RESPONSE) as req:
        api.send_status_request()

    req.assert_called_once_with("<CSV></CSV>")


def test_send_echonet_enable_omits_connect_by_default(api):
    with patch.object(api, "make_request", return_value=REAL_DEVICE_XML_RESPONSE) as req:
        api.send_echonet_enable()

    req.assert_called_once_with("<CSV><ECHONET>ON</ECHONET></CSV>")


def test_send_echonet_enable_writes_connect_when_asked(api):
    with patch.object(api, "make_request", return_value=REAL_DEVICE_XML_RESPONSE) as req:
        api.send_echonet_enable(connect=True)

    req.assert_called_once_with("<CSV><CONNECT>ON</CONNECT><ECHONET>ON</ECHONET></CSV>")
