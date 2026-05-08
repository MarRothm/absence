# Feature Specification: Absence Management Dashboard

**Feature Branch**: `001-absence-dashboard`
**Created**: 2026-05-07
**Status**: Draft
**Input**: User description: "I have an input Excel Spreadsheet where project members document their planned absences. I need graphical dashboard that shows per calendar week for the rest of the year absences. Per team member one line. Duplicates are resolved in a way that absences are combined but only one line per person. I want to add dependencies between people and visualize this."

## Clarifications

### Session 2026-05-08

- Q: How should a partial-week absence be visually represented in the calendar-week-based timeline? → A: Expand each calendar-week column into 5 sub-columns (Mon–Fri); each day is individually marked as absent or present — exact day-level granularity. A person absent fewer than 5 days in a given week must not appear as fully absent for that week.
- Q: Should the at-risk dependency indicator match day-level or week-level granularity? → A: Week-level: if a depended-on person is absent any day in a given calendar week, the dependent person's entire week (all 5 day sub-columns) is marked at-risk for that CW.
- Q: When a merged absence spans multiple consecutive weeks, how should it appear in the day-column layout? → A: One continuous visual bar stretching across all absent day sub-columns regardless of week boundaries — a single unbroken block (e.g., CW22 Thu–Fri and CW23 Mon–Wed render as one connected bar).
- Q: How should the Monday date be formatted in the calendar week column header? → A: English short format — "CW22 | 25 May" (CW number followed by the day number and abbreviated month name of that Monday).
- Q: Should individual day sub-columns also display their specific dates? → A: No — only the CW header shows the Monday date; day sub-columns display only the weekday label (Mon/Tue/Wed/Thu/Fri) without individual dates.
- Q: What single-character labels should day sub-columns use? → A: M, T, W, T, F — one character per day (Mon→M, Tue→T, Wed→W, Thu→T, Fri→F); reverting the three-character abbreviations introduced earlier.
- Q: How should project phases be displayed in the timeline? → A: Horizontal banner row above all member rows, spanning the phase's full date range across day-columns; consistent with the CW header row pattern.
- Q: Should member cells within a phase date range receive additional visual treatment? → A: No — the phase banner alone communicates criticality; absence and at-risk cell colors render unchanged.
- Q: How does the manager create and manage project phases? → A: Dashboard UI panel (same pattern as dependencies and clusters); phase name and start/end date range entered in the UI; persisted in config.json alongside other UI-defined config.
- Q: Can two project phases overlap in their date ranges? → A: Yes — overlapping phases are allowed; each renders as a separate stacked banner row in the timeline.

### Session 2026-05-07

- Q: Which people appear on the dashboard — all spreadsheet rows or a filtered subset? → A: Only team members marked with "x" in the "Projekt Migration" column of the Excel spreadsheet.
- Q: Where are person-to-person dependencies defined? → A: Dependencies are managed interactively in the dashboard UI (not stored in the Excel file or a separate config file).
- Q: How should high-risk members be highlighted? → A: Bottleneck members (those depended on by 2+ others) should be visually marked on the dashboard.
- Q: How should substitutability be represented? → A: Project members who can do the same work should be grouped into skill clusters, visible in the dashboard layout.
- Q: How is the dashboard delivered and run? → A: Local web application — the manager runs a command and opens `localhost:<PORT>` in a standard desktop browser.
- Q: If one person has several rows in the Excel file with exactly the same name spelling, how should they appear? → A: Treat all rows with identical name spelling as the same person; combine all their absence periods and display exactly one row for that person in the dashboard.
- Q: What are the exact column header names in the Excel file for person name, absence start date, and absence end date? → A: The Excel file uses a date-grid layout (not start/end-date columns). Column D header is "Team Mitglied" (person name). Row 1 contains calendar week numbers; Row 2 contains weekday names (weekends are not present). Column F is the first dated column, representing April 27, 2026 (Monday). Absence data is encoded per individual working day in the grid cells, not as date-range pairs.
- Q: Which column contains "Projekt Migration" (the filter that selects project members)? → A: Column C.
- Q: What value in a grid cell indicates a person is absent on that day? → A: The literal text value "x" (case-insensitive) in the cell. Any other value or empty cell means the person is present.
- Q: How does the manager point the application at the Excel file? → A: Command-line argument at startup (e.g. `python app.py absences.xlsx`).
- Q: What is the preferred technology stack? → A: Python — openpyxl for Excel parsing, Flask or FastAPI for the local web server, browser-based frontend.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Absence Timeline View (Priority: P1)

A project manager opens the dashboard and sees a Gantt-style timeline of planned absences for
all project members marked with "x" in the "Projekt Migration" column of the Excel spreadsheet.
The view is organized by calendar week (CW) for the remaining weeks of the current year. Each
project member occupies exactly one row. Where a person has multiple overlapping or adjacent
absence entries, those are merged into a single continuous visual block on that person's row.

**Why this priority**: This is the core deliverable. Without this view, the tool has no value.
Every other user story builds on this foundation.

**Independent Test**: Load the dashboard with a sample Excel file where 3 of 5 people have "x"
in "Projekt Migration" and have overlapping absences. Verify exactly 3 rows are shown, absences
are correctly merged, and calendar weeks run from the current week through year-end.

**Acceptance Scenarios**:

1. **Given** an Excel file with 5 rows, 3 marked "x" in "Projekt Migration", each with 1–3
   absence entries,
   **When** the dashboard is loaded,
   **Then** exactly 3 rows are shown (one per project member), with absence blocks in the
   correct calendar weeks.

2. **Given** a project member has two overlapping absence periods (e.g., 2026-06-01 to 2026-06-10
   and 2026-06-08 to 2026-06-15),
   **When** the dashboard renders that person's row,
   **Then** a single merged absence block from 2026-06-01 to 2026-06-15 is shown.

3. **Given** a project member has no planned absences,
   **When** the dashboard is loaded,
   **Then** the person's row is still shown with an empty timeline.

4. **Given** the dashboard is loaded on 2026-05-07,
   **When** the timeline is displayed,
   **Then** only calendar weeks CW 19 (current week) through the final week of 2026 are shown;
   earlier weeks are hidden.

---

### User Story 2 - Dependency Visualization (Priority: P2)

A project manager uses the dashboard UI to define directed dependencies between project members
(e.g., "Person A's work is blocked when Person B is absent"). The dashboard visualizes these
as at-risk indicators on the dependent person's row for every calendar week where the depended-on
person is absent.

**Why this priority**: Dependency awareness turns a plain absence calendar into actionable risk
information — the core differentiator of this tool.

**Independent Test**: In the dashboard UI, create dependencies A→B and C→D. Load absences for B
and D. Verify A's and C's rows show "at risk" indicators in the weeks where B and D are absent.

**Acceptance Scenarios**:

1. **Given** Person A has a dependency on Person B (entered via dashboard UI), and B is absent on any day(s) within CW 23 (even just one day),
   **When** the dashboard renders CW 23,
   **Then** all 5 day sub-columns of Person A's CW 23 band are visually marked as "at risk".

2. **Given** no dependencies have been defined in the dashboard,
   **When** the dashboard is loaded,
   **Then** no risk indicators appear.

3. **Given** a dependency exists A→B, and B has no absence in CW 25,
   **When** the dashboard renders CW 25,
   **Then** Person A's row for CW 25 shows no risk indicator.

4. **Given** the dashboard stores dependencies between project members,
   **When** the manager opens the dependency management area in the UI,
   **Then** they can add, view, and remove dependencies using only names present in the
   loaded Excel data.

---

### User Story 3 - Bottleneck Marking (Priority: P3)

A project manager can see at a glance which project members are bottlenecks — people that two or
more other project members depend on. The dashboard marks these members visually so that the
manager immediately recognizes which absences pose the highest risk to the whole team.

**Why this priority**: Bottleneck identification makes dependency data actionable. Without it, the
manager must manually count incoming dependencies to spot the most critical people.

**Independent Test**: Define dependencies so that Person B is referenced by A and C. Verify that
B's row carries a distinct bottleneck marker that neither A nor C carries.

**Acceptance Scenarios**:

1. **Given** Person B is listed as a dependency by both Person A and Person C,
   **When** the dashboard renders,
   **Then** Person B's row is marked with a distinct bottleneck indicator; Persons A and C have
   no such indicator.

2. **Given** Person D is depended on by only one other person,
   **When** the dashboard renders,
   **Then** Person D does NOT receive a bottleneck indicator.

3. **Given** a bottleneck person is absent in CW 27,
   **When** the dashboard renders CW 27,
   **Then** all project members who depend on that bottleneck show at-risk indicators, AND the
   bottleneck's absence block is visually distinct from a non-bottleneck absence.

---

### User Story 4 - Skill Cluster Grouping (Priority: P4)

A project manager defines skill clusters — named groups of project members who can perform the
same type of work and can therefore substitute for each other. The dashboard displays project
members organized by their skill cluster, making it immediately visible whether a substitute is
available when a member is absent.

**Why this priority**: Skill clusters provide the substitutability context needed to distinguish
a critical risk (no one else can do the work) from a manageable absence (a cluster peer is
available). This makes the dependency and bottleneck information actionable.

**Independent Test**: Define a cluster "Backend" containing persons A, B, and C. Load absences
for B. Verify that the dashboard groups A, B, C together and that context makes it clear A and C
are available as substitutes.

**Acceptance Scenarios**:

1. **Given** a skill cluster "Backend" contains Persons A, B, and C,
   **When** the dashboard renders,
   **Then** A, B, and C are displayed as a contiguous group with the cluster name visible.

2. **Given** Person B (in cluster "Backend") is absent in CW 24,
   **When** the dashboard renders CW 24,
   **Then** the cluster grouping makes it visually clear that A and C are in the same cluster
   and are potentially available as substitutes.

3. **Given** a project member is not assigned to any skill cluster,
   **When** the dashboard renders,
   **Then** the member is shown without a cluster label (ungrouped section or "Unassigned").

4. **Given** the manager opens the skill cluster management area in the UI,
   **When** they define or edit a cluster,
   **Then** they can add or remove project members using only names present in the loaded Excel
   data, and the dashboard updates immediately.

---

### User Story 5 - Dashboard Refresh (Priority: P5)

A project manager can reload the dashboard after the Excel file has been updated to see the latest
absence data without restarting the application. All UI-defined dependencies and skill cluster
groupings are preserved across refreshes.

**Why this priority**: Absence data changes regularly. Refresh capability keeps the tool useful
without requiring the manager to re-enter all dependency and cluster configuration.

**Independent Test**: Define a dependency and a skill cluster. Update the Excel file. Trigger a
refresh. Verify the new absence data appears and both dependency and cluster definitions are intact.

**Acceptance Scenarios**:

1. **Given** the dashboard has UI-defined dependencies and skill clusters,
   **When** a user triggers a refresh,
   **Then** the dashboard re-reads the Excel file, updates the timeline within 5 seconds, and
   retains all dependencies and cluster definitions.

2. **Given** the Excel file is missing or unreadable at refresh time,
   **When** a refresh is triggered,
   **Then** the dashboard displays a clear error message and retains the last successfully
   loaded data along with all UI-defined configuration.

---

### User Story 6 - Project Phase Visualization (Priority: P6)

A project manager defines named project phases — time-boxed periods where high team availability
is critical (e.g., "Go-Live", "Sprint 5", "Release Freeze"). Each phase has a name and a
start/end date range. The dashboard renders each phase as a horizontal banner row above all member
rows, spanning the day-columns covered by the phase, so the manager can immediately see which
absence or at-risk situations overlap with high-stakes periods.

**Why this priority**: Project phases provide the context that makes absence data most actionable.
Knowing that a bottleneck member is absent during a Go-Live window is more critical than knowing
they are absent during a routine sprint week.

**Independent Test**: Define phases "Go-Live" (2026-06-22 to 2026-06-26) and "Sprint 10"
(2026-06-15 to 2026-06-26, overlapping with Go-Live). Verify: two stacked banner rows appear
above the member rows; each spans only its own date columns; member rows and their absence/at-risk
colors are unchanged.

**Acceptance Scenarios**:

1. **Given** the manager defines a phase "Go-Live" spanning 2026-06-22 to 2026-06-26,
   **When** the dashboard renders,
   **Then** a banner row labelled "Go-Live" appears above all member rows, spanning exactly the
   5 day-columns for that week.

2. **Given** two phases "Sprint 10" (2026-06-15–2026-06-26) and "Go-Live" (2026-06-22–2026-06-26)
   overlap in date range,
   **When** the dashboard renders,
   **Then** both banner rows appear stacked above member rows; each banner spans only its own
   date range; no merging or truncation occurs.

3. **Given** a phase is defined,
   **When** the manager views the dependency or cluster panels,
   **Then** member absence and at-risk cell colors within the phase date range are unchanged —
   the phase banner is the only additional visual element.

4. **Given** the manager opens the project phases UI panel,
   **When** they define or remove a phase,
   **Then** they can add a name and a start/end date; the dashboard updates immediately without
   a page reload; the phase is persisted in config.json.

---

### Edge Cases

- A project member is absent for fewer than 5 days in a given calendar week — only the specific absent day sub-columns are marked; the remaining day sub-columns in that week remain unmarked (present).
- A project member is not assigned to any skill cluster — their row is shown in an "Unassigned"
  group at the bottom of the dashboard.
- A project member belongs to more than one skill cluster — each cluster assignment is displayed;
  the member appears in each relevant cluster group.
- No rows in the Excel file have "x" in "Projekt Migration" — the dashboard shows a clear
  empty-state message.
- A project member appears multiple times in the Excel file with the **same exact name spelling** —
  all their rows are merged into one dashboard row with all absence periods combined.
- A team member appears multiple times in the Excel file with **different name spellings** (e.g.,
  "Anna Mayer" vs "A. Mayer") — treated as separate, distinct people (exact string match only;
  no fuzzy matching).
- An absence entry spans the year boundary — only the portion within the current year is shown.
- A dependency cycle exists (A depends on B, B depends on A) — detected and a warning displayed;
  the cycle-creating dependency is not saved.
- The user attempts to add a dependency or cluster member referencing a person not in the loaded
  Excel data — prevented with a validation error.
- All members of a skill cluster are absent in the same week — the dashboard renders correctly
  with all cluster member rows showing absence blocks.
- A bottleneck member has no absences — they are still visually marked as a bottleneck so the
  manager is aware of the risk even when currently present.
- The Excel file contains rows with empty or malformed date fields — those rows are skipped with
  a warning; valid rows are still processed.
- A project phase spans a single calendar day (start = end) — the banner row spans exactly that
  one day-column.
- A project phase start date precedes the visible timeline start (current week) — only the
  portion within the visible date range is rendered; the phase is not hidden entirely.
- A project phase end date falls after the timeline end (last week of 2026) — only the visible
  portion is rendered.
- No project phases are defined — the timeline renders without any banner rows; member rows
  display normally.
- All members are present during a project phase — the banner row still renders; phase visibility
  is independent of absence data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST read absence data from a user-provided Excel spreadsheet file structured as a date-grid: Column D ("Team Mitglied ") is the person name; Column C ("Projekt Migration") is the membership filter; Row 1 contains calendar week labels; Row 2 contains weekday names (Mon–Fri); Column F onward are individual working-day columns starting April 27, 2026. A cell value of "x" (case-insensitive) in a day-column indicates absence for that person on that day; any other value or empty cell means present. The system derives each person's absence periods from consecutive "x"-marked cells in their row.
- **FR-002**: The system MUST display a timeline organized by calendar week (ISO week numbers) from the current calendar week through the final week of the current year. Each calendar-week column header MUST display the CW number and the date of its Monday in the format `"CW[N] | D Mon"` (e.g., `"CW22 | 25 May"`). Each calendar-week column MUST be sub-divided into 5 individual working-day sub-columns; each sub-column header displays a single-character weekday label (M / T / W / T / F for Mon–Fri) without an individual date. Absence and presence are indicated per day: only the specific days a person is absent are marked; a person absent fewer than 5 days in a given week MUST NOT appear as fully absent for that week.
- **FR-003**: The dashboard MUST show exactly one row per project member. A project member is
  identified by their exact name string (Column D, "Team Mitglied"); only rows with "x"
  (case-insensitive) in Column C ("Projekt Migration") are included. All rows sharing the same
  name spelling are treated as a single person.
- **FR-004**: The system MUST collect all absence periods across every Excel row for a given project member name and merge overlapping or adjacent periods into a single continuous visual block per merged span. A merged absence block MUST render as one unbroken bar across all absent day sub-columns, crossing week-column boundaries without visual interruption (e.g., an absence spanning Thu–Fri of CW22 and Mon–Wed of CW23 is displayed as a single connected bar, not two separate per-week blocks).
- **FR-005**: The dashboard MUST provide a UI area where the manager can add, view, and remove
  directed dependencies between project members (A depends on B).
- **FR-006**: The dashboard MUST visually mark a project member's entire calendar-week band (all 5 day sub-columns) with an at-risk indicator for any CW in which at least one day of the depended-on person's absence falls. The at-risk indicator is week-granular: a single absent day in a CW triggers the full-week at-risk highlight on the dependent's row.
- **FR-007**: The system MUST detect dependency cycles and display a warning; cycle-creating
  dependencies MUST NOT be saved.
- **FR-008**: The system MUST automatically mark project members who are listed as a dependency
  by two or more other project members with a distinct bottleneck indicator.
- **FR-009**: The dashboard MUST provide a UI area where the manager can define named skill
  clusters and assign project members to them.
- **FR-010**: The dashboard MUST display project members organized by their skill cluster;
  members not assigned to any cluster MUST appear in an "Unassigned" group.
- **FR-011**: Skill cluster and dependency changes in the UI MUST take effect on the timeline
  immediately without a page reload.
- **FR-012**: The system MUST allow the dashboard to be refreshed to reflect changes in the
  Excel file without a full restart, preserving all UI-defined dependencies and cluster
  definitions across refreshes.
- **FR-013**: The system MUST skip malformed or incomplete absence rows and surface a summary
  of skipped entries to the user.
- **FR-016**: The system MUST accept the path to the Excel file as a required command-line argument at startup (e.g. `python app.py absences.xlsx`). If the argument is missing or the file is not found, the application MUST exit with a clear error message before starting the server.
- **FR-014**: The system MUST display an empty-state message when no rows in the Excel file
  are marked for "Projekt Migration".
- **FR-015**: Dependencies and skill cluster assignments MUST only reference project member
  names present in the currently loaded Excel dataset.
- **FR-017**: The dashboard MUST provide a UI panel where the manager can add, view, and remove
  named project phases. Each phase has a name (non-empty string) and a start and end date
  (inclusive; end ≥ start).
- **FR-018**: Each project phase MUST be rendered as a horizontal banner row above all member
  rows in the timeline, spanning the exact day-columns covered by the phase's start and end dates.
  If a phase extends beyond the visible timeline range, only the visible portion is rendered.
- **FR-019**: Multiple project phases MAY overlap in date range. Each overlapping phase MUST
  render as a separate, independently labelled banner row; no merging or deduplication of
  overlapping phases occurs.
- **FR-020**: Project phases MUST be persisted in `config.json` alongside dependencies and skill
  clusters, and MUST survive dashboard refreshes.
- **FR-021**: Adding or removing a project phase in the UI MUST take effect immediately without
  a page reload.

### Key Entities

- **Project Member**: A person whose Excel row has "x" (case-insensitive) in Column C
  ("Projekt Migration"); identified by their exact name string from Column D ("Team Mitglied ");
  has zero or more absence periods and zero or more skill cluster memberships.
- **Absence Period**: A continuous span of working days derived by reading consecutive "x"-marked
  cells in a project member's row in the date-grid. Represented internally as (start date, end
  date inclusive); the source is individual day-columns in the Excel grid, not explicit date columns.
- **Merged Absence Block**: The combined result of all overlapping/adjacent raw absence periods for a project member — a single non-overlapping span rendered as one unbroken visual bar across all constituent day sub-columns, crossing calendar-week column boundaries without interruption.
- **Dependency**: A directed relationship (A → B) stored in the dashboard UI meaning "A is at
  risk when B is absent." Cycles are prohibited.
- **Bottleneck**: A project member who is the target of dependencies from two or more distinct
  other project members. Computed automatically from the dependency graph.
- **Skill Cluster**: A named group of project members defined by the manager in the dashboard
  UI, representing people who can perform the same type of work and can substitute for each other.
- **Calendar Week**: An ISO 8601 calendar week (CW01–CW53) within the current year; the visible
  range starts at the current week.
- **Project Phase**: A named time-boxed period defined by the manager in the dashboard UI,
  representing a window where high team availability is critical (e.g., "Go-Live", "Sprint 5").
  Has a name (unique), a start date, and an end date (inclusive). Multiple phases may overlap.
  Rendered as a horizontal banner row above all member rows spanning its date columns. Persisted
  in `config.json`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The dashboard fully loads and displays all project members within 5 seconds for a
  team of up to 50 project members.
- **SC-002**: 100% of overlapping absence periods for the same project member are correctly merged
  into non-overlapping blocks (verifiable by automated test against known input).
- **SC-003**: A project manager can identify all at-risk dependency weeks at a glance without
  additional filtering or navigation on a standard desktop screen.
- **SC-004**: The dashboard correctly displays all calendar weeks from the current week through
  the end of the current year, with no weeks missing or duplicated.
- **SC-005**: Refreshing the dashboard after an Excel update reflects the new data within 5 seconds,
  with all previously defined dependencies and cluster assignments intact.
- **SC-006**: Adding or removing a dependency or cluster assignment in the UI takes effect on
  the timeline immediately, with no page reload required.
- **SC-007**: Bottleneck members are visually distinguishable from non-bottleneck members at a
  glance without the manager needing to count dependencies manually.
- **SC-008**: Skill cluster groupings in the dashboard layout immediately reveal whether a
  substitute cluster member is available when any given member is absent.
- **SC-009**: Project phase banner rows are immediately visible above the member rows without
  additional navigation; overlapping phases stack as distinct rows without visual merging.

## Assumptions

- The Excel spreadsheet uses a date-grid layout: Column D (header "Team Mitglied") holds the
  person name; Row 1 holds calendar week labels; Row 2 holds weekday names (Mon–Fri only,
  weekends are not present as columns); Column F is the first dated column (April 27, 2026, a
  Monday). Each subsequent column to the right represents the next working day. A separate column
  Column C (header "Projekt Migration") marks project members with "x". Absence is encoded as a marked value in the per-day cell of a person's row — not as
  start/end date pairs. The cell value that denotes absence is "x" (case-insensitive); any other value or empty cell means present.
- The dashboard is delivered as a local web application: the manager runs a start command with
  the Excel file path as a required argument (e.g. `python app.py absences.xlsx`) and accesses
  the dashboard at `localhost:<PORT>` in a standard desktop browser. Mobile optimization and
  remote hosting are out of scope for v1.
- Calendar weeks follow ISO 8601 week numbering (week starts on Monday).
- "Rest of the year" means from the current calendar week through the last week of calendar
  year 2026.
- Dependencies and skill cluster definitions are managed entirely in the dashboard UI and are
  not stored in or read from the Excel file.
- UI-defined configuration (dependencies, skill clusters) is persisted across dashboard refreshes;
  the specific persistence mechanism (e.g., browser local storage, local file) is a planning
  decision.
- Project member identity is determined by exact name string matching; no fuzzy matching or
  ID lookup is performed.
- The tool is used by a single user (project manager) at a time; multi-user concurrent access
  is out of scope for v1.
- Absence types/reasons (vacation, sick, training) are treated uniformly for display purposes;
  no category-based filtering is required for v1.
- A bottleneck threshold of 2 or more incoming dependencies is fixed; it is not configurable
  in v1.

## Technical Constraints

- **Language**: Python (3.10+).
- **Excel parsing**: `openpyxl` library; input files must be `.xlsx` format.
- **Web server**: Flask or FastAPI (decision deferred to planning); serves the dashboard at `localhost:<PORT>`.
- **Frontend**: Browser-based; rendered in a standard desktop browser with no mobile optimization required for v1.
- **Packaging**: No containerisation required for v1; the manager runs the app directly via Python.
