chore: Add modern Python tooling and align with HA standards

- Add pyproject.toml with centralized tool configurations
- Add pre-commit hooks for code quality
- Add GitHub Actions workflow for CI/CD
- Update code to Python 3.12+ syntax and fix linting issues
- Simplify setup.py to delegate to pyproject.toml
- Add developer documentation (CONTRIBUTING.md)
- Add local quality check script
- Align quality standards with Home Assistant ecosystem

All tests passing, code formatted with Ruff, type hints modernized.
MyPy reports 55 type errors but configured as non-blocking for
gradual improvement.
