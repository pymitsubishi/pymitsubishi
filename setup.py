#!/usr/bin/env python3
"""Minimal setup.py for backwards compatibility.

All configuration is now in pyproject.toml.
This file exists only for compatibility with older pip versions
and tools that don't support PEP 517/518.
"""

from setuptools import setup

# Keeping version here for PROJECT_RULES.md requirement
# This must match the version in pyproject.toml and pymitsubishi/__init__.py
VERSION = "0.3.0"

if __name__ == "__main__":
    setup(
        version=VERSION,
        # All other configuration is in pyproject.toml
    )
