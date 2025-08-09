# Contributing to PyMitsubishi

Thank you for your interest in contributing to PyMitsubishi! This document provides guidelines and instructions for contributing to the project.

## Development Setup

### Prerequisites

- Python 3.12 or higher
- Git
- Virtual environment (recommended)

### Setting Up Your Development Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/pymitsubishi/pymitsubishi.git
   cd pymitsubishi
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install the package in development mode with all dependencies:**
   ```bash
   pip install -e ".[dev]"
   ```

   Or if you prefer using requirements files:
   ```bash
   pip install -r requirements-dev.txt
   pip install -e .
   ```

4. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

## Code Quality Standards

We maintain code quality standards aligned with Home Assistant ecosystem practices:

### Pre-commit Hooks

Pre-commit hooks run automatically before each commit:

- **Ruff**: Formats and lints Python code
- **mypy**: Basic type checking (optional)
- **File fixes**: Trailing whitespace, end-of-file, YAML/JSON/TOML validation

To run pre-commit manually:
```bash
# Run on all files
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files
```

### Manual Code Quality Checks

#### Formatting (Ruff)
```bash
# Check formatting
ruff format --check pymitsubishi tests

# Auto-format code
ruff format pymitsubishi tests
```

#### Linting (Ruff)
```bash
# Check for linting issues
ruff check pymitsubishi tests

# Auto-fix linting issues
ruff check --fix pymitsubishi tests
```

#### Type Checking (mypy)
```bash
mypy pymitsubishi --config-file pyproject.toml
```


#### Testing
```bash
# Run tests with coverage report
pytest tests/ -v --cov=pymitsubishi --cov-report=term-missing

# Generate HTML coverage report (optional)
pytest tests/ --cov=pymitsubishi --cov-report=html
# Open htmlcov/index.html in your browser
```

## Writing Pythonic Code

We follow Python 3.12+ best practices:

### Use Type Hints
```python
def calculate_temperature(celsius: float) -> float:
    """Convert Celsius to Fahrenheit.

    Args:
        celsius: Temperature in Celsius.

    Returns:
        Temperature in Fahrenheit.
    """
    return celsius * 9/5 + 32
```

### Use f-strings for Formatting
```python
# Good
message = f"Temperature is {temp}°C"

# Avoid
message = "Temperature is {}°C".format(temp)
message = "Temperature is %d°C" % temp
```

### Use Pathlib for File Operations
```python
from pathlib import Path

# Good
config_path = Path.home() / ".config" / "pymitsubishi"
config_path.mkdir(parents=True, exist_ok=True)

# Avoid
import os
config_path = os.path.join(os.path.expanduser("~"), ".config", "pymitsubishi")
```

### Use Context Managers
```python
# Good
with open("file.txt") as f:
    content = f.read()

# Avoid
f = open("file.txt")
content = f.read()
f.close()
```

### Prefer List/Dict Comprehensions
```python
# Good
squares = [x**2 for x in range(10)]
filtered = {k: v for k, v in data.items() if v > 0}

# Avoid
squares = []
for x in range(10):
    squares.append(x**2)
```

## Testing Guidelines

### Writing Tests

1. **Test files** should mirror the source structure in the `tests/` directory
2. **Test names** should be descriptive: `test_<what_is_being_tested>`
3. **Use fixtures** for common test data
4. **Aim for high test coverage** for new code

Example test:
```python
import pytest
from pymitsubishi import MitsubishiController

@pytest.fixture
def controller():
    """Create a test controller instance."""
    return MitsubishiController("192.168.1.100")

def test_controller_initialization(controller):
    """Test that controller initializes with correct IP."""
    assert controller.ip_address == "192.168.1.100"
    assert controller.port == 80
```

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_controller.py

# Run with coverage
pytest --cov=pymitsubishi
```

## Version Management

**CRITICAL**: When releasing a new version, you MUST update the version in THREE places:

1. `pyproject.toml` - Line with `version = "X.Y.Z"`
2. `setup.py` - Line with `VERSION = "X.Y.Z"`
3. `pymitsubishi/__init__.py` - Line with `__version__ = "X.Y.Z"`

The GitHub Action will verify version synchronization on every push.

## GitHub Actions

Our CI/CD pipeline includes:

1. **Code Quality** (`code-quality.yml`):
   - Pre-commit hooks
   - Ruff formatting and linting
   - Type checking with mypy
   - Test execution with coverage reporting
   - Version synchronization check

2. **Test and Publish** (`publish.yml`):
   - Tests on Python 3.12 and 3.13
   - Automatic PyPI publication on release

## Making a Pull Request

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the code quality standards

3. **Ensure all tests pass:**
   ```bash
   pytest --cov=pymitsubishi
   ```

4. **Run pre-commit hooks:**
   ```bash
   pre-commit run --all-files
   ```

5. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: Add your feature description"
   ```

6. **Push to GitHub:**
   ```bash
   git push origin feature/your-feature-name
   ```

7. **Create a Pull Request** on GitHub

## Commit Message Convention

We follow conventional commits:

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation changes
- `style:` Code style changes (formatting, etc.)
- `refactor:` Code refactoring
- `test:` Test additions or changes
- `chore:` Maintenance tasks

Example:
```bash
git commit -m "feat: Add temperature conversion utility"
git commit -m "fix: Correct humidity sensor parsing"
git commit -m "docs: Update installation instructions"
```

## Getting Help

If you have questions:

1. Check existing [GitHub Issues](https://github.com/pymitsubishi/pymitsubishi/issues)
2. Review the [documentation](README.md)
3. Create a new issue for discussion

Thank you for contributing to PyMitsubishi!
