# Data Model: Absence Management Dashboard

**Phase 1 output** | **Date**: 2026-05-07 | **Plan**: [plan.md](plan.md)

---

## Entities

### ProjectMember

Represents a person filtered in by the "Projekt Migration" column.

| Field | Type | Constraints |
|-------|------|-------------|
| `name` | string | Non-empty; unique key; exact match from Excel |
| `absence_periods` | list[AbsencePeriod] | Zero or more raw periods from Excel |
| `merged_blocks` | list[MergedAbsenceBlock] | Computed; never stored |

**Identity rule**: All Excel rows with the same exact `name` string AND "x" in "Projekt Migration"
are consolidated into one ProjectMember. Rows with different `name` strings are treated as
distinct people, even if names differ only by spacing or capitalization (no fuzzy matching).

---

### AbsencePeriod

A continuous span of working days derived from consecutive "x"-marked cells in a person's row
in the date-grid. Computed by `merger.py` from `ProjectMember.absence_days`; never read directly
from a start/end-date column (the Excel file has no such columns).

| Field | Type | Constraints |
|-------|------|-------------|
| `member_name` | string | FK → ProjectMember.name |
| `start_date` | date | First day of the span (inclusive) |
| `end_date` | date | Last day of the span (inclusive); `end_date >= start_date` always |

**Source**: `parser.py` reads each day-column (Column F onward) for a given person row. A cell
value of `"x"` (case-insensitive, stripped) contributes that column's working date to
`ProjectMember.absence_days`. `merger.py` then applies sort-then-sweep to produce the minimal
non-overlapping list of `AbsencePeriod` spans (see research.md Decision 7).

**Working-day column → date mapping**: Column index `c` (c ≥ 6) maps to the `(c − 6)`th working
day starting from 2026-04-27 (April 27, 2026, a Monday). The mapping is built once at parse time
by iterating forward from 2026-04-27, skipping Saturday and Sunday.

**Validation**: Rows where Column D ("Team Mitglied ") is empty or whitespace-only after
stripping are skipped; a warning entry is added to the `skipped_rows` list in the API response.

---

### MergedAbsenceBlock

The result of merging all AbsencePeriods for one ProjectMember into non-overlapping spans.
Computed on every data load; never persisted.

| Field | Type | Constraints |
|-------|------|-------------|
| `member_name` | string | FK → ProjectMember.name |
| `start_date` | date | First absent working day (inclusive) |
| `end_date` | date | Last absent working day (inclusive); `end_date >= start_date` always |

**Algorithm**: Sort by `start_date`, sweep and merge if next period overlaps or is adjacent
(next.start ≤ current.end + 1 working day). See research.md Decision 7.

**Display rule** (clarification 2026-05-08): Rendered as a single unbroken visual bar across
all `<td>` cells covering every working day from `start_date` to `end_date`, crossing calendar-
week column boundaries without interruption. A person absent only on Mon–Wed of CW23 has exactly
3 day-cells highlighted; the remaining Thu–Fri cells of CW23 are unmarked. See research.md
Decision 9 for the CSS border-suppression technique.

---

### CalendarWeek

A computed entity — never stored. Represents one ISO 8601 week within the display range.

| Field | Type | Constraints |
|-------|------|-------------|
| `year` | int | ISO year (may differ from calendar year near year boundaries) |
| `week_number` | int | 1–53 |
| `start` | date | Monday of the week |
| `end` | date | Sunday of the week |
| `label` | string | Display label, e.g. `"CW19 \| 4 May"` — CW number and Monday's date (day + abbreviated month); format confirmed clarification 2026-05-08 |
| `days` | list[date] | The 5 working dates for this week (Mon–Fri), ordered ascending |

**Display range**: From the current ISO week (CW19 / 2026-05-04) through the last ISO week of
2026. Since 2026-12-31 falls in ISO week 53 of 2026, the range is CW19–CW53 (35 weeks, 175
day-columns).

**Timeline structure** (clarification 2026-05-08): Each `CalendarWeek` occupies 5 adjacent
day-columns in the timeline table (one per working day, Mon–Fri). A two-row header displays the
CW label spanning all 5 day-columns in row 1 (format: `"CW[N] | D Mon"`, e.g., `"CW22 | 25 May"`)
and individual weekday labels (Mon / Tue / Wed / Thu / Fri) without dates in row 2.

---

### Dependency

A directed relationship stored in `state/state.json`. Means "Person A is at risk when Person B
is absent."

| Field | Type | Constraints |
|-------|------|-------------|
| `from_member` | string | FK → ProjectMember.name (the at-risk person) |
| `to_member` | string | FK → ProjectMember.name (the person depended on) |

**Constraints**:
- `from_member ≠ to_member` (self-dependency not allowed)
- Both names MUST exist in the currently loaded Excel data (enforced at write time)
- No duplicate pairs allowed
- Adding a dependency that would create a cycle MUST be rejected (409 Conflict)

**Bottleneck computation**: A ProjectMember is a bottleneck if the count of distinct
`from_member` values with `to_member = this_member` is ≥ 2. Computed on read; not stored.

**At-risk rule** (clarification 2026-05-08): For a given dependent A and a CalendarWeek W, A is
at-risk in W if A has a Dependency(A → B) and `B.absent_dates ∩ W.days ≠ ∅` (i.e., B is absent
on **any** day in that week). The at-risk indicator is week-granular: all 5 day-columns of A's
row for CW W are highlighted, regardless of how many days B is actually absent in that week.

---

### SkillCluster

A named group of ProjectMembers who can substitute for each other. Stored in `state/state.json`.

| Field | Type | Constraints |
|-------|------|-------------|
| `name` | string | Non-empty; unique cluster name |
| `members` | list[string] | Each entry must be a FK → ProjectMember.name |

**Constraints**:
- Cluster names are unique.
- A member may belong to zero, one, or more clusters.
- All member names MUST exist in the currently loaded Excel data (enforced at write time).
- An empty `members` list is allowed (cluster with no members).

---

### ProjectPhase

A named time-boxed period defined by the manager in the dashboard UI, representing a window
where high team availability is critical. Stored in `config.json`. Multiple phases may overlap.

| Field | Type | Constraints |
|-------|------|-------------|
| `name` | string | Non-empty; unique across all phases |
| `start_date` | date | First day of the phase (inclusive); ISO date string in storage |
| `end_date` | date | Last day of the phase (inclusive); `end_date >= start_date` |

**Display rule** (clarification 2026-05-08): Each phase renders as a horizontal banner row above
all member rows in the timeline. The row spans exactly the day-columns from `start_date` to
`end_date`. If a phase extends beyond the visible timeline, only the visible portion is rendered.
Multiple phases with overlapping date ranges stack as separate consecutive banner rows — no
merging occurs.

**Validation**: `start_date` and `end_date` must be valid ISO dates; `end_date >= start_date`.
Phase names must be unique. Phase date ranges are not constrained to the visible timeline window
(out-of-range portions are silently clipped when rendering).

---

## State File Schema (`state/state.json`)

```json
{
  "dependencies": [
    { "from_member": "Alice", "to_member": "Bob" },
    { "from_member": "Carol", "to_member": "Bob" }
  ],
  "clusters": [
    {
      "name": "Backend",
      "members": ["Alice", "Bob", "Dave"]
    },
    {
      "name": "Frontend",
      "members": ["Carol", "Eve"]
    }
  ],
  "phases": [
    { "name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26" },
    { "name": "Sprint 10", "start_date": "2026-06-15", "end_date": "2026-06-26" }
  ]
}
```

**Initialization**: If `state.json` does not exist on startup, the application creates it with
`{ "dependencies": [], "clusters": [], "phases": [] }`.

**Integrity on refresh**: When the Excel file is reloaded, any dependency or cluster member
referencing a name no longer present in the filtered Excel data is removed automatically and
the removal is reported in the refresh response.

---

## Computed Dashboard View

The API assembles a single `DashboardData` response object for the frontend:

```json
{
  "calendar_weeks": [
    {
      "year": 2026, "week_number": 19, "label": "CW19",
      "start": "2026-05-04", "end": "2026-05-10",
      "days": ["2026-05-04","2026-05-05","2026-05-06","2026-05-07","2026-05-08"]
    }
  ],
  "members": [
    {
      "name": "Alice",
      "clusters": ["Backend"],
      "is_bottleneck": false,
      "merged_blocks": [
        { "start": "2026-06-01", "end": "2026-06-10" }
      ],
      "at_risk_weeks": [22, 23],
      "depends_on": ["Bob"]
    }
  ],
  "clusters": [...],
  "dependencies": [...],
  "skipped_rows": [...],
  "bottlenecks": ["Bob"],
  "last_loaded": "2026-05-11T14:32:00"
}
```

**`last_loaded`**: ISO 8601 datetime string (`YYYY-MM-DDTHH:MM:SS`) recording the moment the
server last successfully read and parsed the Excel data. Set on initial load and updated on every
successful `POST /api/refresh`. The frontend displays this in the fixed header bar, top-right, in
the format `"Last loaded: D Mon YYYY, HH:MM"` (e.g., `"Last loaded: 11 May 2026, 14:32"`).

**`calendar_weeks.days`**: The ordered list of 5 Mon–Fri dates for each CW. The frontend uses
this to map each date to its `<td>` column position and to apply absence/at-risk CSS classes.

**`at_risk_weeks`**: List of ISO week numbers (integers) for which this member is at-risk. A
week appears here if any day in `W.days` intersects any dependency's absent dates. The frontend
highlights all 5 day-cells for each week in this list with the at-risk style.

**Member ordering**: Within each cluster, members are sorted alphabetically. Ungrouped members
follow all clusters, also sorted alphabetically. Cluster order matches definition order in
`state.json`.
