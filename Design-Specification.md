# LMU Telemetry Analyzer — Design Spec (Option B)

## Introduction

LMU (Le Mans Ultimate) is a PC Sim Racing Game with extensive Telemetry Data as duckdb files.

### Goal

Build a **local-first telemetry analysis tool** for *Le Mans Ultimate* that enables interactive inspection and comparison of driving data recorded in LMU’s DuckDB telemetry files.

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

Establish **reliable access** to LMU telemetry data and define the project’s **core data boundaries**, without assuming a fixed schema.

### Backend responsibilities

* Locate LMU telemetry files in a configured directory
* Open and inspect DuckDB telemetry files
* Discover available sessions, laps, and signals dynamically
* Expose *what exists*, not interpretations of it

### High-level entities introduced

* **Session**: a single telemetry recording
* **Lap**: a unit of driving within a session
* **Signal**: a time-varying measurement

### API (minimal)

* List available sessions
* Retrieve basic session metadata
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

* Serve requested signals for a given lap
* Support retrieving multiple laps for comparison
* Perform minimal alignment (time-based only)

### Frontend responsibilities

* Session and lap selection
* Interactive signal plots (overlayed laps)
* Fast iteration and visual feedback

### High-level entities extended

* **Signal slice**: a portion of a signal for a lap
* **Lap comparison**: target vs reference lap

### Outcome of Step 2

The user can:

* Plot key signals
* Overlay laps
* Visually identify differences and inconsistencies

---

## Step 3 — Track Segmentation & Derived Metrics

### Purpose

Introduce **domain interpretation** by structuring telemetry into meaningful driving segments.

### Backend responsibilities

* Segment laps into logical driving sections (e.g. corners)
* Compute simple, explainable derived metrics per segment
* Persist derived data separately from raw telemetry

### Frontend responsibilities

* Display segment lists/tables
* Link segments to plots (click → zoom)
* Compare segment metrics between laps

### High-level entities introduced

* **Segment**: a meaningful subdivision of a lap
* **Metric**: a derived numeric description of driving behavior

### Outcome of Step 3

The tool answers:

* *Where* time is gained or lost
* *Which* driving sections differ most between laps

---

## Step 4 — Hardening & Extension Points

### Purpose

Stabilize the system and prepare for future growth without redesign.

### Backend focus

* Cache derived data efficiently
* Make signal and metric discovery explicit
* Improve alignment strategies where data allows

### Frontend focus

* Improve usability and responsiveness
* Reduce coupling to backend internals
* Preserve flexibility for new analyses

### Outcome of Step 4

A clean, extensible foundation that supports:

* Additional signals
* New metrics
* More advanced analyses later
