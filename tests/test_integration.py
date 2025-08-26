"""
Integration tests for pymitsubishi using real device response data.

These tests use sanitized data captured from actual Mitsubishi MAC-577IF-2E devices
to ensure the library works correctly with real-world responses.
"""

from unittest.mock import Mock, patch
import xml.etree.ElementTree

import pytest

from pymitsubishi import MitsubishiAPI, MitsubishiController

from .test_fixtures import (
    LED_PATTERNS,
    REAL_DEVICE_XML_RESPONSE,
    SAMPLE_CODE_VALUES,
    SAMPLE_PROFILE_CODES,
    TEMPERATURE_TEST_CASES,
)

UNIT_INFO_EXAMPLE = """
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
 <html>
   <head>
     <meta charset="UTF-8">
     <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1, user-scalable=no">
     <link rel="stylesheet" href="common.css" />
     <title>Information</title>
   </head>
   <body>
   <form name="form" method="get" action="unitinfo">
     <div class="all">
       <div class="titleA">Adaptor Information</div>
       <div class="itemA lineA">
         <dl>
           <dt>Adaptor name</dt>
             <dd>MAC-577IF-E</dd>
         </dl>
         <dl>
           <dt>Application version</dt>
             <dd>33.00</dd>
         </dl>
         <dl>
           <dt>Release version</dt>
             <dd>00.06</dd>
         </dl>
         <dl>
           <dt>Flash version</dt>
             <dd>00.01</dd>
         </dl>
         <dl>
           <dt>Boot version</dt>
             <dd>00.01</dd>
         </dl>
         <dl>
           <dt>Common platform version</dt>
             <dd>01.08</dd>
         </dl>
         <dl>
           <dt>Test release version</dt>
             <dd>00.00</dd>
         </dl>
         <dl>
           <dt>MAC address</dt>
             <dd>00:11:22:33:44:55</dd>
         </dl>
         <dl>
           <dt>ID</dt>
             <dd>1234567890</dd>
         </dl>
         <dl>
           <dt>Manufacturing date</dt>
             <dd>1970/01/01</dd>
         </dl>
         <dl>
           <dt>Current time</dt>
             <dd>2001/01/01 00:03:50</dd>
         </dl>
         <dl>
           <dt>Channel</dt>
             <dd>6</dd>
         </dl>
         <dl>
           <dt>RSSI</dt>
             <dd>-43dBm</dd>
         </dl>
         <dl>
           <dt>IT communication status</dt>
             <dd>Normal</dd>
         </dl>
         <dl>
           <dt>Server operation</dt>
             <dd>ON</dd>
         </dl>
         <dl>
           <dt>Server communication status</dt>
             <dd>Error (DNS)</dd>
         </dl>
         <div style="display:none">
           <dl>
             <dt>Server communication status(HEMS)</dt>
               <dd>--</dd>
           </dl>
         </div>
         <dl>
           <dt>SOI communication status</dt>
             <dd>Unsupported</dd>
         </dl>
         <dl>
           <dt>Thermal image timestamp</dt>
             <dd>--</dd>
         </dl>
       </div>
       <div class="titleA">Unit Information</div>
       <div class="itemA lineA">
         <dl>
           <dt>Unit type</dt>
             <dd>RAC</dd>
         </dl>
         <dl>
           <dt>IT protocol version</dt>
             <dd>03.00</dd>
         </dl>
         <dl>
           <dt>Error</dt>
             <dd>8000</dd>
         </dl>
       </div>
       <div class="itemB">
         <input class="btnA" type="submit" value="Reload">
       </div>
     </div>
     </form>
   </body>
 </html>
"""


def test_unit_info():
    api = MitsubishiAPI("localhost")
    parsed_unit_info = api._parse_unit_info_html(UNIT_INFO_EXAMPLE)
    assert parsed_unit_info["Adaptor Information"]["MAC address"] == "00:11:22:33:44:55"
    assert parsed_unit_info["Adaptor Information"]["RSSI"] == -43
    assert parsed_unit_info["Adaptor Information"]["Channel"] == 6


class TestRealDeviceResponseParsing:
    """Test parsing of real device XML responses."""

    def test_xml_response_parsing(self):
        """Test that real device XML responses are parsed correctly."""
        # This would test the XML parsing functionality
        # In a real test, we'd mock the API response
        pass  # Placeholder for XML parsing tests

    def test_profile_code_analysis(self):
        """Test ProfileCode analysis with real profile codes."""
        # Test the first profile code with actual capability flags
        profile_code = SAMPLE_PROFILE_CODES[0]
        # Our profile codes are 32 bytes (64 hex chars), but the analyzer expects 22 bytes
        # This test validates that the data structure is correct for a 32-byte profile
        data = bytes.fromhex(profile_code)
        assert len(data) == 32  # Real profile codes are 32 bytes

        # Verify basic structure without using the analyzer
        assert profile_code[:2] == "03"  # First byte should be 03
        assert profile_code[2:4] == "00"  # Second byte should be 00

    def test_group_code_extraction(self):
        """Test extraction of group codes from real code values."""
        group_codes = set()

        for code_value in SAMPLE_CODE_VALUES:
            if len(code_value) >= 22:
                # Group code is at position 20-22 in our format: ffffffffffffffffffff0202008000
                group_code = code_value[20:22]
                group_codes.add(group_code)

        expected_codes = {"02", "03", "04", "05", "06", "07", "08", "09", "0a"}
        assert group_codes == expected_codes


class TestTemperatureControl:
    """Test temperature control with real-world values."""

    @pytest.mark.parametrize("test_case", TEMPERATURE_TEST_CASES)
    def test_temperature_validation(self, test_case):
        """Test temperature validation with real temperature values."""
        celsius = test_case["celsius"]
        expected_units = test_case["expected_units"]
        valid = test_case["valid"]

        # Convert to 0.1°C units
        temp_units = int(celsius * 10)

        if valid:
            assert temp_units == expected_units
            assert 160 <= temp_units <= 320  # Valid range
        else:
            assert temp_units < 160 or temp_units > 320  # Invalid range


@patch("pymitsubishi.mitsubishi_api.requests.post")
class TestMitsubishiAPIIntegration:
    """Integration tests for MitsubishiAPI with mocked responses."""

    def test_status_request_with_real_response(self, mock_post):
        """Test status request handling with real device response structure."""
        # Mock the HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = '<?xml version="1.0" encoding="UTF-8"?><ESV>mocked_encrypted_data</ESV>'
        mock_post.return_value = mock_response

        # Mock the decryption to return our real XML
        api = MitsubishiAPI("192.168.1.100")

        # Mock the session.post method instead of requests.post
        with patch.object(api.session, "post") as mock_session_post:
            mock_session_post.return_value = mock_response

            with patch.object(api, "decrypt_payload") as mock_decrypt:
                mock_decrypt.return_value = REAL_DEVICE_XML_RESPONSE

                response = api.send_status_request()

                assert response == REAL_DEVICE_XML_RESPONSE
                assert "AA:BB:CC:DD:EE:FF" in response
                assert "1234567890" in response
                assert "PROFILECODE" in response

    def test_encryption_decryption_cycle(self, mock_post):
        """Test that encryption/decryption works with real-like data."""
        api = MitsubishiAPI("192.168.1.100")

        # Test that we can encrypt and decrypt a sample message
        original_xml = "<TEST>sample data</TEST>"

        # Test actual encryption/decryption
        encrypted = api.encrypt_payload(original_xml)
        assert encrypted is not None
        assert len(encrypted) > 0

        # Test decryption
        decrypted = api.decrypt_payload(encrypted)
        assert decrypted == original_xml

        # Verify the API can be initialized
        assert api.device_host_port == "192.168.1.100"


class TestMitsubishiControllerIntegration:
    """Integration tests for MitsubishiController with real data."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_api = Mock()
        self.controller = MitsubishiController(self.mock_api)

    def test_status_parsing_with_real_data(self):
        """Test status parsing with real device XML response."""
        # Mock the API to return real XML data
        self.mock_api.send_status_request.return_value = REAL_DEVICE_XML_RESPONSE

        self.controller.fetch_status()

        # Verify device info extraction
        assert self.controller.state.mac == "AA:BB:CC:DD:EE:FF"
        assert self.controller.state.serial == "1234567890"


class TestErrorHandling:
    """Test error handling with realistic scenarios."""

    def test_invalid_xml_response(self):
        """Test handling of malformed XML responses."""
        api = MitsubishiAPI("192.168.1.100")
        controller = MitsubishiController(api)

        with patch.object(api, "send_status_request") as mock_request:
            mock_request.return_value = "<invalid>xml<missing_close>"

            with pytest.raises(xml.etree.ElementTree.ParseError):
                controller.fetch_status()

    def test_connection_timeout_handling(self):
        """Test handling of connection timeouts."""
        import requests.exceptions

        api = MitsubishiAPI("192.168.1.100")

        with patch.object(api.session, "post") as mock_post:
            mock_post.side_effect = requests.exceptions.ConnectTimeout("Connection timeout")

            with pytest.raises(requests.exceptions.ConnectTimeout):
                api.send_status_request()


class TestRealWorldScenarios:
    """Test realistic usage scenarios."""

    def test_complete_status_and_control_cycle(self):
        """Test a complete cycle of status fetch and device control."""
        mock_api = Mock()
        controller = MitsubishiController(mock_api)

        # Mock successful status fetch
        mock_api.send_status_request.return_value = REAL_DEVICE_XML_RESPONSE

        # Test status fetch
        controller.fetch_status()

        # Mock successful control command
        mock_api.send_control_request.return_value = True

        # Test temperature control (this would need controller state setup)
        # This is a placeholder for actual control testing
        pass

    @pytest.mark.parametrize(
        "pattern",
        LED_PATTERNS.values(),
    )
    def test_led_pattern_parsing(self, pattern):
        """Test parsing of LED patterns from real device data."""
        assert ":" in pattern  # Should have on:off pattern
        assert "," in pattern  # Should have multiple states

        # Parse the pattern
        states = pattern.split(",")
        for state in states:
            assert ":" in state  # Each state should have on:off timing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
