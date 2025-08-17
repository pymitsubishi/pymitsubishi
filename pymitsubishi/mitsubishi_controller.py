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

    def fetch_status(self) -> bool:
        """Fetch current device status and optionally detect capabilities"""
        response = self.api.send_status_request()
        if response:
            self._parse_status_response(response)
            return True
        return False

    def _parse_status_response(self, response: str):
        """Parse the device status response and update state"""
        try:
            # Parse the XML response
            root = ET.fromstring(response)

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

        except ET.ParseError as e:
            logger.error(f"Error parsing status response: {e}")

    def _check_state_available(self) -> bool:
        """Check if device state is available"""
        if not self.state.general:
            logger.warning("No device state available. Fetch status first.")
            return False
        return True

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

    def set_power(self, power_on: bool) -> bool:
        """Set power on/off"""
        if not self._check_state_available():
            return False

        new_power = PowerOnOff.ON if power_on else PowerOnOff.OFF
        updated_state = self._create_updated_state(power_on_off=new_power)
        return self._send_general_control_command(updated_state, {"power_on_off": True})

    def set_temperature(self, temperature_celsius: float) -> bool:
        """Set target temperature in Celsius"""
        if not self._check_state_available():
            return False

        # Convert to 0.1°C units and validate range
        temp_units = int(temperature_celsius * 10)
        if temp_units < 160 or temp_units > 320:  # 16°C to 32°C
            logger.warning(f"Temperature {temperature_celsius}°C is out of range (16-32°C)")
            return False

        updated_state = self._create_updated_state(temperature=temp_units)
        return self._send_general_control_command(updated_state, {"temperature": True})

    def set_mode(self, mode: DriveMode) -> bool:
        """Set operating mode"""
        if not self._check_state_available():
            return False

        updated_state = self._create_updated_state(drive_mode=mode)
        return self._send_general_control_command(updated_state, {"drive_mode": True})

    def set_fan_speed(self, speed: WindSpeed) -> bool:
        """Set fan speed"""
        if not self._check_state_available():
            return False

        updated_state = self._create_updated_state(wind_speed=speed)
        return self._send_general_control_command(updated_state, {"wind_speed": True})

    def set_vertical_vane(self, direction: VerticalWindDirection, side: str = "right") -> bool:
        """Set vertical vane direction (right or left side)"""
        if not self._check_state_available():
            return False

        if side.lower() not in ["right", "left"]:
            logger.warning("Side must be 'right' or 'left'")
            return False

        if side.lower() == "right":
            updated_state = self._create_updated_state(vertical_wind_direction_right=direction)
        else:
            updated_state = self._create_updated_state(vertical_wind_direction_left=direction)

        return self._send_general_control_command(updated_state, {"up_down_wind_direct": True})

    def set_horizontal_vane(self, direction: HorizontalWindDirection) -> bool:
        """Set horizontal vane direction"""
        if not self._check_state_available():
            return False

        updated_state = self._create_updated_state(horizontal_wind_direction=direction)
        return self._send_general_control_command(updated_state, {"left_right_wind_direct": True})

    def set_dehumidifier(self, setting: int) -> bool:
        """Set dehumidifier level (0-100)"""
        if not self._check_state_available():
            return False

        if setting < 0 or setting > 100:
            logger.warning("Dehumidifier setting must be between 0-100")
            return False

        updated_state = self._create_updated_state(dehum_setting=setting)
        return self._send_extend08_command(updated_state, {"dehum": True})

    def set_power_saving(self, enabled: bool) -> bool:
        """Enable or disable power saving mode"""
        if not self._check_state_available():
            return False

        updated_state = self._create_updated_state(is_power_saving=enabled)
        return self._send_extend08_command(updated_state, {"power_saving": True})

    def send_buzzer_command(self, enabled: bool = True) -> bool:
        """Send buzzer control command"""
        if not self._check_state_available():
            return False

        if not self.state.general:
            return False

        return self._send_extend08_command(self.state.general, {"buzzer": enabled})

    def _send_general_control_command(self, state: GeneralStates, controls: dict[str, bool]) -> bool:
        """Send a general control command to the device"""
        # Generate the hex command
        hex_command = state.generate_general_command(controls)

        logger.debug(f"🔧 Sending command: {hex_command}")

        response = self.api.send_hex_command(hex_command)

        if response:
            logger.debug("✅ Command sent successfully")
            # Update our local state to reflect the change
            self.state.general = state
            return True
        else:
            logger.debug("❌ Command failed")
            return False

    def _send_extend08_command(self, state: GeneralStates, controls: dict[str, bool]) -> bool:
        """Send an extend08 command for advanced features"""
        # Generate the hex command
        hex_command = state.generate_extend08_command(controls)

        logger.debug(f"🔧 Sending extend08 command: {hex_command}")

        response = self.api.send_hex_command(hex_command)

        if response:
            logger.debug("✅ Extend08 command sent successfully")
            # Update our local state to reflect the change
            self.state.general = state
            return True
        else:
            logger.debug("❌ Extend08 command failed")
            return False

    def enable_echonet(self) -> bool:
        """Send ECHONET enable command"""
        response = self.api.send_echonet_enable()
        return response is not None

    def get_unit_info(self) -> dict[str, Any] | None:
        """Get detailed unit information from the admin interface"""
        unit_info = self.api.get_unit_info()

        if unit_info:
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
