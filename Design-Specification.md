# LMU Telemetry Analyzer — Design Spec (Option B)

## Introduction

LMU (Le Mans Ultimate) is a PC Sim Racing Game with extensive Telemetry Data as duckdb files.

### Goal

Build a **local-first telemetry analysis tool** for *Le Mans Ultimate* that enables interactive inspection and comparison of driving data recorded in LMU's DuckDB telemetry files.

This is a **hobby project**, but built with **sound software engineering practices** so it remains maintainable, testable, and extensible without unnecessary complexity.

### Plan

Proposed to do the project in 4 steps:

1. **Access** — discover and read telemetry safely
2. **Inspect** — visualize and compare raw signals
3. **Interpret** — segment and quantify driving behavior
4. **Stabilize** — harden and prepare for future ideas

---

## Step 1 — Telemetry Discovery & Access

### Purpose

Establish **reliable access** to LMU telemetry data and define the project's **core data boundaries**, without assuming a fixed schema.

### Backend responsibilities

* Locate LMU telemetry files in a configured directory (auto-discovery with YAML config)
* Open and inspect DuckDB telemetry files in read-only mode
* Discover available sessions, laps, and signals dynamically
* Expose *what exists*, not interpretations of it

### High-level entities introduced

* **Session**: a single telemetry recording with metadata (track, car, driver, weather)
* **Lap**: a unit of driving within a session (start/end times, lap time, validity)
* **Signal**: a time-varying measurement with frequency and unit

### API (minimal)

* List available sessions
* Retrieve basic session metadata including available channels/events
* List laps belonging to a session

### Outcome of Step 1

The system can reliably:

* See telemetry recordings
* Identify sessions and laps
* Act as a read-only explorer of LMU telemetry data

---

## Step 2 — Signal Access & Visual Inspection

### Purpose

Enable **interactive inspection** of telemetry signals and basic lap comparison.

### Backend responsibilities

* Serve requested signals for a given lap with optional downsampling
* Support retrieving multiple laps for comparison
* Perform time-based alignment with normalized timestamps
* Support distance-based X-axis using Lap Dist normalization

### Frontend responsibilities

* Session and lap selection
* Interactive signal plots (overlayed laps)
* Fast iteration and visual feedback

### High-level entities extended

* **Signal slice**: a portion of a signal for a lap (timestamps, normalized time, distance)
* **Lap comparison**: target vs reference lap with normalized X-axis

### Outcome of Step 2

The user can:

* Plot key signals
* Overlay laps using time or distance alignment
* Visually identify differences and inconsistencies

---

## Step 3 — Track Segmentation & Derived Metrics

### Purpose

Introduce **domain interpretation** by structuring telemetry into meaningful driving segments with **two-tier caching** and **distance-based coordinates**.

### Backend responsibilities

* **Auto-select reference lap** using heuristics (fastest valid lap with clean steering/braking)
* **Detect track layout** automatically from steering curvature:
  - Corners (high curvature zones with entry/apex/exit points)
  - Straights (gaps between corners)
  - Complexes (adjacent corners merged)
* **Normalize Lap Dist** to monotonic 0..track_length coordinates (handles wrap-around)
* **Compute derived metrics per segment**:
  - Speed: entry, mid, exit, min, max, average
  - Time: segment duration, delta to reference lap
  - Technique: braking distance, throttle application, steering smoothness
* **Two-tier caching** (Parquet files in `./cache/`):
  - Tier 1: Track layouts per track (versioned, persistent)
  - Tier 2: Lap metrics per session/lap (invalidated on layout version change)

### Frontend responsibilities

* Display segment lists/tables
* Link segments to plots (click → zoom)
* Compare segment metrics between laps

### High-level entities introduced

* **Segment**: corner, straight, or complex with distance-based boundaries (start_dist, end_dist, entry/apex/exit points)
* **TrackLayout**: versioned track definition with segment list and reference lap info
* **SegmentMetrics**: per-segment derived measurements with time deltas

### Key Design Decisions

* **Distance-based segments**: All segment boundaries use track distance (meters from S/F) rather than time, enabling consistent comparison across laps
* **Read-only source**: Never write to DuckDB files; cache derived data separately in Parquet
* **Auto-reference**: Best lap selected automatically but user can override
* **Versioned layouts**: Layout version controls cache invalidation

### Outcome of Step 3

The tool answers:

* *Where* time is gained or lost per segment
* *Which* driving sections differ most between laps
* *How* driving technique differs (braking points, throttle application)

---

## Step 4a — Backend Hardening & Reliability

### Purpose

Stabilize the backend with API doc and health endpoints before building the frontend.

### Backend focus

* **API documentation**: Auto-generated Swagger/OpenAPI docs with FastAPI, including request/response examples
* **Health endpoints**: `/health` (liveness), `/ready` (readiness), and `/metrics` (basic telemetry stats) endpoints

### Outcome of Step 4a

A reliable backend with auto-generated API documentation, health monitoring endpoints.
Docs available at `/openapi.json`, `/docs` and `/redoc`

---

## Step 4b — Frontend Foundation & Client Code

### Purpose

Establish the frontend project foundation with type-safe client code consuming the documented API from Step 4a.

### Backend focus

* **Validation**: Ensure endpoints have Pydantic schemas and error responses documented

### Frontend focus (NEW)

* **Project setup**: Initialize React + TypeScript + ECharts project with Vite, configure strict TypeScript
* **Type generation**: Auto-generate TypeScript types from OpenAPI spec (consuming `/openapi.json` from 4a)
* **API client**: Build typed API client layer (React Query or similar) with error handling
* **Stub components**: Create placeholder components matching the target UI structure

### Outcome of Step 4b

A frontend project with auto-generated TypeScript types, typed API client, and component stubs ready for UI implementation.

---

## Step 4c — Frontend Implementation

### Purpose

Build the complete user interface on top of the stable backend and established client foundation.

### Frontend focus

* **Session browser**: Search, filter, and select sessions with lap lists
* **Signal visualization**: Interactive Apache ECharts plots with time/distance axis switching, lap overlay
* **Segment analysis**: Sortable segment table with metrics, time deltas, linking to plots
* **UX polish**: Loading states, progress indicators, error boundaries, responsive layout
* **Reduce coupling**: Basic state management, reusable components

### Extension points prepared

* New signal channels (add to channel lists, no schema changes)
* New metrics (extend SegmentMetrics, recalculate)
* New segment types (extend segment detection algorithm)
* Multi-session comparison (current design is per-session)

### Outcome of Step 4c

A complete, telemetry analysis tool:

* Reliable backend with caching and error handling
* Working frontend for interactive analysis
* Clean separation between raw telemetry and derived data
* Extensible architecture for future analyses

---

## Architecture Notes

### Coordinate Systems

* **Time**: Session timestamps (seconds from session start) — for raw signal display
* **Normalized Time**: Seconds from lap start — for lap-to-lap time comparison
* **Distance**: Meters from start/finish line — for segment boundaries and consistent comparison

### Caching Strategy

* **Source data**: Read-only DuckDB files (never cached, always current)
* **Tier 1 (Track Layout)**: Per track, versioned, persistent across sessions
* **Tier 2 (Lap Metrics)**: Per session/lap, invalidated when layout version changes
* **Storage**: Parquet files in local `./cache/` directory (configurable)

### Service Layer

```
API Routes (thin) → Core Services (business logic) → DuckDB Service (I/O)
                           ↓
                    Segment Cache (persistence)
```

* `TelemetryManager`: Session discovery and caching
* `SignalService`: Signal slicing and lap comparison
* `SegmentService`: Layout detection, metrics calculation, cache orchestration
* `TrackLayoutService`: Automatic segment detection from telemetry
* `MetricsCalculator`: Per-segment metric computation
* `ReferenceLapSelector`: Heuristic-based best lap selection
* `SegmentCache`: Two-tier Parquet persistence

---

## Data Boundaries

**Read-Only Contract**: The system never modifies source DuckDB files.

**Cache-Only Writes**: All derived data (layouts, metrics) written to separate cache directory.

**Dynamic Schema**: No assumptions about available signals — channels discovered at runtime.

**Local-First**: No cloud services, no external APIs, works entirely offline.
