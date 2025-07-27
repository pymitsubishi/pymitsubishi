# PyMitsubishi

[![PyPI version](https://badge.fury.io/py/pymitsubishi.svg)](https://badge.fury.io/py/pymitsubishi)
[![Python Versions](https://img.shields.io/pypi/pyversions/pymitsubishi.svg)](https://pypi.org/project/pymitsubishi/)
[![Downloads](https://static.pepy.tech/badge/pymitsubishi)](https://pepy.tech/project/pymitsubishi)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python library for controlling and monitoring Mitsubishi MAC-577IF-2E air conditioners.

## Features

- **Device Control**: Power, temperature, mode, fan speed, and vane direction control
- **Status Monitoring**: Real-time device status, temperatures, and error states
- **Capability Detection**: Dynamic detection of device capabilities using ProfileCode analysis
- **Group Code Analysis**: Advanced protocol analysis for enhanced device understanding
- **Encryption Support**: Full support for Mitsubishi's encryption protocol

## Installation

```bash
pip install pymitsubishi
```

## Quick Start

```python
from pymitsubishi import MitsubishiAPI, MitsubishiController

# Initialize the API and controller
api = MitsubishiAPI(device_ip="192.168.1.100")
controller = MitsubishiController(api=api)

# Fetch device status
if controller.fetch_status():
    summary = controller.get_status_summary()
    print(f"Power: {summary['power']}")
    print(f"Temperature: {summary['target_temp']}°C")
    print(f"Mode: {summary['mode']}")

# Control the device
controller.set_power(True)
controller.set_temperature(24.0)
controller.set_mode(DriveMode.COOLER)

# Clean up
api.close()
```

## Advanced Usage

### Capability Detection

```python
from pymitsubishi import CapabilityDetector

detector = CapabilityDetector(api=api)
capabilities = detector.detect_all_capabilities(debug=True)

# Check specific capabilities
if capabilities.has_capability(CapabilityType.OUTDOOR_TEMPERATURE_SENSOR):
    print("Device has outdoor temperature sensor")

# Save capabilities for later use
detector.save_capabilities("device_capabilities.json")
```

### ProfileCode Analysis

The library automatically analyzes ProfileCode data from device responses to detect capabilities and device characteristics:

```python
# Fetch status with capability detection
controller.fetch_status(detect_capabilities=True)

# Access detected capabilities
summary = controller.get_status_summary()
if 'capabilities' in summary:
    for cap_name, cap_info in summary['capabilities'].items():
        print(f"{cap_name}: {cap_info['supported']}")
```

## API Reference

### MitsubishiAPI

Core communication class handling encryption and HTTP requests.

### MitsubishiController

High-level control interface for device operations.

### CapabilityDetector

Advanced capability detection using ProfileCode and group code analysis.

### Data Classes

- `PowerOnOff`: Power state enumeration
- `DriveMode`: Operating mode enumeration  
- `WindSpeed`: Fan speed enumeration
- `VerticalWindDirection`, `HorizontalWindDirection`: Vane direction enumerations

## Requirements

- Python 3.12+
- requests
- pycryptodome

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
