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
from .mitsubishi_atw import (
    EcodanStatus,
    ZoneMode,
    generate_forced_dhw_command,
    generate_set_dhw_setpoint_command,
    generate_set_flow_setpoint_command,
    generate_set_power_command,
    generate_set_zone_mode_command,
    is_atw_payload,
    parse_atw_code_values,
)
from .mitsubishi_parser import (
    Controls,
    Controls08,
    DriveMode,
    GeneralStates,
    HorizontalWindDirection,
    ParsedDeviceState,
    PowerOnOff,
    RemoteLock,
    SetRemoteTemperature,
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
        mode_value = 8 if drive_mode == DriveMode.AUTO else drive_mode.value
        self.desired_state.drive_mode = mode_value
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
        # Air-to-water (Ecodan) support. Populated automatically by
        # _parse_status_response when the device responds with ATW payloads.
        self.is_atw: bool = False
        self.atw_status: EcodanStatus | None = None
        self.has_zone2: bool = False

    @classmethod
    def create(cls, device_host_port: str, encryption_key: str | bytes = "unregistered"):
        """Create a MitsubishiController with the specified port and encryption key"""
        api = MitsubishiAPI(device_host_port=device_host_port, encryption_key=encryption_key)
        return cls(api)

    def fetch_status(self, connect: bool | None = None) -> ParsedDeviceState:
        """Fetch current device status and optionally detect capabilities.

        connect=None (the default) leaves the MELCloud connection setting
        untouched. Pass True or False only to change it.
        """
        response = self.api.send_status_request(connect=connect)  # may raise
        return self._parse_status_response(response)

    def set_cloud_connect(self, enabled: bool) -> ParsedDeviceState:
        """Enable or disable the adapter's connection to the MELCloud servers.

        Local control over /smart keeps working while the cloud connection is
        disabled.
        """
        return self.fetch_status(connect=enabled)

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

        # The adapter echoes its current cloud and ECHONET Lite settings.
        for tag, attr in (("CONNECT", "cloud_connect"), ("ECHONET", "echonet_enabled")):
            elem = root.find(f".//{tag}")
            if elem is not None and elem.text is not None:
                setattr(self.state, attr, elem.text.strip().upper() == "ON")

        profile_elems = root.findall(".//PROFILECODE/DATA/VALUE") or root.findall(".//PROFILECODE/VALUE")
        self.profile_code = []
        profile_hex: list[str] = []
        for elem in profile_elems:
            if elem.text:
                profile_hex.append(elem.text)
                self.profile_code.append(bytes.fromhex(elem.text))

        # Detect and parse an air-to-water (Ecodan) unit. ATW status packets use
        # a different preamble (0x02 0x7a) so they are ignored by the ATA parser
        # above and recognised here. This is purely additive: air-to-air devices
        # never pass is_atw_payload, so their behaviour is unchanged.
        self._parse_atw_status(code_values, profile_hex, root)

        return self.state

    def _parse_atw_status(self, code_values: list[str], profile_hex: list[str], root: ET.Element) -> None:
        """Detect ATW (Ecodan) payloads and populate is_atw / atw_status / has_zone2."""
        is_atw = False
        for hexv in code_values:
            try:
                if is_atw_payload(bytes.fromhex(hexv)):
                    is_atw = True
                    break
            except ValueError:
                continue

        self.is_atw = is_atw
        if not is_atw:
            self.atw_status = None
            self.has_zone2 = False
            return

        # The profile code carries FTC version / refrigerant type (0xC9 group).
        # Pick the ATW profile packet so parse_atw_code_values can decode it.
        atw_profile: str | None = None
        for hexv in profile_hex:
            try:
                data = bytes.fromhex(hexv)
            except ValueError:
                continue
            if len(data) >= 6 and data[2:4] == b"\x02\x7a" and data[5] == 0xC9:
                atw_profile = hexv
                break

        status = parse_atw_code_values(code_values, atw_profile)

        # Identity from the /smart XML wrapper.
        mac_elem = root.find(".//MAC")
        if mac_elem is not None and mac_elem.text is not None:
            status.mac = mac_elem.text
        serial_elem = root.find(".//SERIAL")
        if serial_elem is not None and serial_elem.text is not None:
            status.serial = serial_elem.text
        rssi_elem = root.find(".//RSSI")
        if rssi_elem is not None and rssi_elem.text is not None:
            status.rssi = rssi_elem.text

        self.atw_status = status
        self.has_zone2 = (
            status.zone2_room_temperature is not None
            or status.zone2_flow_setpoint is not None
            or status.zone2_mode is not None
        )

    def _ensure_state_available(self):
        if self.state is None or self.state.general is None:
            self.fetch_status()

    def changeset(self) -> MitsubishiChangeSet:
        self._ensure_state_available()
        if self.state is None or self.state.general is None:
            raise RuntimeError("Failed to fetch device state")
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

    def set_temperature(self, temperature_celsius: float) -> ParsedDeviceState | None:
        cs = self.changeset()
        cs.set_temperature(temperature_celsius)
        return self.apply_changeset(cs)

    def set_current_temperature(self, temperature_celsius: float | None) -> None:
        cmd = SetRemoteTemperature()
        if temperature_celsius is None:
            cmd.mode = SetRemoteTemperature.Mode.UseInternal
        else:
            cmd.mode = SetRemoteTemperature.Mode.RemoteTemp
            cmd.remote_temperature = temperature_celsius
        command = cmd.generate_command()
        response = self.api.send_command(command)
        self.state = self._parse_status_response(response)

    def set_mode(self, mode: DriveMode) -> ParsedDeviceState | None:
        cs = self.changeset()
        cs.set_mode(mode)
        return self.apply_changeset(cs)

    def set_fan_speed(self, speed: WindSpeed) -> ParsedDeviceState | None:
        cs = self.changeset()
        cs.set_fan_speed(speed)
        return self.apply_changeset(cs)

    def set_vertical_vane(self, direction: VerticalWindDirection) -> ParsedDeviceState | None:
        cs = self.changeset()
        cs.set_vertical_vane(direction)
        return self.apply_changeset(cs)

    def set_horizontal_vane(self, direction: HorizontalWindDirection) -> ParsedDeviceState | None:
        cs = self.changeset()
        cs.set_horizontal_vane(direction)
        return self.apply_changeset(cs)

    def set_dehumidifier(self, setting: int) -> ParsedDeviceState | None:
        cs = self.changeset()
        cs.set_dehumidifier(setting)
        return self.apply_changeset(cs)

    def set_power_saving(self, enabled: bool) -> ParsedDeviceState | None:
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

    # --- Air-to-water (Ecodan) control --------------------------------------
    # Each builds a packet via mitsubishi_atw and sends it via the shared
    # transport. They return True on success and deliberately do NOT re-fetch
    # status; the caller should call fetch_status() after a settle delay.

    def _require_atw_status(self) -> EcodanStatus:
        if self.atw_status is None:
            self.fetch_status()
        if not self.is_atw or self.atw_status is None:
            raise RuntimeError("Not an air-to-water device or status unavailable")
        return self.atw_status

    def _send_atw_command(self, command: bytes) -> bool:
        """Send a prebuilt ATW packet; return True if the device accepted it."""
        try:
            self.api.send_command(command)
            return True
        except Exception:
            logger.exception("Failed to send ATW command")
            return False

    def set_zone_flow_setpoint(
        self,
        zone1_setpoint: float,
        zone2_setpoint: float,
        zone_mode: ZoneMode | None = None,
    ) -> bool:
        """Set the Z1/Z2 flow setpoints, preserving DHW/power/eco state.

        If zone_mode is None the unit's current Zone-1 mode is reused.
        """
        status = self._require_atw_status()
        mode: ZoneMode | int
        if zone_mode is not None:
            mode = zone_mode
        elif status.zone1_mode is not None:
            mode = status.zone1_mode
        else:
            mode = ZoneMode.COOL_FLOW
        dhw_setpoint = status.dhw_setpoint if status.dhw_setpoint is not None else 50.0
        power_on = status.power_on if status.power_on is not None else True
        dhw_eco = status.dhw_eco if status.dhw_eco is not None else True
        command = generate_set_flow_setpoint_command(
            zone1_setpoint,
            zone2_setpoint,
            dhw_setpoint,
            power_on=power_on,
            dhw_eco=dhw_eco,
            zone_mode=mode,
        )
        return self._send_atw_command(command)

    def set_dhw_setpoint(self, temp: float) -> bool:
        """Set the hot-water tank target temperature."""
        return self._send_atw_command(generate_set_dhw_setpoint_command(temp))

    def set_dhw_boost(self, on: bool) -> bool:
        """Force (boost) hot-water production on or off."""
        return self._send_atw_command(generate_forced_dhw_command(on))

    def set_zone_mode(self, zone1: ZoneMode, zone2: ZoneMode) -> bool:
        """Set the heating/cooling control mode for each zone."""
        return self._send_atw_command(generate_set_zone_mode_command(zone1, zone2))

    def set_power(self, on: bool) -> bool | ParsedDeviceState | None:
        """Turn the system on or off.

        On an air-to-water (Ecodan) unit this sends the ATW power packet and
        returns True/False for success (the documented ATW contract). On an
        air-to-air unit it preserves the original changeset behaviour and
        returns the updated ParsedDeviceState.
        """
        if self.is_atw:
            return self._send_atw_command(generate_set_power_command(on))
        # Air-to-air power control (original behaviour, unchanged).
        cs = self.changeset()
        cs.set_power(PowerOnOff.ON if on else PowerOnOff.OFF)
        return self.apply_changeset(cs)

    def _send_general_control_command(self, state: GeneralStates, controls: Controls) -> ParsedDeviceState:
        """Send a general control command to the device"""
        # Generate the hex command
        hex_command = state.generate_general_command(controls).hex()
        response = self.api.send_hex_command(hex_command)
        return self._parse_status_response(response)

    def _send_extend08_command(self, state: GeneralStates, controls: Controls08) -> ParsedDeviceState:
        """Send an extend08 command for advanced features"""
        # Generate the hex command
        hex_command = state.generate_extend08_command(controls).hex()
        response = self.api.send_hex_command(hex_command)
        return self._parse_status_response(response)

    def enable_echonet(self, connect: bool | None = None) -> None:
        """Enable ECHONET Lite. connect=None leaves the MELCloud connection setting untouched."""
        self.api.send_echonet_enable(connect=connect)

    def get_unit_info(self) -> dict[str, Any]:
        """Get detailed unit information from the admin interface"""
        self.unit_info = self.api.get_unit_info()
        logger.debug(
            f"✅ Unit info retrieved: "
            f"{len(self.unit_info.get('Adaptor Information', {}))} adaptor fields, "
            f"{len(self.unit_info.get('Unit Info', {}))} unit fields"
        )
        return self.unit_info
