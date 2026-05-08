# Implementation Plan: Absence Management Dashboard

**Branch**: `001-absence-dashboard` | **Date**: 2026-05-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/001-absence-dashboard/spec.md`

## Summary

Build a local Python web application that reads a date-grid `.xlsx` spreadsheet, visualises
planned absences per project member as a Gantt-style day-level timeline for the remainder of the
year, and lets the manager define dependencies, skill clusters, and named project phases in the
browser UI. Technical approach: Flask + openpyxl backend; vanilla HTML/CSS/JS frontend; local
`config.json` for UI config persistence. Day sub-columns display single-character weekday labels
(M/T/W/T/F). Project phases render as horizontal banner rows above member rows.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: openpyxl 3.x (Excel parsing), Flask 3.x (local web server)
**Storage**: `config.json` on disk (UI-defined dependencies, skill clusters, and project phases)
**Testing**: pytest 7+ with Flask test client for API integration tests
**Target Platform**: Local development machine (macOS / Windows / Linux); accessed at
`localhost:5000` in a standard desktop browser
**Project Type**: Local web-service (single-user, no authentication required for v1)
**Performance Goals**: Full dashboard load ≤5 s for ≤50 project members; Excel refresh ≤5 s
**Constraints**: No containerisation; no mobile optimisation; `.xlsx` files only; single user v1
**Scale/Scope**: ≤50 project members; ~35–52 visible calendar weeks; single manager user

## Constitution Check

### Principle I — Spec-First Development
**PASS** — `spec.md` is complete with user stories (US1–US6), acceptance scenarios, functional
requirements, and measurable success criteria.

### Principle II — Test-Driven Development
**PASS (plan-level)** — Task sequencing enforces Red-Green-Refactor. All core algorithms and
new phase endpoints have concrete acceptance scenarios in the spec translatable to pytest cases.

### Principle III — Data Integrity & Accuracy
**JUSTIFIED DEVIATION** — Read-only visualisation dashboard; no write paths on absence records.
Accuracy upheld by tested interval-merge and cycle-detection algorithms. See Complexity Tracking.

### Principle IV — Privacy & Compliance
**JUSTIFIED DEVIATION** — Localhost-only, single authorized user. `config.json` stores only
names, cluster assignments, and phase date ranges — no sensitive personal data. See Complexity
Tracking.

### Principle V — Simplicity & Maintainability
**PASS** — Stack unchanged: Python stdlib + openpyxl + Flask + vanilla JS. Project phases
follow the same CRUD pattern as clusters; no new abstractions introduced.

## Project Structure

### Documentation (this feature)

```
specs/001-absence-dashboard/
├── plan.md              # This file
├── research.md          # Phase 0 — technical decisions
├── data-model.md        # Phase 1 — entity definitions (includes ProjectPhase)
├── quickstart.md        # Phase 1 — installation and run instructions
├── contracts/
│   └── api.md           # Phase 1 — REST API contract (includes phase endpoints)
└── tasks.md             # Phase 2 — /speckit-tasks output
```

### Source Code (repository root)

```
absence_dashboard/
├── app.py               # Flask entry point; CLI arg parsing; route registration
├── models.py            # Dataclasses: ProjectMember, AbsencePeriod, MergedBlock,
│                        #   Dependency, SkillCluster, ProjectPhase, UIConfig, CalendarWeek
├── excel_reader.py      # openpyxl parsing; builds per-person absence day sets
├── absence_merger.py    # Interval-merge algorithm
├── dependency_graph.py  # Dependency CRUD + DFS cycle detection + bottleneck computation
├── cluster_manager.py   # Skill cluster CRUD
├── phases_manager.py    # Project phase CRUD (name, start_date, end_date)
├── calendar_utils.py    # ISO week enumeration; CW-to-date mapping; display labels
├── config_store.py      # Load/save config.json (dependencies, clusters, phases)
└── requirements.txt     # openpyxl, flask

frontend/
├── index.html           # Single-page dashboard shell
├── css/
│   └── dashboard.css    # Gantt grid layout; absence/risk/bottleneck/phase styling
└── js/
    ├── dashboard.js     # Gantt table render; phase banner rows; absence/at-risk/bottleneck
    ├── dependencies.js  # Add/remove dependency UI panel
    ├── clusters.js      # Add/view/remove skill-cluster UI panel
    └── phases.js        # Add/view/remove project phase UI panel

tests/
├── test_excel_reader.py
├── test_absence_merger.py
├── test_dependency_graph.py
├── test_cluster_manager.py
├── test_phases_manager.py
├── test_calendar_utils.py
└── test_api.py          # Flask test-client integration tests (all API routes)
```

**Structure Decision**: Flat single-project layout with one module per concern. `phases_manager.py`
follows the exact same pattern as `cluster_manager.py`. The `config_store.py` schema gains a
`"phases"` array alongside `"dependencies"` and `"clusters"`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Principle III — no audit trail | Dashboard is read-only; absence records live in the Excel file | Adding write paths + audit log is outside scope and out of proportion for v1 |
| Principle IV — no encryption at rest | `config.json` stores only names, cluster assignments, and phase dates; no medical/sensitive data; localhost-only single user | Encryption requires key management with no practical security benefit for a local single-user tool |
