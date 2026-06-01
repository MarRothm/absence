# Feature Specification: Absence Management Dashboard

**Feature Branch**: `001-absence-dashboard`
**Created**: 2026-05-07
**Status**: Draft
**Input**: User description: "I have an input Excel Spreadsheet where project members document their planned absences. I need graphical dashboard that shows per calendar week for the rest of the year absences. Per team member one line. Duplicates are resolved in a way that absences are combined but only one line per person. I want to add dependencies between people and visualize this."

## Clarifications

### Session 2026-06-01

- Q: Which rows are displayed in "all entries" mode? → A: All rows with a non-empty name in Column D (both migration and non-migration people).
- Q: What should the dashboard display by default on first load? → A: Migration team only — "all entries" is an opt-in view.
- Q: How should the filter control be presented? → A: Toggle button in the fixed header bar switching between "Show All" and "Migration Only".
- Q: Should non-migration members be visually distinct in "all entries" mode? → A: Yes — non-migration rows are rendered with a muted/dimmed style to distinguish them from migration members.
- Q: Should non-migration members be selectable in dependency and cluster management panels? → A: No — dependency and cluster panels remain limited to migration members only regardless of the active filter.

### Session 2026-05-15

- Q: Should the dependency date interval be optional or required? → A: Optional — omitting both dates means the dependency is always active (indefinite); a date range is only provided when the collaboration window is known.
- Q: Can one dependency have multiple separate date intervals? → A: No — one contiguous start–end range per dependency entry; multiple non-contiguous windows are expressed as separate dependency entries.
- Q: Outside a dependency's active date range, what happens to the at-risk indicator? → A: No indicator shown — the dependency is inactive outside its window; affected calendar weeks render as if the dependency doesn't exist.
- Q: With date intervals, what defines a duplicate dependency? → A: The tuple (from, to, start_date, end_date) is the unique key — the same (from, to) pair may appear multiple times with different date ranges; only an identical four-field tuple is rejected as a duplicate.
- Q: Is a dependency stored as one source + a pool of targets, or as individual pairs? → A: One dependency record = one source person + an explicit pool (list) of one or more target persons; stored as a single record with a `to_members` list. A pool of one is valid.
- Q: How should a deadlock (all pool members absent) be visualized? → A: Color the dependent person's Gantt row cells for the deadlock week in a distinct critical color AND display a "Deadlock" text label in the affected band.
- Q: Should phase banners be highlighted when a deadlock overlaps their date range? → A: Yes — a phase banner turns a warning/alert color when a deadlock (all pool members absent) overlaps any day within the phase's date range.
- Q: Where should the red vertical line be positioned relative to today's day sub-column? → A: Left edge of today's day sub-column — line sits on the column's left border, separating past from present.
- Q: If today is Saturday or Sunday, where should the today indicator appear? → A: Do not show the indicator — the line is hidden entirely on weekends.
- Q: Should the today indicator include a text label? → A: Yes — a small "Today" label anchored in the CW/day header row above the line.
- Q: Should the today indicator extend through project phase banner rows? → A: Yes — full height spanning phase banner rows and all member rows.

### Session 2026-05-11

- Q: Should the SharePoint URL be an alternative data source alongside local file, or replace it? → A: Both supported — CLI accepts either a local file path or a SharePoint URL; app detects which is provided at startup.
- Q: What authentication method should the app use for SharePoint? → A: Anonymous / public — the SharePoint link is an "anyone with the link" public share; no credentials needed.
- Q: What timestamp should "date and time of the data" show on the dashboard? → A: Last loaded/refreshed time — the moment the app last successfully read and processed the data.
- Q: Where should the last-loaded timestamp appear? → A: Fixed header bar, top-right corner — always visible above the timeline regardless of scroll position.
- Q: What type of SharePoint URL will the manager provide? → A: SharePoint share URL — app automatically converts it to a direct download URL (appending `?download=1` or equivalent).
- Q: What UI interaction pattern should editing use across all three management panels (dependencies, phases, clusters)? → A: Inline row expansion — clicking Edit transforms the list item into editable fields directly in place; no modal or side panel.
- Q: For dependency editing, which endpoints are editable? → A: Both the "from" and "to" person dropdowns are editable in place; saving atomically replaces the old dependency.
- Q: For cluster editing, what fields are editable? → A: Both the cluster name (text field) and its member list (multi-select) are editable inline.
- Q: How should an inline edit be committed? → A: Explicit Save and Cancel buttons appear in the expanded row; clicking Save commits the change; Cancel discards it.
- Q: When Save fails validation (cycle, duplicate name, invalid date range), what happens? → A: The edit row stays open and displays an inline error message below the affected field(s); no data is modified.

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

5. **Given** the dashboard is loaded (default "Migration Only" mode),
   **When** the manager clicks the "Show All" toggle in the header bar,
   **Then** all persons with a non-empty name in Column D are shown; non-migration members
   appear with a visually distinct muted/dimmed style; the dependency, cluster, and phase
   panels are unchanged and still list only migration members.

6. **Given** the dashboard is in "All Entries" mode,
   **When** the manager clicks the toggle to switch back to "Migration Only",
   **Then** non-migration rows are immediately hidden and the view returns to the migration
   subset without a page reload.

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
   **Then** they can add, view, edit, and remove dependencies using only names present in the
   loaded Excel data; clicking Edit expands the row inline with both "from" and "to" dropdowns
   editable, and Save/Cancel buttons to commit or discard the change.

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
   **When** they edit a cluster,
   **Then** clicking Edit expands the cluster row inline with the cluster name (text field) and
   member list (multi-select) both editable; Save commits the change and collapses the row;
   Cancel discards it; the dashboard updates immediately; only names present in the loaded Excel
   data are available in the member multi-select.

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
   **When** they add, edit, or remove a phase,
   **Then** they can add a name and a start/end date; clicking Edit on an existing phase expands
   the row inline with name, start date, and end date all editable; Save commits the change;
   Cancel discards it; the dashboard updates immediately without a page reload; the phase is
   persisted in config.json.

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
- Today falls on a Saturday or Sunday — the today indicator is not shown; no line or label appears.
- Today falls before the visible timeline start or after the last visible week — the today indicator is not shown.
- All members are present during a project phase — the banner row still renders; phase visibility
  is independent of absence data.
- The manager edits a dependency such that it would create a cycle — the edit row stays open with an inline cycle-detection error; the original dependency is unchanged (extends FR-007 to the edit path).
- A dependency has `active_from` set but `active_to` omitted, or vice versa — both fields must be provided together or both omitted; a partially filled date range is rejected with an inline validation error.
- A dependency's `active_from` date is later than its `active_to` date — rejected with an inline error; no data is saved.
- Two A→B dependency entries exist with different date ranges — both are valid and both contribute at-risk indicators within their respective active windows; calendar weeks covered by either range show at-risk indicators.
- A dependency's active date range falls entirely before the visible timeline start (current week) — the dependency is stored but produces no at-risk indicators in the visible range (no error shown).
- The manager adds a second A→B entry with an identical (from, to, active_from, active_to) tuple — rejected as a duplicate with an inline error; the original entry is unchanged.
- A dependency pool has only one target (B) and B is absent — this is immediately a deadlock; the dependent person's row shows the deadlock color and "Deadlock" label.
- A dependency pool has three targets (B, C, D); B and C are absent but D is present — bottleneck pressure only: D gains bottleneck weight, no deadlock coloring on the dependent's row.
- A dependency pool has three targets (B, C, D); all three are absent in the same CW — deadlock: dependent person's CW band rendered in `--color-deadlock` with "Deadlock" label; any phase overlapping that week also renders in `--color-phase-deadlock`.
- A phase overlaps with a deadlock week from one dependency AND is normal for all other dependencies — the phase banner turns alert color; only one deadlock is needed to trigger the highlight.
- A deadlock exists outside any defined phase's date range — dependent person's row still shows the deadlock color; no phase banner is affected.
- The manager edits a phase with an end date earlier than the start date — the edit row stays open with an inline date-range error; the original phase is unchanged.
- The manager edits a cluster or phase name to one already used by another cluster or phase — the edit row stays open with an inline duplicate-name error; the original name is unchanged.
- The manager edits a dependency to an (A→B) pair that already exists — the edit row stays open with an inline duplicate-dependency error; the original is unchanged.
- The Excel file contains no non-migration rows — the "All Entries" toggle is still present and functional; toggling it produces no visual change since all persons are already migration members.
- In "All Entries" mode, the manager attempts to add a non-migration person to a dependency or cluster — the management panel dropdowns/multi-selects do not include non-migration members; the action is not possible.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST read absence data from a user-provided Excel spreadsheet file structured as a date-grid: Column D ("Team Mitglied ") is the person name; Column C ("Projekt Migration") is the membership filter; Row 1 contains calendar week labels; Row 2 contains weekday names (Mon–Fri); Column F onward are individual working-day columns starting April 27, 2026. A cell value of "x" (case-insensitive) in a day-column indicates absence for that person on that day; any other value or empty cell means present. The system derives each person's absence periods from consecutive "x"-marked cells in their row.
- **FR-002**: The system MUST display a timeline organized by calendar week (ISO week numbers) from the current calendar week through the final week of the current year. Each calendar-week column header MUST display the CW number and the date of its Monday in the format `"CW[N] | D Mon"` (e.g., `"CW22 | 25 May"`). Each calendar-week column MUST be sub-divided into 5 individual working-day sub-columns; each sub-column header displays a single-character weekday label (M / T / W / T / F for Mon–Fri) without an individual date. Absence and presence are indicated per day: only the specific days a person is absent are marked; a person absent fewer than 5 days in a given week MUST NOT appear as fully absent for that week.
- **FR-003**: The dashboard MUST show exactly one row per person, where a person is identified by their exact name string in Column D ("Team Mitglied"). The active display mode determines which persons appear: in "Migration Only" mode (the default on first load) only rows with "x" (case-insensitive) in Column C ("Projekt Migration") are included; in "All Entries" mode all rows with a non-empty name in Column D are included regardless of Column C. All rows sharing the same name spelling are treated as a single person across both modes.
- **FR-004**: The system MUST collect all absence periods across every Excel row for a given project member name and merge overlapping or adjacent periods into a single continuous visual block per merged span. A merged absence block MUST render as one unbroken bar across all absent day sub-columns, crossing week-column boundaries without visual interruption (e.g., an absence spanning Thu–Fri of CW22 and Mon–Wed of CW23 is displayed as a single connected bar, not two separate per-week blocks).
- **FR-005**: The dashboard MUST provide a UI area where the manager can add, view, edit, and
  remove dependencies. Each dependency has one `from_member` (the dependent person) and a
  `to_members` pool (multi-select, one or more project members who can satisfy the dependency).
  Each dependency MAY optionally include an active date range (`active_from` date, `active_to`
  date); when both are omitted the dependency is active indefinitely. When provided,
  `active_from` ≤ `active_to` is required. Editing a dependency expands its row inline with the
  "from" person dropdown, the "to" pool multi-select, and the optional date fields all editable;
  saving atomically replaces the old dependency entry.
- **FR-006**: The dashboard MUST compute two risk states per dependency per calendar week (within the dependency's active date range, if set):
  - **Deadlock**: ALL members of `to_members` are absent in that CW → the dependent person (from_member) is fully blocked. The dependent person's entire CW band (all 5 day sub-columns) MUST be rendered in a distinct critical color (`--color-deadlock`, e.g. crimson/deep red) AND a "Deadlock" text label MUST appear in the first day sub-column of the affected week band.
  - **Bottleneck pressure**: SOME but not ALL members of `to_members` are absent → the present members of the pool gain increased bottleneck weight for that CW. No at-risk coloring is shown on the dependent person's row; instead the present pool member(s) are marked with elevated bottleneck status.
  Member rows MUST NOT display at-risk cell coloring under either state.
- **FR-007**: Duplicate dependencies are identified by the tuple (from_member, frozenset(to_members), active_from, active_to); an identical tuple MUST be rejected with an inline error. Two entries with the same (from_member, to_members) but different date ranges are NOT duplicates. Cycle detection is not required for pool-based dependencies.
- **FR-008**: The system MUST compute a **bottleneck weight** for each project member per calendar week: the number of active dependencies whose `to_members` pool contains that person AND for which that person is the only present pool member in that CW. A member with bottleneck weight ≥ 1 in any CW MUST carry a visible bottleneck indicator on their row header. Bottleneck absence cells MUST NOT be colored differently from normal absence cells (red bottleneck-absent coloring is removed).
- **FR-009**: The dashboard MUST provide a UI area where the manager can add, edit, and remove
  named skill clusters and assign project members to them. Editing a cluster expands its row
  inline with both the cluster name (text field) and its member list (multi-select) editable.
- **FR-010**: The dashboard MUST display project members organized by their skill cluster;
  members not assigned to any cluster MUST appear in an "Unassigned" group.
- **FR-011**: Skill cluster, dependency, and phase additions, edits, and removals in the UI MUST
  take effect on the timeline immediately without a page reload.
- **FR-012**: The system MUST allow the dashboard to be refreshed to reflect changes in the
  Excel file without a full restart, preserving all UI-defined dependencies and cluster
  definitions across refreshes.
- **FR-013**: The system MUST skip malformed or incomplete absence rows and surface a summary
  of skipped entries to the user.
- **FR-016**: The system MUST accept either a local `.xlsx` file path or a SharePoint "anyone with the link" share URL as the required command-line argument at startup (e.g. `python app.py absences.xlsx` or `python app.py https://company.sharepoint.com/...`). The app distinguishes between the two by detecting an `http://` or `https://` scheme. If the argument is missing, the local file is not found, or the SharePoint URL is unreachable, the application MUST exit with a clear error message before starting the server.
- **FR-014**: The system MUST display an empty-state message when no rows in the Excel file
  are marked for "Projekt Migration".
- **FR-015**: Dependencies and skill cluster assignments MUST only reference project member
  names present in the currently loaded Excel dataset.
- **FR-017**: The dashboard MUST provide a UI panel where the manager can add, view, edit, and
  remove named project phases. Each phase has a name (non-empty string) and a start and end date
  (inclusive; end ≥ start). Editing a phase expands its row inline with all three fields
  (name, start date, end date) editable.
- **FR-018**: Each project phase MUST be rendered as a horizontal banner row above all member
  rows in the timeline, spanning the exact day-columns covered by the phase's start and end dates.
  If a phase extends beyond the visible timeline range, only the visible portion is rendered.
  A phase banner MUST be rendered in a distinct alert color (`--color-phase-deadlock`) when at
  least one dependency deadlock (all `to_members` absent simultaneously) overlaps any day within
  the phase's date range and the dependency's active window. A phase with no overlapping deadlock
  renders in its normal color.
- **FR-019**: Multiple project phases MAY overlap in date range. Each overlapping phase MUST
  render as a separate, independently labelled banner row; no merging or deduplication of
  overlapping phases occurs.
- **FR-020**: Project phases MUST be persisted in `config.json` alongside dependencies and skill
  clusters, and MUST survive dashboard refreshes.
- **FR-021**: Adding, editing, or removing a project phase in the UI MUST take effect immediately
  without a page reload.
- **FR-022**: All three management panels (dependencies, phases, skill clusters) MUST use a
  consistent inline row-expansion pattern for editing: clicking an Edit control on an existing
  item expands that row into editable fields in place; explicit Save and Cancel buttons appear
  within the expanded row; Save commits and collapses, Cancel discards and collapses.
- **FR-023**: When an inline Save fails validation (dependency would create a cycle; dependency
  `active_from` is after `active_to`; identical (from, to, active_from, active_to) tuple already
  exists; phase end date is before start date; cluster or phase name duplicates an existing one),
  the edit row MUST remain open and display an inline error message below the affected field(s);
  no persisted data is modified.
- **FR-024**: When a SharePoint URL is provided as the CLI argument, the system MUST convert it
  to a direct download URL (by appending `?download=1` or equivalent SharePoint download
  parameter) and fetch the `.xlsx` file via an anonymous HTTP GET request using the `requests`
  library. No authentication headers or credentials are required. On refresh, the app MUST
  re-fetch from the SharePoint URL to pick up the latest version of the file.
- **FR-026**: The dashboard MUST display a red vertical indicator line at the left edge of the current day's day sub-column to mark today's date. The line MUST span the full height of the timeline, including all project phase banner rows and all member rows. A small "Today" label MUST appear above the line, anchored in the day-header row. The indicator MUST NOT be shown when today falls on a Saturday or Sunday. When today falls before the visible timeline range or after year-end, the indicator is also not shown.

- **FR-025**: The dashboard MUST display the date and time the Excel data was last successfully
  loaded or refreshed in the fixed header bar, top-right corner, using the format
  `"Last loaded: D Mon YYYY, HH:MM"` (e.g., `"Last loaded: 11 May 2026, 14:32"`). This
  timestamp MUST update immediately after every successful data refresh.

- **FR-027**: The dashboard MUST provide a toggle button in the fixed header bar that switches between two display modes: **"Migration Only"** (default on first load — only persons with "x" in Column C shown) and **"All Entries"** (all persons with a non-empty name in Column D shown). In "All Entries" mode, non-migration persons (those without "x" in Column C) MUST be rendered with a visually distinct muted/dimmed style to differentiate them from migration members at a glance. The toggle MUST take effect immediately without a page reload. The dependency, skill cluster, and project phase management panels MUST remain limited to migration members regardless of the active display mode.

### Key Entities

- **Project Member**: A person whose Excel row has "x" (case-insensitive) in Column C
  ("Projekt Migration"); identified by their exact name string from Column D ("Team Mitglied ");
  has zero or more absence periods and zero or more skill cluster memberships.
- **Absence Period**: A continuous span of working days derived by reading consecutive "x"-marked
  cells in a project member's row in the date-grid. Represented internally as (start date, end
  date inclusive); the source is individual day-columns in the Excel grid, not explicit date columns.
- **Merged Absence Block**: The combined result of all overlapping/adjacent raw absence periods for a project member — a single non-overlapping span rendered as one unbroken visual bar across all constituent day sub-columns, crossing calendar-week column boundaries without interruption.
- **Dependency**: A relationship stored in the dashboard UI meaning "person A needs at least one
  person from the target pool {B, C, D, …} to be present." Stored as one record with a single
  `from_member` and a `to_members` list (one or more targets). Optionally bounded by an active
  date range (`active_from`, `active_to`, both inclusive; omitting both means permanently active).
  Uniqueness key: (from_member, frozenset(to_members), active_from, active_to).
  **Satisfied** when ≥ 1 member of `to_members` is present during the relevant period.
  **Deadlock** when ALL members of `to_members` are simultaneously absent during a calendar week.
  **Bottleneck pressure**: when some (but not all) of `to_members` are absent, the present
  member(s) in the pool gain increased bottleneck weight (they are the sole satisfiers of the
  dependency). Cycle detection is not applicable under this model (a pool-based dependency
  cannot form a directed cycle in the same way as a 1-to-1 edge).
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
- **SC-006**: Adding, editing, or removing a dependency, cluster, or phase in the UI takes effect
  on the timeline immediately, with no page reload required.
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
  either a local Excel file path or a SharePoint "anyone with the link" share URL as the required
  argument (e.g. `python app.py absences.xlsx` or `python app.py https://...`) and accesses the
  dashboard at `localhost:<PORT>` in a standard desktop browser. Mobile optimization and remote
  hosting are out of scope for v1. SharePoint URLs must be public shares requiring no authentication;
  the app detects a URL by its `http://` or `https://` scheme and converts it to a direct download
  link automatically.
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
- The dashboard defaults to "Migration Only" display mode on first load; the manager can switch
  to "All Entries" via a toggle in the fixed header bar to see all persons with a name in Column D.
  Non-migration persons in "All Entries" mode are shown with a muted/dimmed visual style.
  Management panels (dependencies, clusters, phases) are always scoped to migration members only.
- A bottleneck threshold of 2 or more incoming dependencies is fixed; it is not configurable
  in v1.

## Technical Constraints

- **Language**: Python (3.10+).
- **Excel parsing**: `openpyxl` library; input files must be `.xlsx` format.
- **HTTP fetching**: `requests` library; used to download the Excel file from a SharePoint public share URL when a URL is provided instead of a local path.
- **Web server**: Flask or FastAPI (decision deferred to planning); serves the dashboard at `localhost:<PORT>`.
- **Frontend**: Browser-based; rendered in a standard desktop browser with no mobile optimization required for v1.
- **Packaging**: No containerisation required for v1; the manager runs the app directly via Python.
