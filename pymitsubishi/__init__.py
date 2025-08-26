"""
PyMitsubishi - Control and monitor Mitsubishi MAC-577IF-2E air conditioners

This library provides a Python interface for controlling and monitoring
Mitsubishi air conditioners via the MAC-577IF-2E WiFi adapter.
"""

__version__ = "0.3.0"

# Import main classes for easy access
from .mitsubishi_api import MitsubishiAPI
from .mitsubishi_controller import MitsubishiController
from .mitsubishi_parser import (
    AutoMode,
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
)

__all__ = [
    # Main API classes
    "MitsubishiAPI",
    "MitsubishiController",
    # Enums and data classes
    "PowerOnOff",
    "DriveMode",
    "WindSpeed",
    "VerticalWindDirection",
    "HorizontalWindDirection",
    "AutoMode",
    "GeneralStates",
    "SensorStates",
    "EnergyStates",
    "ErrorStates",
    "ParsedDeviceState",
]
