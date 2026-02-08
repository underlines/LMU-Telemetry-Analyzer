# AGENTS.md — LMU Telemetry Analyzer

Local-first telemetry analysis tool for Le Mans Ultimate (LMU) racing game.

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, uv only, no system wide python, DuckDB
- **Frontend**: React + TypeScript (future)
- **Testing**: pytest with TestClient for FastAPI

## Commands

```bash
# Setup
cd backend
uv sync                           # Install dependencies
uv add <package>                  # Add new dependency
uv run python -c "..."            # Run python directly

# Testing
uv run pytest                     # Run all tests
uv run pytest -v                  # Verbose
uv run pytest tests/test_file.py  # Single test file
uv run pytest tests/test_file.py::TestClass::test_method  # Single test
uv run pytest -k "pattern"        # Run matching tests
uv run pytest --tb=short -x       # Short tracebacks, stop on first failure

# Lint & Format
uv run ruff check .               # Check linting
uv run ruff check --fix .         # Fix auto-fixable
uv run ruff format .              # Format code
uv run mypy .                     # Type check

# Pre-commit (run all)
uv run ruff check . && uv run mypy . && uv run pytest tests/ -q
```

## Code Style

### Python

**Type Hints** — Required on all functions:
```python
from __future__ import annotations
from collections.abc import Iterator

def process(data: dict[str, Any]) -> list[Result]:
    ...

@contextmanager
def connect() -> Iterator[Connection]:
    ...
```

**Imports** — Group and sort:
```python
# 1. Stdlib (alphabetically)
from collections.abc import Iterator
from pathlib import Path
from typing import Any

# 2. Third-party (alphabetically)
import duckdb
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

# 3. Local (alphabetically)
from app.core.config import get_telemetry_path
from app.models.session import Lap
```

**Naming**:
| Item | Convention |
|------|------------|
| Functions/variables | `snake_case` |
| Classes | `PascalCase` |
| Constants | `UPPER_SNAKE_CASE` |
| Private | `_leading_underscore` |
| Files | `snake_case.py` |

**Functions**:
- Keep under 30 lines
- Early returns over nested conditionals
- Pure functions preferred for analysis

**Classes**:
- `@dataclass` for data containers
- Pydantic models for API boundaries
- Private methods prefixed with `_`

**Error Handling**:
```python
def process_data(data: dict) -> Result:
    if not data:
        raise ValueError("Data cannot be empty")
    
    try:
        result = risky_operation(data)
        return result
    except SpecificError as e:
        logger.error(f"Operation failed: {e}")
        raise ProcessingError("Could not process") from e
```

- Use exceptions for exceptional cases only
- Log errors with context
- HTTP exceptions in routes only
- Convert domain errors to HTTP exceptions in API layer

### TypeScript

- Strict mode enabled
- Explicit return types on all functions
- Use interfaces for data structures
- Prefer `const` over `let`
- Destructure props in function parameters
- Components: `PascalCase.tsx`
- Utils: `camelCase.ts`

## Project Structure

```
backend/
  app/
    api/            # FastAPI routes (thin)
    core/           # Business logic
    models/         # Pydantic models
    services/       # External integrations (DuckDB)
    utils/          # Pure helpers
  tests/
    test_*.py       # Mirror app structure

frontend/ (future)
  src/
    components/     # React components
    api/            # API client
    types/          # TypeScript types
    utils/          # Helpers
```

## Testing

```python
# Test file: tests/test_module.py
class TestFeature:
    """Test class naming: Test*"""
    
    def test_does_something(self) -> None:
        """Test function naming: test_*"""
        # Arrange
        data = create_test_data()
        
        # Act
        result = process(data)
        
        # Assert
        assert result.value == expected
```

- Mock external I/O (filesystem, DuckDB)
- Test edge cases and error paths
- Use FastAPI TestClient for API tests

## Key Principles

1. **Local-first**: No cloud services or external APIs
2. **Read-only**: Never modify source DuckDB files
3. **Cache separately**: Derived data to Parquet, never back to source
4. **Dynamic discovery**: Query schema at runtime
5. **Fail fast**: Validate inputs early
6. **No premature abstraction**: Solve current problem well

## Ruff/Mypy Config

From `pyproject.toml`:
- Line length: 100
- Target Python: 3.11
- Quote style: double
- Indent: spaces
- Strict mypy enabled
