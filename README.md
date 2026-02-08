# LMU Telemetry Analyzer

Local-first telemetry analysis tool for Le Mans Ultimate (LMU) racing game. Analyze driving data from DuckDB telemetry files with interactive signal plots, track segmentation, and lap comparisons.

## Stack

**Backend**: Python 3.11+ • FastAPI • DuckDB • Pydantic

**Frontend**: React 19 • TypeScript • Vite • MUI • ECharts • TanStack Query

## Project Structure

```
├── backend/          # FastAPI application
│   ├── app/
│   │   ├── api/      # REST endpoints (sessions, signals, segments, health)
│   │   ├── core/     # Business logic (telemetry, signals, segments)
│   │   ├── models/   # Pydantic schemas
│   │   └── services/ # DuckDB I/O
│   └── tests/
├── frontend/         # React application
│   ├── src/
│   │   ├── api/      # API client + services
│   │   ├── components/ # Reusable UI (Layout, SignalPlot, SegmentTable)
│   │   ├── hooks/    # React Query hooks (useApi.ts)
│   │   ├── pages/    # Route components (Dashboard, SessionBrowser, etc.)
│   │   └── types/    # TypeScript definitions
│   └── package.json
├── config.yaml       # Telemetry directory configuration
└── cache/            # Generated track layouts & metrics (Parquet)
```

## Quick Start

### Prerequisites

- Python 3.11+ with `uv`
- Node.js 18+ with `npm`
- LMU telemetry files (`.duckdb`) in configured directory

### Backend

```bash
cd backend
uv sync                          # Install dependencies
uv run uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev                      # Starts on http://localhost:3000
```

Vite proxies `/api` to backend automatically.

## Main Entry Points

### Backend

- **Main**: `backend/app/main.py` - FastAPI app factory
- **Routes**: `backend/app/api/` - Sessions, signals, segments, health
- **Models**: `backend/app/models/` - Pydantic schemas
- **Config**: `backend/app/core/config.py` - Reads `config.yaml`

### Frontend

- **Entry**: `frontend/src/main.tsx` - React root
- **App**: `frontend/src/App.tsx` - Router & providers
- **API**: `frontend/src/api/services.ts` - Service layer
- **Hooks**: `frontend/src/hooks/useApi.ts` - React Query integration

## Development Workflow

1. Place `.duckdb` telemetry files in the directory specified in `config.yaml`
2. Start backend (`:8000`)
3. Start frontend (`:3000`)
4. Browse sessions at http://localhost:3000/sessions

## Scripts

**Backend**:
```bash
uv run pytest           # Run tests
uv run ruff check .     # Lint
uv run ruff format .    # Format
uv run mypy .           # Type check
```

**Frontend**:
```bash
npm run dev             # Dev server
npm run build           # Production build
npm run typecheck       # TypeScript check
npm run generate-types  # Regenerate from OpenAPI
```

## Key Features

- **Session Discovery**: Auto-discovers telemetry files
- **Signal Visualization**: ECharts plots with time/distance axis
- **Track Segmentation**: Auto-detects corners/straights from steering data
- **Lap Comparison**: Overlay laps with time deltas
- **Two-Tier Caching**: Track layouts (Tier 1) + Lap metrics (Tier 2) in `./cache/`

## Architecture

```
API Routes → Core Services → DuckDB (read-only)
                    ↓
            Cache (Parquet)
```

Read-only on source data. All derived data cached separately.
