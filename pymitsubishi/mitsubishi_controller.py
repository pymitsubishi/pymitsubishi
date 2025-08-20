#!/usr/bin/env python3
"""
Mitsubishi Air Conditioner Business Logic Layer

This module is responsible for managing control operations and state
for Mitsubishi MAC-577IF-2E devices.
"""

import logging
from typing import Any
import xml.etree.ElementTree as ET

from .mitsubishi_api import MitsubishiAPI
from .mitsubishi_parser import (
    DriveMode,
    GeneralStates,
    HorizontalWindDirection,
    ParsedDeviceState,
    PowerOnOff,
    VerticalWindDirection,
    WindSpeed,
)

logger = logging.getLogger(__name__)


class MitsubishiController:
    """Business logic controller for Mitsubishi AC devices"""

    def __init__(self, api: MitsubishiAPI):
        self.api = api
        self.profile_code: list[bytes] = []
        self.state = ParsedDeviceState()

    @classmethod
    def create(cls, device_host_port: str, encryption_key: str | bytes = "unregistered"):
        """Create a MitsubishiController with the specified port and encryption key"""
        api = MitsubishiAPI(device_host_port=device_host_port, encryption_key=encryption_key)
        return cls(api)

    def fetch_status(self) -> ParsedDeviceState:
        """Fetch current device status and optionally detect capabilities"""
        response = self.api.send_status_request()  # may raise
        self._parse_status_response(response)
        return self.state

    def _parse_status_response(self, response: str):
        """Parse the device status response and update state"""
        # Parse the XML response
        root = ET.fromstring(response)  # may raise

        # Extract code values for parsing
        code_values_elems = root.findall(".//CODE/VALUE")
        code_values = [elem.text for elem in code_values_elems if elem.text]

        # Use the parser module to get structured state
        parsed_state = ParsedDeviceState.parse_code_values(code_values)

        if parsed_state:
            self.state = parsed_state

        # Extract and set device identity
        mac_elem = root.find(".//MAC")
        if mac_elem is not None and mac_elem.text is not None:
            self.state.mac = mac_elem.text

        serial_elem = root.find(".//SERIAL")
        if serial_elem is not None and serial_elem.text is not None:
            self.state.serial = serial_elem.text

        profile_elems = root.findall(".//PROFILECODE/DATA/VALUE") or root.findall(".//PROFILECODE/VALUE")
        self.profile_code = []
        for elem in profile_elems:
            if elem.text:
                self.profile_code.append(bytes.fromhex(elem.text))

    def _ensure_state_available(self):
        if not self.state.general:
            self.fetch_status()

    def _create_updated_state(self, **overrides) -> GeneralStates:
        """Create updated state with specified field overrides"""
        if not self.state.general:
            # Create default state if none exists
            return GeneralStates(**overrides)

        return GeneralStates(
            power_on_off=overrides.get("power_on_off", self.state.general.power_on_off),
            coarse_temperature=int(overrides.get("temperature", self.state.general.temperature)),
            fine_temperature=overrides.get("temperature", self.state.general.temperature),
            drive_mode=overrides.get("drive_mode", self.state.general.drive_mode),
            wind_speed=overrides.get("wind_speed", self.state.general.wind_speed),
            vertical_wind_direction=overrides.get(
                "vertical_wind_direction", self.state.general.vertical_wind_direction
            ),
            horizontal_wind_direction=overrides.get(
                "horizontal_wind_direction", self.state.general.horizontal_wind_direction
            ),
            dehum_setting=overrides.get("dehum_setting", self.state.general.dehum_setting),
            is_power_saving=overrides.get("is_power_saving", self.state.general.is_power_saving),
            wind_and_wind_break_direct=overrides.get(
                "wind_and_wind_break_direct", self.state.general.wind_and_wind_break_direct
            ),
        )

    def set_power(self, power_on: bool) -> ParsedDeviceState:
        """Set power on/off"""
        self._ensure_state_available()

        new_power = PowerOnOff.ON if power_on else PowerOnOff.OFF
        updated_state = self._create_updated_state(power_on_off=new_power)
        new_state = self._send_general_control_command(updated_state, {"power_on_off": True})
        self.state = new_state
        return new_state

    def set_temperature(self, temperature_celsius: float) -> ParsedDeviceState:
        """Set target temperature in Celsius"""
        self._ensure_state_available()

        updated_state = self._create_updated_state(temperature=temperature_celsius)
        new_state = self._send_general_control_command(updated_state, {"temperature": True})
        self.state = new_state
        return new_state

    def set_mode(self, mode: DriveMode) -> ParsedDeviceState:
        """Set operating mode"""
        self._ensure_state_available()

        updated_state = self._create_updated_state(drive_mode=mode)
        new_state = self._send_general_control_command(updated_state, {"drive_mode": True})
        self.state = new_state
        return new_state

    def set_fan_speed(self, speed: WindSpeed) -> ParsedDeviceState:
        """Set fan speed"""
        self._ensure_state_available()

        updated_state = self._create_updated_state(wind_speed=speed)
        new_state = self._send_general_control_command(updated_state, {"wind_speed": True})
        self.state = new_state
        return new_state

    def set_vertical_vane(self, direction: VerticalWindDirection) -> ParsedDeviceState:
        """Set vertical vane direction (right or left side)"""
        self._ensure_state_available()

        updated_state = self._create_updated_state(vertical_wind_direction=direction)
        new_state = self._send_general_control_command(updated_state, {"up_down_wind_direct": True})
        self.state = new_state
        return new_state

    def set_horizontal_vane(self, direction: HorizontalWindDirection) -> ParsedDeviceState:
        """Set horizontal vane direction"""
        self._ensure_state_available()

        updated_state = self._create_updated_state(horizontal_wind_direction=direction)
        new_state = self._send_general_control_command(updated_state, {"left_right_wind_direct": True})
        self.state = new_state
        return new_state

    def set_dehumidifier(self, setting: int) -> ParsedDeviceState:
        """Set dehumidifier level (0-100)"""
        self._ensure_state_available()

        updated_state = self._create_updated_state(dehum_setting=setting)
        new_state = self._send_extend08_command(updated_state, {"dehum": True})
        self.state = new_state
        return new_state

    def set_power_saving(self, enabled: bool) -> ParsedDeviceState:
        """Enable or disable power saving mode"""
        self._ensure_state_available()

        updated_state = self._create_updated_state(is_power_saving=enabled)
        new_state = self._send_extend08_command(updated_state, {"power_saving": True})
        self.state = new_state
        return new_state

    def send_buzzer_command(self, enabled: bool = True) -> ParsedDeviceState:
        """Send buzzer control command"""
        self._ensure_state_available()
        new_state = self._send_extend08_command(self.state.general, {"buzzer": enabled})
        self.state = new_state
        return new_state

    def _send_general_control_command(self, state: GeneralStates, controls: dict[str, bool]) -> ParsedDeviceState:
        """Send a general control command to the device"""
        # Generate the hex command
        hex_command = state.generate_general_command(controls).hex()

        logger.debug(f"🔧 Sending command: {hex_command}")

        response = self.api.send_hex_command(hex_command)
        self._parse_status_response(response)
        return self.state

    def _send_extend08_command(self, state: GeneralStates, controls: dict[str, bool]) -> ParsedDeviceState:
        """Send an extend08 command for advanced features"""
        # Generate the hex command
        hex_command = state.generate_extend08_command(controls).hex()

        logger.debug(f"🔧 Sending extend08 command: {hex_command}")

        response = self.api.send_hex_command(hex_command)
        self._parse_status_response(response)
        return self.state

    def enable_echonet(self) -> None:
        """Send ECHONET enable command"""
        self.api.send_echonet_enable()

    def get_unit_info(self) -> dict[str, Any]:
        """Get detailed unit information from the admin interface"""
        unit_info = self.api.get_unit_info()
        logger.debug(
            f"✅ Unit info retrieved: {len(unit_info.get('adaptor_info', {}))} adaptor fields, {len(unit_info.get('unit_info', {}))} unit fields"
        )
        return unit_info

    def get_status_summary(self) -> dict[str, Any]:
        """Get human-readable status summary"""
        summary: dict[str, Any] = {
            "mac": self.state.mac,
            "serial": self.state.serial,
        }

        if self.state.general:
            general_dict: dict[str, Any] = {
                "power": self.state.general.power_on_off.name,
                "mode": self.state.general.drive_mode.name,
                "target_temp": self.state.general.temperature,
                "fan_speed": self.state.general.wind_speed.name,
                "dehumidifier_setting": self.state.general.dehum_setting,
                "power_saving_mode": self.state.general.is_power_saving,
                "vertical_vane": self.state.general.vertical_wind_direction.name,
                "horizontal_vane": self.state.general.horizontal_wind_direction.name,
            }
            summary.update(general_dict)

        if self.state.sensors:
            sensor_dict: dict[str, Any] = {
                "room_temp": self.state.sensors.room_temperature,
                "outside_temp": self.state.sensors.outside_temperature,
                "runtime_minutes": self.state.sensors.runtime_minutes,
                "inside_temperature_1_coarse": self.state.sensors.inside_temperature_1_coarse,
                "inside_temperature_1_fine": self.state.sensors.inside_temperature_1_fine,
                "inside_temperature_2": self.state.sensors.inside_temperature_2,
            }
            summary.update(sensor_dict)

        if self.state.energy:
            summary.update({
                "operating": self.state.energy.operating,
                "power_watt": self.state.energy.power_watt,
                "energy_kWh": self.state.energy.energy_hecto_watt_hour / 10.,
            })

        if self.state.errors:
            error_dict: dict[str, Any] = {
                "error_code": self.state.errors.error_code,
                "error_state": self.state.errors.is_abnormal_state,
            }
            summary.update(error_dict)

        if self.state._unknown5:
            summary.update({
            })

        if self.state._unknown9:
            summary.update({
                "power_mode": self.state._unknown9.power_mode,
            })

        return summary
