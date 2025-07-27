#!/usr/bin/env python3
"""
Mitsubishi Air Conditioner Business Logic Layer

This module is responsible for managing control operations and state
for Mitsubishi MAC-577IF-2E devices.
"""

import xml.etree.ElementTree as ET
from typing import Dict, Optional, Any
from .mitsubishi_api import MitsubishiAPI
from .mitsubishi_parser import (
    PowerOnOff, DriveMode, WindSpeed, VerticalWindDirection, 
    HorizontalWindDirection, GeneralStates, ParsedDeviceState, 
    parse_code_values, generate_general_command, generate_extend08_command
)


class MitsubishiController:
    """Business logic controller for Mitsubishi AC devices"""
    
    def __init__(self, api: MitsubishiAPI):
        self.api = api
        self.state = ParsedDeviceState()
    
    @classmethod
    def create(cls, device_ip: str, encryption_key: str = "unregistered"):
        """Create a MitsubishiController with the specified encryption key"""
        api = MitsubishiAPI(device_ip=device_ip, encryption_key=encryption_key)
        return cls(api)
        
    def fetch_status(self, debug: bool = False, detect_capabilities: bool = True) -> bool:
        """Fetch current device status and optionally detect capabilities"""
        response = self.api.send_status_request(debug=debug)
        if response:
            self._parse_status_response(response)
            
            # Optionally perform capability detection
            if detect_capabilities:
                self._detect_capabilities_from_response(response, debug=debug)
            
            return True
        return False

    def _parse_status_response(self, response: str):
        """Parse the device status response and update state"""
        try:
            # Parse the XML response
            root = ET.fromstring(response)
            
            # Extract code values for parsing
            code_values_elems = root.findall('.//CODE/VALUE')
            code_values = [elem.text for elem in code_values_elems if elem.text]
            
            # Use the parser module to get structured state
            parsed_state = parse_code_values(code_values)
            
            if parsed_state:
                self.state = parsed_state

            # Extract and set device identity
            mac_elem = root.find('.//MAC')
            if mac_elem is not None:
                self.state.mac = mac_elem.text
                
            serial_elem = root.find('.//SERIAL')
            if serial_elem is not None:
                self.state.serial = serial_elem.text

        except ET.ParseError as e:
            print(f"Error parsing status response: {e}")
    
    def _detect_capabilities_from_response(self, response: str, debug: bool = False):
        """Detect capabilities from the status response"""
        try:
            from .mitsubishi_capabilities import CapabilityDetector, DeviceCapabilities
            
            if debug:
                print("🔍 Detecting capabilities from status response...")
            
            # Create a temporary capability detector to analyze the response
            temp_detector = CapabilityDetector(api=self.api)
            temp_detector.capabilities = DeviceCapabilities()
            
            # Parse the XML response for ProfileCode and other capability indicators
            root = ET.fromstring(response)
            
            # Extract basic device info
            mac_elem = root.find('.//MAC')
            if mac_elem is not None:
                temp_detector.capabilities.mac_address = mac_elem.text
                
            serial_elem = root.find('.//SERIAL')
            if serial_elem is not None:
                temp_detector.capabilities.serial_number = serial_elem.text
                
            # Look for firmware/version info
            version_elem = root.find('.//VERSION')
            if version_elem is not None:
                temp_detector.capabilities.firmware_version = version_elem.text
            
            # Extract and analyze ProfileCodes
            profile_elems = root.findall('.//PROFILECODE/DATA/VALUE') or root.findall('.//PROFILECODE/VALUE')
            for elem in profile_elems:
                if elem.text:
                    profile_key = f"profile_{len(temp_detector.capabilities.profile_codes)}"
                    temp_detector.capabilities.profile_codes[profile_key] = elem.text
                    
                    # Analyze the ProfileCode for capabilities
                    try:
                        analysis = temp_detector.capabilities.analyze_profile_code(elem.text)
                        if debug:
                            print(f"✅ ProfileCode {profile_key} analyzed successfully")
                    except Exception as e:
                        if debug:
                            print(f"⚠️ Failed to analyze ProfileCode {profile_key}: {e}")
                    
                    # Try to extract model info from profile codes
                    if not temp_detector.capabilities.device_model and len(elem.text) > 10:
                        temp_detector.capabilities.device_model = elem.text[:12]
            
            # Extract and analyze code values for group codes
            code_values_elems = root.findall('.//CODE/DATA/VALUE') or root.findall('.//CODE/VALUE')
            code_values = [elem.text for elem in code_values_elems if elem.text]
            
            # Track group codes found
            for code_value in code_values:
                if len(code_value) >= 12:
                    try:
                        # Group code is at position 10-11 in hex string
                        group_code = code_value[10:12]
                        temp_detector.capabilities.supported_group_codes.add(group_code)
                    except IndexError:
                        continue
            
            # Analyze parsed state to determine capabilities
            if self.state.general:
                temp_detector._analyze_parsed_state(self.state)
            
            # Analyze group codes to validate capabilities
            temp_detector._analyze_group_codes(debug=debug)
            
            # Attach the capabilities to our state
            self.state.capabilities = temp_detector.capabilities
            
            if debug:
                print(f"✅ Capabilities detected: {len(temp_detector.capabilities.capabilities)} found")
                
        except Exception as e:
            if debug:
                print(f"⚠️ Error detecting capabilities: {e}")
    
    def _check_state_available(self) -> bool:
        """Check if device state is available"""
        if not self.state.general:
            print("❌ No device state available. Fetch status first.")
            return False
        return True
    
    def _create_updated_state(self, **overrides) -> GeneralStates:
        """Create updated state with specified field overrides"""
        return GeneralStates(
            power_on_off=overrides.get('power_on_off', self.state.general.power_on_off),
            temperature=overrides.get('temperature', self.state.general.temperature),
            drive_mode=overrides.get('drive_mode', self.state.general.drive_mode),
            wind_speed=overrides.get('wind_speed', self.state.general.wind_speed),
            vertical_wind_direction_right=overrides.get('vertical_wind_direction_right', self.state.general.vertical_wind_direction_right),
            vertical_wind_direction_left=overrides.get('vertical_wind_direction_left', self.state.general.vertical_wind_direction_left),
            horizontal_wind_direction=overrides.get('horizontal_wind_direction', self.state.general.horizontal_wind_direction),
            dehum_setting=overrides.get('dehum_setting', self.state.general.dehum_setting),
            is_power_saving=overrides.get('is_power_saving', self.state.general.is_power_saving),
            wind_and_wind_break_direct=overrides.get('wind_and_wind_break_direct', self.state.general.wind_and_wind_break_direct),
        )

    def set_power(self, power_on: bool, debug: bool = False) -> bool:
        """Set power on/off"""
        if not self._check_state_available():
            return False
            
        new_power = PowerOnOff.ON if power_on else PowerOnOff.OFF
        updated_state = self._create_updated_state(power_on_off=new_power)
        return self._send_general_control_command(updated_state, {'power_on_off': True}, debug=debug)

    def set_temperature(self, temperature_celsius: float, debug: bool = False) -> bool:
        """Set target temperature in Celsius"""
        if not self._check_state_available():
            return False
            
        # Convert to 0.1°C units and validate range
        temp_units = int(temperature_celsius * 10)
        if temp_units < 160 or temp_units > 320:  # 16°C to 32°C
            print(f"❌ Temperature {temperature_celsius}°C is out of range (16-32°C)")
            return False
            
        updated_state = self._create_updated_state(temperature=temp_units)
        return self._send_general_control_command(updated_state, {'temperature': True}, debug=debug)

    def set_mode(self, mode: DriveMode, debug: bool = False) -> bool:
        """Set operating mode"""
        if not self._check_state_available():
            return False
            
        updated_state = self._create_updated_state(drive_mode=mode)
        return self._send_general_control_command(updated_state, {'drive_mode': True}, debug=debug)

    def set_fan_speed(self, speed: WindSpeed, debug: bool = False) -> bool:
        """Set fan speed"""
        if not self._check_state_available():
            return False
            
        updated_state = self._create_updated_state(wind_speed=speed)
        return self._send_general_control_command(updated_state, {'wind_speed': True}, debug=debug)

    def set_vertical_vane(self, direction: VerticalWindDirection, side: str = 'right', debug: bool = False) -> bool:
        """Set vertical vane direction (right or left side)"""
        if not self._check_state_available():
            return False
        
        if side.lower() not in ['right', 'left']:
            print("❌ Side must be 'right' or 'left'")
            return False
            
        if side.lower() == 'right':
            updated_state = self._create_updated_state(vertical_wind_direction_right=direction)
        else:
            updated_state = self._create_updated_state(vertical_wind_direction_left=direction)
            
        return self._send_general_control_command(updated_state, {'up_down_wind_direct': True}, debug=debug)

    def set_horizontal_vane(self, direction: HorizontalWindDirection, debug: bool = False) -> bool:
        """Set horizontal vane direction"""
        if not self._check_state_available():
            return False
            
        updated_state = self._create_updated_state(horizontal_wind_direction=direction)
        return self._send_general_control_command(updated_state, {'left_right_wind_direct': True}, debug=debug)

    def set_dehumidifier(self, setting: int, debug: bool = False) -> bool:
        """Set dehumidifier level (0-100)"""
        if not self._check_state_available():
            return False
            
        if setting < 0 or setting > 100:
            print("❌ Dehumidifier setting must be between 0-100")
            return False
            
        updated_state = self._create_updated_state(dehum_setting=setting)
        return self._send_extend08_command(updated_state, {'dehum': True}, debug=debug)

    def set_power_saving(self, enabled: bool, debug: bool = False) -> bool:
        """Enable or disable power saving mode"""
        if not self._check_state_available():
            return False
            
        updated_state = self._create_updated_state(is_power_saving=enabled)
        return self._send_extend08_command(updated_state, {'power_saving': True}, debug=debug)

    def send_buzzer_command(self, enabled: bool = True, debug: bool = False) -> bool:
        """Send buzzer control command"""
        if not self._check_state_available():
            return False
            
        return self._send_extend08_command(self.state.general, {'buzzer': enabled}, debug=debug)

    def _send_general_control_command(self, state: GeneralStates, controls: Dict[str, bool], debug: bool = False) -> bool:
        """Send a general control command to the device"""
        # Generate the hex command
        hex_command = generate_general_command(state, controls)
        
        if debug:
            print(f"🔧 Sending command: {hex_command}")
            
        response = self.api.send_hex_command(hex_command, debug=debug)
        
        if response:
            if debug:
                print("✅ Command sent successfully")
            # Update our local state to reflect the change
            self.state.general = state
            return True
        else:
            if debug:
                print("❌ Command failed")
            return False

    def _send_extend08_command(self, state: GeneralStates, controls: Dict[str, bool], debug: bool = False) -> bool:
        """Send an extend08 command for advanced features"""
        # Generate the hex command
        hex_command = generate_extend08_command(state, controls)
        
        if debug:
            print(f"🔧 Sending extend08 command: {hex_command}")
            
        response = self.api.send_hex_command(hex_command, debug=debug)
        
        if response:
            if debug:
                print("✅ Extend08 command sent successfully")
            # Update our local state to reflect the change
            self.state.general = state
            return True
        else:
            if debug:
                print("❌ Extend08 command failed")
            return False

    def enable_echonet(self, debug: bool = False) -> bool:
        """Send ECHONET enable command"""
        response = self.api.send_echonet_enable(debug=debug)
        return response is not None

    def get_unit_info(self, debug: bool = False) -> Optional[Dict[str, Any]]:
        """Get detailed unit information from the admin interface"""
        unit_info = self.api.get_unit_info(debug=debug)
        
        if unit_info and debug:
            print(f"✅ Unit info retrieved: {len(unit_info.get('adaptor_info', {}))} adaptor fields, {len(unit_info.get('unit_info', {}))} unit fields")
        
        return unit_info

    def get_status_summary(self) -> Dict[str, any]:
        """Get human-readable status summary"""
        summary = {
            'mac': self.state.mac,
            'serial': self.state.serial,
        }
        
        if self.state.general:
            summary.update({
                'power': 'ON' if self.state.general.power_on_off == PowerOnOff.ON else 'OFF',
                'mode': self.state.general.drive_mode.name,
                'target_temp': self.state.general.temperature / 10.0,
                'fan_speed': self.state.general.wind_speed.name,
                'dehumidifier_setting': self.state.general.dehum_setting,
                'power_saving_mode': self.state.general.is_power_saving,
                'vertical_vane_right': self.state.general.vertical_wind_direction_right.name,
                'vertical_vane_left': self.state.general.vertical_wind_direction_left.name,
                'horizontal_vane': self.state.general.horizontal_wind_direction.name,
            })
            
        if self.state.sensors:
            summary.update({
                'room_temp': self.state.sensors.room_temperature / 10.0,
                'outside_temp': self.state.sensors.outside_temperature / 10.0 if self.state.sensors.outside_temperature else None,
            })
            
        if self.state.errors:
            summary.update({
                'error_code': self.state.errors.error_code,
                'abnormal_state': self.state.errors.is_abnormal_state,
            })
            
        # Include capabilities if available
        if hasattr(self.state, 'capabilities') and self.state.capabilities:
            summary['capabilities'] = {
                (cap_type.value if hasattr(cap_type, 'value') else str(cap_type)): {
                    'supported': cap.supported,
                    'min_value': cap.min_value,
                    'max_value': cap.max_value,
                    'supported_values': cap.supported_values,
                    'metadata': cap.metadata,
                } for cap_type, cap in self.state.capabilities.capabilities.items()
            }
        
        return summary
