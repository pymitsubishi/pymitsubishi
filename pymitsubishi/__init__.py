"""
PyMitsubishi - Control and monitor Mitsubishi MAC-577IF-2E air conditioners

This library provides a Python interface for controlling and monitoring
Mitsubishi air conditioners via the MAC-577IF-2E WiFi adapter.
"""

__version__ = "0.1.7"

# Import main classes for easy access
from .mitsubishi_api import MitsubishiAPI
from .mitsubishi_controller import MitsubishiController
from .mitsubishi_capabilities import (
    CapabilityDetector, 
    DeviceCapabilities, 
    DeviceCapability,
    CapabilityType,
    ProfileCodeAnalysis
)
from .mitsubishi_parser import (
    PowerOnOff,
    DriveMode, 
    WindSpeed,
    VerticalWindDirection,
    HorizontalWindDirection,
    GeneralStates,
    SensorStates,
    EnergyStates,
    ErrorStates,
    ParsedDeviceState,
    parse_code_values,
    generate_general_command,
    generate_extend08_command
)

__all__ = [
    # Main API classes
    'MitsubishiAPI',
    'MitsubishiController',
    
    # Capability detection
    'CapabilityDetector',
    'DeviceCapabilities',
    'DeviceCapability', 
    'CapabilityType',
    'ProfileCodeAnalysis',
    
    # Enums and data classes
    'PowerOnOff',
    'DriveMode',
    'WindSpeed', 
    'VerticalWindDirection',
    'HorizontalWindDirection',
    'GeneralStates',
    'SensorStates',
    'EnergyStates',
    'ErrorStates',
    'ParsedDeviceState',
    
    # Utility functions
    'parse_code_values',
    'generate_general_command',
    'generate_extend08_command',
]
