# Project Instructions

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/) for all commit messages.

Format: `<type>(<optional scope>): <description>`

Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `ci`, `build`, `perf`, `style`

## Development

- `just setup` — install deps and configure hooks
- `just check` — run all checks (lint + typecheck + tests)
- `just lint` / `just fix` — ruff lint / auto-fix
- `just typecheck` — mypy strict, must pass with 0 errors
- `just test` — full test suite, must pass with 0 warnings
- `just demo <name>` — run a playground demo (e.g. `just demo flow`)
- Python >=3.14, zero runtime dependencies
- Pre-commit hook runs ruff + mypy automatically
