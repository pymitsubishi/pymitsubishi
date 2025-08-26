#!/usr/bin/env python3
"""
Mitsubishi Air Conditioner Protocol Parser

This module contains all the parsing logic for Mitsubishi AC protocol payloads,
including enums, state classes, and functions for decoding hex values.
"""

from __future__ import annotations

import dataclasses
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PowerOnOff(Enum):
    OFF = 0
    ON = 1


class DriveMode(Enum):
    AUTO = 0
    HEATER = 1
    DEHUM = 2
    COOLER = 3
    FAN = 7


class WindSpeed(Enum):
    AUTO = 0
    S1 = 1
    S2 = 2
    S3 = 3
    # value 4 does not seem to exist?
    S4 = 5
    FULL = 6


class VerticalWindDirection(Enum):
    AUTO = 0
    V1 = 1
    V2 = 2
    V3 = 3
    V4 = 4
    V5 = 5
    SWING = 7


class HorizontalWindDirection(Enum):
    AUTO = 0
    FAR_LEFT = 1
    LEFT = 2
    CENTER = 3
    RIGHT = 4
    FAR_RIGHT = 5
    LEFT_CENTER = 6
    CENTER_RIGHT = 7
    LEFT_RIGHT = 8
    LEFT_CENTER_RIGHT = 9  # I don't see a difference in vane position vs 8
    SWING = 12


class AutoMode(Enum):
    OFF = 0
    SWITCHING = 1
    AUTO_HEATING = 2
    AUTO_COOLING = 3


def log_unexpected_value(code_value: str, position: int, value: int | bytes):
    svalue = "[" + value.hex() + "]" if isinstance(value, bytes) else str(value)
    logger.warning(f"Unexpected value found in {code_value} at position {position}: {svalue}")
    logger.warning("Please report this, so this can be added to the decoding.")


def try_enum_or_log(code_value: str, position: int, value: int, enum_class: type):
    try:
        return enum_class(value)
    except ValueError:
        log_unexpected_value(code_value, position, value)
        return value


@dataclasses.dataclass
class GeneralStates:
    """Parsed general AC states from device response"""

    power_on_off: PowerOnOff = PowerOnOff.OFF
    drive_mode: DriveMode = DriveMode.AUTO
    coarse_temperature: int = 22
    fine_temperature: float | None = 22.0
    wind_speed: WindSpeed = WindSpeed.AUTO
    vertical_wind_direction: VerticalWindDirection = VerticalWindDirection.AUTO
    horizontal_wind_direction: HorizontalWindDirection = HorizontalWindDirection.AUTO
    dehum_setting: int = 0
    is_power_saving: bool = False
    wind_and_wind_break_direct: int = 0
    i_see_sensor: bool = True  # i-See sensor active flag
    wide_vane_adjustment: bool = False

    @property
    def temperature(self) -> float:
        if self.fine_temperature is not None:
            return self.fine_temperature
        return self.coarse_temperature

    @temperature.setter
    def temperature(self, value: float):
        self.fine_temperature = value
        self.coarse_temperature = int(value)

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
            log_unexpected_value(cls.__name__, 1, data[1:2])
        if data[2:5] != b"\x01\x30\x10":
            log_unexpected_value(cls.__name__, 2, data[2:5])
        if data[5] != 0x02:
            raise ValueError(f"Not GeneralStates message: data[5] == 0x{data[5]:02x} != 0x02")

        obj = cls.__new__(cls)

        if data[6:8] != b"\0\0":
            log_unexpected_value(cls.__name__, 6, data[6:8])

        obj.power_on_off = try_enum_or_log(cls.__name__, 8, data[8], PowerOnOff)

        obj.drive_mode = try_enum_or_log(cls.__name__, 9, data[9] & 0x07, DriveMode)
        obj.i_see_sensor = bool(data[9] & 0x08)
        if data[9] & 0xF0 != 0x00:
            log_unexpected_value(cls.__name__, 9, data[9:10])

        obj.coarse_temperature = 31 - data[10]
        obj.wind_speed = try_enum_or_log(cls.__name__, 11, data[11], WindSpeed)
        obj.vertical_wind_direction = try_enum_or_log(cls.__name__, 12, data[12], VerticalWindDirection)

        if data[13:15] != b"\0\0":
            log_unexpected_value(cls.__name__, 13, data[13:15])

        # Enhanced wide vane parsing with adjustment flag (SwiCago)
        wide_vane_data = data[15]  # data[10] in SwiCago
        obj.horizontal_wind_direction = try_enum_or_log(
            cls.__name__, 15, wide_vane_data & 0x0F, HorizontalWindDirection
        )  # Lower 4 bits
        obj.wide_vane_adjustment = (wide_vane_data & 0xF0) == 0x80  # Upper 4 bits = 0x80

        if data[16] != 0x00:
            obj.fine_temperature = (data[16] - 0x80) / 2
        else:
            obj.fine_temperature = None

        # Extra states
        obj.dehum_setting = data[17]
        obj.is_power_saving = data[18] > 0
        obj.wind_and_wind_break_direct = data[19]

        if data[20:-1] != b"\0":  # don't include the FCC
            log_unexpected_value(cls.__name__, 20, data[20:-1])

        return obj

    def generate_general_command(self, controls: dict[str, bool]) -> bytes:
        cmd = bytearray(b"\x41\x01\x30\x10\x01")
        cmd += b"\0" * 15

        # Even though this is a bitfield, my heatpump only reads in 1 change per update
        # TODO: enforce this
        cmd[5] = (
            0x01
            if controls.get("power_on_off")
            else 0 + 0x02
            if controls.get("drive_mode")
            else 0 + 0x04
            if controls.get("temperature")
            else 0 + 0x08
            if controls.get("wind_speed")
            else 0 + 0x10
            if controls.get("up_down_wind_direct")
            else 0
            # 0x20 ?
            # 0x40 ?
            # 0x80 ?
        )
        cmd[6] = (
            0x01 if controls.get("left_right_wind_direct") else 0 + 0x02 if controls.get("outside_control", True) else 0
            # other flags?
        )
        cmd[7] = self.power_on_off.value
        cmd[8] = self.drive_mode.value if isinstance(self.drive_mode, DriveMode) else self.drive_mode
        # TODO: figure out how to combine mode with iSee; Mode changes don't seem to work when >0x08
        cmd[9] = 31 - int(self.temperature)
        cmd[10] = self.wind_speed.value
        cmd[11] = self.vertical_wind_direction.value
        cmd[12] = 0
        cmd[13] = 0
        cmd[14] = 0
        cmd[15] = 0
        cmd[16] = 0
        cmd[17] = self.horizontal_wind_direction.value
        cmd[18] = 0x80 + int(self.fine_temperature * 2) if self.fine_temperature is not None else 0x00
        cmd[19] = 0x41

        # Calculate and append FCC
        fcc = calc_fcc(cmd)
        return b"\xfc" + cmd + bytes([fcc])

    def generate_extend08_command(self, controls: dict[str, bool]) -> bytes:
        cmd = bytearray(b"\x41\x01\x30\x10\x08")
        cmd += b"\0" * 15
        cmd[5] = (
            # 0x01?
            # 0x02?
            0x04
            if controls.get("dehum")
            else 0 + 0x08
            if controls.get("power_saving")
            else 0 + 0x10
            if controls.get("buzzer")
            else 0 + 0x20
            if controls.get("wind_and_wind_break")
            else 0
            # 0x40?
            # 0x80?
        )
        # cmd[6:8] = 0
        cmd[8] = self.dehum_setting if controls.get("dehum") else 0
        cmd[9] = 0x0A if self.is_power_saving else 0x00
        cmd[10] = self.wind_and_wind_break_direct if controls.get("wind_and_wind_break") else 0x00
        cmd[11] = 0x01 if controls.get("buzzer") else 0x00
        # cmd[12:20] = 0

        fcc = calc_fcc(cmd)
        return b"\xfc" + cmd + bytes([fcc])


@dataclasses.dataclass
class SensorStates:
    """Parsed sensor states from device response"""

    inside_temperature_1_coarse: int = 24
    outside_temperature: float = 21.0
    inside_temperature_1_fine: float = 24.5
    inside_temperature_2: float = 24.0
    runtime_minutes: int = 0

    @property
    def room_temperature(self) -> float:
        return self.inside_temperature_2

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
            log_unexpected_value(cls.__name__, 1, data[1:2])
        if data[2:5] != b"\x01\x30\x10":
            log_unexpected_value(cls.__name__, 2, data[2:5])
        if data[5] != 0x03:
            raise ValueError(f"Not SensorStates message: data[5] == 0x{data[5]:02x} != 0x03")

        obj = cls.__new__(cls)

        if data[6:8] != b"\0\0":
            log_unexpected_value(cls.__name__, 6, data[6:8])

        obj.inside_temperature_1_coarse = 10 + data[8]

        if data[9:10] != b"\0":
            log_unexpected_value(cls.__name__, 9, data[9:10])

        obj.outside_temperature = (data[10] - 0x80) * 0.5
        obj.inside_temperature_1_fine = (data[11] - 0x80) * 0.5
        obj.inside_temperature_2 = (data[12] - 0x80) * 0.5
        # What's the difference between data[8], data[11] and data[12]?
        # data[8] and data[11] seem to be the exact same value (with different conversion & thus truncation)
        # but they seem to move exactly together
        # data[12] moves differently and seems to lead vs data[8]/data[11]

        if data[13] != 0xFE:
            # also seen: 0x00
            log_unexpected_value(cls.__name__, 13, data[13])

        if data[14] != 0x42:
            log_unexpected_value(cls.__name__, 14, data[14])

        obj.runtime_minutes = int.from_bytes(data[15:19], "big", signed=False)
        # runtime is at least 24 bit long data[16:19]
        # Since 24 bits is a bit odd, I'm assuming it's 32bit and join in an additional leading 0x00 at data[15]

        if data[19:-1] != b"\0\0":
            log_unexpected_value(cls.__name__, 19, data[19:-1])

        return obj


@dataclasses.dataclass
class EnergyStates:
    """Parsed energy and operational states from device response"""

    operating: bool = False
    power_watt: int = 0
    energy_hecto_watt_hour: int = 0

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
            log_unexpected_value(cls.__name__, 1, data[1:2])
        if data[2:5] != b"\x01\x30\x10":
            log_unexpected_value(cls.__name__, 2, data[2:5])
        if data[5] != 0x06:
            raise ValueError(f"Not EnergyStates message: data[5] == 0x{data[5]:02x} != 0x06")

        obj = cls.__new__(cls)

        if data[6:9] != b"\0\0\0":
            log_unexpected_value(cls.__name__, 6, data[6:9])

        obj.operating = bool(data[9])
        if data[9] not in [0, 1]:
            log_unexpected_value(cls.__name__, 9, data[9:10])

        # The outdoor unit is reported as part of the first indoor unit (port A)
        # Doesn't match exactly with my power meter, but it's close.
        obj.power_watt = int.from_bytes(data[10:12], "big", signed=False)
        obj.energy_hecto_watt_hour = int.from_bytes(data[12:14], "big", signed=False)  # in 100Wh units

        if data[14:-1] != b"\0\0\x42\0\0\0\0":
            log_unexpected_value(cls.__name__, 12, data[12:-1])

        return obj


@dataclasses.dataclass
class ErrorStates:
    """Parsed error states from device response"""

    error_code: int = 0x8000

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
            log_unexpected_value(cls.__name__, 1, data[1:2])
        if data[2:5] != b"\x01\x30\x10":
            log_unexpected_value(cls.__name__, 2, data[2:5])
        if data[5] != 0x04:
            raise ValueError(f"Not ErrorStates message: data[5] == 0x{data[5]:02x} != 0x04")

        obj = cls.__new__(cls)

        if data[6:9] != b"\0\0\0":
            log_unexpected_value(cls.__name__, 6, data[6:9])

        obj.error_code = int.from_bytes(data[9:11], "big")

        if data[11:-1] != b"\0\0\0\0\0\0\0\0\0\0":
            log_unexpected_value(cls.__name__, 11, data[11:-1])

        return obj


@dataclasses.dataclass
class Unknown5States:
    @staticmethod
    def is_unknown5_states_payload(data: bytes) -> bool:
        """Check if payload contains error states data"""
        if len(data) < 6:
            return False
        return data[1] in [0x62, 0x7B] and data[5] == 0x05

    @classmethod
    def parse_unknown5_states(cls, data: bytes) -> Unknown5States:
        """Parse error states from hex payload"""
        logger.debug(f"Parsing {cls.__name__} payload: {data.hex()}")
        if len(data) < 6:
            raise ValueError(f"{cls.__name__} payload too short")

        if data[0] != 0xFC:
            raise ValueError(f"{cls.__name__}[0] == 0x{data[0]:02x} != 0xfc")

        calculated_fcc = calc_fcc(data[1:-1])
        if calculated_fcc != data[-1]:
            raise ValueError(f"Invalid checksum, expected 0x{calculated_fcc:02x}, received 0x{data[-1]:02x}")

        # Verify for parts that we think are static:
        if data[1] != 0x62 and data[1] != 0x7B:
            log_unexpected_value(cls.__name__, 1, data[1:2])
        if data[2:5] != b"\x01\x30\x10":
            log_unexpected_value(cls.__name__, 2, data[2:5])
        if data[5] != 0x05:
            raise ValueError(f"Not {cls.__name__} message: data[5] == 0x{data[5]:02x} != 0x05")

        obj = cls.__new__(cls)

        if data[6:-1] != b"\0\0\0\0\0\0\0\0\0\0\0\0\0\0\0":
            log_unexpected_value(cls.__name__, 6, data[6:-1])

        return obj


@dataclasses.dataclass
class AutoStates:
    power_mode: int = 0
    auto_mode: AutoMode = AutoMode.OFF

    @staticmethod
    def is_auto_states_payload(data: bytes) -> bool:
        """Check if payload contains error states data"""
        if len(data) < 6:
            return False
        return data[1] in [0x62, 0x7B] and data[5] == 0x09

    @classmethod
    def parse_unknown9_states(cls, data: bytes) -> AutoStates:
        """Parse error states from hex payload"""
        logger.debug(f"Parsing {cls.__name__} payload: {data.hex()}")
        if len(data) < 6:
            raise ValueError(f"{cls.__name__} payload too short")

        if data[0] != 0xFC:
            raise ValueError(f"{cls.__name__}[0] == 0x{data[0]:02x} != 0xfc")

        calculated_fcc = calc_fcc(data[1:-1])
        if calculated_fcc != data[-1]:
            raise ValueError(f"Invalid checksum, expected 0x{calculated_fcc:02x}, received 0x{data[-1]:02x}")

        # Verify for parts that we think are static:
        if data[1] != 0x62 and data[1] != 0x7B:
            log_unexpected_value(cls.__name__, 1, data[1:2])
        if data[2:5] != b"\x01\x30\x10":
            log_unexpected_value(cls.__name__, 2, data[2:5])
        if data[5] != 0x09:
            raise ValueError(f"Not {cls.__name__} message: data[5] == 0x{data[5]:02x} != 0x09")

        obj = cls.__new__(cls)

        if data[6:8] != b"\0\0":
            log_unexpected_value(cls.__name__, 6, data[6:9])

        if data[8] != 0:
            # observed 0x04 during auto-mode heating startup
            # "switching pump direction" or something?
            log_unexpected_value(cls.__name__, 8, data[8])

        obj.power_mode = data[9]
        # This seems demand-related.
        # It's 0 when off, and goes up to 6 (?)
        # On but not pumping is 1 (operating in Energy turns to 0 in this case)
        # Higher seems to indicate higher demand

        obj.auto_mode = try_enum_or_log(cls.__name__, 10, data[10], AutoMode)

        if data[11:-1] != b"\0\0\0\0\0\0\0\0\0\0":
            log_unexpected_value(cls.__name__, 10, data[10:-1])

        return obj


@dataclasses.dataclass
class ParsedDeviceState:
    """Complete parsed device state combining all state types"""

    general: GeneralStates | None = None
    sensors: SensorStates | None = None
    errors: ErrorStates | None = None
    energy: EnergyStates | None = None  # New energy/operational data
    auto_state: AutoStates | None = None
    mac: str = ""
    serial: str = ""
    rssi: str = ""
    app_version: str = ""

    _unknown5: Unknown5States | None = None

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
            elif Unknown5States.is_unknown5_states_payload(value):
                parsed_state._unknown5 = Unknown5States.parse_unknown5_states(value)
            elif AutoStates.is_auto_states_payload(value):
                parsed_state.auto_state = AutoStates.parse_unknown9_states(value)
            else:
                logger.debug(f"Ignoring unknown code value: {value.hex()}")

        return parsed_state


def calc_fcc(payload: bytes) -> int:
    """Calculate FCC checksum for Mitsubishi protocol payload"""
    return (0x100 - (sum(payload[0:20]) % 0x100)) % 0x100  # TODO: do we actually need to limit this to 20 bytes?


def convert_temperature(temperature: int) -> str:
    """Convert temperature in 0.1°C units to segment format"""
    t = max(16, min(31, temperature))
    e = 31 - int(t)
    last_digit = "0" if str(t)[-1] == "0" else "1"
    return last_digit + format(e, "x")


def convert_temperature_to_segment(temperature: int) -> str:
    """Convert temperature to segment 14 format"""
    value = 0x80 + (temperature // 0.5)
    return format(int(value), "02x")


def get_normalized_temperature(hex_value: int) -> int:
    """Normalize temperature from hex value to 0.1°C units"""
    adjusted = 5 * (hex_value - 0x80)
    if adjusted >= 400:
        return 400
    elif adjusted <= 0:
        return 0
    else:
        return adjusted
