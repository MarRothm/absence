# Tasks: Absence Management Dashboard

**Input**: Design documents from `specs/001-absence-dashboard/`
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅, contracts/api.md ✅

**Format**: `[ID] [P?] [Story] Description with file path`
- **[P]**: Can run in parallel (different files, no unmet dependencies)
- **[Story]**: User story this task belongs to (US1–US5; omitted for Setup/Foundational/Polish)
- **TDD is NON-NEGOTIABLE** (Constitution Principle II): every logic module has its test written
  and confirmed failing before implementation begins

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization, directory scaffolding, and shared test fixtures.

- [x] T001 Create project directory structure: `absence_dashboard/`, `absence_dashboard/static/`, `state/`, `tests/`, `tests/unit/`, `tests/integration/`, `tests/fixtures/` per `specs/001-absence-dashboard/plan.md`
- [x] T002 Create `absence_dashboard/requirements.txt` with pinned versions: `Flask>=3.0`, `openpyxl>=3.1`, `pytest>=7.0`, `pytest-flask>=1.3`
- [x] T003 [P] Create `tests/conftest.py` with: (a) `app` fixture returning the Flask app pointed at a temp Excel file, (b) `client` fixture using `pytest-flask`, (c) `sample_workbook` fixture that builds an in-memory `.xlsx` workbook via openpyxl matching the confirmed grid layout — Row 1 CW labels, Row 2 weekday names, Col C "Projekt Migration", Col D "Team Mitglied ", Col F = 2026-04-27; 5 data rows, 3 marked "x" in Col C, with known absence patterns for deterministic assertions
- [x] T004 [P] Create `run.sh` (convenience wrapper: `python absence_dashboard/app.py "$@"`) and stub `README.md` pointing to `specs/001-absence-dashboard/quickstart.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Excel parser, absence merger, state persistence, and Flask skeleton — shared by all
user stories. All tests must be written and confirmed failing before any implementation starts.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

### parser.py

- [x] T005 [P] Write failing unit tests for `absence_dashboard/parser.py` in `tests/unit/test_parser.py`: working-day offset mapping (Col F index 6 → 2026-04-27, index 7 → 2026-04-28, index 11 → 2026-05-04 skipping weekend), "x" detection (case-insensitive, whitespace-stripped), Col C filter (only "x" rows included), Col D name extraction (whitespace-stripped), rows 1–2 skipped as headers, empty-name data rows skipped with warning entry, multi-row same-name person aggregated into one entry
- [x] T006 Implement `absence_dashboard/parser.py`: `build_date_map(ws) → dict[int, date]` (column index ≥ 6 → working date starting 2026-04-27, skipping Sat/Sun), `parse_members(ws) → tuple[list[PersonAbsence], list[SkippedRow]]` — confirm T005 now passes

### merger.py

- [x] T007 [P] Write failing unit tests for `absence_dashboard/merger.py` in `tests/unit/test_merger.py`: overlapping date spans merged into one, adjacent spans (end+1 = next start) merged, non-adjacent spans kept separate, single-day span preserved, empty input returns empty list, multiple disjoint spans returned in sorted order
- [x] T008 [P] Implement `absence_dashboard/merger.py`: `merge_periods(dates: list[date]) → list[AbsencePeriod]` using sort-then-sweep (sort dates, group consecutive working days into spans) — confirm T007 now passes

### state.py

- [x] T009 Write failing unit tests for `absence_dashboard/state.py` in `tests/unit/test_state.py`: `load_state` on missing file returns empty `AppState`, `load_state` on valid JSON deserialises dependencies and clusters correctly, `save_state` writes valid JSON, round-trip load→save→load preserves all data, `save_state` creates `state/` directory if it does not exist
- [x] T010 Implement `absence_dashboard/state.py`: `AppState` dataclass (`dependencies: list[dict]`, `clusters: list[dict]`), `load_state(path: str) → AppState`, `save_state(state: AppState, path: str) → None` — confirm T009 now passes

### Flask skeleton

- [x] T011 Create `absence_dashboard/app.py`: parse `sys.argv[1]` as Excel file path (print actionable error and `sys.exit(1)` if missing or file not found); initialise Flask app; load `state/state.json` at startup via `state.load_state`; stub all `/api/*` routes returning `{"error": "not implemented"}, 501`; `GET /` serves `absence_dashboard/static/index.html`
- [x] T012 Create `absence_dashboard/static/index.html`: full-page HTML shell with `<div id="timeline-grid">`, `<div id="dependency-panel">`, `<div id="cluster-panel">`, `<div id="warnings">` placeholders; `<link>` to `style.css`; `<script src="main.js">`; Reload button (`id="btn-reload"`) in header
- [x] T013 [P] Create `absence_dashboard/static/style.css`: CSS custom properties for colours (`--color-absent`, `--color-at-risk`, `--color-bottleneck-absent`, `--color-bottleneck-row`); CSS grid layout for `.timeline-grid` (auto rows, columns = CW count); sticky first-column member names; cluster-group separator rows; overflow-x scroll for wide grids; responsive panel layout for dependency and cluster sections

**Checkpoint**: Flask starts, validates CLI arg, serves index.html, all stubs return 501. All
foundational tests pass (T005–T010).

---

## Phase 3: User Story 1 — Absence Timeline View (Priority: P1) 🎯 MVP

**Goal**: Gantt-style absence grid showing one row per filtered member, one column per calendar
week CW19–CW53 2026, with correctly merged absence blocks. No interactivity required.

**Independent Test**: Load dashboard with `sample.xlsx` (3 of 5 members marked). Verify: exactly
3 rows shown; overlapping absences correctly merged; calendar weeks run from current week to
year-end; no earlier weeks visible; member with no absences shows empty row.

### Tests for US1

- [x] T014 [P] [US1] Write failing integration tests for `GET /api/dashboard` in `tests/integration/test_app.py`: response contains exactly 3 members (matching filtered names), `merged_blocks` are non-overlapping and sorted, `calendar_weeks` array starts at current ISO week and ends at last ISO week of 2026, no duplicate week entries, `skipped_rows` list present (empty for clean fixture), HTTP 200

### Implementation for US1

- [x] T015 [US1] Implement `GET /api/dashboard` in `absence_dashboard/app.py`: call `parser.parse_members(ws)`, call `merger.merge_periods` per member, call `build_calendar_weeks(current_week, end_of_year)`, assemble full `DashboardData` JSON (`calendar_weeks`, `members` with `name`/`merged_blocks`/`is_bottleneck=false`/`at_risk_weeks=[]`/`depends_on=[]`/`clusters=[]`, `dependencies=[]`, `skill_clusters=[]`, `skipped_rows`, `bottlenecks=[]`) — confirm T014 now passes
- [x] T016 [P] [US1] Add `build_calendar_weeks(from_iso: tuple, to_iso: tuple) → list[dict]` helper in `absence_dashboard/app.py`: iterate ISO weeks from current week through last ISO week of 2026; each entry has `year`, `week_number`, `start` (Monday ISO date string), `end` (Friday ISO date string), `days` (list of 5 working-day ISO date strings Mon–Fri), `label` (format `"CW[N] | D Mon"` e.g. `"CW19 | 4 May"` — clarification 2026-05-08)
- [x] T017 [US1] Implement timeline rendering in `absence_dashboard/static/main.js`: `fetchDashboard()` calls `GET /api/dashboard`; `renderTimeline(data)` builds HTML `<table>` — two-row header: row 1 one `<th colspan="5">` per CW showing the `label` (e.g. `"CW19 | 4 May"`); row 2 one `<th>` per working day showing weekday abbreviation only (Mon/Tue/Wed/Thu/Fri, no dates — clarification 2026-05-08); one `<td>` per working day per member; colours absence cells per `merged_blocks` using `absent-start`/`absent-mid`/`absent-end`/`absent-single` CSS classes for continuous bars across week boundaries; member name in sticky first column; ungrouped members in alphabetical order
- [x] T018 [US1] Add empty-state handling in `absence_dashboard/static/main.js`: if `members` array is empty render "No project members found — verify 'Projekt Migration' column contains 'x' values" message inside `#timeline-grid`; if `skipped_rows` non-empty show count in `#warnings`

**Checkpoint**: US1 fully functional. `python app.py absences.xlsx` → `localhost:5000` shows
correct Gantt grid with merged absence blocks for all ~20 filtered members.

---

## Phase 4: User Story 2 — Dependency Visualization (Priority: P2)

**Goal**: Manager adds/views/removes directed dependencies (A depends on B) in the UI. A's row
shows at-risk indicators for every calendar week where B is absent.

**Independent Test**: Add A→B via UI. Mark B absent in CW23 in fixture. Verify A's CW23 cell
shows at-risk colour; A's cells where B is present show no indicator; no-dependency rows
unaffected.

### Tests for US2

- [x] T019 [P] [US2] Write failing unit tests for `absence_dashboard/graph.py` in `tests/unit/test_graph.py`: `add_edge` stores edge, `remove_edge` removes it (404 on missing), self-loop raises `ValueError`, duplicate edge raises `ValueError`, direct cycle A→B + B→A detected and rejected, indirect cycle A→B→C→A detected and rejected, `get_bottlenecks` returns member with ≥2 incoming, excludes member with exactly 1 incoming, `get_at_risk_weeks` returns correct CW numbers where target is absent

### Implementation for US2

- [x] T020 [US2] Implement `absence_dashboard/graph.py`: `DependencyGraph` class — `add_edge(source, target, members)` (validates names, calls `_has_cycle`, stores edge), `remove_edge(source, target)`, `_has_cycle(source, target) → bool` (iterative DFS), `get_bottlenecks(edges) → set[str]` (count incoming per node, return those with ≥2), `compute_at_risk_weeks(member_name, edges, member_blocks_map, calendar_weeks) → list[int]` — confirm T019 now passes
- [x] T021 [US2] Wire `graph.py` into `GET /api/dashboard` in `absence_dashboard/app.py`: load `AppState.dependencies`, call `get_bottlenecks`, call `compute_at_risk_weeks` per member, populate `is_bottleneck`, `at_risk_weeks`, `depends_on` fields in response
- [x] T022 [P] [US2] Write failing integration tests for dependency endpoints in `tests/integration/test_app.py`: `POST /api/dependencies` returns 201 with updated list on valid input; 400 on unknown member name; 409 on cycle (response includes `cycle_path`); 409 on duplicate; `DELETE /api/dependencies` returns 200 on success; 404 on non-existent edge; state persisted after each mutation
- [x] T023 [US2] Implement `POST /api/dependencies` and `DELETE /api/dependencies` routes in `absence_dashboard/app.py`: validate both names exist in loaded member set, call `graph._has_cycle`, update `AppState`, call `save_state` — confirm T022 now passes
- [x] T024 [US2] Add dependency management panel to `absence_dashboard/static/main.js` and `index.html`: "From" and "To" `<select>` dropdowns populated from `members[]`, Add Dependency button calls `POST /api/dependencies`, dependency list rendered with ✕ remove button per entry calling `DELETE /api/dependencies`, full timeline re-renders on change
- [x] T025 [US2] Add at-risk cell colouring in `absence_dashboard/static/main.js`: for each member apply `--color-at-risk` to cells whose CW number is in `at_risk_weeks`; at-risk and absent can overlap (show absent colour); cycle rejection displays inline error near Add button (no `alert()`)

**Checkpoint**: US2 functional. Add A→B, absent B in CW23; A shows at-risk in CW23. Cycles
rejected with error message. State survives page reload.

---

## Phase 5: User Story 3 — Bottleneck Marking (Priority: P3)

**Goal**: Members depended on by 2+ others are visually marked with a distinct bottleneck
indicator on their row header and absence cells. Indicator visible even when member is present.

**Independent Test**: Define A→B and C→B. Verify B's row carries bottleneck badge; A and C do
not. Define only D→E; verify E has no bottleneck badge. Absent bottleneck week shows distinct
bottleneck-absent colour.

### Tests for US3

- [x] T026 [P] [US3] Write failing integration tests for bottleneck in `tests/integration/test_app.py`: `GET /api/dashboard` with state `[A→B, C→B]` returns `is_bottleneck: true` for B only; state `[A→B]` returns `is_bottleneck: false` for B; `bottlenecks` array in root response matches

### Implementation for US3

- [x] T027 [US3] Confirm `get_bottlenecks()` in `absence_dashboard/graph.py` (implemented in T020) satisfies T026; add any missing threshold-boundary edge cases and re-run — confirm T026 now passes
- [x] T028 [P] [US3] Add bottleneck visual indicators in `absence_dashboard/static/main.js` and `absence_dashboard/static/style.css`: bottleneck row header badge (e.g., "⚠ Bottleneck" label or distinct border); absence cells of a bottleneck member rendered with `--color-bottleneck-absent` (visually distinct from normal absent); indicator visible on row even when member has no absences that week

**Checkpoint**: US3 functional. B (2+ incoming) carries bottleneck badge. Absence cells of
bottleneck members visually distinct from non-bottleneck absences.

---

## Phase 6: User Story 4 — Skill Cluster Grouping (Priority: P4)

**Goal**: Manager defines named skill clusters (groups of substitutable members). Dashboard
renders members grouped by cluster; ungrouped members appear in "Unassigned" section at bottom.
Cluster layout makes substitute availability immediately visible.

**Independent Test**: Define cluster "Backend" with A, B, C. Load B's absences. Verify A, B, C
are a contiguous group with cluster label; an ungrouped member appears separately. Remove cluster;
all members move to Unassigned.

### Tests for US4

- [x] T029 [P] [US4] Write failing integration tests for cluster endpoints in `tests/integration/test_app.py`: `POST /api/clusters` returns 201 (valid), 400 (duplicate name), 400 (unknown member); `PUT /api/clusters/<name>` returns 200 (valid update), 404 (unknown cluster), 400 (unknown member); `DELETE /api/clusters/<name>` returns 200 (success), 404 (unknown); `GET /api/dashboard` groups members by cluster and places ungrouped in "Unassigned"; member may appear in multiple clusters

### Implementation for US4

- [x] T030 [US4] Implement `POST /api/clusters`, `PUT /api/clusters/<name>`, `DELETE /api/clusters/<name>` routes in `absence_dashboard/app.py`: validate all member names exist in loaded dataset, update `AppState.clusters`, `save_state` — confirm T029 now passes
- [x] T031 [US4] Update `GET /api/dashboard` in `absence_dashboard/app.py`: populate `clusters` membership list per member; order member list — cluster groups first (in `state.json` order), "Unassigned" group last; alphabetical sort within each group; member appearing in multiple clusters listed under each
- [x] T032 [US4] Add cluster management panel to `absence_dashboard/static/main.js` and `index.html`: cluster name `<input>`, multi-select `<select>` for members (populated from `members[]`), Create button calls `POST /api/clusters`; cluster list with +/− member buttons calling `PUT`, and Delete button calling `DELETE /api/clusters/<name>`; full dashboard re-render on any change
- [x] T033 [US4] Update timeline rendering in `absence_dashboard/static/main.js`: insert cluster separator rows between groups with cluster name label; render "Unassigned" label row before ungrouped members section; separator rows span all CW columns

**Checkpoint**: US4 functional. Cluster groups visible in timeline. Substitute availability
apparent by cluster membership. Ungrouped members shown in "Unassigned" section.

---

## Phase 7: User Story 5 — Dashboard Refresh (Priority: P5)

**Goal**: Manager clicks Reload to re-read an updated Excel file without restarting the server.
All dependencies and cluster assignments survive the refresh. Stale references (members no
longer in Excel) are auto-removed and reported.

**Independent Test**: Define dependency A→B and cluster "Backend"=[A,B]. Update sample Excel (change
absences). POST /api/refresh. Verify: new absences shown; dependency and cluster preserved.
Remove B from Excel, refresh; verify stale A→B dependency removed with `removed_stale_references`
in response.

### Tests for US5

- [x] T034 [P] [US5] Write failing integration tests for `POST /api/refresh` in `tests/integration/test_app.py`: 200 with updated member data after Excel change; dependency and cluster config preserved when all names still valid; stale dependency referencing removed member appears in `removed_stale_references` and is deleted from state; stale cluster member removed; 422 on unreadable Excel with `stale_data: true` and last-good data returned

### Implementation for US5

- [x] T035 [US5] Implement `POST /api/refresh` route in `absence_dashboard/app.py`: re-open and re-parse Excel file, recompute members, diff `AppState` against new member set (remove dependencies/cluster-members referencing absent names), `save_state`, return full `DashboardData` plus `removed_stale_references: list[dict]`; on `Exception` return 422 with last-cached data — confirm T034 now passes
- [x] T036 [US5] Wire Reload button in `absence_dashboard/static/main.js`: `btn-reload` click calls `POST /api/refresh`; on 200 call `renderTimeline(data)` with fresh data; if `removed_stale_references` non-empty show dismissible warning in `#warnings` listing removed items; on 422 show error banner "Could not read Excel file — showing last loaded data" without clearing the current view

**Checkpoint**: US5 functional. Reload button refreshes absence data; config preserved; stale
references cleaned up with visible user notification.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Edge-case UX, missing contract endpoints, port handling, and quickstart validation.

- [x] T037 [P] Add `GET /api/dependencies` route in `absence_dashboard/app.py` (contract completeness); write and pass its integration test in `tests/integration/test_app.py`
- [x] T038 [P] Add `GET /api/clusters` route in `absence_dashboard/app.py` (contract completeness); write and pass its integration test in `tests/integration/test_app.py`
- [x] T039 [P] Add optional `--port` CLI argument to `absence_dashboard/app.py` (default 5000); catch `OSError` on `app.run()` and print "Port <N> in use — retry with --port <M>"
- [x] T040 [P] Add year-boundary edge-case handling in `absence_dashboard/parser.py`: absence cells in columns that map to a date after 2026-12-31 are silently excluded from the display range (the parser still reads them but `build_calendar_weeks` caps at last ISO week of 2026)
- [x] T041 [P] Add member-in-multiple-clusters edge case test in `tests/integration/test_app.py`: member assigned to two clusters appears in both cluster groups in dashboard response; no duplication of absence data
- [x] T042 Run quickstart validation: follow `specs/001-absence-dashboard/quickstart.md` end-to-end with the actual Excel file; verify every step produces the documented output; update quickstart.md for any discovered inaccuracies
- [x] T043 Update `build_calendar_weeks()` in `absence_dashboard/app.py` to produce `label` in `"CW[N] | D Mon"` format (e.g. `"CW19 | 4 May"`) using `monday.strftime('%d %b').lstrip('0')`; update calendar-week unit tests in `tests/` to assert the new format (clarification 2026-05-08)
- [x] T044 Update timeline rendering in `absence_dashboard/static/main.js` to use the `label` field directly for two-row headers: row 1 `<th colspan="5">` shows the `"CW19 | 4 May"` label; row 2 shows Mon/Tue/Wed/Thu/Fri abbreviations only (no dates); verify CW headers are human-readable without knowing CW numbers by heart (clarification 2026-05-08)
- [x] T045 Revert `DAY_ABBR` in `absence_dashboard/static/main.js` from `["Mon","Tue","Wed","Thu","Fri"]` back to `["M","T","W","T","F"]` per clarification 2026-05-08 (single-character weekday labels)

**Checkpoint**: All 5 user stories working, all contract endpoints present, edge cases handled,
documentation validated against the real Excel file, weekday labels single-character.

---

---

## Phase 9: User Story 6 — Project Phase Visualization (Priority: P6)

**Goal**: Manager defines named project phases (name + start/end date) in the dashboard UI.
Each phase renders as a horizontal banner row above all member rows, spanning its date columns.
Multiple overlapping phases stack as separate rows.

**Independent Test**: Define "Go-Live" (2026-06-22–2026-06-26) and "Sprint 10"
(2026-06-15–2026-06-26). Verify two stacked banner rows appear above member rows; each spans only
its own date columns; member absence/at-risk cells render unchanged.

### Tests for US6

- [x] T046 [P] [US6] Write failing unit tests for `absence_dashboard/phases_manager.py` in `tests/unit/test_phases_manager.py`: `add_phase` valid returns updated list; duplicate name raises `ValueError`; `end_date < start_date` raises `ValueError`; `remove_phase` success returns updated list; `remove_phase` on missing name raises `KeyError`; `list_phases` empty and non-empty
- [x] T047 [P] [US6] Write failing integration tests for phase endpoints in `tests/integration/test_app.py`: `POST /api/phases` 201 (valid), 400 (duplicate name), 400 (end < start); `DELETE /api/phases/<name>` 200 (success), 404 (missing); `GET /api/phases` 200 with phases list; `GET /api/dashboard` includes `"phases"` array; phase survives `POST /api/refresh`

### Implementation for US6

- [x] T048 [US6] Extend `AppState` in `absence_dashboard/state.py` to add `phases: list` field (default `[]`); update `load_state` to default `phases=[]` on missing key (backwards-compatible); update empty-state init to `{"dependencies":[],"clusters":[],"phases":[]}`
- [x] T049 [US6] Implement `absence_dashboard/phases_manager.py`: `add_phase(name, start_date_str, end_date_str, current_phases) → list[dict]` (validates unique name and `end_date >= start_date`, raises `ValueError` otherwise); `remove_phase(name, current_phases) → list[dict]` (raises `KeyError` if not found) — confirm T046 now passes
- [x] T050 [US6] Implement `GET /api/phases`, `POST /api/phases`, `DELETE /api/phases/<name>` routes in `absence_dashboard/app.py`; update `GET /api/dashboard` to include `phases` field from state; update `POST /api/refresh` to preserve phases unchanged (phases are date-based, no member-name stale references to purge) — confirm T047 now passes
- [x] T051 [P] [US6] Add phase banner CSS to `absence_dashboard/static/style.css`: `--color-phase` custom property; `.phase-banner` cell class (background-color using `--color-phase`, semitransparent, with phase name text in first occupied cell via `.phase-label` span); `.tg-row.tg-phase-row` row-level styling distinct from member rows
- [x] T052 [US6] Render project phase banner rows in `absence_dashboard/static/main.js` `renderTimeline()`: for each phase in `data.phases`, insert a `.tg-row.tg-phase-row` before member rows; cells within `phase.start_date`–`phase.end_date` receive `.phase-banner`; first such cell contains a `.phase-label` span with the phase name; cells outside the range are empty; overlapping phases stack as consecutive rows naturally
- [x] T053 [US6] Add project phase management UI to `absence_dashboard/static/main.js` and `absence_dashboard/static/index.html`: add `<div id="phase-panel">` with phase name `<input>`, start/end `<input type="date">` pickers, Add Phase button (`POST /api/phases`), and phase list with ✕ remove buttons (`DELETE /api/phases/<name>`); add `btn-toggle-phases` nav button; inline error display on 400; full `renderTimeline` + `renderPhases` re-render on any mutation

**Checkpoint**: US6 functional. Phase banners visible above member rows. Overlapping phases
stacked. Panel allows add/remove. Config persists across reload.

---

## Phase 10: Final Polish

**Purpose**: Close remaining open items from all clarification sessions.

- [x] T054 Run full `pytest` suite confirming all 98+ tests green; perform end-to-end smoke test covering US6 (add a phase, verify banner row renders at correct columns, delete phase, verify row disappears); update `specs/001-absence-dashboard/quickstart.md` with any discovered inaccuracies

**Checkpoint**: Full suite green, phases feature validated end-to-end.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — **blocks all user stories**
- **Phase 3 (US1)**: Depends on Phase 2 — independent of US2–US5
- **Phase 4 (US2)**: Depends on Phase 2 — integrates into dashboard but independent of US1
- **Phase 5 (US3)**: Depends on Phase 4 (`graph.py` required); frontend layer only
- **Phase 6 (US4)**: Depends on Phase 2 — independent of US1–US3
- **Phase 7 (US5)**: Depends on Phase 2 — integrates with all stories but independent
- **Phase 8 (Polish)**: Depends on all user story phases complete
- **Phase 9 (US6)**: Depends on Phase 2; independent of US1–US5 (new entity, no shared state)
- **Phase 10 (Final Polish)**: Depends on Phase 9 complete

### User Story Dependencies

- **US1 (P1)**: After Phase 2 — no story dependencies
- **US2 (P2)**: After Phase 2 — no story dependencies
- **US3 (P3)**: After Phase 4 (US2) — graph.py must exist
- **US4 (P4)**: After Phase 2 — no story dependencies
- **US5 (P5)**: After Phase 2 — no story dependencies
- **US6 (P6)**: After Phase 2 — independent of US1–US5 (phases have no member-name dependencies)

### Within Each Phase (TDD order — NON-NEGOTIABLE)

1. Write test → confirm it **FAILS**
2. Implement minimum to make it pass
3. Confirm test **PASSES**
4. Refactor if needed

---

## Parallel Example: Phase 2 (Foundational)

```
# Group A — can start simultaneously:
T005  Write tests/unit/test_parser.py (failing)
T007  Write tests/unit/test_merger.py (failing)
T009  Write tests/unit/test_state.py  (failing)

# Group B — after Group A:
T006  Implement absence_dashboard/parser.py  (pass T005)
T008  Implement absence_dashboard/merger.py  (pass T007)
T010  Implement absence_dashboard/state.py   (pass T009)

# Sequential after Group B:
T011  Flask app skeleton
T012  static/index.html
T013  static/style.css   ← parallel with T012
```

## Parallel Example: User Stories (after Phase 2 complete)

```
Phase 3 (US1) — dashboard GET + frontend timeline
Phase 4 (US2) — graph.py + dependency POST/DELETE
Phase 6 (US4) — cluster POST/PUT/DELETE
Phase 7 (US5) — refresh POST
```

Phase 5 (US3) starts only after Phase 4 completes.

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks everything)
3. Complete Phase 3: User Story 1 (Absence Timeline)
4. **STOP and VALIDATE**: `python absence_dashboard/app.py absences.xlsx` → `localhost:5000`
5. Demo if ready — full absence grid is already useful standalone

### Incremental Delivery

1. Setup + Foundational → server starts, CLI validates, shell loads
2. + US1 → Gantt timeline with merged absences **(MVP)**
3. + US2 → Dependencies + at-risk indicators
4. + US3 → Bottleneck highlighting
5. + US4 → Skill cluster grouping
6. + US5 → Reload without restart
7. Polish → port arg, contract completeness, quickstart validation
8. + US6 → Project phase banner rows
9. Final Polish → full suite green, end-to-end smoke test

---

## Notes

- [P] tasks target different files with no unmet dependencies — safe to parallelise
- [Story] labels (US1–US5) map to user stories in `specs/001-absence-dashboard/spec.md`
- Commit after each phase checkpoint passes
- `state/state.json` is created automatically on first run; delete it to reset all config
- `tests/conftest.py` `sample_workbook` fixture must exactly mirror confirmed grid layout: Col C filter, Col D name, Col F+ dates starting 2026-04-27
- Total tasks: **54** (T001–T054; T043–T044 added 2026-05-08 clarification round 1; T045–T054 added 2026-05-08 clarification round 2 — weekday revert + US6 project phases)
