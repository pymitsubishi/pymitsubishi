#!/usr/bin/env python3
"""
Mitsubishi Air Conditioner Protocol Parser

This module contains all the parsing logic for Mitsubishi AC protocol payloads,
including enums, state classes, and functions for decoding hex values.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Temperature constants
MIN_TEMPERATURE = 160  # 16.0°C in 0.1°C units
MAX_TEMPERATURE = 310  # 31.0°C in 0.1°C units


class PowerOnOff(Enum):
    OFF = "00"
    ON = "01"

    @classmethod
    def get_on_off_status(cls, segment: str) -> PowerOnOff:
        if segment in ["01", "02"]:
            return PowerOnOff.ON
        else:
            return PowerOnOff.OFF


class DriveMode(Enum):
    AUTO = 8  # Fixed: Changed from 0 to 8 based on actual device behavior
    HEATER = 1
    DEHUM = 2
    COOLER = 3
    FAN = 7
    # Extended modes (these appear to be special cases)
    AUTO_COOLER = 0x1B  # 27 in decimal
    AUTO_HEATER = 0x19  # 25 in decimal

    @classmethod
    def get_drive_mode(cls, mode_value: int) -> DriveMode:
        """Parse drive mode from integer value

        Args:
            mode_value: Integer mode value (typically masked with 0x07)
        """
        # Map the basic mode values (0-7)
        try:
            return DriveMode(mode_value)
        except ValueError:
            # Handle special extended modes
            if mode_value == 0x1B:
                return DriveMode.AUTO_COOLER
            elif mode_value == 0x19:
                return DriveMode.AUTO_HEATER
            # Default to FAN for unknown modes
            return DriveMode.FAN


class WindSpeed(Enum):
    AUTO = 0
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_4 = 5
    LEVEL_FULL = 6

    @classmethod
    def get_wind_speed(cls, segment: str) -> WindSpeed:
        """Parse wind speed from segment"""
        speed_map = {
            "00": WindSpeed.AUTO,
            "01": WindSpeed.LEVEL_1,
            "02": WindSpeed.LEVEL_2,
            "03": WindSpeed.LEVEL_3,
            "05": WindSpeed.LEVEL_4,
            "06": WindSpeed.LEVEL_FULL,
        }
        return speed_map.get(segment, WindSpeed.AUTO)


class VerticalWindDirection(Enum):
    AUTO = 0
    V1 = 1
    V2 = 2
    V3 = 3
    V4 = 4
    V5 = 5
    SWING = 7

    @classmethod
    def get_vertical_wind_direction(cls, segment: str) -> VerticalWindDirection:
        """Parse vertical wind direction from segment"""
        direction_map = {
            "00": VerticalWindDirection.AUTO,
            "01": VerticalWindDirection.V1,
            "02": VerticalWindDirection.V2,
            "03": VerticalWindDirection.V3,
            "04": VerticalWindDirection.V4,
            "05": VerticalWindDirection.V5,
            "07": VerticalWindDirection.SWING,
        }
        return direction_map.get(segment, VerticalWindDirection.AUTO)


class HorizontalWindDirection(Enum):
    AUTO = 0
    L = 1
    LS = 2
    C = 3
    RS = 4
    R = 5
    LC = 6
    CR = 7
    LR = 8
    LCR = 9
    LCR_S = 12

    @classmethod
    def get_horizontal_wind_direction(cls, segment: str) -> HorizontalWindDirection:
        """Parse horizontal wind direction from segment"""
        value = int(segment, 16) & 0x7F  # 127 & value
        try:
            return HorizontalWindDirection(value)
        except ValueError:
            return HorizontalWindDirection.AUTO


@dataclass
class GeneralStates:
    """Parsed general AC states from device response"""

    power_on_off: PowerOnOff = PowerOnOff.OFF
    drive_mode: DriveMode = DriveMode.AUTO
    coarse_temperature: int = 220  # 22.0°C in 0.1°C units
    fine_temperature: int | None = 220
    wind_speed: WindSpeed = WindSpeed.AUTO
    vertical_wind_direction_right: VerticalWindDirection = VerticalWindDirection.AUTO
    vertical_wind_direction_left: VerticalWindDirection = VerticalWindDirection.AUTO
    horizontal_wind_direction: HorizontalWindDirection = HorizontalWindDirection.AUTO
    dehum_setting: int = 0
    is_power_saving: bool = False
    wind_and_wind_break_direct: int = 0
    # Enhanced functionality based on SwiCago insights
    i_see_sensor: bool = False  # i-See sensor active flag
    mode_raw_value: int = 0  # Raw mode value before i-See processing
    wide_vane_adjustment: bool = False  # Wide vane adjustment flag (SwiCago wideVaneAdj)

    _unknown_6_7: bytes = b"\0\0"
    _unknown_13_14: bytes = b"\0"
    _unknown_21_: bytes = b""

    @property
    def temperature(self) -> int:
        if self.fine_temperature is not None:
            return self.fine_temperature
        return self.coarse_temperature

    @property
    def temp_mode(self) -> bool:
        return self.fine_temperature is not None

    @staticmethod
    def is_general_states_payload(data: bytes) -> bool:
        """Check if payload contains general states data"""
        if len(data) < 6:
            return False
        return data[1] in [0x62, 0x7B] and data[5] == 0x02

    @classmethod
    def parse_general_states(cls, data: bytes) -> GeneralStates:
        """Parse general states from hex payload with enhanced SwiCago-based parsing

        Enhanced with SwiCago insights:
        - Dual temperature parsing modes (segment vs direct)
        - Wide vane adjustment flag detection
        - i-See sensor detection from mode byte
        """
        logger.debug(f"Parsing general states payload: {data.hex()}")

        if len(data) < 21:
            raise ValueError("GeneralStates payload too short")

        if data[0] != 0xFC:
            raise ValueError(f"GeneralStates[0] == 0x{data[0]:02x} != 0xfc")

        calculated_fcc = calc_fcc(data[1:-1])
        if calculated_fcc != data[-1]:
            raise ValueError(f"Invalid checksum, expected 0x{calculated_fcc:02x}, received 0x{data[-1]:02x}")

        # Verify for parts that we think are static:
        if data[1] != 0x62 and data[1] != 0x7B:
            logger.warning(f"GeneralStates[1] == 0x{data[1]:02x} != (0x62 or 0x7b)")
        if data[2] != 0x01:
            logger.warning(f"GeneralStates[2] == 0x{data[2]:02x} != 0x01")
        if data[3] != 0x30:
            logger.warning(f"GeneralStates[3] == 0x{data[3]:02x} != 0x30")
        if data[4] != 0x10:
            logger.warning(f"GeneralStates[4] == 0x{data[4]:02x} != 0x10")
        if data[5] != 0x02:
            raise ValueError(f"Not GeneralStates message: data[5] == 0x{data[5]:02x} != 0x02")

        obj = cls.__new__(cls)
        obj._unknown_6_7 = data[6:8]
        obj.power_on_off = PowerOnOff.get_on_off_status(format(data[8], "02x"))

        # Enhanced mode parsing with i-See sensor detection
        mode_byte = data[9]  # data[4] in SwiCago
        obj.drive_mode, obj.i_see_active, obj.raw_mode = cls.parse_mode_with_i_see(mode_byte)

        obj.coarse_temperature = (31 - data[10]) * 10
        obj.wind_speed = WindSpeed.get_wind_speed(format(data[11], "02x"))  # data[6] in SwiCago
        obj.vertical_wind_direction_right = VerticalWindDirection.get_vertical_wind_direction(
            format(data[12], "02x")
        )  # data[7] in SwiCago

        obj._unknown_13_14 = data[13:15]

        # Enhanced wide vane parsing with adjustment flag (SwiCago)
        wide_vane_data = data[15]  # data[10] in SwiCago
        obj.horizontal_wind_direction = HorizontalWindDirection.get_horizontal_wind_direction(
            f"{wide_vane_data & 0x0F:02x}"
        )  # Lower 4 bits
        obj.wide_vane_adjustment = (wide_vane_data & 0xF0) == 0x80  # Upper 4 bits = 0x80

        if data[16] != 0x00:
            obj.fine_temperature = int((data[16] - 0x80) / 2) * 10
        else:
            obj.fine_temperature = None

        # Extra states
        obj.dehum_setting = data[17]
        obj.is_power_saving = data[18] > 0
        obj.wind_and_wind_break_direct = data[19]

        obj.vertical_wind_direction_left = VerticalWindDirection.get_vertical_wind_direction(format(data[20], "02x"))

        if len(data) > 21:
            obj._unknown_21_ = data[21:-1]  # don't include the FCC

        return obj

    @staticmethod
    def parse_mode_with_i_see(mode_byte: int) -> tuple[DriveMode, bool, int]:
        """Parse drive mode considering i-See sensor flag

        Based on niobos fork and SwiCago implementation:
        - Bits 0-2 (0x07): Drive mode
        - Bit 3 (0x08): i-See sensor flag OR part of mode value for AUTO
        - Bits 4-7 (0xF0): Unknown/reserved

        Args:
            mode_byte: Raw mode byte value from payload

        Returns:
            tuple of (drive_mode, i_see_active, raw_mode_value)
        """
        # Special case: AUTO mode uses value 8 (0x08)
        if mode_byte == 0x08:
            return DriveMode.AUTO, False, mode_byte

        # Extract drive mode from lower 3 bits for other modes
        actual_mode_value = mode_byte & 0x07

        # Check if i-See sensor flag is set (bit 3) for non-AUTO modes
        i_see_active = bool(mode_byte & 0x08)

        # Get the drive mode enum
        drive_mode = DriveMode.get_drive_mode(actual_mode_value)

        return drive_mode, i_see_active, mode_byte

    @staticmethod
    def analyze_undocumented_bits(payload: str) -> dict[str, Any]:
        """Analyze payload for undocumented bit patterns and flags

        This function helps identify unknown functionality by examining
        bit patterns that haven't been documented yet.
        """
        analysis: dict[str, Any] = {
            "payload_length": len(payload),
            "suspicious_patterns": [],
            "high_bits_set": [],
            "unknown_segments": {},
        }

        if len(payload) < 42:
            return analysis

        try:
            suspicious_patterns: list[dict[str, Any]] = []
            high_bits_set: list[dict[str, Any]] = []
            unknown_segments: dict[int, dict[str, Any]] = {}

            # Examine each byte for unusual patterns
            for i in range(0, min(len(payload), 42), 2):
                if i + 2 <= len(payload):
                    byte_hex = payload[i : i + 2]
                    byte_val = int(byte_hex, 16)
                    position = i // 2

                    # Look for high bits that might indicate additional flags
                    if byte_val & 0x80:  # High bit set
                        high_bits_set.append(
                            {"position": position, "hex": byte_hex, "value": byte_val, "binary": f"{byte_val:08b}"}
                        )

                    # Look for patterns that don't match known mappings
                    if position == 9 and byte_val not in [
                        0x00,
                        0x01,
                        0x02,
                        0x03,
                        0x07,
                        0x08,
                        0x09,
                        0x0A,
                        0x0B,
                        0x0C,
                        0x19,
                        0x1B,
                    ]:  # Mode byte position
                        suspicious_patterns.append(
                            {
                                "type": "unknown_mode",
                                "position": position,
                                "hex": byte_hex,
                                "value": byte_val,
                                "possible_i_see": byte_val > 0x08,
                            }
                        )

                    # Check for non-zero values in typically unused positions
                    unused_positions = [12, 17, 19]  # Add more as we discover them
                    if position in unused_positions and byte_val != 0:
                        unknown_segments[position] = {
                            "hex": byte_hex,
                            "value": byte_val,
                            "binary": f"{byte_val:08b}",
                        }

            analysis["suspicious_patterns"] = suspicious_patterns
            analysis["high_bits_set"] = high_bits_set
            analysis["unknown_segments"] = unknown_segments

        except (ValueError, IndexError) as e:
            analysis["parse_error"] = str(e)
            logger.warning(f"Error analyzing undocumented bits in payload {payload[:20]}...: {e}")

        return analysis

    def generate_general_command(self, controls: dict[str, bool]) -> str:
        """Generate general control command hex string"""
        segments = {
            "segment0": "01",
            "segment1": "00",
            "segment2": "00",
            "segment3": "00",
            "segment4": "00",
            "segment5": "00",
            "segment6": "00",
            "segment7": "00",
            "segment13": "00",
            "segment14": "00",
            "segment15": "00",
        }

        # Calculate segment 1 value (control flags)
        segment1_value = 0
        if controls.get("power_on_off"):
            segment1_value |= 0x01
        if controls.get("drive_mode"):
            segment1_value |= 0x02
        if controls.get("temperature"):
            segment1_value |= 0x04
        if controls.get("wind_speed"):
            segment1_value |= 0x08
        if controls.get("up_down_wind_direct"):
            segment1_value |= 0x10

        # Calculate segment 2 value
        segment2_value = 0
        if controls.get("left_right_wind_direct"):
            segment2_value |= 0x01
        if controls.get("outside_control", True):  # Default true
            segment2_value |= 0x02

        segments["segment1"] = f"{segment1_value:02x}"
        segments["segment2"] = f"{segment2_value:02x}"
        segments["segment3"] = self.power_on_off.value
        segments["segment4"] = f"{self.drive_mode.value:02x}"  # Convert int to hex string
        segments["segment6"] = f"{self.wind_speed.value:02x}"
        segments["segment7"] = f"{self.vertical_wind_direction_right.value:02x}"
        segments["segment13"] = f"{self.horizontal_wind_direction.value:02x}"
        segments["segment15"] = "41"  # checkInside: 41 true, 42 false

        segments["segment5"] = convert_temperature(self.temperature)
        segments["segment14"] = convert_temperature_to_segment(self.temperature)

        # Build payload
        payload = "41013010"
        for i in range(16):
            segment_key = f"segment{i}"
            payload += segments.get(segment_key, "00")

        # Calculate and append FCC
        fcc = format(calc_fcc(bytes.fromhex(payload)), "02x")
        return "fc" + payload + fcc

    def generate_extend08_command(self, controls: dict[str, bool]) -> str:
        """Generate extend08 command for buzzer, dehum, power saving, etc."""
        segment_x_value = 0
        if controls.get("dehum"):
            segment_x_value |= 0x04
        if controls.get("power_saving"):
            segment_x_value |= 0x08
        if controls.get("buzzer"):
            segment_x_value |= 0x10
        if controls.get("wind_and_wind_break"):
            segment_x_value |= 0x20

        segment_x = f"{segment_x_value:02x}"
        segment_y = f"{self.dehum_setting:02x}" if controls.get("dehum") else "00"
        segment_z = "0A" if self.is_power_saving else "00"
        segment_a = f"{self.wind_and_wind_break_direct:02x}" if controls.get("wind_and_wind_break") else "00"
        buzzer_segment = "01" if controls.get("buzzer") else "00"

        payload = (
            "4101301008" + segment_x + "0000" + segment_y + segment_z + segment_a + buzzer_segment + "0000000000000000"
        )
        fcc = format(calc_fcc(bytes.fromhex(payload)), "02x")
        return "fc" + payload + fcc


@dataclass
class SensorStates:
    """Parsed sensor states from device response"""

    outside_temperature: int | None = None
    room_temperature: int = 220  # 22.0°C in 0.1°C units
    thermal_sensor: bool = False
    wind_speed_pr557: int = 0

    _unknown_6_9: bytes = b"\0\0\0\0"
    _unknown_11: bytes = b"\0"
    _unknown_13_18: bytes = b"\0\0\0\0\0\0"
    _unknown_21_: bytes = b""

    @staticmethod
    def is_sensor_states_payload(data: bytes) -> bool:
        """Check if payload contains sensor states data"""
        if len(data) < 6:
            return False
        return data[1] in [0x62, 0x7B] and data[5] == 0x03

    @classmethod
    def parse_sensor_states(cls, data: bytes) -> SensorStates:
        """Parse sensor states from hex payload"""
        logger.debug(f"Parsing sensor states payload: {data.hex()}")
        if len(data) < 21:
            raise ValueError("SensorStates payload too short")

        if data[0] != 0xFC:
            raise ValueError(f"SensorStates[0] == 0x{data[0]:02x} != 0xfc")

        calculated_fcc = calc_fcc(data[1:-1])
        if calculated_fcc != data[-1]:
            raise ValueError(f"Invalid checksum, expected 0x{calculated_fcc:02x}, received 0x{data[-1]:02x}")

        # Verify for parts that we think are static:
        if data[1] != 0x62 and data[1] != 0x7B:
            logger.warning(f"SensorStates[1] == 0x{data[1]:02x} != (0x62 or 0x7b)")
        if data[2] != 0x01:
            logger.warning(f"SensorStates[2] == 0x{data[2]:02x} != 0x01")
        if data[3] != 0x30:
            logger.warning(f"SensorStates[3] == 0x{data[3]:02x} != 0x30")
        if data[4] != 0x10:
            logger.warning(f"SensorStates[4] == 0x{data[4]:02x} != 0x10")
        if data[5] != 0x03:
            raise ValueError(f"Not SensorStates message: data[5] == 0x{data[5]:02x} != 0x03")

        obj = cls.__new__(cls)
        obj._unknown_6_9 = data[6:10]

        outside_temp_raw = data[10]
        obj._unknown_11 = data[11:12]

        obj.outside_temperature = None if outside_temp_raw < 16 else get_normalized_temperature(outside_temp_raw)
        obj.room_temperature = get_normalized_temperature(data[12])

        obj._unknown_13_18 = data[13:19]

        obj.thermal_sensor = (data[19] & 0x01) != 0
        obj.wind_speed_pr557 = 1 if (data[20] & 0x01) == 1 else 0

        if len(data) > 21:
            obj._unknown_21_ = data[21:-1]

        return obj


@dataclass
class EnergyStates:
    """Parsed energy and operational states from device response"""

    compressor_frequency: int | None = None  # Raw compressor frequency value
    operating: bool = False  # True if heat pump is actively operating
    estimated_power_watts: float | None = None  # Estimated power consumption in Watts

    _unknown_6_8: bytes = b"\0\0\0"
    _unknown_11_: bytes = b""

    @staticmethod
    def is_energy_states_payload(data: bytes) -> bool:
        """Check if payload contains energy/status data (SwiCago group 06)"""
        if len(data) < 6:
            return False
        return data[1] in [0x62, 0x7B] and data[5] == 0x06

    @classmethod
    def parse_energy_states(cls, data: bytes, general_states: GeneralStates | None = None) -> EnergyStates:
        """Parse energy/status states from hex payload (SwiCago group 06)

        Based on SwiCago implementation:
        - data[3] = compressor frequency
        - data[4] = operating status (boolean)

        Args:
            data: payload as bytes
            general_states: Optional general states for power estimation context
        """
        logger.debug(f"Parsing energy states payload: {data.hex()}")
        if len(data) < 12:  # Need at least enough bytes for data[4]
            raise ValueError("EnergyStates payload too short")

        if data[0] != 0xFC:
            raise ValueError(f"EnergyStates[0] == 0x{data[0]:02x} != 0xfc")

        calculated_fcc = calc_fcc(data[1:-1])
        if calculated_fcc != data[-1]:
            raise ValueError(f"Invalid checksum, expected 0x{calculated_fcc:02x}, received 0x{data[-1]:02x}")

        # Verify for parts that we think are static:
        if data[1] != 0x62 and data[1] != 0x7B:
            logger.warning(f"EnergyStates[1] == 0x{data[1]:02x} != (0x62 or 0x7b)")
        if data[2] != 0x01:
            logger.warning(f"EnergyStates[2] == 0x{data[2]:02x} != 0x01")
        if data[3] != 0x30:
            logger.warning(f"EnergyStates[3] == 0x{data[3]:02x} != 0x30")
        if data[4] != 0x10:
            logger.warning(f"EnergyStates[4] == 0x{data[4]:02x} != 0x10")
        if data[5] != 0x06:
            raise ValueError(f"Not EnergyStates message: data[5] == 0x{data[5]:02x} != 0x06")

        obj = cls.__new__(cls)
        obj._unknown_6_8 = data[6:9]

        # Extract compressor frequency from data[3] (position 18-19 in hex string)
        obj.compressor_frequency = data[9]

        # Extract operating status from data[4] (position 20-21 in hex string)
        obj.operating = data[10] > 0

        if len(data) > 11:
            obj._unknown_11_ = data[11:-1]

        # Estimate power consumption if we have context
        obj.estimated_power = None
        if general_states:
            obj.estimated_power = cls.estimate_power_consumption(
                obj.compressor_frequency, general_states.drive_mode, general_states.wind_speed
            )

        return obj

    @staticmethod
    def estimate_power_consumption(compressor_frequency: int, mode: DriveMode, fan_speed: WindSpeed) -> float:
        """Estimate power consumption based on compressor frequency and operational parameters

        This is a rough estimation based on empirical data from heat pump literature.
        Actual consumption varies significantly based on outdoor conditions, efficiency rating, etc.

        Args:
            compressor_frequency: Raw compressor frequency value (0-255 typical)
            mode: Operating mode (affects base consumption)
            fan_speed: Fan speed (affects additional consumption)

        Returns:
            Estimated power consumption in Watts
        """
        if compressor_frequency == 0:
            # Unit is not actively operating - only standby power
            return 10.0  # Typical standby consumption

        # Base power estimation from compressor frequency
        # This is a rough linear approximation - real curves are more complex
        frequency_factor = compressor_frequency / 255.0  # Normalize to 0-1

        # Mode-based base consumption (typical values for residential units)
        mode_base_watts = {
            DriveMode.COOLER: 1200,  # Cooling tends to use more power
            DriveMode.HEATER: 1000,  # Heating can be more efficient
            DriveMode.AUTO: 1100,  # Average
            DriveMode.DEHUM: 800,  # Dehumidification uses less
            DriveMode.FAN: 50,  # Fan only
            DriveMode.AUTO_COOLER: 1200,
            DriveMode.AUTO_HEATER: 1000,
        }

        base_power = mode_base_watts.get(mode, 1000)

        # Compressor power scales roughly with frequency
        compressor_power = base_power * frequency_factor

        # Fan power addition
        fan_power_map = {
            WindSpeed.AUTO: 50,  # Variable
            WindSpeed.LEVEL_1: 30,  # Low speed
            WindSpeed.LEVEL_2: 60,  # Medium-low
            WindSpeed.LEVEL_3: 90,  # Medium-high
            WindSpeed.LEVEL_FULL: 120,  # High speed
        }

        fan_power = fan_power_map.get(fan_speed, 50)

        # Total estimated power
        total_power = compressor_power + fan_power + 20  # +20W for control electronics

        return round(total_power, 1)


@dataclass
class ErrorStates:
    """Parsed error states from device response"""

    error_code: int = 0x8000

    _unknown_6_8: bytes = b"\0\0\0"
    _unknown_11_: bytes = b""

    @property
    def is_abnormal_state(self) -> bool:
        return self.error_code != 0x8000

    @staticmethod
    def is_error_states_payload(data: bytes) -> bool:
        """Check if payload contains error states data"""
        if len(data) < 6:
            return False
        return data[1] in [0x62, 0x7B] and data[5] == 0x04

    @classmethod
    def parse_error_states(cls, data: bytes) -> ErrorStates:
        """Parse error states from hex payload"""
        logger.debug(f"Parsing error states payload: {data.hex()}")
        if len(data) < 11:
            raise ValueError("ErrorStates payload too short")

        if data[0] != 0xFC:
            raise ValueError(f"ErrorStates[0] == 0x{data[0]:02x} != 0xfc")

        calculated_fcc = calc_fcc(data[1:-1])
        if calculated_fcc != data[-1]:
            raise ValueError(f"Invalid checksum, expected 0x{calculated_fcc:02x}, received 0x{data[-1]:02x}")

        # Verify for parts that we think are static:
        if data[1] != 0x62 and data[1] != 0x7B:
            logger.warning(f"ErrorStates[1] == 0x{data[1]:02x} != (0x62 or 0x7b)")
        if data[2] != 0x01:
            logger.warning(f"ErrorStates[2] == 0x{data[2]:02x} != 0x01")
        if data[3] != 0x30:
            logger.warning(f"ErrorStates[3] == 0x{data[3]:02x} != 0x30")
        if data[4] != 0x10:
            logger.warning(f"ErrorStates[4] == 0x{data[4]:02x} != 0x10")
        if data[5] != 0x04:
            raise ValueError(f"Not ErrorStates message: data[5] == 0x{data[5]:02x} != 0x04")

        obj = cls.__new__(cls)
        obj._unknown_6_8 = data[6:9]

        obj.error_code = int.from_bytes(data[9:11], "big")

        if len(data) > 11:
            obj._unknown_11_ = data[11:-1]

        return obj


@dataclass
class ParsedDeviceState:
    """Complete parsed device state combining all state types"""

    general: GeneralStates | None = None
    sensors: SensorStates | None = None
    errors: ErrorStates | None = None
    energy: EnergyStates | None = None  # New energy/operational data
    mac: str = ""
    serial: str = ""
    rssi: str = ""
    app_version: str = ""

    @classmethod
    def parse_code_values(cls, code_values: list[str]) -> ParsedDeviceState:
        """Parse a list of code values and return combined device state with energy information"""
        parsed_state = ParsedDeviceState()
        logger.debug(f"Parsing {len(code_values)} code values")

        for hex_value in code_values:
            value = bytes.fromhex(hex_value)

            # Parse different payload types
            if GeneralStates.is_general_states_payload(value):
                parsed_state.general = GeneralStates.parse_general_states(value)
            elif SensorStates.is_sensor_states_payload(value):
                parsed_state.sensors = SensorStates.parse_sensor_states(value)
            elif ErrorStates.is_error_states_payload(value):
                parsed_state.errors = ErrorStates.parse_error_states(value)
            elif EnergyStates.is_energy_states_payload(value):
                # Parse energy states with context from general states if available
                parsed_state.energy = EnergyStates.parse_energy_states(value, parsed_state.general)
            else:
                logger.debug(f"Ignoring unknown code value: {value.hex()}")

        return parsed_state

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result: dict[str, Any] = {
            "device_info": {
                "mac": self.mac,
                "serial": self.serial,
                "rssi": self.rssi,
                "app_version": self.app_version,
            }
        }

        if self.general:
            general_dict: dict[str, Any] = {
                "power": "ON" if self.general.power_on_off == PowerOnOff.ON else "OFF",
                "mode": self.general.drive_mode.name,
                "target_temperature_celsius": self.general.temperature / 10.0,
                "fan_speed": self.general.wind_speed.name,
                "vertical_wind_direction_right": self.general.vertical_wind_direction_right.name,
                "vertical_wind_direction_left": self.general.vertical_wind_direction_left.name,
                "horizontal_wind_direction": self.general.horizontal_wind_direction.name,
                "dehumidification_setting": self.general.dehum_setting,
                "power_saving_mode": self.general.is_power_saving,
                "wind_and_wind_break_direct": self.general.wind_and_wind_break_direct,
                # Enhanced functionality
                "i_see_sensor_active": self.general.i_see_sensor,
                "mode_raw_value": self.general.mode_raw_value,
            }
            result["general_states"] = general_dict

        if self.sensors:
            sensor_dict: dict[str, Any] = {
                "room_temperature_celsius": self.sensors.room_temperature / 10.0,
                "outside_temperature_celsius": self.sensors.outside_temperature / 10.0
                if self.sensors.outside_temperature
                else None,
                "thermal_sensor_active": self.sensors.thermal_sensor,
                "wind_speed_pr557": self.sensors.wind_speed_pr557,
            }
            result["sensor_states"] = sensor_dict

        if self.errors:
            error_dict: dict[str, Any] = {
                "abnormal_state": self.errors.is_abnormal_state,
                "error_code": self.errors.error_code,
            }
            result["error_states"] = error_dict

        if self.energy:
            energy_dict: dict[str, Any] = {
                "compressor_frequency": self.energy.compressor_frequency,
                "operating": self.energy.operating,
                "estimated_power_watts": self.energy.estimated_power_watts,
            }
            result["energy_states"] = energy_dict

        return result


def calc_fcc(payload: bytes) -> int:
    """Calculate FCC checksum for Mitsubishi protocol payload"""
    return (0x100 - (sum(payload[0:20]) % 0x100)) % 0x100  # TODO: do we actually need to limit this to 20 bytes?


def convert_temperature(temperature: int) -> str:
    """Convert temperature in 0.1°C units to segment format"""
    t = max(MIN_TEMPERATURE, min(MAX_TEMPERATURE, temperature))
    e = 31 - (t // 10)
    last_digit = "0" if str(t)[-1] == "0" else "1"
    return last_digit + format(e, "x")


def convert_temperature_to_segment(temperature: int) -> str:
    """Convert temperature to segment 14 format"""
    value = 0x80 + (temperature // 5)
    return format(value, "02x")


def get_normalized_temperature(hex_value: int) -> int:
    """Normalize temperature from hex value to 0.1°C units"""
    adjusted = 5 * (hex_value - 0x80)
    if adjusted >= 400:
        return 400
    elif adjusted <= 0:
        return 0
    else:
        return adjusted
