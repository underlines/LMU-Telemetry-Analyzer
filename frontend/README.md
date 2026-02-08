# LMU Telemetry Analyzer - Frontend

React + TypeScript frontend for the LMU Telemetry Analyzer.

## Tech Stack

- **React 19** with TypeScript (strict mode)
- **Vite** for development and building
- **MUI (Material-UI)** for components and theming
- **TanStack Query (React Query)** for data fetching and caching
- **Apache ECharts** for telemetry visualizations
- **React Router** for client-side routing

## Project Structure

```
src/
  api/          # API client and services
    client.ts   # Axios instance with interceptors
    services.ts # API service functions
  components/   # Reusable UI components
    Layout.tsx      # App shell with navigation
    SignalPlot.tsx  # ECharts telemetry plot
    SegmentTable.tsx # Data grid for segment metrics
  hooks/        # Custom React hooks
    useApi.ts   # React Query hooks for all API endpoints
  pages/        # Route-level page components
    Dashboard.tsx      # Home/dashboard page
    SessionBrowser.tsx # Session list with search
    SessionDetail.tsx  # Session info and lap list
    LapDetail.tsx      # Lap analysis with signals/segments
  types/        # TypeScript type definitions
    api.ts      # API types (auto-generated from OpenAPI)
  utils/        # Utility functions
```

## Development

### Prerequisites

- Node.js 18+ with npm
- Backend running on http://localhost:8000

### Setup

```bash
cd frontend
npm install
```

### Run Development Server

```bash
npm run dev
```

The app will be available at http://localhost:5173

Vite is configured to proxy API calls to the backend at http://localhost:8000

### Generate Types from OpenAPI

When the backend API changes, regenerate TypeScript types:

```bash
# Ensure backend is running first
npm run generate-types
```

This fetches `/openapi.json` from the backend and generates `src/types/api.ts`

### Build for Production

```bash
npm run build
```

### Type Checking

```bash
npm run typecheck
```

### Linting

```bash
npm run lint
```

## Features

### Step 4b (Current)

- [x] Vite + React + TypeScript project setup
- [x] MUI theming with dark mode
- [x] API client with Axios
- [x] React Query integration with caching
- [x] Type-safe API hooks
- [x] React Router setup with routes:
  - `/` - Dashboard
  - `/sessions` - Session browser
  - `/sessions/:sessionId` - Session detail
  - `/sessions/:sessionId/laps/:lapNumber` - Lap analysis
- [x] Component stubs for Step 4c
- [x] ECharts integration for signal plotting

### Step 4c (Upcoming)

- [ ] Session search and filtering
- [ ] Lap comparison UI
- [ ] Segment highlighting on plots
- [ ] Time delta visualization
- [ ] Responsive layout improvements
- [ ] Loading states and error boundaries

## API Integration

The frontend communicates with the FastAPI backend through these endpoints:

- **Sessions**: `GET /api/v1/sessions`, `GET /api/v1/sessions/:id`, `GET /api/v1/sessions/:id/laps`
- **Signals**: `GET /api/v1/signals/sessions/:id`, `GET /api/v1/signals/sessions/:id/laps/:lapNumber`
- **Segments**: `GET /api/v1/segments/sessions/:id/layout`, `GET /api/v1/segments/sessions/:id/laps/:lapNumber/segments`
- **Health**: `GET /health`, `GET /ready`, `GET /metrics`

All API calls are typed and use React Query for caching and state management.

## Configuration

Vite proxy configuration in `vite.config.ts`:

```typescript
server: {
  port: 5173,
  proxy: {
    '/api': 'http://localhost:8000',
    '/openapi.json': 'http://localhost:8000',
    '/health': 'http://localhost:8000',
    // ...etc
  }
}
```

This allows the frontend to make requests to `/api/v1/sessions` which gets proxied to the backend.
