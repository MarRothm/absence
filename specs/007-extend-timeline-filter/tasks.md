# Tasks: Extended Timeline with Month-Range Filter

**Input**: Design documents from `specs/007-extend-timeline-filter/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/dashboard-time-range-api.md, quickstart.md

**Tests**: REQUIRED — Constitution Principle II (TDD, non-negotiable). Every test task MUST be run
and confirmed **failing** before its implementation task starts.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested
independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1 / US2 / US3 from spec.md

## Path Conventions

Single Flask project: backend in `absence_dashboard/`, frontend in `absence_dashboard/static/`,
tests in `tests/unit/` (pure functions, no I/O) and `tests/integration/test_app.py`
(`app.test_client()`; shared fixtures `client`, `app`, `sample_xlsx` in `tests/conftest.py`).
Run tests with `.venv/bin/python -m pytest -q`.

---

## Phase 1: Setup

**Purpose**: Confirm a green baseline before changing anything.

- [X] T001 Run `.venv/bin/python -m pytest -q` from repo root and confirm the baseline passes (227 tests at plan time); record the count in the PR description

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared week builder used by the rolling default (US1) and the month filter (US2).

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T002 Write failing unit tests in new file `tests/unit/test_timeline.py`, class `TestBuildCalendarWeeks`, for `build_calendar_weeks(start: date, end: date) -> list[dict]` from `absence_dashboard.timeline`: (a) each week dict has keys `key`, `year`, `week_number`, `label`, `start`, `end`, `days`; (b) `key` is `f"{iso_year}-W{week:02d}"`, e.g. `"2027-W05"`; (c) `label` is `f"CW{week} {iso_year} | {monday.day} {monday:%b}"`, e.g. `build_calendar_weeks(date(2027,2,1), date(2027,2,5))[0]["label"] == "CW5 2027 | 1 Feb"`; (d) `days` are the five Mon–Fri ISO strings, `start`/`end` = Monday/Friday; (e) a week is included iff at least one Mon–Fri day lies in `[start, end]`: `build_calendar_weeks(date(2026,8,1), date(2026,8,31))[0]["key"] == "2026-W32"` (Sat 1 Aug excludes W31) and `build_calendar_weeks(date(2026,5,1), date(2026,5,31))[-1]["key"] == "2026-W22"` (Sun 31 May excludes W23); (f) ISO week 53: `build_calendar_weeks(date(2026,12,28), date(2027,1,8))` keys are `["2026-W53", "2027-W01"]`; (g) chronological, no duplicates, no gaps over a 2-year span; (h) `start > end` returns `[]`
- [X] T003 Create `absence_dashboard/timeline.py` (pure, no I/O, module docstring + section comments in the style of `absence_dashboard/cumul_groups.py`) implementing `build_calendar_weeks(start, end)` to make T002 pass: iterate Mondays from the Monday of `start`'s ISO week through the Monday of `end`'s ISO week, keep weeks where any Mon–Fri day is within `[start, end]`, build the dict shape above (keep the existing `year`/`week_number`/`start`/`end`/`days` fields exactly as `_build_calendar_weeks` in `absence_dashboard/app.py` produces them today, add `key`, change `label`)

**Checkpoint**: `tests/unit/test_timeline.py::TestBuildCalendarWeeks` green; rest of suite unchanged.

---

## Phase 3: User Story 1 — Plan absences beyond December 2026 (Priority: P1) 🎯 MVP

**Goal**: Timeline is a rolling 12-month window (current ISO week → week containing today + 1 year),
weeks are identified by year+week everywhere, and the Excel file is dated in the right year after
2026.

**Independent Test**: Load a file spanning late 2026 into 2027 with absences in 2027 (within 12
months of today); without touching anything, the 2027 weeks show with year labels and the last week
is the one containing today's date next year.

### Tests for User Story 1 ⚠️ (write first, confirm FAILING)

- [X] T004 [P] [US1] Add class `TestDefaultRange` to `tests/unit/test_timeline.py` for `default_range(today: date) -> tuple[date, date]`: `default_range(date(2026,10,13)) == (date(2026,10,12), date(2027,10,13))`; start is always the Monday of today's ISO week (test with a Sunday, e.g. `date(2026,10,18)` → `date(2026,10,12)`); `default_range(date(2028,2,29))[1] == date(2029,2,28)`; and `build_calendar_weeks(*default_range(date(2026,10,13)))` runs from key `"2026-W42"` to `"2027-W41"`
- [X] T005 [P] [US1] Add class `TestBuildDateMapYearInference` to `tests/unit/test_parser.py` (reuse the `_make_ws` helper pattern from `TestBuildDateMap`) for `build_date_map(ws, year=None, today=None)`: (a) columns `KW18 Mo … KW53 Fr` with `today=date(2026,10,13)` → `dm[6] == date(2026,4,27)`; (b) same sheet with `today=date(2027,1,15)` → still 2026 dates and **no `ValueError`** (2027 has no W53); (c) a rolling sheet `KW40 Mo`, `KW52 Fr`, `KW1 Mo`, `KW39 Fr` with `today=date(2027,8,1)` → first column `date(2026,9,28)` and `KW1 Mo` → `date(2027,1,4)`; (d) `KW18 Mo` with `today=date(2026,10,13)` → 2026 (closest span wins over 2027); (e) explicit `year=` bypasses inference (`build_date_map(ws, year=2030, today=date(2026,1,1))` dates in 2030); (f) sheet with no week numbers → `{}`
- [X] T006 [P] [US1] Update `tests/unit/test_cumul_groups.py`: extend `_week(...)` helper to also emit `"key": f"{year}-W{week_number:02d}"`; change every assertion on `compute_cumul_risk_weeks` / `compute_sole_coverage_weeks` return values from week numbers (e.g. `[19]`) to week keys (e.g. `["2026-W19"]`); add `test_same_week_number_in_different_years_kept_apart` with calendar weeks `2026-W05` and `2027-W05` where only the 2027 week has overlapping critical absences → result `["2027-W05"]`
- [X] T007 [US1] Update `tests/integration/test_app.py` class `TestGetDashboard`: replace `test_calendar_weeks_ends_at_cw53_2026` with `test_calendar_weeks_end_at_week_containing_today_next_year` (last week's `days` range must contain `default_range(date.today())[1]`'s Mon–Fri week, i.e. `weeks[-1]["key"] == build_calendar_weeks(*default_range(date.today()))[-1]["key"]`); add `test_calendar_weeks_have_unique_key` and `test_calendar_week_label_contains_year`; update `test_calendar_week_label_format` to the new `"CW{n} {year} | {d} {Mon}"` format; in `TestCumulRiskWeeks` and `TestSoleCoverage` replace `week_number` comparisons on `cumul_risks` / `sole_coverage` entries with `week_key` (`f"{critical_weeks['year']}-W{wn:02d}"`); make the `critical_weeks` fixture year-safe by computing the three Mondays as `date.fromisocalendar(*today_iso[:2], 1) + timedelta(weeks=k)` for k=1..3 and deriving `year`/`week_numbers` from each Monday's `isocalendar()` (store a `keys` list) instead of `start_week + n`, so the suite passes in late December
- [X] T008 [US1] Run `.venv/bin/python -m pytest -q tests/unit/test_timeline.py tests/unit/test_parser.py tests/unit/test_cumul_groups.py tests/integration/test_app.py` and confirm T004–T007 fail for the expected reasons (missing function / old values), not for typos

### Implementation for User Story 1

- [X] T009 [P] [US1] Add `default_range(today: date) -> tuple[date, date]` to `absence_dashboard/timeline.py` (start = Monday of today's ISO week; end = same month/day next year, falling back to 28 Feb for 29 Feb) — makes T004 pass
- [X] T010 [P] [US1] Implement start-year inference in `absence_dashboard/parser.py` `build_date_map(ws, year=None, today=None)` per research R4: extract the per-column `(col_idx, week_number, weekday)` list once (keeping the existing merged-cell forward-fill); if `year` is given use it; otherwise for candidates `today.year-1, today.year, today.year+1` build the map (with the existing roll-over on decreasing week number), discard candidates where `date.fromisocalendar` raises `ValueError`, pick the one whose `[min, max]` date span is closest to `today` (0 if inside), ties → earlier year; update the docstring paragraph about `year` defaulting — makes T005 pass and existing `TestBuildDateMap` tests stay green
- [X] T011 [P] [US1] Change `compute_cumul_risk_weeks` and `compute_sole_coverage_weeks` in `absence_dashboard/cumul_groups.py` to collect `cw["key"]` instead of `cw["week_number"]` (return sorted list of keys / dict of member → list of keys); update their docstrings/type hints — makes T006 pass
- [X] T012 [US1] In `absence_dashboard/app.py`: delete `_last_iso_week` and `_build_calendar_weeks` (and the "Calendar week helpers" section header); import `build_calendar_weeks`, `default_range` from `absence_dashboard.timeline`; in `_assemble_dashboard` build `calendar_weeks = build_calendar_weeks(*default_range(date.today()))`; emit risk entries as `{"group": ..., "week_key": key}` (rename loop variables accordingly) — depends on T003, T009, T011; makes T007 pass
- [X] T013 [US1] Re-key the frontend on week keys in `absence_dashboard/static/main.js`: `buildDayIndex` pushes `{ date, week: cw.key }`; `groupByWeek` destructures `week_key`; `cumulRiskWeekSet` maps `r.week_key`; build a `weekLabel` lookup (`Map` of `cw.key` → `"CW{week_number} {year}"`) in `renderTimeline` and use it in the cumul-risk cell tooltip (`Cumul risk CW5 2027: …`), the in-cell week label (currently around `labeledWeeks`), and the sole-coverage badge title (replace `CW${weeks.join(", CW")}` with the joined labels); grep the file for any remaining `week_number` use on risk entries and convert it
- [X] T014 [US1] Check `absence_dashboard/static/style.css` `.tg-cw-group` header cells still fit the longer `CW5 2027 | 1 Feb` label (allow wrapping or reduce font-size if it overflows); manually load `.venv/bin/python run.py absences.xlsx` and confirm labels/tooltips render

**Checkpoint**: Full suite green; dashboard shows CW42 2026 → CW41 2027 (on 2026-10-13) with year labels; `absences.xlsx` still dated in 2026. US1 is shippable on its own.

---

## Phase 4: User Story 2 — Restrict the view to a month range (Priority: P2)

**Goal**: Manager enters From/To (MM/YYYY), sees only weeks touching that range, can reset; invalid
input rejected; filter survives Reload and panel edits for the session; notice when the file has no
data in range.

**Independent Test**: Apply 11/2026 – 02/2027 → only weeks touching those months, CW53 2026 once;
Reset → rolling 12 months; 02/2027 – 01/2027 → error, previous view kept.

### Tests for User Story 2 ⚠️ (write first, confirm FAILING)

- [X] T015 [P] [US2] Add classes `TestParseMonth` and `TestResolveRange` to `tests/unit/test_timeline.py`: `parse_month("03/2027") == (2027, 3)`, `parse_month("3/2027") == (2027, 3)`, `parse_month(" 03/2027 ")` accepted; `ValueError` for `"13/2027"`, `"00/2027"`, `"2027"`, `"03/27"`, `"03-2027"`, `""`; `resolve_range(None, None, today)` returns `(*default_range(today), True)`; `resolve_range("01/2027", "03/2027", today) == (date(2027,1,1), date(2027,3,31), False)`; `resolve_range("02/2028", "02/2028", today)[1] == date(2028,2,29)`; `ValueError` when only one of from/to given, when `to < from`; and `build_calendar_weeks(*resolve_range("01/2027","01/2027",today)[:2])[0]["key"] == "2026-W53"` (Fri 1 Jan 2027 is in 2026-W53)
- [X] T016 [P] [US2] Add class `TestTimeRangeFilter` to `tests/integration/test_app.py`: `GET /api/dashboard?from=11/2026&to=02/2027` → 200, first week key `"2026-W45"` (Sun 1 Nov excludes W44) … last `"2027-W08"` (Sun 28 Feb excludes nothing later), `"2026-W53"` present exactly once; `time_range == {"start": "2026-11-01", "end": "2027-02-28", "from": "11/2026", "to": "02/2027", "is_default": False}`; no params → `time_range["is_default"] is True`; 400 with `error` mentioning `MM/YYYY` for `from=13/2026&to=02/2027` and for `from=11/2026` only; 400 for `from=02/2027&to=01/2027`; `POST /api/refresh?from=11/2026&to=02/2027` → 200 with same `time_range`, and `POST /api/refresh?from=bad&to=02/2027` → 400 without reloading (assert `app.config["LAST_LOADED"]` unchanged); `data_in_range` is `True` for `from=04/2026&to=05/2026` with the `client` fixture (whose file covers 2026-04-27…2026-05-05) and `False` for `from=01/2030&to=02/2030`; a multi-year request `from=01/2027&to=12/2028` returns both `"2027-W05"` and `"2028-W05"` with distinct labels (FR-002/FR-003)
- [X] T017 [P] [US2] Add test to `tests/unit/test_parser.py` for `parse_members(ws, date_map=...)`: passing a precomputed map is used as-is (e.g. a map that shifts column 6 to `date(2030,1,7)` yields that absence date), and calling without `date_map` behaves as before
- [X] T018 [US2] Run `.venv/bin/python -m pytest -q` and confirm T015–T017 fail for the expected reasons

### Implementation for User Story 2

- [X] T019 [P] [US2] Add `parse_month(value: str) -> tuple[int, int]` (strip, regex `^(\d{1,2})/(\d{4})$`, month 1–12, else `ValueError(f"Invalid month '{value}' — expected MM/YYYY.")`) and `resolve_range(from_s, to_s, today) -> tuple[date, date, bool]` (both None → default; exactly one → `ValueError("Both 'from' and 'to' are required (MM/YYYY).")`; `to < from` → `ValueError("'To' month must be the same as or later than 'From' month.")`; end = last day via `calendar.monthrange`) to `absence_dashboard/timeline.py` — makes T015 pass
- [X] T020 [P] [US2] Add optional `date_map: dict = None` parameter to `parse_members(ws, date_map=None)` in `absence_dashboard/parser.py` (use it when given, else `build_date_map(ws)`) — makes T017 pass
- [X] T021 [US2] In `absence_dashboard/app.py`: (a) `_load_excel` builds `date_map = build_date_map(ws)` once, passes it to `parse_members(ws, date_map=date_map)`, and returns an extra `data_range` = `(min(date_map.values()), max(date_map.values()))` or `None`; store it as `app.config["DATA_RANGE"]` in `create_app` and in `post_refresh` (update both unpacking sites); (b) change `_assemble_dashboard(app)` to `_assemble_dashboard(app, start, end, is_default)` building `calendar_weeks = build_calendar_weeks(start, end)` and adding `"time_range": {"start", "end", "from": f"{start:%m/%Y}", "to": f"{end:%m/%Y}", "is_default"}` and `"data_in_range"` (overlap of `DATA_RANGE` with `[start, end]`, `False` if `None`); (c) add helper `_requested_range()` that calls `resolve_range(request.args.get("from"), request.args.get("to"), date.today())`; in `get_dashboard` and at the **top** of `post_refresh` (before `_load_excel`) catch `ValueError` → `jsonify({"error": str(e)}), 400` — depends on T019, T020; makes T016 pass
- [X] T022 [P] [US2] Add the time-filter control group to the header in `absence_dashboard/static/index.html` after `#btn-toggle-clusters`, per contracts UI section: `<input type="text" id="time-from" placeholder="MM/YYYY" size="7">`, `<input type="text" id="time-to" placeholder="MM/YYYY" size="7">` with visible "From"/"To" labels, `<button id="btn-time-apply" class="btn btn-secondary">Apply</button>`, `<button id="btn-time-reset" class="btn btn-secondary">Reset</button>`, `<span id="time-range-status"></span>`, `<div id="time-error" class="inline-error hidden"></div>`
- [X] T023 [P] [US2] Style the time-filter group in `absence_dashboard/static/style.css` (inline flex, compact inputs, status text muted; reuse existing `.btn`/`.inline-error` classes)
- [X] T024 [US2] Wire the filter in `absence_dashboard/static/main.js`: add `let timeFilter = null; // { from, to } (MM/YYYY) or null = rolling 12-month default — session only` next to `showAll`; add `dashboardUrl(path)` that appends `?from=…&to=…` via `URLSearchParams` when `timeFilter` is set; use it in `refreshDashboard()` (`/api/dashboard`) and the Reload handler (`/api/refresh`); add `isValidMonth(s)` (`/^\s*(0?[1-9]|1[0-2])\/\d{4}\s*$/`) and `monthIndex(s)` (year*12+month) for client-side checks; Apply handler: validate both fields and order, show message in `#time-error` and return without changing `timeFilter` on failure, else set `timeFilter`, call `refreshDashboard()`, and if the response is 400 restore the previous `timeFilter` and show the server `error`; Reset handler: `timeFilter = null`, clear inputs/error, `refreshDashboard()`; add `renderTimeRange(data)` called from both render paths that sets `#time-range-status` to `Rolling 12 months (CW… – CW…)` using first/last `calendar_weeks` labels when `data.time_range.is_default`, else `${from} – ${to}`, and fills the inputs from `data.time_range` when a filter is applied; when `data.data_in_range === false` call `showWarning("The loaded file contains no data for the selected range.", "no-data-in-range")` (avoid duplicates by checking for an existing banner with that `data-warn-id`) — depends on T021, T022

**Checkpoint**: Full suite green; filter applies/reset/rejects as in quickstart steps 2–5; Reload keeps the filter.

---

## Phase 5: User Story 3 — Filtered view keeps risk information correct (Priority: P3)

**Goal**: Filtering only hides weeks: markers in visible weeks are identical filtered vs unfiltered;
critical absences crossing the filter edge still count; phases are clipped or hidden correctly.

**Independent Test**: A long absence starting before the From month still produces the same
cumul-risk markers in the visible weeks; a phase entirely outside the range disappears from the
timeline but stays in the Phases panel.

### Tests for User Story 3 ⚠️ (write first, confirm FAILING or passing-by-design)

- [X] T025 [US3] Add class `TestFilterDoesNotChangeRisk` to `tests/integration/test_app.py` with its own fixture building a workbook (pattern of `critical_workbook`) around a month boundary `M` = first day of the month two months after today: Alice absent the 5 working days before `M` plus the first 3 working days on/after `M` (> 5 calendar days, critical), Bob absent the first 6 working days on/after `M`, both in a cumul group created via `POST /api/cumul-groups`; assert (a) `GET /api/dashboard?from={M:%m/%Y}&to={M:%m/%Y}` yields Alice `cumul_risks` for the week(s) after `M` where both overlap, and (b) for every `week_key` present in the filtered `calendar_weeks`, the set of Alice's and Bob's `cumul_risks`/`sole_coverage` entries equals that from `GET /api/dashboard` (default) restricted to the same keys (SC-005); and (c) `merged_blocks` are identical in both responses (unclipped). These are expected to pass once US1+US2 are in (FR-010 holds by design, research R5) — run once before T021 is merged to confirm the test exercises the code (it must fail with 400/KeyError on the old code)
- [X] T026 [P] [US3] Add test to `tests/integration/test_app.py` class `TestTimeRangeFilter`: after `POST /api/phases` with a phase entirely outside the filter (e.g. `2027-06-01`–`2027-06-30` with `from=01/2027&to=03/2027`), the filtered `/api/dashboard` still returns it in `phases` and `GET /api/phases` lists it (the panel is fed from all phases; hiding is a frontend concern)

### Implementation for User Story 3

- [X] T027 [US3] In `renderTimeline` in `absence_dashboard/static/main.js`, skip a phase row (do not append it) when no `dayIndex` date lies within `[phase.start_date, phase.end_date]`; keep the existing clipped rendering and full-date `title` tooltips for partially visible phases; confirm `renderPhases` (side panel) still lists every phase
- [X] T028 [US3] Manually verify in the running app (`.venv/bin/python run.py absences.xlsx`): a phase spanning beyond the filter edge is drawn up to the edge with its full dates in the tooltip; a phase fully outside is hidden in the timeline and still editable in the Phases panel

**Checkpoint**: All three stories functional and independently verified.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T029 [P] Update `README.md` usage section with a short note on the rolling 12-month default and the From/To filter (MM/YYYY)
- [X] T030 Grep the repo for leftover year bounds and week-number-only keying (`2026` in `absence_dashboard/`, `week_number` on risk entries in `absence_dashboard/static/main.js`, `_build_calendar_weeks` anywhere) and remove/convert any found
- [X] T031 Run the full suite `.venv/bin/python -m pytest -q` (must be green, count ≥ baseline from T001 minus the one replaced test) and walk through every step of `specs/007-extend-timeline-filter/quickstart.md` "Verifying (manual)", including the 24-month range render time (< 2 s, SC-003)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → user stories.
- **US1 (Phase 3)** depends on Phase 2.
- **US2 (Phase 4)** depends on Phase 2 and on US1's T012 (`_assemble_dashboard` already using `timeline.py` and `week_key`) and T013 (frontend keyed on `cw.key`; multi-year filtered views would otherwise collide).
- **US3 (Phase 5)** depends on US2 (needs `from`/`to` query parameters).
- **Polish (Phase 6)** after all desired stories.

### Within Each User Story

- Tests first, run, confirm failing (T008, T018, T025 note) → implementation.
- `timeline.py` / `parser.py` / `cumul_groups.py` changes before `app.py`; `app.py` before `main.js`.

### Parallel Opportunities

- T004, T005, T006 (three different test files) in parallel; T007 after them only because it imports from `timeline` for the expected value.
- T009, T010, T011 (three different modules) in parallel.
- T015, T016, T017 in parallel; T019, T020, T022, T023 in parallel.
- T026 in parallel with T025 (same file but independent classes — coordinate edits).

---

## Parallel Example: User Story 1

```bash
# Tests (different files):
Task: "T004 TestDefaultRange in tests/unit/test_timeline.py"
Task: "T005 TestBuildDateMapYearInference in tests/unit/test_parser.py"
Task: "T006 week-key assertions in tests/unit/test_cumul_groups.py"

# Implementation (different files):
Task: "T009 default_range in absence_dashboard/timeline.py"
Task: "T010 year inference in absence_dashboard/parser.py"
Task: "T011 week keys in absence_dashboard/cumul_groups.py"
```

## Parallel Example: User Story 2

```bash
Task: "T019 parse_month/resolve_range in absence_dashboard/timeline.py"
Task: "T020 parse_members(date_map=) in absence_dashboard/parser.py"
Task: "T022 filter controls in absence_dashboard/static/index.html"
Task: "T023 filter styling in absence_dashboard/static/style.css"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 + Phase 2.
2. Phase 3 (US1) → **stop and validate**: rolling window, year labels, `absences.xlsx` dated 2026.
3. This alone removes the December 2026 cliff and the January 2027 file-load crash — shippable.

### Incremental Delivery

1. US1 → ship (timeline keeps working past 2026).
2. US2 → ship (month-range filter).
3. US3 → ship (edge-correctness guarantees + phase hiding).

---

## Implementation Notes

- **Test fixture pinned to 2026 (unplanned, needed for T005/T010)**: with year inference, the shared
  `sample_workbook` (KW18–KW19, no year) would be dated in 2027 from ~30 Oct 2026 onwards, breaking
  ~20 existing tests that expect 2026 dates (the old "current year" rule would have broken them on
  1 Jan 2027). `tests/conftest.py` now has a `parser_today_2026` fixture that pins the parser's
  "today" to 2026-05-01; `sample_workbook` depends on it.
- **Header layout (T014/T023)**: CW labels render on two lines ("CW42 2026" / "12 Oct"). With the
  filter controls the header can wrap on narrow screens (≈1280 px), so `body` is now a flex column
  and `.app-body` takes the remaining height instead of `calc(100vh - 50px)`.
- **T025**: the two risk-equality tests fail against the pre-feature backend; the "phases still
  listed" and "merged blocks unclipped" tests pass on it by design and act as regression guards.
- **Verification**: UI scenarios (default range, 11/2026–02/2027, reversed/invalid input, Reload
  keeps filter, no-data notice, Reset, 24-month range = 105 weeks rendered in ~40 ms, phase
  clipping/hiding) were driven in headless Chrome against `absences.xlsx`.
