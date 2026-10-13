# Implementation Plan: Extended Timeline with Month-Range Filter

**Branch**: `007-extend-timeline-filter` | **Date**: 2026-10-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification `specs/007-extend-timeline-filter/spec.md`

## Summary

Remove the hard-coded "end of 2026" bound on the dashboard timeline and replace it with a rolling
12-month default window (current ISO week → week containing today + 1 year), plus an optional
manager-chosen month range (`from`/`to` as MM/YYYY). Week building, range resolution and month
parsing move into a new pure module `absence_dashboard/timeline.py`; `GET /api/dashboard` and
`POST /api/refresh` accept the range as query parameters and build only the visible weeks. Every
calendar week gets a year-unique `key` (`"2027-W05"`) and a year-bearing label, and cumul-risk /
sole-coverage entries are keyed on it so markers never collide across years. The Excel parser stops
assuming the file starts in the current year and instead infers the year from today's date and ISO
week validity — without this, today's 2026 file would be dated a year late (and crash on CW53) as
soon as 2027 begins. The frontend adds a small filter control group, remembers the applied range for
the session, hides phases fully outside the range, and shows a notice when the file has no data in
range. No new dependencies, no persisted-state changes.

## Technical Context

**Language/Version**: Python 3.10+ (venv currently 3.14) — no change.

**Primary Dependencies**: Flask, openpyxl (existing). No new backend or frontend dependencies.
Frontend remains vanilla JS (`absence_dashboard/static/main.js`), no build step.

**Storage**: None changed. `state/state.json` and `launch_config.json` untouched; the time filter is
session-only (held in the browser page) by confirmed spec assumption.

**Testing**: pytest, two-tier convention — new `tests/unit/test_timeline.py` (pure week/range
logic), extended `tests/unit/test_parser.py` (year inference), updated
`tests/unit/test_cumul_groups.py` (week keys), and `tests/integration/test_app.py` (query
parameters, 400s, payload fields, cross-year markers). Tests written and confirmed failing first
(Constitution II).

**Target Platform**: Unchanged — local Flask app and the Windows/Citrix standalone package.

**Project Type**: Single-project web application (Flask backend + vanilla JS frontend), in-place
modification.

**Performance Goals**: 24-month range renders in < 2 s with the usual team size (SC-003); see
research R9 — linear scaling of the existing approach is sufficient.

**Constraints**: Zero network calls (feature 005) preserved. Default range must roll with the
current date and be independent of file extent (FR-007).

**Scale/Scope**: ~1 new module (`timeline.py`, ~60 lines), edits to `parser.py`, `cumul_groups.py`,
`app.py`, `index.html`, `main.js`, `style.css`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I — Spec-First Development
**PASS** — `spec.md` complete (3 prioritized stories, FR-001–FR-014, SC-001–SC-005); default range
and remaining defaults clarified on 2026-10-13; no `[NEEDS CLARIFICATION]` markers.

### Principle II — Test-Driven Development (NON-NEGOTIABLE)
**PASS (plan-level)** — every behaviour has a planned failing test first: week inclusion / ISO 53 /
year boundaries / month parsing (unit), parser year inference including the "January 2027 + CW53"
crash case (unit), `week_key` risk keying (unit), and query-param validation, default window, cross-
year marker isolation, filtered-vs-unfiltered marker equality (integration). The existing
`test_calendar_weeks_ends_at_cw53_2026` is replaced, not deleted silently.

### Principle III — Data Integrity & Accuracy
**PASS** — read-only view change; absence records are not created/edited. The parser change
*improves* accuracy (prevents absences being dated in the wrong year). Risk computation still uses
full, unclipped absence blocks (FR-010).

### Principle IV — Privacy & Compliance
**PASS** — no new personal data, no new transmission, nothing persisted.

### Principle V — Simplicity & Maintainability
**PASS** — one week-builder serves both default and filtered views; one week identity (`key`)
replaces the ambiguous `week_number` in risk entries rather than adding a parallel field. Year
inference is a small bounded search (3 candidates) instead of a new config setting users must
maintain.

**Post-design re-check (after Phase 1)**: PASS — design artifacts introduce no persisted schema, no
new services, and no additional patterns. Contract documented in `contracts/` per Development
Standards.

## Project Structure

### Documentation (this feature)

```text
specs/007-extend-timeline-filter/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── dashboard-time-range-api.md   # Phase 1 output
└── tasks.md             # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
absence_dashboard/
├── timeline.py          # NEW — pure, no I/O:
│                        #   parse_month("MM/YYYY") -> (year, month)        [ValueError]
│                        #   default_range(today) -> (start, end)
│                        #   resolve_range(from_s, to_s, today) -> (start, end, is_default) [ValueError]
│                        #   build_calendar_weeks(start, end) -> list[dict]  (adds "key", year label)
├── parser.py            # MODIFIED: build_date_map(ws, year=None, today=None) infers start year
│                        #   (research R4); parse_members(ws, date_map=None) reuses a given map
├── cumul_groups.py      # MODIFIED: compute_cumul_risk_weeks / compute_sole_coverage_weeks
│                        #   return week keys ("YYYY-Www") instead of week numbers
├── app.py               # MODIFIED: _build_calendar_weeks/_last_iso_week removed;
│                        #   _load_excel also returns DATA_RANGE; _assemble_dashboard(app, start, end,
│                        #   is_default) emits time_range, data_in_range, week_key entries;
│                        #   /api/dashboard + /api/refresh parse from/to (400 on error)
└── static/
    ├── index.html       # MODIFIED: header time-filter group (#time-from, #time-to, Apply, Reset,
    │                    #   #time-range-status, #time-error)
    ├── main.js          # MODIFIED: timeFilter session var + dashboardUrl(); all keying on
    │                    #   cw.key / week_key; tooltips use week labels; hide phases fully out of
    │                    #   range; data_in_range notice; client-side MM/YYYY validation
    └── style.css        # MODIFIED: time-filter control styling

tests/
├── unit/
│   ├── test_timeline.py       # NEW
│   ├── test_parser.py         # MODIFIED — year inference cases
│   └── test_cumul_groups.py   # MODIFIED — week-key return values, cross-year weeks
└── integration/
    └── test_app.py            # MODIFIED — calendar-week tests rewritten for rolling default;
                               #   new TestTimeRangeFilter class; risk tests use week_key
```

**Structure Decision**: In-place change in the existing single Flask project. The only new module,
`timeline.py`, follows the established pattern of pure business-logic modules
(`phases_manager.py`, `cumul_groups.py`) with matching unit tests.

## Complexity Tracking

*No Constitution Check violations — intentionally empty.*
