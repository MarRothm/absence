# Research: Extended Timeline with Month-Range Filter

All Technical Context items were resolvable from the existing codebase; no external research was
needed. Each decision below records what was found in the code and why the chosen approach fits.

## R1 — Where the 2026 limit lives

**Finding**: `absence_dashboard/app.py:_build_calendar_weeks()` hard-codes
`_last_iso_week(2026)` as the end of the timeline and always starts at the current ISO week. Nothing
else in the backend is year-bounded; `cumul_groups.py` and `phases_manager.py` work on real
`date`s and ISO strings and accept any year (FR-012 is already met — only tests are needed).

**Decision**: Replace `_build_calendar_weeks()` with a pure function
`build_calendar_weeks(start: date, end: date)` in a new module `absence_dashboard/timeline.py`. It
includes every ISO week that has at least one Mon–Fri day within `[start, end]` (FR-005). The
rolling default (FR-007) and the manager's month range (FR-004) both reduce to a `(start, end)` pair
and use the same builder.

**Rationale**: One code path for both default and filtered views; a pure, I/O-free module mirrors
`phases_manager.py` / `cumul_groups.py` and is directly unit-testable with injected `today`.

**Alternatives considered**: Keep the builder in `app.py` and add parameters — rejected because the
range-resolution and month-parsing logic would also land in `app.py`, which has no unit tests of its
own (only integration tests), making edge cases (ISO week 53, month starting on a weekend, Feb 29)
expensive to cover.

## R2 — Rolling 12-month default

**Decision**: `default_range(today)` returns `start = Monday of today's ISO week` and
`end = same calendar date one year later` (29 Feb → 28 Feb). Passing these to
`build_calendar_weeks` yields the current week through the week containing that date (if that date
is a Saturday/Sunday, its Mon–Fri days are all ≤ `end`, so that week is included — matches the
clarification "ending with the calendar week that contains the same date 12 months later").
Recomputed on every `/api/dashboard` and `/api/refresh` call, so it rolls forward automatically.

## R3 — Week identity across years (FR-002, FR-003)

**Finding**: Cumul-risk and sole-coverage entries are emitted as `{"group", "week_number"}`
(`app.py:105-114`), and the frontend keys its day index, risk maps and tooltips on `week_number`
alone (`main.js:65,74,158,235,258`). With a timeline longer than 52 weeks, CW42 2026 and CW42 2027
would share markers.

**Decision**: Each calendar-week dict gains a `key` field, the ISO week string `"YYYY-Www"` (e.g.
`"2027-W05"`). `compute_cumul_risk_weeks` / `compute_sole_coverage_weeks` return week keys instead
of week numbers; payload entries become `{"group", "week_key"}`. The frontend keys everything on
`week_key` and looks up the week's label for tooltips. Labels become `"CW5 2027 | 1 Feb"` (ISO year,
so CW1 starting in late December shows the year it belongs to).

**Rationale**: ISO week strings are standard, sort lexicographically, and are unambiguous. Replacing
(not adding alongside) `week_number` in risk entries avoids two identities for one thing.

**Alternatives considered**: Use `(year, week_number)` pairs — rejected; awkward as JS `Map`/`Set`
keys. Use the week's Monday date — works, but less readable in tooltips/tests.

## R4 — Dating the Excel file after 2026 (FR-014)

**Finding**: The real file (`absences.xlsx`) carries only ISO week numbers (`KW` row: 18…53) and
weekday names — no year anywhere. `parser.build_date_map()` assumes the first week belongs to
`date.today().year`. Consequences once 2027 starts, with today's file:
- every column would be dated one year late (Apr–Dec 2027 instead of 2026), and
- `date.fromisocalendar(2027, 53, …)` raises `ValueError` (2027 has only 52 ISO weeks), so loading
  the file would **crash**.

**Decision**: When no explicit `year` is passed, `build_date_map` infers the starting year: try
candidates `today.year - 1`, `today.year`, `today.year + 1`; discard any candidate for which some
column's week number is invalid in its (rolled-over) year; among the rest pick the one whose
resulting date span is closest to `today` (distance 0 if `today` lies inside the span); ties go to
the earlier year. If the header has no week numbers at all, behaviour is unchanged (empty map). The
existing within-file roll-over (week number decreases → next year) is kept. Explicit `year=` still
bypasses inference, so all existing parser tests keep passing.

Worked examples (file KW18–KW53):
- today 13 Oct 2026 → 2026 contains today → 2026 ✔
- today 15 Jan 2027 → 2027 invalid (W53), 2025 invalid (W53) → 2026 ✔ (previously: crash)

Worked example (rolling file KW40 → KW39, i.e. Sep 2026–Sep 2027), today 1 Aug 2027 → candidate
2026 contains today → 2026 ✔ (previously: 2027, i.e. a year late).

**Rationale**: The planning file is always maintained around "now", so "span closest to today" is
the right heuristic; ISO-week validity gives a hard signal in 53-week years. No new configuration
for the manager to maintain.

**Alternatives considered**: (a) a `start_year` setting in `launch_config.json` — rejected as the
primary mechanism: one more thing to remember to update each year, and the failure mode (stale
setting) is silent. (b) Asking the file owner to add a year row — outside our control.

## R5 — Where filtering happens

**Decision**: Server-side. `GET /api/dashboard` and `POST /api/refresh` accept optional query
parameters `from` and `to` (`MM/YYYY`). The server resolves the range, builds only the visible weeks,
and computes cumul-risk / sole-coverage for those weeks. Critical-absence days are still derived from
each member's **full** merged blocks (`critical_absence_days(m.merged_blocks)` is already computed
before and independently of the week list), so FR-010 holds without extra work. Merged blocks are
sent unclipped; the frontend only draws days present in the week list.

**Rationale**: Week building, validation and risk computation already live server-side and are
covered by pytest; the frontend just needs to remember and resend the range.

**Alternatives considered**: Send all weeks of the file and filter in JS — rejected; duplicates week
logic in untested JS and makes the default range depend on file extent (contradicts FR-007).

## R6 — Filter session state and input format

**Decision**: The applied filter lives in a module-level JS variable (`timeFilter`, `null` = rolling
default) and is appended to the two dashboard-returning calls. It survives Reload and every panel
action (they all re-fetch through `refreshDashboard()` or `/api/refresh`) and is lost on browser
reload or app restart, which is the confirmed "session-only" behaviour. Inputs are two text fields
with placeholder `MM/YYYY` (accepting `M/YYYY` too), validated client-side for immediate feedback and
again server-side (400 on error, previous filter kept — FR-006).

**Alternatives considered**: `<input type="month">` — rejected: renders in browser-locale format,
not MM/YYYY, and is not supported by every browser the Citrix package may run in.

## R7 — "No data in range" notice (FR-013)

**Decision**: `_load_excel` captures the min/max date of the file's date map (`DATA_RANGE`). The
dashboard payload carries `data_in_range: bool` (true iff the file's span overlaps the visible
range). The frontend shows a dismissible notice when false.

## R8 — Phases outside the range (FR-011)

**Finding**: `renderTimeline` already draws phase cells only for days in the day index and already
treats a phase start before the first visible day as a visual start (`main.js:184-185`), so clipping
works. A phase entirely outside the range currently renders an empty row.

**Decision**: Skip phase rows with no visible day; the phases side panel is untouched.

## R9 — Performance (SC-003)

A 24-month range is ~105 weeks ≈ 525 day cells per row; with a few dozen members that is
≈ 15–25k DOM cells, the same order as today's ~11 weeks × 5 days scaled linearly. Backend work is
O(groups × weeks × members) set intersections. No optimisation is planned; SC-003 is verified
manually in quickstart.
