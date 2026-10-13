# Feature Specification: Extended Timeline with Month-Range Filter

**Feature Branch**: `007-extend-timeline-filter`

**Created**: 2026-10-13

**Status**: Draft

**Input**: User description: "extend usage for time after December 2026. Add a time filter (from MM/YYYY to MM/YYYY)"

## Clarifications

### Session 2026-10-13

- Q: What is the default timeline range when no filter is set? → A: A rolling 12-month timeframe
  starting at the current calendar week and ending with the calendar week that contains the same
  date 12 months later; it moves forward automatically as time passes.
- Q: Are the remaining defaults acceptable (session-only filter, past months selectable, no
  maximum range length)? → A: Yes, confirmed as stated in Assumptions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Plan absences beyond December 2026 (Priority: P1)

A manager loads an absence file that contains planned absences in 2027 (or later). Today the
dashboard timeline always stops at the last calendar week of 2026, so anything recorded after that
is invisible. After this change, the timeline is a rolling 12-month window starting at the current
week, so it always reaches into the next year, and any later period can be reached with the time
filter (Story 2). The manager can review absences, phases, and cumul risks in 2027 and beyond
exactly as they do for 2026.

**Why this priority**: From January 2026 onward the dashboard becomes progressively less useful and
stops working for forward planning entirely once 2026 ends. This is the blocking problem; the
filter (Story 2) is only meaningful once the timeline can reach beyond 2026.

**Independent Test**: Load a file whose columns span from a 2026 week into a 2027 week with a few
absences marked in 2027 (within 12 months of today), open the dashboard with no filter changes, and
confirm the 2027 weeks and absences appear in the timeline and the last week shown is the week
containing today's date one year later.

**Acceptance Scenarios**:

1. **Given** a loaded file containing absences in March 2027, **When** the manager opens the
   dashboard, **Then** the March 2027 calendar weeks are reachable in the timeline and the absences
   appear in the correct days.
2. **Given** the current date is in 2027, **When** the manager opens the dashboard, **Then** the
   timeline still works (it is not empty and does not stop at December 2026).
3. **Given** the timeline spans two years that both contain a calendar week with the same number
   (e.g. CW5 2027 and CW5 2028), **When** the manager looks at those weeks, **Then** each week is
   clearly labelled with its year and absence, phase, cumul-risk and sole-coverage markers appear
   only in the week they actually belong to.
4. **Given** a timeline that crosses a year boundary, **When** the manager looks at the weeks around
   the boundary (including years with an ISO week 53), **Then** no week is missing or duplicated.

---

### User Story 2 - Restrict the view to a month range (Priority: P2)

The manager wants to focus on a specific planning window, for example a project phase from 03/2027
to 08/2027. They set a "From" month (MM/YYYY) and a "To" month (MM/YYYY) and the timeline only shows
the calendar weeks inside that range. They can change or reset the range at any time.

**Why this priority**: Once the timeline can cover multiple years, it becomes long and hard to read;
the filter makes the extended timeline usable. It depends on Story 1 for ranges outside 2026 to have
any content.

**Independent Test**: With any loaded file, set From = 11/2026 and To = 02/2027 and confirm only
weeks touching November 2026 through February 2027 are shown; then reset the filter and confirm the
default range returns.

**Acceptance Scenarios**:

1. **Given** the dashboard is open, **When** the manager sets From = 01/2027 and To = 03/2027,
   **Then** only calendar weeks that contain at least one working day (Mon–Fri) between 1 January
   2027 and 31 March 2027 are shown.
2. **Given** a filter is applied, **When** the manager resets it, **Then** the timeline returns to
   the default range.
3. **Given** the manager enters a "To" month earlier than the "From" month, **When** they try to
   apply it, **Then** the filter is not applied and a clear message explains that "To" must be the
   same as or later than "From".
4. **Given** the manager enters a month that is not a valid MM/YYYY value (e.g. 13/2027 or
   "2027"), **When** they try to apply it, **Then** the filter is not applied and a clear message
   shows the expected format.
5. **Given** a filter is applied, **When** the manager reloads/refreshes the absence data, **Then**
   the same filter stays applied for the rest of the session.
6. **Given** a filter is applied, **When** the manager looks at the filter controls, **Then** the
   currently applied range is visible at all times.

---

### User Story 3 - Filtered view keeps risk information correct (Priority: P3)

When the manager narrows the view to a month range, all derived information (phases, cumul-risk
weeks, sole-coverage flags, absence blocks) for the visible weeks is exactly the same as it would be
in the unfiltered view; the filter only hides weeks, it never changes how risks are calculated.

**Why this priority**: Prevents the filter from silently producing misleading risk information, but
only matters once Stories 1 and 2 exist.

**Independent Test**: Note the cumul-risk and sole-coverage markers in a given week in the
unfiltered view, then apply a filter whose range starts in the middle of a long absence that covers
that week, and confirm the markers for that week are identical.

**Acceptance Scenarios**:

1. **Given** a member has a 10-day continuous absence starting in the last days of February 2027,
   **When** the manager filters From = 03/2027, **Then** the absence still counts as a critical
   absence (more than 5 days) in the visible March weeks, even though part of it lies outside the
   range.
2. **Given** a phase from January 2027 to June 2027, **When** the manager filters From = 03/2027
   To = 04/2027, **Then** the phase is shown across the whole visible range (clipped to it) and its
   full start and end dates remain visible in its tooltip/details.
3. **Given** a phase lying entirely outside the selected range, **When** the filter is applied,
   **Then** the phase does not appear in the timeline but remains listed and editable in the phase
   management panel.

---

### Edge Cases

- **Week straddling month boundaries**: a calendar week is shown if at least one of its working days
  (Mon–Fri) falls inside the selected range; such a week is shown in full.
- **Week straddling a year boundary** (e.g. ISO week 1 starting in late December): treated like any
  other week and labelled with its ISO year.
- **ISO week 53** (e.g. 2026 has 53 ISO weeks): included and labelled correctly.
- **Range with no data**: if the selected range lies entirely outside the dates covered by the
  loaded file, the timeline shows the weeks but with no absences, together with a notice that the
  loaded file contains no data for the selected range.
- **From = To**: a single-month range is valid and shows all weeks touching that month.
- **Very long range**: the manager may select a multi-year range; the dashboard remains usable (see
  SC-003).
- **File spanning a year boundary without explicit years**: absence columns after a year change in
  the file are dated in the following year (existing behaviour, must continue to hold for every
  year, not only 2026→2027).
- **Cumul groups / phases with active dates beyond 2026**: active_from/active_to and phase dates in
  2027+ are accepted and evaluated exactly as dates in 2026 are.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The dashboard timeline MUST NOT be limited to any fixed end year; calendar weeks in any
  year for which the loaded absence file contains dates MUST be reachable, either within the default
  rolling window (FR-007) or by setting the time filter.
- **FR-002**: Every calendar week MUST be uniquely identified by its ISO year and week number;
  absence, phase, cumul-risk and sole-coverage markers MUST be attributed to the correct year/week
  pair and never to a same-numbered week in another year.
- **FR-003**: Calendar-week labels MUST include enough year information that the manager can tell
  weeks with the same number in different years apart (e.g. "CW5 2027").
- **FR-004**: The dashboard MUST provide a time filter with a "From" month and a "To" month, each
  expressed as MM/YYYY.
- **FR-005**: When a filter is applied, the timeline MUST show exactly those calendar weeks that
  contain at least one working day (Mon–Fri) between the first day of the "From" month and the last
  day of the "To" month, inclusive.
- **FR-006**: The system MUST reject a filter where "To" is earlier than "From", or where either
  value is not a valid MM/YYYY month, with a clear message, and MUST keep the previously applied
  range in that case.
- **FR-007**: When no filter has been set by the manager, the timeline MUST show a rolling 12-month
  timeframe: from the current calendar week up to and including the calendar week that contains the
  same date 12 months later (e.g. on 13 October 2026: CW42 2026 to the week containing 13 October
  2027). The default is recalculated each time the dashboard is opened or refreshed, so it moves
  forward with the current date, independent of how far the loaded file extends. Weeks in the
  default window not covered by the file are shown empty.
- **FR-008**: The manager MUST be able to reset the filter to the default range in a single action.
- **FR-009**: The applied range MUST remain in effect when the manager refreshes/reloads absence data
  during the same session, and MUST be visible in the filter controls at all times; while no filter
  is set, the controls MUST indicate that the rolling 12-month default is active.
- **FR-010**: The filter MUST only affect which weeks are displayed. Critical-absence detection,
  cumul-risk weeks, sole-coverage flags and merged absence blocks MUST be computed on the full
  absence data, so a visible week shows the same markers filtered or unfiltered.
- **FR-011**: Phases partially overlapping the selected range MUST be shown clipped to the visible
  weeks with their full dates available in their details; phases entirely outside the range MUST be
  hidden from the timeline but remain listed and editable in phase management.
- **FR-012**: Dates entered for phases and for cumul-group active periods MUST be accepted for any
  year, including years after 2026.
- **FR-013**: If the selected range contains no dates covered by the loaded file, the dashboard MUST
  display a notice saying so instead of silently showing an empty timeline.
- **FR-014**: Reading of the absence file MUST continue to date columns correctly across any number
  of year boundaries contained in the file.

### Key Entities

- **Calendar week**: an ISO week identified by (ISO year, week number), with its Monday–Friday
  working days and a display label including the year.
- **Time filter**: a "From" month and a "To" month (each month + year), inclusive, chosen by the
  manager for the current session. When unset, the rolling 12-month default window (current week
  to the week containing the same date one year later) applies.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of absences in a loaded file are reachable in the timeline for dates up to at
  least 31 December 2030, without any software change.
- **SC-002**: In a timeline spanning two or more years, 0 markers (absence, phase, cumul risk, sole
  coverage) appear in a week of the wrong year.
- **SC-003**: The dashboard displays a 24-month range in under 2 seconds with the usual team size.
- **SC-004**: A manager can narrow the view to a chosen month range in under 15 seconds and with no
  more than 3 interactions after opening the dashboard.
- **SC-005**: For every visible week, cumul-risk and sole-coverage markers are identical between the
  filtered and unfiltered view (verified on a sample covering filter edges that cut through long
  absences).

## Assumptions

- The absence file remains the single source of dates; the dashboard does not invent data for weeks
  the file does not cover (it may show such weeks empty, see FR-013).
- Past months are selectable in the filter, so the manager can review history as long as the loaded
  file contains it.
- The filter is a viewing preference for the current session only; it is not persisted across
  application restarts and returns to the default range on restart. This avoids a stale saved
  "From" month hiding the current period.
- The filter is applied manually (e.g. via an Apply action) rather than on every keystroke; this is
  a UX detail that can be refined during planning.
- No maximum range length is enforced; usability for long ranges is covered by SC-003.
- The definition of "working day" (Mon–Fri) and of a "critical absence" (continuous absence of more
  than 5 calendar days) from feature 006 are unchanged.
- No existing data (phases, cumul groups, clusters) needs migration; existing dates remain valid.
