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
    Controls,
    Controls08,
    DriveMode,
    GeneralStates,
    HorizontalWindDirection,
    ParsedDeviceState,
    PowerOnOff,
    RemoteLock,
    VerticalWindDirection,
    WindSpeed,
)

logger = logging.getLogger(__name__)


class MitsubishiChangeSet:
    desired_state: GeneralStates
    changes: Controls
    changes08: Controls08

    def __init__(self, current_state: GeneralStates):
        self.desired_state = current_state
        self.changes = Controls.NoControl
        self.changes08 = Controls08.NoControl

    @property
    def empty(self) -> bool:
        return self.changes == Controls.NoControl and self.changes08 == Controls08.NoControl

    def set_power(self, power: PowerOnOff):
        self.desired_state.power_on_off = power
        self.changes |= Controls.PowerOnOff

    def set_mode(self, drive_mode: DriveMode):
        if drive_mode == DriveMode.AUTO:
            drive_mode = 8
        else:
            drive_mode = drive_mode.value
        self.desired_state.drive_mode = drive_mode
        self.changes |= Controls.DriveMode

    def set_temperature(self, temperature: float):
        self.desired_state.temperature = temperature
        self.changes |= Controls.Temperature

    def set_dehumidifier(self, humidity: int):
        self.desired_state.dehum_setting = humidity
        self.changes08 |= Controls08.Dehum

    def set_fan_speed(self, fan_speed: WindSpeed):
        self.desired_state.wind_speed = fan_speed
        self.changes |= Controls.WindSpeed

    def set_vertical_vane(self, v_vane: VerticalWindDirection):
        self.desired_state.vertical_wind_direction = v_vane
        self.changes |= Controls.UpDownWindDirection

    def set_horizontal_vane(self, h_vane: HorizontalWindDirection):
        self.desired_state.horizontal_wind_direction = h_vane
        self.changes |= Controls.LeftRightWindDirect

    def set_power_saving(self, power_saving: bool):
        self.desired_state.is_power_saving = power_saving
        self.changes08 |= Controls08.PowerSaving


class MitsubishiController:
    """Business logic controller for Mitsubishi AC devices"""

    wait_time_after_command = 5  # Number of seconds after a command that the result is visible in the returned status
    # Found experimentally by increasing until I reliably saw my updates

    def __init__(self, api: MitsubishiAPI):
        self.api = api
        self.profile_code: list[bytes] = []
        self.state: ParsedDeviceState | None = None
        self.unit_info: dict[str, dict[str, Any]] = {}

    @classmethod
    def create(cls, device_host_port: str, encryption_key: str | bytes = "unregistered"):
        """Create a MitsubishiController with the specified port and encryption key"""
        api = MitsubishiAPI(device_host_port=device_host_port, encryption_key=encryption_key)
        return cls(api)

    def fetch_status(self) -> ParsedDeviceState:
        """Fetch current device status and optionally detect capabilities"""
        response = self.api.send_status_request()  # may raise
        return self._parse_status_response(response)

    def _parse_status_response(self, response: str) -> ParsedDeviceState:
        """Parse the device status response and update state"""
        # Parse the XML response
        root = ET.fromstring(response)  # may raise

        # Extract code values for parsing
        code_values_elems = root.findall(".//CODE/VALUE")
        code_values = [elem.text for elem in code_values_elems if elem.text]

        # Use the parser module to get structured state
        self.state = ParsedDeviceState.parse_code_values(code_values)

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

        return self.state

    def _ensure_state_available(self):
        if self.state is None or self.state.general is None:
            self.fetch_status()

    def changeset(self):
        self._ensure_state_available()
        return MitsubishiChangeSet(self.state.general)

    def apply_changeset(self, cs: MitsubishiChangeSet) -> ParsedDeviceState | None:
        new_state = None

        if cs.changes != Controls.NoControl:
            new_state = self._send_general_control_command(cs.desired_state, cs.changes)

        if cs.changes08 != Controls08.NoControl:
            new_state = self._send_extend08_command(cs.desired_state, cs.changes08)

        return new_state

    def _create_updated_state(self, **overrides) -> GeneralStates:
        """Create updated state with specified field overrides"""
        if not self.state or not self.state.general:
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
            remote_lock=overrides.get("remote_lock", self.state.general.remote_lock),
        )

    def set_power(self, power_on: bool) -> ParsedDeviceState:
        cs = self.changeset()
        cs.set_power(PowerOnOff.ON if power_on else PowerOnOff.OFF)
        return self.apply_changeset(cs)

    def set_temperature(self, temperature_celsius: float) -> ParsedDeviceState:
        cs = self.changeset()
        cs.set_temperature(temperature_celsius)
        return self.apply_changeset(cs)

    def set_mode(self, mode: DriveMode) -> ParsedDeviceState:
        cs = self.changeset()
        cs.set_mode(mode)
        return self.apply_changeset(cs)

    def set_fan_speed(self, speed: WindSpeed) -> ParsedDeviceState:
        cs = self.changeset()
        cs.set_fan_speed(speed)
        return self.apply_changeset(cs)

    def set_vertical_vane(self, direction: VerticalWindDirection) -> ParsedDeviceState:
        cs = self.changeset()
        cs.set_vertical_vane(direction)
        return self.apply_changeset(cs)

    def set_horizontal_vane(self, direction: HorizontalWindDirection) -> ParsedDeviceState:
        cs = self.changeset()
        cs.set_horizontal_vane(direction)
        return self.apply_changeset(cs)

    def set_dehumidifier(self, setting: int) -> ParsedDeviceState:
        cs = self.changeset()
        cs.set_dehumidifier(setting)
        return self.apply_changeset(cs)

    def set_power_saving(self, enabled: bool) -> ParsedDeviceState:
        cs = self.changeset()
        cs.set_power_saving(enabled)
        return self.apply_changeset(cs)

    def send_buzzer_command(self, enabled: bool = True) -> ParsedDeviceState:
        """Send buzzer control command"""
        self._ensure_state_available()
        if self.state is not None and self.state.general is not None:
            general_state = self.state.general
        else:
            general_state = GeneralStates()
        new_state = self._send_extend08_command(general_state, Controls08.Buzzer)
        self.state = new_state
        return new_state

    def set_remote_lock(self, lock: RemoteLock) -> ParsedDeviceState:
        self._ensure_state_available()

        updated_state = self._create_updated_state(remote_lock=lock)
        new_state = self._send_general_control_command(updated_state, Controls.RemoteLock)
        self.state = new_state
        return new_state

    def _send_general_control_command(self, state: GeneralStates, controls: Controls) -> ParsedDeviceState:
        """Send a general control command to the device"""
        # Generate the hex command
        hex_command = state.generate_general_command(controls).hex()

        logger.debug(f"🔧 Sending command: {hex_command}")

        response = self.api.send_hex_command(hex_command)
        return self._parse_status_response(response)

    def _send_extend08_command(self, state: GeneralStates, controls: Controls08) -> ParsedDeviceState:
        """Send an extend08 command for advanced features"""
        # Generate the hex command
        hex_command = state.generate_extend08_command(controls).hex()

        logger.debug(f"🔧 Sending extend08 command: {hex_command}")

        response = self.api.send_hex_command(hex_command)
        return self._parse_status_response(response)

    def enable_echonet(self) -> None:
        """Send ECHONET enable command"""
        self.api.send_echonet_enable()

    def get_unit_info(self) -> dict[str, Any]:
        """Get detailed unit information from the admin interface"""
        self.unit_info = self.api.get_unit_info()
        logger.debug(
            f"✅ Unit info retrieved: "
            f"{len(self.unit_info.get('Adaptor Information', {}))} adaptor fields, "
            f"{len(self.unit_info.get('Unit Info', {}))} unit fields"
        )
        return self.unit_info
