"""Test basic package functionality and imports."""

import pytest


def test_package_imports():
    """Test that the main package components can be imported."""
    try:
        from pymitsubishi import MitsubishiAPI, MitsubishiController

        assert MitsubishiAPI is not None
        assert MitsubishiController is not None
    except ImportError as e:
        pytest.fail(f"Failed to import package components: {e}")


def test_enums_import():
    """Test that enums can be imported."""
    try:
        from pymitsubishi.mitsubishi_parser import (
            DriveMode,
            HorizontalWindDirection,
            PowerOnOff,
            VerticalWindDirection,
            WindSpeed,
        )

        assert PowerOnOff is not None
        assert DriveMode is not None
        assert WindSpeed is not None
        assert VerticalWindDirection is not None
        assert HorizontalWindDirection is not None
    except ImportError as e:
        pytest.fail(f"Failed to import enums: {e}")


def test_api_initialization():
    """Test that API can be initialized without connection."""
    from pymitsubishi import MitsubishiAPI

    api = MitsubishiAPI("192.168.1.100")  # Dummy IP
    assert api.device_host_port == "192.168.1.100"


def test_controller_initialization():
    """Test that controller can be initialized."""
    from pymitsubishi import MitsubishiAPI, MitsubishiController

    api = MitsubishiAPI("192.168.1.100")  # Dummy IP
    controller = MitsubishiController(api)
    assert controller.api.device_host_port == "192.168.1.100"
