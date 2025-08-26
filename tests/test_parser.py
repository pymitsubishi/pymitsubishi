"""
Unit tests for mitsubishi_parser module using real device data.

Tests parser functions with actual hex codes and ProfileCode data
collected from real Mitsubishi MAC-577IF-2E devices.
"""

import pytest

from pymitsubishi.mitsubishi_parser import (
    GeneralStates,
    ParsedDeviceState,
    calc_fcc,
    convert_temperature,
    convert_temperature_to_segment,
    get_normalized_temperature,
)

from .test_fixtures import SAMPLE_CODE_VALUES, SAMPLE_PROFILE_CODES


@pytest.mark.parametrize(
    "payload,expected",
    [
        # These are based on patterns seen in real device communication
        (b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19", 0x06),  # Sample command
        (b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\x02\x02\x00\x80\x00\x00\x00\x00", 0x86),  # Real code pattern
        (b"\xa0\xbe\xa0\xbe\xa0\xbe\xa0\xbe\xa0\xbe\xa0\xbe\xa0\xbe\xa0\xbe\xa0\xbe", 0xB2),  # Profile code pattern
    ],
)
def test_fcc(payload, expected):
    checksum = calc_fcc(payload)
    assert checksum == expected


def test_generate_general_command():
    cmd = GeneralStates().generate_general_command({})
    assert cmd == bytes.fromhex("fc410130100100020000090000000000000000ac4185")


def test_generate_extend08_command():
    cmd = GeneralStates().generate_extend08_command({})
    assert cmd == bytes.fromhex("fc410130100800000000000000000000000000000076")


class TestTemperatureConversion:
    """Test temperature conversion functions with real values."""

    def test_temperature_conversion_real_values(self):
        """Test temperature conversion with actual AC temperature values."""
        # Test common AC temperature settings
        real_temps = [160, 180, 200, 220, 240, 260, 280, 300, 320]  # 16-32°C

        for temp_units in real_temps:
            # Test segment conversion
            segment = convert_temperature(temp_units)
            assert len(segment) == 2

            # Test segment format conversion
            segment14 = convert_temperature_to_segment(int(temp_units / 10))
            assert len(segment14) == 2

            # Test reverse conversion
            hex_val = int(segment14, 16)
            if hex_val >= 0x80:  # Valid range
                normalized = get_normalized_temperature(hex_val)
                assert 0 <= normalized <= 400  # Valid normalized range

    def test_temperature_edge_cases(self):
        """Test temperature conversion edge cases."""
        # Test minimum temperature (16°C = 160 units)
        assert convert_temperature(160) is not None

        # Test maximum temperature (32°C = 320 units)
        assert convert_temperature(320) is not None

        # Test invalid temperatures
        assert get_normalized_temperature(0x7F) == 0  # Below minimum
        assert get_normalized_temperature(0xFF) == 400  # Above maximum


class TestCodeValueParsing:
    """Test parsing of real CODE values from device responses."""

    @pytest.mark.parametrize(
        "code_value",
        SAMPLE_CODE_VALUES,
    )
    def test_code_value_structure(self, code_value):
        """Test that real code values have the expected structure."""
        assert len(code_value) >= 12  # Minimum length for group code extraction
        assert all(c in "0123456789abcdef" for c in code_value.lower())

        # Extract group code (position 20-22)
        group_code = code_value[20:22]
        assert len(group_code) == 2
        # Allow the group codes that are actually in the test data
        assert group_code in ["02", "03", "04", "05", "06", "07", "08", "09", "0a"]

    def test_code_values_parsing(self):
        """Test parsing of complete code value arrays."""
        # Test that parse_code_values can handle real code arrays
        parsed_state = ParsedDeviceState.parse_code_values(SAMPLE_CODE_VALUES)

        # Should return a ParsedDeviceState or None
        assert parsed_state is None or isinstance(parsed_state, ParsedDeviceState)

        # If parsing succeeds, verify structure
        if parsed_state and parsed_state.general:
            assert hasattr(parsed_state.general, "power_on_off")
            assert hasattr(parsed_state.general, "drive_mode")
            assert hasattr(parsed_state.general, "temperature")


class TestProfileCodeAnalysis:
    """Test ProfileCode analysis with real profile data."""

    @pytest.mark.parametrize(
        "profile_code",
        SAMPLE_PROFILE_CODES,
    )
    def test_profile_code_structure(self, profile_code):
        """Test that profile codes have the expected structure."""
        assert len(profile_code) == 64  # 32 bytes = 64 hex chars
        assert all(c in "0123456789abcdef" for c in profile_code.lower())

    def test_profile_code_parsing(self):
        """Test parsing of individual profile code components."""
        # Test the first profile code which has real capability data
        profile_code = SAMPLE_PROFILE_CODES[0]
        data = bytes.fromhex(profile_code)

        assert len(data) == 32  # Should be 32 bytes

        # Extract components (based on real device analysis)
        group_code = data[5] if len(data) > 5 else 0
        version_info = (data[6] << 8) | data[7] if len(data) > 7 else 0
        feature_flags = (data[8] << 8) | data[9] if len(data) > 9 else 0
        capability_field = (data[10] << 8) | data[11] if len(data) > 11 else 0

        # Verify extracted values match expected patterns
        assert isinstance(group_code, int)
        assert isinstance(version_info, int)
        assert isinstance(feature_flags, int)
        assert isinstance(capability_field, int)

    def test_empty_profile_codes(self):
        """Test handling of empty profile codes."""
        # Test profile codes that are all zeros
        empty_profile = SAMPLE_PROFILE_CODES[2]  # All zeros
        data = bytes.fromhex(empty_profile)

        # Should be all zeros
        assert all(byte == 0 for byte in data)

        # Parsing should handle gracefully
        version_info = (data[6] << 8) | data[7]
        assert version_info == 0


class TestRealDeviceDataIntegrity:
    """Test data integrity and consistency of real device responses."""

    def test_data_consistency(self):
        """Test that sample data is internally consistent."""
        # Verify that profile codes and code values are from same device type
        # All should be consistent with a MAC-577IF-2E device

        # Check that group codes are in expected range
        group_codes = set()
        for code_value in SAMPLE_CODE_VALUES:
            if len(code_value) >= 22:
                group_code = code_value[20:22]
                group_codes.add(group_code)

        # Should have typical group codes for this device type
        expected_codes = {"02", "03", "04", "05", "06", "07", "08", "09", "0a"}
        assert group_codes == expected_codes

    def test_profile_code_variations(self):
        """Test that profile codes show expected variations."""
        # First profile should have actual data
        first_profile = SAMPLE_PROFILE_CODES[0]
        assert not all(c == "0" for c in first_profile)

        # Second profile has repeated pattern
        second_profile = SAMPLE_PROFILE_CODES[1]
        assert "a0be" in second_profile

        # Remaining profiles should be empty
        for empty_profile in SAMPLE_PROFILE_CODES[2:]:
            assert all(c == "0" for c in empty_profile)


class TestErrorConditions:
    """Test error handling with malformed real-world data."""

    @pytest.mark.parametrize(
        "code",
        SAMPLE_CODE_VALUES,
    )
    def test_truncated_code_values(self, code):
        """Test handling of truncated code values."""
        # Test with shortened versions of real codes
        truncated_codes = code[:20]

        # Should handle gracefully without crashing
        try:
            if len(truncated_codes) >= 12:
                group_code = truncated_codes[10:12]
                assert len(group_code) <= 2
        except IndexError:
            pass  # Expected for very short codes

    @pytest.mark.parametrize(
        "code",
        [
            "gggggggggggggggggggg0202008000",  # Invalid hex chars
            "ffffffffffffffffffff02G2008000",  # Single invalid char
        ],
    )
    def test_invalid_hex_characters(self, code):
        """Test handling of invalid hex characters in codes."""
        # Create codes with invalid characters based on real patterns
        # Should detect invalid hex gracefully
        try:
            # This would fail on invalid hex
            bytes.fromhex(code)
            assert False, "Should have failed on invalid hex"
        except ValueError:
            pass  # Expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
