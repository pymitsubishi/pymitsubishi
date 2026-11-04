"""
PyMitsubishi - Control and monitor Mitsubishi MAC-577IF-2E air conditioners

This library provides a Python interface for controlling and monitoring
Mitsubishi air conditioners via the MAC-577IF-2E WiFi adapter.
"""

__version__ = "0.6.1"

# Import main classes for easy access
from .mitsubishi_api import MitsubishiAPI
from .mitsubishi_atw import (
    EcodanOperationMode,
    EcodanStatus,
    FTCVersion,
    ZoneMode,
    is_atw_payload,
    parse_atw_code_values,
)
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
    RemoteLock,
    SensorStates,
    SetRemoteTemperature,
    VerticalWindDirection,
    WindSpeed,
)
from .mitsubishi_telemetry import (
    FIELD_INFO,
    ATATelemetry,
    TelemetryField,
    TelemetryFrame,
    parse_ata_response,
    parse_ata_telemetry,
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
    "RemoteLock",
    "SetRemoteTemperature",
    # Air-to-water (Ecodan) public API
    "EcodanStatus",
    "EcodanOperationMode",
    "ZoneMode",
    "FTCVersion",
    "is_atw_payload",
    "parse_atw_code_values",
    "ATATelemetry",
    "TelemetryField",
    "TelemetryFrame",
    "FIELD_INFO",
    "parse_ata_telemetry",
    "parse_ata_response",
]
