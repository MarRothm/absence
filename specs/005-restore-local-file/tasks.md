---

description: "Task list for Restore Local File Data Source"

---

# Tasks: Restore Local File Data Source

**Input**: Design documents from `/specs/005-restore-local-file/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/launch-config.md,
quickstart.md

**Tests**: Included — this project's constitution makes Test-Driven Development NON-NEGOTIABLE
(Principle II); every reverted behavior gets its test rewritten to the local-path contract first,
confirmed failing against the current SharePoint/auth-requiring code, before the implementation
change lands. This is a net-deletion feature: several tests and one whole module are removed
outright rather than rewritten, since there's no longer any behavior for them to cover.

**Organization**: Tasks are grouped by user story (spec.md priorities — US1 is P1, US2 is P2).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- File paths are relative to the repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependency and config cleanup, independent of the code revert itself

- [X] T001 [P] Remove `msal`, `msal-extensions`, `truststore`, and `requests` from `requirements.txt` (research.md #4 — verified `requests` has no other caller once the HTTP fetch path is gone)
- [ ] T002 [P] Revert `launch_config.example.json` to `{"excel_source": "absences.xlsx", "port": 5002}` — remove `client_id`/`tenant_id`, per `specs/005-restore-local-file/contracts/launch-config.md`
- [X] T003 [P] Remove the `state/token_cache.bin` entry from `.gitignore` (no longer created by anything)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Revert the core fetch/config-validation logic both user stories build on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Rewrite `tests/unit/test_data_fetcher.py`: replace all Graph/URL/Bearer-token/read-only-guarantee test classes with simple local-path tests — an existing local file loads correctly; a nonexistent path raises `FileNotFoundError` with a clear message (the "never touches the network" guarantee is now structural, not testable via mocking, since there's no network code path left to guard — see research.md #2). Confirm these FAIL against the current code (which requires an `access_token` and rejects local paths)
- [X] T005 [P] Rewrite `tests/unit/test_launch_config.py`: replace all `client_id`/`tenant_id` tests with local-path validation tests — a valid config with an existing `excel_source` path returns `(excel_source, port)`; a nonexistent path or missing `excel_source` raises `FileNotFoundError`. Confirm these FAIL against the current code
- [X] T006 [P] Delete `tests/unit/test_graph_auth.py` entirely — no `graph_auth` module will remain to test
- [X] T007 Modify `absence_dashboard/data_fetcher.py`: `get_workbook(source)` reads `source` as a local path directly via `openpyxl.load_workbook(source, read_only=True, data_only=True)` — remove the `requests`/`truststore` imports, the `truststore.inject_into_ssl()` call, `GRAPH_BASE_URL`, and `_encode_share_id()` entirely. Makes T004 pass (depends on T004)
- [X] T008 Modify `absence_dashboard/launch_config.py`: `load_launch_config()` validates `excel_source` as an existing local path (restoring the pre-003 `os.path.exists` check) and returns `(excel_source, port)`; remove the `client_id`/`tenant_id` reads and validation entirely. Makes T005 pass (depends on T005)
- [X] T009 Delete `absence_dashboard/graph_auth.py` entirely (depends on T006)

**Checkpoint**: Foundation ready — local-path fetch and config validation both work standalone,
`graph_auth.py` no longer exists

---

## Phase 3: User Story 1 - Load the dashboard from a local file, no sign-in required (Priority: P1) 🎯 MVP

**Goal**: The dashboard starts and loads from a manager-configured local file, with zero sign-in,
zero device code, and zero network access of any kind.

**Independent Test**: With no SharePoint credentials, network access, or prior sign-in available,
configure the dashboard with a local file path and confirm it loads and displays the absence data.

### Tests for User Story 1 ⚠️

> Rewrite/remove these tests FIRST — confirm the rewritten ones FAIL before implementing T012/T013

- [X] T010 [P] [US1] Rewrite the `TestResolveLaunchSource` class in `tests/integration/test_app.py`: revert to the `(source, port)` 2-tuple; a CLI `excel_file` argument (or `launch_config.json`'s `excel_source`) must be an existing local path — a nonexistent path raises `FileNotFoundError`. Confirm FAIL against the current 4-tuple-returning code
- [X] T011 [P] [US1] Delete the `TestMainStartupTokenFlow` class in `tests/integration/test_app.py` entirely — there is no token-acquisition step left in `main()` to test

### Implementation for User Story 1

- [X] T012 [US1] Modify `absence_dashboard/app.py`: remove the `graph_auth` import and `TOKEN_CACHE_PATH` constant; `_load_excel(source)` drops the `access_token` parameter; `create_app(excel_source, state_path="state/state.json")` drops `access_token`/`client_id`/`tenant_id` and their `app.config` entries; `resolve_launch_source(excel_file, port_arg, config_path)` reverts to local-path CLI validation and returns `(source, port)`; `main()` removes the token-acquisition `try`/`except` block and calls `create_app(source, state_path=...)` directly. Makes T010 pass (depends on T010, T011, T007, T008, T009)
- [X] T013 [US1] Update `tests/conftest.py`'s `app`/`client` fixtures: remove all `requests`/`graph_auth` monkeypatching entirely; pass `sample_xlsx` (a local path) directly to `create_app(sample_xlsx, state_path=...)` again, exactly as before feature 003. Run the full suite and confirm it is green (depends on T012)

**Checkpoint**: User Story 1 is fully functional and testable independently — the dashboard loads
from a local file with zero network access anywhere

---

## Phase 4: User Story 2 - Refresh data by downloading a new copy (Priority: P2)

**Goal**: Reload re-reads the same configured local file — no SharePoint or network attempt, ever.

**Independent Test**: Replace the configured local file with an updated version and confirm the
dashboard shows the updated content after a Reload, with no network call made.

### Tests for User Story 2 ⚠️

> Rewrite this test FIRST — confirm it FAILS before implementing T015

- [X] T014 [P] [US2] Simplify `test_refresh_stale_dependency_removed` in `tests/integration/test_app.py`: swap `app.config["EXCEL_SOURCE"]` to a new local file path directly (no more `requests` mocking needed) and confirm refresh picks up the change; delete the `TestRefreshExpiredSession` class entirely — there is no token-renewal failure mode left to test. Confirm the rewritten test FAILS against the current code (which expects a URL and calls `graph_auth.acquire_token`)

### Implementation for User Story 2

- [X] T015 [US2] Modify `post_refresh()` in `absence_dashboard/app.py`: remove the `graph_auth.acquire_token(..., interactive_fallback=False)` call entirely; re-read via `_load_excel(app.config["EXCEL_SOURCE"])` directly. Makes T014 pass (depends on T014, T012)

**Checkpoint**: Both user stories are independently functional — the dashboard loads and refreshes
from a local file with zero sign-in and zero network access anywhere

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Documentation cleanup and final verification spanning both user stories

- [X] T016 [P] Update root `README.md`: revert the Quick Start section to local-file usage, removing all sign-in/device-code language
- [X] T017 [P] Update `specs/002-windows-standalone-build/quickstart.md`: revert its `launch_config.json` example to local-path configuration, removing `client_id`/`tenant_id` and the sign-in-related troubleshooting rows (per research.md #5 — living operational doc, kept current)
- [X] T018 [P] Add/update forward-pointing notices in `specs/001-absence-dashboard/quickstart.md`, `specs/003-sharepoint-direct-connection/quickstart.md`, and `specs/004-sharepoint-device-code-auth/quickstart.md`, all pointing directly at `specs/005-restore-local-file/quickstart.md` as current truth (per research.md #5 — their `spec.md`/`plan.md`/`research.md`/`data-model.md`/`contracts/*.md` stay untouched as historical record)
- [X] T019 Run the full `pytest` suite and confirm zero regressions — and a smaller, simpler suite overall (depends on T013, T015)
- [X] T020 Grep the repository for any remaining references to `client_id`/`tenant_id`/`graph_auth`/`msal`/a SharePoint URL as a data source, outside the historical `spec.md`/`plan.md`/`research.md`/`data-model.md`/`contracts/*.md` of features 002/003/004, and fix any found (depends on T012, T015, T016, T017, T018)
- [X] T021 Rebuild the PyInstaller standalone bundle locally (`scripts/build-windows-standalone.sh`) and confirm `msal`/`msal-extensions`/`truststore` are no longer bundled (a smaller build than feature 004's), and that the bundle still assembles correctly for local-file mode (depends on T012)
- [X] T022 Run `specs/005-restore-local-file/quickstart.md`'s local/dev walkthrough end-to-end with a real local file and confirm the documented steps work (depends on T012, T013)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: No dependency on Setup — BLOCKS both user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (T007, T008, T009) completion
- **User Story 2 (Phase 4)**: Depends on US1 (T012) — `post_refresh()`'s revert builds directly on `app.py`'s revert
- **Polish (Phase 5)**: Depends on all prior phases

### Within Each User Story

- Tests (T010/T011, T014) MUST be rewritten/removed and confirmed failing before their implementation (T012, T015)
- Within Foundational: `data_fetcher.py` (T007) and `launch_config.py` (T008) can proceed in parallel once their respective tests (T004, T005) are written; `graph_auth.py`'s deletion (T009) can happen any time after its test file is deleted (T006)

### Parallel Opportunities

- T001, T002, T003 (Setup) can all run in parallel
- T004, T005, T006 (Foundational test rewrites/deletions) can run in parallel — different files
- T010 and T011 (US1 test changes) can run in parallel — different concerns in the same file, but non-overlapping edits; sequence carefully if working in the same session
- T016, T017, T018 (Polish docs) can all run in parallel — different files

---

## Parallel Example: Foundational Phase

```bash
# Launch all three foundational test/deletion tasks together:
Task: "Rewrite tests/unit/test_data_fetcher.py to local-path tests"
Task: "Rewrite tests/unit/test_launch_config.py to local-path tests"
Task: "Delete tests/unit/test_graph_auth.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T009 — local-path fetch/config work standalone, `graph_auth.py` gone)
3. Complete Phase 3: User Story 1 (T010–T013)
4. **STOP and VALIDATE**: confirm the dashboard loads from a local file with zero network access
5. This alone already satisfies the feature's core reason for existing (spec.md US1)

### Incremental Delivery

1. Setup + Foundational → local-path fetch/config validation both work standalone
2. Add User Story 1 → dashboard loads locally, no sign-in → MVP restored
3. Add User Story 2 → confirm Reload re-reads the local file with no network attempt
4. Polish → docs updated everywhere a manager might look, full regression run, smaller PyInstaller bundle confirmed, real local-file walkthrough

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Commit after each task or logical group
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
