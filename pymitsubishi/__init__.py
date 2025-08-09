"""
PyMitsubishi - Control and monitor Mitsubishi MAC-577IF-2E air conditioners

This library provides a Python interface for controlling and monitoring
Mitsubishi air conditioners via the MAC-577IF-2E WiFi adapter.
"""

__version__ = "0.2.0"

# Import main classes for easy access
from .mitsubishi_api import MitsubishiAPI
from .mitsubishi_capabilities import (
    CapabilityDetector,
    CapabilityType,
    DeviceCapabilities,
    DeviceCapability,
    ProfileCodeAnalysis,
)
from .mitsubishi_controller import MitsubishiController
from .mitsubishi_parser import (
    DriveMode,
    EnergyStates,
    ErrorStates,
    GeneralStates,
    HorizontalWindDirection,
    ParsedDeviceState,
    PowerOnOff,
    SensorStates,
    VerticalWindDirection,
    WindSpeed,
    generate_extend08_command,
    generate_general_command,
    parse_code_values,
)

__all__ = [
    # Main API classes
    "MitsubishiAPI",
    "MitsubishiController",
    # Capability detection
    "CapabilityDetector",
    "DeviceCapabilities",
    "DeviceCapability",
    "CapabilityType",
    "ProfileCodeAnalysis",
    # Enums and data classes
    "PowerOnOff",
    "DriveMode",
    "WindSpeed",
    "VerticalWindDirection",
    "HorizontalWindDirection",
    "GeneralStates",
    "SensorStates",
    "EnergyStates",
    "ErrorStates",
    "ParsedDeviceState",
    # Utility functions
    "parse_code_values",
    "generate_general_command",
    "generate_extend08_command",
]
