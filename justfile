# penstock development tasks

# Install dependencies and set up dev environment
setup:
    uv sync
    uv run pre-commit install
    @echo "Dev environment ready."

# Run all checks (lint + typecheck + tests)
check: lint typecheck test

# Run ruff linter
lint:
    uv run ruff check

# Run ruff with auto-fix
fix:
    uv run ruff check --fix

# Run mypy strict type checking
typecheck:
    uv run mypy

# Run test suite
test *args='':
    uv run pytest tests/ -v {{ args }}

# Run a playground demo (e.g. just demo flow)
demo name:
    uv run python -m playground.demo_{{ name }}

# Build the package
build:
    uv build

# Clean build artifacts
clean:
    rm -rf dist/ build/ *.egg-info
