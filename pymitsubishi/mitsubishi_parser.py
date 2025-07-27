#!/usr/bin/env python3
"""
Mitsubishi Air Conditioner Protocol Parser

This module contains all the parsing logic for Mitsubishi AC protocol payloads,
including enums, state classes, and functions for decoding hex values.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

# Temperature constants
MIN_TEMPERATURE = 160  # 16.0°C in 0.1°C units
MAX_TEMPERATURE = 310  # 31.0°C in 0.1°C units

class PowerOnOff(Enum):
    OFF = '00'
    ON = '01'

class DriveMode(Enum):
    HEATER = '01'
    DEHUM = '02' 
    COOLER = '03'
    AUTO = '08'
    AUTO_COOLER = '1b'
    AUTO_HEATER = '19'
    FAN = '07'

class WindSpeed(Enum):
    AUTO = 0
    LEVEL_1 = 1
    LEVEL_2 = 2
    LEVEL_3 = 3
    LEVEL_FULL = 5

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

@dataclass
class GeneralStates:
    """Parsed general AC states from device response"""
    power_on_off: PowerOnOff = PowerOnOff.OFF
    drive_mode: DriveMode = DriveMode.AUTO
    temperature: int = 220  # 22.0°C in 0.1°C units
    wind_speed: WindSpeed = WindSpeed.AUTO
    vertical_wind_direction_right: VerticalWindDirection = VerticalWindDirection.AUTO
    vertical_wind_direction_left: VerticalWindDirection = VerticalWindDirection.AUTO
    horizontal_wind_direction: HorizontalWindDirection = HorizontalWindDirection.AUTO
    dehum_setting: int = 0
    is_power_saving: bool = False
    wind_and_wind_break_direct: int = 0

@dataclass
class SensorStates:
    """Parsed sensor states from device response"""
    outside_temperature: Optional[int] = None
    room_temperature: int = 220  # 22.0°C in 0.1°C units
    thermal_sensor: bool = False
    wind_speed_pr557: int = 0

@dataclass 
class ErrorStates:
    """Parsed error states from device response"""
    is_abnormal_state: bool = False
    error_code: str = "8000"

@dataclass
class ParsedDeviceState:
    """Complete parsed device state combining all state types"""
    general: Optional[GeneralStates] = None
    sensors: Optional[SensorStates] = None
    errors: Optional[ErrorStates] = None
    mac: str = ""
    serial: str = ""
    rssi: str = ""
    app_version: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        result = {
            'device_info': {
                'mac': self.mac,
                'serial': self.serial,
                'rssi': self.rssi,
                'app_version': self.app_version,
            }
        }
        
        if self.general:
            result['general_states'] = {
                'power': 'ON' if self.general.power_on_off == PowerOnOff.ON else 'OFF',
                'mode': self.general.drive_mode.name,
                'target_temperature_celsius': self.general.temperature / 10.0,
                'fan_speed': self.general.wind_speed.name,
                'vertical_wind_direction_right': self.general.vertical_wind_direction_right.name,
                'vertical_wind_direction_left': self.general.vertical_wind_direction_left.name,
                'horizontal_wind_direction': self.general.horizontal_wind_direction.name,
                'dehumidification_setting': self.general.dehum_setting,
                'power_saving_mode': self.general.is_power_saving,
                'wind_and_wind_break_direct': self.general.wind_and_wind_break_direct,
            }
            
        if self.sensors:
            result['sensor_states'] = {
                'room_temperature_celsius': self.sensors.room_temperature / 10.0,
                'outside_temperature_celsius': self.sensors.outside_temperature / 10.0 if self.sensors.outside_temperature else None,
                'thermal_sensor_active': self.sensors.thermal_sensor,
                'wind_speed_pr557': self.sensors.wind_speed_pr557,
            }
            
        if self.errors:
            result['error_states'] = {
                'abnormal_state': self.errors.is_abnormal_state,
                'error_code': self.errors.error_code,
            }
            
        return result

def calc_fcc(payload_hex: str) -> str:
    """Calculate FCC checksum for Mitsubishi protocol payload"""
    total = 0
    # Process 20 pairs of hex characters (40 characters total)
    for i in range(20):
        start_pos = 2 * i
        end_pos = start_pos + 2
        if start_pos < len(payload_hex):
            hex_pair = payload_hex[start_pos:end_pos]
            if len(hex_pair) == 2:
                total += int(hex_pair, 16)
    
    # Calculate checksum: 256 - (total % 256)
    checksum = 256 - (total % 256)
    checksum_hex = format(checksum, '02x')
    
    # Return last 2 characters
    return checksum_hex[-2:]

def convert_temperature(temperature: int) -> str:
    """Convert temperature in 0.1°C units to segment format"""
    t = max(MIN_TEMPERATURE, min(MAX_TEMPERATURE, temperature))
    e = 31 - (t // 10)
    last_digit = '0' if str(t)[-1] == '0' else '1'
    return last_digit + format(e, 'x')

def convert_temperature_to_segment(temperature: int) -> str:
    """Convert temperature to segment 14 format"""
    value = 0x80 + (temperature // 5)
    return format(value, '02x')

def get_normalized_temperature(hex_value: int) -> int:
    """Normalize temperature from hex value to 0.1°C units"""
    adjusted = 5 * (hex_value - 0x80)
    if adjusted >= 400:
        return 400
    elif adjusted <= 0:
        return 0
    else:
        return adjusted

def get_on_off_status(segment: str) -> PowerOnOff:
    """Parse power on/off status from segment"""
    if segment in ['01', '02']:
        return PowerOnOff.ON
    else:
        return PowerOnOff.OFF

def get_drive_mode(segment: str) -> DriveMode:
    """Parse drive mode from segment"""
    mode_map = {
        '03': DriveMode.COOLER, '0b': DriveMode.COOLER,
        '01': DriveMode.HEATER, '09': DriveMode.HEATER,
        '08': DriveMode.AUTO,
        '00': DriveMode.DEHUM, '02': DriveMode.DEHUM, '0a': DriveMode.DEHUM, '0c': DriveMode.DEHUM,
        '1b': DriveMode.AUTO_COOLER,
        '19': DriveMode.AUTO_HEATER,
    }
    return mode_map.get(segment, DriveMode.FAN)

def get_wind_speed(segment: str) -> WindSpeed:
    """Parse wind speed from segment"""
    speed_map = {
        '00': WindSpeed.AUTO,
        '01': WindSpeed.LEVEL_1,
        '02': WindSpeed.LEVEL_2,
        '03': WindSpeed.LEVEL_3,
        '05': WindSpeed.LEVEL_FULL,
    }
    return speed_map.get(segment, WindSpeed.AUTO)

def get_vertical_wind_direction(segment: str) -> VerticalWindDirection:
    """Parse vertical wind direction from segment"""
    direction_map = {
        '00': VerticalWindDirection.AUTO,
        '01': VerticalWindDirection.V1,
        '02': VerticalWindDirection.V2,
        '03': VerticalWindDirection.V3,
        '04': VerticalWindDirection.V4,
        '05': VerticalWindDirection.V5,
        '07': VerticalWindDirection.SWING,
    }
    return direction_map.get(segment, VerticalWindDirection.AUTO)

def get_horizontal_wind_direction(segment: str) -> HorizontalWindDirection:
    """Parse horizontal wind direction from segment"""
    value = int(segment, 16) & 0x7F  # 127 & value
    try:
        return HorizontalWindDirection(value)
    except ValueError:
        return HorizontalWindDirection.AUTO

def is_general_states_payload(payload: str) -> bool:
    """Check if payload contains general states data"""
    if len(payload) < 12:
        return False
    return payload[2:4] in ['62', '7b'] and payload[10:12] == '02'

def is_sensor_states_payload(payload: str) -> bool:
    """Check if payload contains sensor states data"""
    if len(payload) < 12:
        return False
    return payload[2:4] in ['62', '7b'] and payload[10:12] == '03'

def is_error_states_payload(payload: str) -> bool:
    """Check if payload contains error states data"""
    if len(payload) < 12:
        return False
    return payload[2:4] in ['62', '7b'] and payload[10:12] == '04'

def parse_general_states(payload: str) -> Optional[GeneralStates]:
    """Parse general states from hex payload"""
    if len(payload) < 42:
        return None
    
    try:
        power_on_off = get_on_off_status(payload[16:18])
        temperature = get_normalized_temperature(int(payload[32:34], 16))
        drive_mode = get_drive_mode(payload[18:20])
        wind_speed = get_wind_speed(payload[22:24])
        right_vertical_wind_direction = get_vertical_wind_direction(payload[24:26])
        left_vertical_wind_direction = get_vertical_wind_direction(payload[40:42])
        horizontal_wind_direction = get_horizontal_wind_direction(payload[30:32])
        
        # Extra states
        dehum_setting = int(payload[34:36], 16) if len(payload) > 35 else 0
        is_power_saving = int(payload[36:38], 16) > 0 if len(payload) > 37 else False
        wind_and_wind_break_direct = int(payload[38:40], 16) if len(payload) > 39 else 0
        
        return GeneralStates(
            power_on_off=power_on_off,
            temperature=temperature,
            drive_mode=drive_mode,
            wind_speed=wind_speed,
            vertical_wind_direction_right=right_vertical_wind_direction,
            vertical_wind_direction_left=left_vertical_wind_direction,
            horizontal_wind_direction=horizontal_wind_direction,
            dehum_setting=dehum_setting,
            is_power_saving=is_power_saving,
            wind_and_wind_break_direct=wind_and_wind_break_direct,
        )
    except (ValueError, IndexError):
        return None

def parse_sensor_states(payload: str) -> Optional[SensorStates]:
    """Parse sensor states from hex payload"""
    if len(payload) < 42:
        return None
    
    try:
        outside_temp_raw = int(payload[20:22], 16)
        outside_temperature = None if outside_temp_raw < 16 else get_normalized_temperature(outside_temp_raw)
        room_temperature = get_normalized_temperature(int(payload[24:26], 16))
        thermal_sensor = (int(payload[38:40], 16) & 0x01) != 0
        wind_speed_pr557 = 1 if (int(payload[40:42], 16) & 0x01) == 1 else 0
        
        return SensorStates(
            outside_temperature=outside_temperature,
            room_temperature=room_temperature,
            thermal_sensor=thermal_sensor,
            wind_speed_pr557=wind_speed_pr557,
        )
    except (ValueError, IndexError):
        return None

def parse_error_states(payload: str) -> Optional[ErrorStates]:
    """Parse error states from hex payload"""
    if len(payload) < 22:
        return None
    
    try:
        code_head = payload[18:20]
        code_tail = payload[20:22]
        is_abnormal_state = not (code_head == '80' and code_tail == '00')
        error_code = f"{code_head}{code_tail}"
        
        return ErrorStates(
            is_abnormal_state=is_abnormal_state,
            error_code=error_code,
        )
    except (ValueError, IndexError):
        return None

def parse_code_values(code_values: List[str]) -> ParsedDeviceState:
    """Parse a list of code values and return combined device state"""
    parsed_state = ParsedDeviceState()
    
    for hex_value in code_values:
        if not hex_value or len(hex_value) < 20:
            continue
            
        hex_lower = hex_value.lower()
        if not all(c in '0123456789abcdef' for c in hex_lower):
            continue
            
        # Parse different payload types
        if is_general_states_payload(hex_lower):
            parsed_state.general = parse_general_states(hex_lower)
        elif is_sensor_states_payload(hex_lower):
            parsed_state.sensors = parse_sensor_states(hex_lower)
        elif is_error_states_payload(hex_lower):
            parsed_state.errors = parse_error_states(hex_lower)
    
    return parsed_state

def generate_general_command(general_states: GeneralStates, controls: Dict[str, bool]) -> str:
    """Generate general control command hex string"""
    segments = {
        'segment0': '01',
        'segment1': '00',
        'segment2': '00',
        'segment3': '00',
        'segment4': '00',
        'segment5': '00',
        'segment6': '00',
        'segment7': '00',
        'segment13': '00',
        'segment14': '00',
        'segment15': '00',
    }
    
    # Calculate segment 1 value (control flags)
    segment1_value = 0
    if controls.get('power_on_off'):
        segment1_value |= 0x01
    if controls.get('drive_mode'):
        segment1_value |= 0x02
    if controls.get('temperature'):
        segment1_value |= 0x04
    if controls.get('wind_speed'):
        segment1_value |= 0x08
    if controls.get('up_down_wind_direct'):
        segment1_value |= 0x10
    
    # Calculate segment 2 value
    segment2_value = 0
    if controls.get('left_right_wind_direct'):
        segment2_value |= 0x01
    if controls.get('outside_control', True):  # Default true
        segment2_value |= 0x02
    
    segments['segment1'] = f"{segment1_value:02x}"
    segments['segment2'] = f"{segment2_value:02x}"
    segments['segment3'] = general_states.power_on_off.value
    segments['segment4'] = general_states.drive_mode.value
    segments['segment6'] = f"{general_states.wind_speed.value:02x}"
    segments['segment7'] = f"{general_states.vertical_wind_direction_right.value:02x}"
    segments['segment13'] = f"{general_states.horizontal_wind_direction.value:02x}"
    segments['segment15'] = '41'  # checkInside: 41 true, 42 false
    
    segments['segment5'] = convert_temperature(general_states.temperature)
    segments['segment14'] = convert_temperature_to_segment(general_states.temperature)
    
    # Build payload
    payload = '41013010'
    for i in range(16):
        segment_key = f'segment{i}'
        payload += segments.get(segment_key, '00')
    
    # Calculate and append FCC
    fcc = calc_fcc(payload)
    return "fc" + payload + fcc

def generate_extend08_command(general_states: GeneralStates, controls: Dict[str, bool]) -> str:
    """Generate extend08 command for buzzer, dehum, power saving, etc."""
    segment_x_value = 0
    if controls.get('dehum'):
        segment_x_value |= 0x04
    if controls.get('power_saving'):
        segment_x_value |= 0x08
    if controls.get('buzzer'):
        segment_x_value |= 0x10
    if controls.get('wind_and_wind_break'):
        segment_x_value |= 0x20
    
    segment_x = f"{segment_x_value:02x}"
    segment_y = f"{general_states.dehum_setting:02x}" if controls.get('dehum') else '00'
    segment_z = '0A' if general_states.is_power_saving else '00'
    segment_a = f"{general_states.wind_and_wind_break_direct:02x}" if controls.get('wind_and_wind_break') else '00'
    buzzer_segment = '01' if controls.get('buzzer') else '00'
    
    payload = "4101301008" + segment_x + "0000" + segment_y + segment_z + segment_a + buzzer_segment + "0000000000000000"
    fcc = calc_fcc(payload)
    return 'fc' + payload + fcc
