---

description: "Task list for Cumul Groups (replacing Dependencies)"
---

# Tasks: Cumul Groups (replacing Dependencies)

**Input**: Design documents from `/specs/006-cumul-groups/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cumul-groups-api.md, quickstart.md

**Tests**: Included — Constitution Principle II (TDD, non-negotiable) requires failing tests before implementation for this codebase; tests are written first in every phase below.

**Organization**: Tasks are grouped by user story (spec.md priorities: US1 P1, US2 P1, US3 P2) to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- Every task includes exact file paths

## Path Conventions

Single-project Flask app: backend modules in `absence_dashboard/`, frontend in
`absence_dashboard/static/`, tests in `tests/unit/` and `tests/integration/`.

---

## Phase 1: Setup

**Purpose**: Confirm a clean baseline before the in-place dependency → cumul-groups replacement begins

- [X] T001 Run `pytest` from repo root and confirm the existing suite passes before any changes, so later failures are attributable to this feature

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Retire the old dependency feature entirely (FR-011/FR-012, SC-003) and establish the
`cumul_groups` state schema — both are shared by every user story below and must land first, since
US1–US3 all touch `state.py`, `app.py`, `index.html`, `main.js`, and `style.css`.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T002 [P] Delete `absence_dashboard/graph.py` (`DependencyGraph` and its deadlock/bottleneck helpers)
- [X] T003 [P] Delete `tests/unit/test_graph.py`
- [X] T004 Replace `AppState.dependencies` with `AppState.cumul_groups: list` in `absence_dashboard/state.py`; delete `_migrate_dependencies()`; update `load_state()`/`save_state()` to read/write the `cumul_groups` key only (old `dependencies` key in existing state files is silently ignored, per FR-012)
- [X] T005 [P] Update `tests/unit/test_state.py` for `cumul_groups` persistence (round-trip save/load), removing the dependency-migration test cases
- [X] T006 Remove the `GET/POST/PUT/DELETE /api/dependencies` routes and the `DependencyGraph` import/usage from `absence_dashboard/app.py`; remove the `deps`/`bottleneck_weights`/`deadlock` computation and the `"dependencies"`, `"is_bottleneck"`, `"deadlock_weeks"` keys from `_assemble_dashboard()`; remove the dependency stale-cleanup block from `/api/refresh`
- [X] T007 [P] Delete the `TestPostDependencies`, `TestPutDependencies`, `TestDeleteDependencies`, `TestPoolDependenciesAPI`, and `TestBottleneck` classes from `tests/integration/test_app.py`, and remove any remaining dependency references in other classes (e.g. `TestRefresh`, `TestGetEndpoints`)
- [X] T008 [P] Remove the `#dependency-panel` markup and the `id="btn-toggle-deps"` header button from `absence_dashboard/static/index.html`
- [X] T009 [P] Remove `renderDependencies()`, its call sites, the dependency-panel toggle listener, and the deadlock/bottleneck rendering (`computeDayClasses` deadlock branch, bottleneck badge, `.deadlock-label`, `phase-has-deadlock` row marking) from `absence_dashboard/static/main.js`
- [X] T010 [P] Remove `.deadlock`, `.deadlock-label`, `.bottleneck-absent`, `.is-bottleneck`, `.bottleneck-badge`, `.phase-has-deadlock` rules and the `--color-deadlock`, `--color-phase-deadlock`, `--color-bottleneck-*` custom properties from `absence_dashboard/static/style.css`

**Checkpoint**: Dependency feature is fully retired; `pytest` passes on the remaining (non-dependency) tests; app still starts and renders with no dependency UI. User story work can now begin.

---

## Phase 3: User Story 1 - Define a cumul group (Priority: P1) 🎯 MVP

**Goal**: Let a coordinator create, list, edit, and remove named cumul groups (≥2 members, unique
name, unique member set), replacing the old directional dependency edges.

**Independent Test**: Create a cumul group of two or more existing resources via the panel/API and
confirm it is saved, listed, editable, and removable — independent of any risk-visibility behavior.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T011 [P] [US1] Write failing unit tests for `add_cumul_group`/`update_cumul_group`/`remove_cumul_group` in `tests/unit/test_cumul_groups.py`: <2 members rejected, empty name rejected, duplicate member within a group rejected, unknown member rejected, duplicate name rejected, duplicate `frozenset(members)` rejected, `active_from`/`active_to` must be given together and `active_from <= active_to`, `KeyError` on unknown `old_name`/`name`
- [X] T012 [P] [US1] Write failing integration tests `TestCumulGroupsCRUD` in `tests/integration/test_app.py` covering `GET /api/cumul-groups`, `POST /api/cumul-groups` (201/400/409), `PUT /api/cumul-groups/<name>` (200/400/404/409), `DELETE /api/cumul-groups/<name>` (200/404), per `contracts/cumul-groups-api.md`

### Implementation for User Story 1

- [X] T013 [US1] Create `absence_dashboard/cumul_groups.py` with `add_cumul_group(name, members, valid_members, groups, active_from=None, active_to=None) -> list`, `update_cumul_group(old_name, groups, *, new_name=None, new_members=None, valid_members=None, active_from=..., active_to=...) -> list`, `remove_cumul_group(name, groups) -> list`, following the `phases_manager.py` convention (pure, non-mutating, returns a new list) — depends on T011
- [X] T014 [US1] Add `GET /api/cumul-groups` and `POST /api/cumul-groups` routes to `absence_dashboard/app.py`, using `cumul_groups.add_cumul_group()` — depends on T013
- [X] T015 [US1] Add `PUT /api/cumul-groups/<name>` and `DELETE /api/cumul-groups/<name>` routes to `absence_dashboard/app.py`, using `cumul_groups.update_cumul_group()`/`remove_cumul_group()` — depends on T013
- [X] T016 [US1] Add `"cumul_groups": state.cumul_groups` to the top-level return of `_assemble_dashboard()` in `absence_dashboard/app.py` — depends on T004
- [X] T017 [P] [US1] Add `#cumul-panel` markup to `absence_dashboard/static/index.html`: name field, multi-select members, optional `active_from`/`active_to`, "Create Cumul Group" button, group list; replace the `id="btn-toggle-deps"` button with a "Cumul" header button
- [X] T018 [US1] Add `renderCumulGroups()` (list/create/edit/delete against `/api/cumul-groups*`) and wire the "Cumul" panel-toggle listener in `absence_dashboard/static/main.js`, replacing the removed `renderDependencies()` call sites — depends on T014, T015, T017

**Checkpoint**: User Story 1 is fully functional and independently testable — cumul groups can be created, listed, edited, and removed through both the API and the UI panel.

---

## Phase 4: User Story 2 - See cumul risk at a glance (Priority: P1)

**Goal**: Flag, directly on the dashboard, which weeks put a cumul group at risk (every member has a
critical >5-calendar-day absence overlapping on a shared day) and which member is sole coverage for a
group in a given week — with the cumul definition always visible (FR-016).

**Independent Test**: Set up absences that fully overlap (each >5 calendar days) for all members of a
defined cumul group in a given week, and confirm the dashboard clearly flags that week for that group,
distinctly from weeks with no such overlap.

### Tests for User Story 2

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T019 [P] [US2] Write failing unit tests for `critical_absence_days`, `compute_cumul_risk_weeks`, `compute_sole_coverage_weeks` in `tests/unit/test_cumul_groups.py`: blocks >5 calendar days are critical, blocks of exactly 5 days are not (Edge Cases), a cumul risk week requires a common critical day across *all* members, sole coverage requires exactly one present member with no common-day requirement across the absent members, both respect `active_from`/`active_to` time-boxing
- [X] T020 [P] [US2] Write failing integration tests `TestCumulRiskWeeks` and `TestSoleCoverage` in `tests/integration/test_app.py` asserting `GET /api/dashboard` returns correct per-member `cumul_risks`/`sole_coverage` lists given fixture absence data, per `contracts/cumul-groups-api.md`

### Implementation for User Story 2

- [X] T021 [US2] Implement `critical_absence_days(merged_blocks) -> set[date]` in `absence_dashboard/cumul_groups.py`, using `(end_date - start_date).days + 1 > 5` on `merger.py`'s `AbsencePeriod` blocks — depends on T019
- [X] T022 [US2] Implement `compute_cumul_risk_weeks(group, member_critical_date_sets, calendar_weeks) -> list[int]` in `absence_dashboard/cumul_groups.py`: per week, flag only if the intersection of every member's critical-date set with the week's days is non-empty across all members; respects `active_from`/`active_to` — depends on T021
- [X] T023 [US2] Implement `compute_sole_coverage_weeks(group, member_critical_date_sets, calendar_weeks) -> dict[str, list[int]]` in `absence_dashboard/cumul_groups.py`: per week, if exactly one member has no critical day that week, map that member's name to the week; respects `active_from`/`active_to` — depends on T021
- [X] T024 [US2] In `_assemble_dashboard()` (`absence_dashboard/app.py`), build `member_critical_absence_date_sets` via `critical_absence_days()`, call `compute_cumul_risk_weeks()`/`compute_sole_coverage_weeks()` per cumul group, and attach `"cumul_risks"`/`"sole_coverage"` lists (`{"group": name, "week_number": int}`) to each member entry — depends on T016, T022, T023
- [X] T025 [P] [US2] Add `.cumul-risk`, `.is-sole-coverage`, `.sole-coverage-badge`, `.phase-has-cumul-risk` CSS rules to `absence_dashboard/static/style.css`, modeled on the retired deadlock/bottleneck styling removed in T010
- [X] T026 [US2] Update day-cell rendering and member-row rendering in `absence_dashboard/static/main.js` to mark cumul-risk day cells (tooltip naming the affected group(s), per FR-010/SC-005) and render the sole-coverage badge (tooltip naming the group), replacing the deadlock/bottleneck rendering removed in T009 — depends on T024, T025
- [X] T027 [US2] Mark phase rows with `.phase-has-cumul-risk` in `absence_dashboard/static/main.js`, mirroring the retired `phase-has-deadlock` logic but sourced from member `cumul_risks` — depends on T026
- [X] T028 [US2] Add the persistent cumul definition text (FR-016: "a cumul is flagged when every group member has a critical, more-than-5-calendar-day absence overlapping on a shared day") to the `#cumul-panel` in `absence_dashboard/static/index.html`, and as tooltip/title text on cumul-risk day cells and sole-coverage badges in `absence_dashboard/static/main.js` — depends on T017, T026

**Checkpoint**: User Stories 1 AND 2 both work independently — cumul groups can be defined and their risk/sole-coverage is visible on the dashboard with the definition shown in-place.

---

## Phase 5: User Story 3 - Cumul groups stay consistent as roster changes (Priority: P2)

**Goal**: Automatically keep cumul groups valid when the underlying roster is refreshed — drop
removed members, remove groups that fall below 2 valid members, and report every change the same way
stale cluster references are reported today.

**Independent Test**: Define a cumul group, refresh the underlying dataset with one member removed,
and confirm the group is corrected (member dropped, or whole group removed if <2 valid members
remain) and the change is reported to the coordinator.

### Tests for User Story 3

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T029 [P] [US3] Write failing integration tests in the `TestRefresh` class of `tests/integration/test_app.py`: a removed member is dropped from a cumul group and reported as `{"type": "cumul_group_member", ...}`; a group reduced below 2 valid members is removed entirely and reported as `{"type": "cumul_group", ...}`; groups unaffected by the refresh remain unchanged

### Implementation for User Story 3

- [X] T030 [US3] Replace the (already-removed in T006) dependency stale-cleanup block in `/api/refresh` (`absence_dashboard/app.py`) with cumul-group cleanup: drop members no longer present in the refreshed dataset, remove the whole group if fewer than 2 valid members remain, and append `{"type": "cumul_group_member", "entry": {...}}` / `{"type": "cumul_group", "entry": {...}}` items to the existing `removed`/`removed_stale_references` list, per `data-model.md` — depends on T029, T006, T016

**Checkpoint**: All three user stories are independently functional — roster refreshes keep cumul groups consistent and reported, matching the existing cluster-cleanup behavior.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanup and validation across all stories

- [X] T031 [P] Update `README.md:4` ("...absence timeline with dependency management and skill cluster grouping.") to describe cumul groups instead of dependency management
- [X] T032 Manually run through `specs/006-cumul-groups/quickstart.md` against the dev server: create/edit/delete a cumul group, verify cumul-risk and sole-coverage rendering plus the visible definition text, and verify refresh-time cleanup — this repo has no automated UI test framework, so this step is manual
- [X] T033 Run the full `pytest` suite and `grep -ril "dependenc" absence_dashboard/ tests/` to confirm all tests pass and no dependency-feature references remain (SC-003)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Setup — BLOCKS all user stories (shared files: `state.py`, `app.py`, `index.html`, `main.js`, `style.css`)
- **User Stories (Phase 3–5)**: All depend on Foundational completion
  - US1 (Phase 3) has no dependency on US2/US3
  - US2 (Phase 4) depends on US1's `cumul_groups.py` module and CRUD routes existing (T013–T016), since risk computation needs groups to operate on — but is independently testable once T016 lands
  - US3 (Phase 5) depends on US1's CRUD (groups must exist to be cleaned up) and on the refresh-route removal from T006
- **Polish (Phase 6)**: Depends on all desired user stories being complete

### Within Each User Story

- Tests written and confirmed failing before implementation
- `cumul_groups.py` functions before the `app.py` routes/assembler code that calls them
- Backend (`app.py`) before frontend (`main.js`) for the same signal
- Story complete before moving to the next priority

### Parallel Opportunities

- All Foundational deletions/removals marked `[P]` (T002, T003, T005, T007, T008, T009, T010) touch distinct files and can run together once T004/T006 (the ones they don't overlap with) are safe to run alongside
- T011 and T012 (US1 tests) can run in parallel — different files
- T017 (US1 HTML) can run in parallel with T013–T016 (US1 backend) — different files
- T019 and T020 (US2 tests) can run in parallel — different files
- T025 (US2 CSS) can run in parallel with T021–T024 (US2 backend)
- T031 (README) can run in parallel with T032/T033

---

## Parallel Example: User Story 1

```bash
# Tests together:
Task: "Failing unit tests for cumul_groups CRUD in tests/unit/test_cumul_groups.py"
Task: "Failing integration tests TestCumulGroupsCRUD in tests/integration/test_app.py"

# Once backend routes exist, frontend markup can be built in parallel with route wiring:
Task: "Add #cumul-panel markup to absence_dashboard/static/index.html"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (retires dependencies, adds `cumul_groups` schema)
3. Complete Phase 3: User Story 1 — cumul groups can be defined, listed, edited, removed
4. **STOP and VALIDATE**: Confirm US1 independently via `pytest` + manual panel check
5. Demo if ready — this alone already satisfies FR-001–FR-006, FR-011–FR-015

### Incremental Delivery

1. Setup + Foundational → old feature gone, new schema ready
2. Add US1 → test independently → demo (MVP)
3. Add US2 → test independently → demo (risk visibility, FR-007–FR-010, FR-016)
4. Add US3 → test independently → demo (refresh consistency, FR-013)
5. Polish → README, quickstart walkthrough, full-suite/grep validation

---

## Notes

- [P] tasks = different files, no unmet dependencies
- [Story] label maps each task to US1/US2/US3 for traceability
- Verify each new test fails before writing the implementation it covers
- Commit after each task or logical group
- Stop at any checkpoint to validate a story independently
