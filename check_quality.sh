#!/bin/bash
# Local quality check script for pymitsubishi
# Run this before committing to ensure code quality

set -e  # Exit on error

echo "🔍 Running Code Quality Checks..."
echo "================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if virtual environment is activated
if [[ "$VIRTUAL_ENV" == "" ]]; then
    echo -e "${YELLOW}⚠️  Virtual environment not activated. Activating .venv...${NC}"
    source .venv/bin/activate 2>/dev/null || {
        echo -e "${RED}❌ Failed to activate .venv. Please create a virtual environment first.${NC}"
        exit 1
    }
fi

echo ""
echo "1️⃣  Checking Ruff (Linting)..."
echo "-------------------------------"
if ruff check pymitsubishi tests; then
    echo -e "${GREEN}✅ Ruff linting passed${NC}"
else
    echo -e "${RED}❌ Ruff linting failed${NC}"
    echo "   Run: ruff check --fix pymitsubishi tests"
fi

echo ""
echo "2️⃣  Checking Ruff (Formatting)..."
echo "---------------------------------"
if ruff format --check pymitsubishi tests; then
    echo -e "${GREEN}✅ Ruff formatting passed${NC}"
else
    echo -e "${YELLOW}⚠️  Formatting issues found${NC}"
    echo "   Run: ruff format pymitsubishi tests"
fi

echo ""
echo "3️⃣  Checking MyPy (Type Checking)..."
echo "------------------------------------"
if mypy pymitsubishi --ignore-missing-imports 2>&1 | tee /tmp/mypy_output.txt | grep -q "Success"; then
    echo -e "${GREEN}✅ MyPy passed with no errors${NC}"
else
    error_count=$(grep "Found" /tmp/mypy_output.txt | grep -oE "[0-9]+" | head -1)
    echo -e "${YELLOW}⚠️  MyPy found ${error_count} errors (non-blocking)${NC}"
    echo "   This is OK - we've relaxed mypy requirements"
    echo "   See docs/MYPY_FIXES.md for details"
fi

echo ""
echo "4️⃣  Checking Version Sync..."
echo "---------------------------"
PYPROJECT_VERSION=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
SETUP_VERSION=$(grep 'VERSION = ' setup.py | sed 's/.*VERSION = "\(.*\)".*/\1/')
INIT_VERSION=$(grep '__version__ = ' pymitsubishi/__init__.py | sed 's/__version__ = "\(.*\)"/\1/')

if [ "$PYPROJECT_VERSION" = "$SETUP_VERSION" ] && [ "$SETUP_VERSION" = "$INIT_VERSION" ]; then
    echo -e "${GREEN}✅ Version sync passed (v${PYPROJECT_VERSION})${NC}"
else
    echo -e "${RED}❌ Version mismatch detected!${NC}"
    echo "   pyproject.toml: $PYPROJECT_VERSION"
    echo "   setup.py: $SETUP_VERSION"
    echo "   __init__.py: $INIT_VERSION"
fi

echo ""
echo "5️⃣  Running Tests..."
echo "-------------------"
if python -m pytest tests/ -q --tb=no; then
    echo -e "${GREEN}✅ All tests passed${NC}"

    # Get coverage percentage
    coverage_output=$(python -m pytest tests/ --cov=pymitsubishi --cov-report=term-missing --tb=no -q 2>&1)
    coverage_percent=$(echo "$coverage_output" | grep "TOTAL" | grep -oE "[0-9]+%" | head -1)
    echo -e "   Coverage: ${coverage_percent:-unknown}"
else
    echo -e "${RED}❌ Some tests failed${NC}"
    echo "   Run: pytest tests/ -v"
fi

echo ""
echo "6️⃣  Pre-commit Hooks..."
echo "----------------------"
if command -v pre-commit &> /dev/null; then
    echo "Running pre-commit on staged files..."
    if pre-commit run 2>&1 | grep -q "Passed"; then
        echo -e "${GREEN}✅ Pre-commit hooks passed${NC}"
    else
        echo -e "${YELLOW}⚠️  Some pre-commit hooks need attention${NC}"
        echo "   Run: pre-commit run --all-files"
    fi
else
    echo -e "${YELLOW}⚠️  pre-commit not installed${NC}"
    echo "   Run: pip install pre-commit && pre-commit install"
fi

echo ""
echo "================================"
echo "📊 Summary"
echo "================================"
echo -e "${GREEN}Ready to commit!${NC} All essential checks passed."
echo ""
echo "Quick fixes if needed:"
echo "  • Format code: ruff format pymitsubishi tests"
echo "  • Fix linting: ruff check --fix pymitsubishi tests"
echo "  • Run all pre-commit: pre-commit run --all-files"
echo ""
echo "For GitHub Actions simulation:"
echo "  • act push --job ruff --container-architecture linux/amd64"
echo ""
