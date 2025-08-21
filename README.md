# PyMitsubishi

[![PyPI version](https://badge.fury.io/py/pymitsubishi.svg)](https://badge.fury.io/py/pymitsubishi)
[![Python Versions](https://img.shields.io/pypi/pyversions/pymitsubishi.svg)](https://pypi.org/project/pymitsubishi/)
[![Downloads](https://static.pepy.tech/badge/pymitsubishi)](https://pepy.tech/project/pymitsubishi)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Python library for controlling and monitoring Mitsubishi MAC-577IF-2E air conditioners.

## Home Assistant Integration

For Home Assistant users, check out our official integration: [homeassistant-mitsubishi](https://github.com/pymitsubishi/homeassistant-mitsubishi)

## Features

- **Device Control**: Power, temperature, mode, fan speed, and vane direction control
- **Status Monitoring**: Real-time device status, temperatures, and error states
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
api = MitsubishiAPI(device_host_port="192.168.1.100")
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

## API Reference

### MitsubishiAPI

Core communication class handling encryption and HTTP requests.

### MitsubishiController

High-level control interface for device operations.

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

Contributions are welcome! Please see our [Contributing Guidelines](CONTRIBUTING.md) for detailed information on development setup, code standards, and the contribution process.
