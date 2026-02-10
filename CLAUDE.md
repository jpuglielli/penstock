# Project Instructions

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/) for all commit messages.

Format: `<type>(<optional scope>): <description>`

Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`, `build`, `perf`, `style`

## Development

- `uv run mypy` — strict type checking, must pass with 0 errors
- `uv run pytest tests/ -v` — full test suite, must pass with 0 warnings
- Python >=3.14, zero runtime dependencies
