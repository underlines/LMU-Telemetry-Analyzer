# AGENTS.md — LMU Telemetry Analyzer

## Project Overview

Local-first telemetry analysis tool for Le Mans Ultimate (LMU) racing game. Analyzes DuckDB telemetry files with a Python backend (FastAPI) and React + TypeScript frontend.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, uv
- **Data**: DuckDB, Polars/NumPy, Parquet cache
- **Frontend**: React + TypeScript
- **Visualization**: Plotly

## Build/Test/Lint Commands

```bash
# Backend (Python)
uv add plotly                    # Install new packages
uv sync                          # Install existing dependencies
uv run pytest                    # Run all tests
uv run pytest tests/test_file.py::test_function  # Run single test
uv run pytest -v                 # Verbose output
uv run pytest -k "test_name"     # Run tests matching pattern
uv run ruff check .              # Lint
uv run ruff check --fix .        # Lint and fix
uv run ruff format .             # Format code
uv run mypy .                    # Type check

# Frontend (when added)
npm install                      # Install dependencies
npm run dev                      # Start dev server
npm run build                    # Production build
npm test                         # Run tests
npm run lint                     # Lint
npm run typecheck                # Type check
```

## Code Style Guidelines

### Python
- Type hints **required** everywhere
- Prefer pure functions for analysis logic
- No business logic in API route handlers
- Keep configuration minimal and explicit
- Optimize for clarity over cleverness
- Separate concerns: ingest, analysis, API, UI

### TypeScript
- Strict mode enabled
- Explicit return types on functions
- Use interfaces for data structures
- Prefer `const` over `let`

### Imports
- Group: stdlib → third-party → local
- Sort alphabetically within groups
- Absolute imports preferred over relative

### Naming
- Python: `snake_case` for functions/variables, `PascalCase` for classes
- TypeScript: `camelCase` for functions/variables, `PascalCase` for classes/types
- Files: `snake_case.py`, `PascalCase.tsx`
- Constants: `UPPER_SNAKE_CASE`

### Error Handling
- Use exceptions for exceptional cases
- Return Result/Option types where appropriate
- Log errors with context
- Never swallow exceptions silently

### Testing
- Write tests for all non-trivial logic
- Test file naming: `test_*.py` or `*.test.ts`
- Arrange-Act-Assert structure
- Mock external dependencies

### Project Structure

```
backend/
  app/
    api/            # FastAPI routes
    core/           # Business logic
    models/         # Data models
    services/       # External integrations
    utils/          # Helpers
  tests/
frontend/
  src/
    components/     # React components
    api/            # API client
    types/          # TypeScript types
    utils/          # Helpers
```

## Key Principles

1. Local-first: No cloud services or authentication
2. Read-only: Never modify source DuckDB files
3. Cache derived data in Parquet separately
4. Discover schema dynamically (no fixed assumptions)
5. Hobby project with production-quality practices
