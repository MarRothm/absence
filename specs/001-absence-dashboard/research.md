# Research: Absence Management Dashboard

**Phase 0 output** | **Date**: 2026-05-07 | **Plan**: [plan.md](plan.md)

---

## Decision 1: Backend Framework

**Decision**: Flask 3.x

**Rationale**: Flask is the simplest Python web framework that still provides routing, JSON
responses, and static file serving — everything this tool needs. It requires minimal boilerplate,
is universally known, and has no asynchronous complexity for a single-user local tool.

**Alternatives considered**:
- *FastAPI*: Excellent for larger APIs with async needs, auto-docs, and strict typing. Overkill
  for a single-user local tool; adds Pydantic validation overhead without benefit here.
- *Streamlit*: Very fast to build dashboards but has limited layout control. The custom
  calendar-week grid with bottleneck and cluster visual indicators exceeds Streamlit's styling
  flexibility without significant workarounds.
- *Django*: Far too heavy; ORM, admin, migrations not needed.

---

## Decision 2: Excel Parsing Library

**Decision**: openpyxl 3.x

**Rationale**: openpyxl reads `.xlsx` files natively in pure Python without requiring a pandas
or numpy dependency chain. It provides direct cell access, column iteration by header name, and
is sufficient for reading tabular absence data. Lighter and faster to install than pandas for this
use case.

**Alternatives considered**:
- *pandas + openpyxl*: `pd.read_excel()` is convenient but adds ~50 MB of dependencies (numpy,
  pandas) for functionality we don't need. Column filtering and date parsing are trivial with plain
  openpyxl.
- *xlrd*: Only supports legacy `.xls` format; dropped `.xlsx` support in v2. Not suitable.

---

## Decision 3: Frontend Visualization

**Decision**: Custom HTML `<table>` with day-level `<td>` cells per calendar week (vanilla JS,
no library)

**Rationale**: The timeline is a fixed grid: rows = project members, columns = calendar weeks
each subdivided into 5 Mon–Fri day sub-columns (clarification 2026-05-08). Each `<td>` is
either empty (present), absent (colored block), at-risk (highlighted week band), or
bottleneck-absent (distinct color). An HTML `<table>` with a two-row header (CW label spanning
5 columns, then individual day names) and one `<tr>` per member is the simplest structure that
naturally expresses this layout. Continuous absence bars across week boundaries are achieved by
removing the inner border between adjacent absent `<td>` cells via CSS class toggling on the
first/last day of a span.

**Alternatives considered**:
- *vis-timeline*: Designed for event bars on a time axis, not a cell matrix. Cannot natively
  express day-level sub-columns within week groups without heavy customisation.
- *frappe-gantt*: Designed for project-task Gantt (tasks as rows). Adapting to person-week
  grid overrides its core assumptions.
- *FullCalendar*: Monthly/weekly calendar — not a multi-person row view.
- *D3.js*: Maximum flexibility but very high complexity; violates Principle V.

---

## Decision 4: State Persistence (Dependencies & Clusters)

**Decision**: Local JSON file (`state/state.json`)

**Rationale**: The only mutable state is UI-defined dependencies and skill clusters — both are
small, structured, and need to survive dashboard refreshes but not scale beyond one user. A JSON
file is human-readable, zero-infrastructure, trivially backed up, and does not require a database
engine. Flask reads it at startup and writes it on every mutation.

**Alternatives considered**:
- *Browser localStorage*: Would be lost if the user opens a different browser or clears storage.
  Not suitable for a tool expected to persist configuration across sessions reliably.
- *SQLite*: Reliable and ACID-compliant but significantly more complex for two tiny tables
  (dependencies: list of pairs; clusters: list of named sets). Violates Principle V.
- *In-memory only*: Lost on every restart. Ruled out by FR-012 (persist across refreshes).

---

## Decision 5: Calendar Week Calculation

**Decision**: Python `datetime.isocalendar()` (stdlib only)

**Rationale**: Python's standard library `datetime.isocalendar()` returns `(ISO_year, week, weekday)`
conforming to ISO 8601. No third-party library needed. The visible range is determined by finding
the current ISO week on load and iterating through all weeks to the last ISO week of 2026
(week 53, since 2026-12-31 falls in CW53).

**Approach**: Generate the list of `(year, week_number)` tuples on server startup. Each tuple
maps to a Monday-to-Sunday date range for cell overlap calculation.

---

## Decision 6: Dependency Cycle Detection

**Decision**: Depth-first search (DFS) with recursion-stack tracking

**Rationale**: The dependency graph is small (≤ 50 nodes). A standard DFS on the directed graph
detects cycles in O(V + E) time. When the user attempts to add a dependency A→B that would create
a cycle, the server runs DFS on the hypothetical graph before saving. If a cycle is found, it
returns a 409 Conflict with the cycle path in the error body.

**Implementation note**: Since Python has a default recursion limit and the graph is small,
an iterative DFS using an explicit stack avoids any recursion depth concern.

---

## Decision 7: Absence Merging Algorithm

**Decision**: Sort-then-sweep interval merge (standard algorithm)

**Approach**:
1. Sort all absence periods for a person by start date.
2. Initialize a running `current` interval = first period.
3. For each subsequent period: if it overlaps or is adjacent to `current` (start ≤ current.end + 1 day), extend `current.end`. Otherwise, emit `current` and start a new one.
4. Result: minimal list of non-overlapping intervals.

**Time complexity**: O(n log n) per person. More than sufficient for ≤ 50 members × typical
annual absence count.

---

## Decision 8: Excel Grid Layout & Column Mapping

**Decision**: Fixed-position column reading (confirmed via clarification; no header scan needed)

**Confirmed layout** (from spec clarifications, session 2026-05-07):
- **Row 1**: Calendar week labels (e.g., "KW18") — skipped by parser
- **Row 2**: Weekday names (Mon–Fri only; weekends absent from the file) — skipped by parser
- **Data rows**: Row 3 onward — one row per person
- **Column C** (index 3): "Projekt Migration" — filter column; only rows with cell value "x"
  (case-insensitive, stripped) are included
- **Column D** (index 4): "Team Mitglied " — person name; stripped before use as identity key
- **Columns A, B, E**: Other metadata; ignored by parser
- **Column F** (index 6): First working day = **April 27, 2026** (Monday, CW18)
- **Column F+n**: The nth working day after April 27, 2026 (Mon–Fri sequence; no weekends)

**Working-day offset calculation**: Since consecutive columns represent consecutive working days
(no weekend columns in the file), column index `c` (c ≥ 6) maps to the `(c − 6)`th working day
starting from 2026-04-27. Implementation uses a helper that iterates forward from 2026-04-27,
incrementing by 1 day and skipping Saturday/Sunday, to build a `column_index → date` mapping
once at parse time.

**Absence marker**: A cell value that, after `.strip().lower()`, equals `"x"` marks the person
as absent on that day. Any other value (empty, other text) means present.

**Rationale**: Column positions and the base date are confirmed facts, not assumptions. Fixed-
position reading is faster and simpler than header scanning. No header discovery logic needed.

**Alternatives considered**: Header-scan in row 1 — not applicable since row 1 contains CW
labels, not column headers. Pandas `read_excel` — adds 50 MB dependency chain for zero benefit.

---

## Decision 9: Day-Level Timeline Rendering & Continuous Bar Across Week Boundaries

**Decision**: HTML `<table>` with one `<td>` per working day; continuous absence bar implemented
via CSS border suppression between adjacent absent cells.

**Approach**:
- The table header has two rows: row 1 has one `<th colspan="5">` per CW, displaying the label
  `"CW[N] | D Mon"` (e.g., `"CW22 | 25 May"` — CW number and the Monday date as day-of-month +
  abbreviated month name; clarification 2026-05-08); row 2 has one `<th>` per working day
  showing only the weekday label (Mon / Tue / Wed / Thu / Fri) without individual dates
  (clarification 2026-05-08).
- Each data row has one `<td>` per working day for the full range CW19–CW53.
- The backend sends `merged_blocks` as `{start, end}` date pairs. The frontend maps each date to
  its `<td>` position and applies CSS classes: `absent-start`, `absent-mid`, `absent-end` (or
  `absent-single` for a single-day span).
- CSS removes left/right borders between adjacent absent cells (`absent-mid` has no left or right
  border; `absent-start` has no right border; `absent-end` has no left border) — creating a
  visually unbroken bar across week column boundaries.
- At-risk bands are week-granular: all 5 `<td>` cells of a week receive the `at-risk` class
  if the dependent person's dependency is absent on any day in that week (clarification
  2026-05-08).

**Rationale**: Pure CSS solution — no canvas, no SVG, no library. Works reliably across all
desktop browsers. The border-suppression trick is a well-known pattern for contiguous cell
highlighting in HTML tables.

**Alternatives considered**:
- *CSS `background` gradient spanning cells*: Not possible across separate `<td>` elements
  without JavaScript measurement of pixel positions.
- *Canvas/SVG overlay*: Accurate but adds JavaScript complexity for hit-testing, resizing, and
  accessibility; violates Principle V.

---

## Decision 10: Project Phase Banner Rows

**Decision**: Render each project phase as a grid row placed above all member rows, spanning
only the day-columns covered by the phase's start/end dates. Use a distinct `phase-banner` CSS
class on those cells and show the phase name as text in the first occupied cell.

**Rationale**: Reusing the existing day-cell grid structure requires zero new layout primitives.
Phase cells outside the date range remain empty; cells inside receive the phase colour. Multiple
phases stack naturally as consecutive rows before the first member row. The frontend already
handles cluster-separator rows with a similar pattern.

**Alternatives considered**: Absolute-positioned overlay (requires pixel measurement, breaks on
scroll/resize); dedicated header section (adds layout complexity when phase count is variable).

---

## Decision 12: Inline Edit UX Pattern for Management Panels

**Decision**: Inline row-expansion — clicking an Edit button on an existing dependency, cluster,
or phase expands that list row into editable fields in place, with explicit Save and Cancel buttons.

**Rationale**: Keeps the user in context (no focus shift to a modal), is the lightest DOM
manipulation (toggle a CSS class to expand/collapse), and unifies edit behaviour across all three
panels with one reusable pattern. Explicit Save/Cancel makes the commit boundary clear, which is
important given that Save triggers server-side validation (cycle detection, date range, duplicate
name) and may return an inline error that the user needs to correct without losing their edits.

**Validation on Save**: If the API returns a 4xx error, the edit row stays open and the error
message is displayed inline below the affected field(s). No data is modified until the server
confirms success (FR-023).

**API mapping**:
- Dependencies: new `PUT /api/dependencies` — sends old and new (from, to) pairs; atomically
  replaces the dependency, re-runs cycle detection.
- Clusters: extended `PUT /api/clusters/{name}` — now accepts optional `new_name` in addition to
  `members`; handles rename atomically.
- Phases: new `PUT /api/phases/{name}` — sends new name, start_date, end_date; validates dates
  and uniqueness.

**Alternatives considered**:
- *Modal/dialog*: More visual interruption; requires focus management and overlay CSS. No benefit
  over inline expansion for small forms with 1–3 fields.
- *Side panel*: More complex layout coordination (panel + list must stay in sync); overkill for
  forms this simple.
- *Auto-save on blur*: Eliminates the discard path; makes validation error recovery awkward when
  the user clicks away mid-edit.

---

## Decision 13: SharePoint URL Download

**Decision**: Detect URL by `http://`/`https://` scheme prefix; append `?download=1` to the share
URL and fetch the file with `requests.get()` (anonymous, no auth headers); write the response body
to a `tempfile.NamedTemporaryFile` and pass that path to `openpyxl.load_workbook()`.

**Rationale**: SharePoint "anyone with the link" share URLs (e.g.,
`https://company.sharepoint.com/:x:/s/site/...`) redirect to the file content when `?download=1`
is appended. `requests` follows redirects by default. Writing to a temp file avoids holding the
entire response in memory and reuses the existing `openpyxl.load_workbook(filepath)` call
unchanged. The temp file is deleted after parsing completes. On refresh, `data_fetcher.py` re-runs
the fetch so the latest version of the file is always used.

**Error handling**: If `requests.get()` raises `ConnectionError` or returns a non-2xx status, the
application exits with a clear error message at startup (same path as a missing local file per
FR-016). On refresh, the error is returned as a 500 response (same as a local file read failure).

**Alternatives considered**:
- *`urllib.request`*: Stdlib, but does not follow all redirect chains reliably for SharePoint CDN
  URLs; less ergonomic error handling.
- *`sharepoint` / `Office365-REST-Python-Client`*: Requires authentication setup; not appropriate
  for anonymous public shares and adds large dependency chain.

---

## Decision 11: Weekday Label Single-Character Revert

**Decision**: Day sub-column headers use `["M", "T", "W", "T", "F"]` (single characters),
reverting the three-letter abbreviations.

**Rationale**: The CW column header already shows the Monday date (`"CW22 | 25 May"`), providing
date context. Single characters keep narrow sub-columns uncluttered — the duplicate "T" is a
universally understood calendar convention.

**Alternatives considered**: Three-letter `Mon/Tue/…` — rejected by explicit user clarification.
