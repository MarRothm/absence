---

description: "Task list for SharePoint Direct Connection"

---

# Tasks: SharePoint Direct Connection

**Input**: Design documents from `/specs/003-sharepoint-direct-connection/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/launch-config.md, quickstart.md

**Tests**: Included — this project's constitution makes Test-Driven Development NON-NEGOTIABLE
(Principle II); every behavior change (rejection logic in `data_fetcher.py`, `launch_config.py`,
`app.py`) gets a test written first. The `conftest.py` fixture adaptation itself isn't a behavior
change under test — it's infrastructure verified by running the full existing suite and confirming
it stays green.

**Organization**: Tasks are grouped by user story (spec.md priorities — both US1 and US2 are P1;
US1 is sequenced first since US2's independent test exercises the connection US1 builds).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2)
- File paths are relative to the repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Independent doc/config fixes that don't depend on the code changes below

- [X] T001 [P] Update `launch_config.example.json` at repo root: change the `excel_source` placeholder from a local filename (`"absences.xlsx"`) to a SharePoint URL example, per `specs/003-sharepoint-direct-connection/contracts/launch-config.md`
- [X] T002 [P] Update root `README.md`'s Quick Start code example: replace `python run.py path/to/absences.xlsx` with a SharePoint URL example (local paths no longer work)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The core "SharePoint-only, read-only" enforcement both user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Replace the `TestLocalPath` class in `tests/unit/test_data_fetcher.py` with tests asserting that a local-path source passed to `get_workbook()` is rejected (raises, with a message stating local-file support has been removed) and that `requests.get` is never called for it; confirm these new tests FAIL against the current code (which still accepts local paths)
- [X] T004 [P] Update `tests/conftest.py`'s `app` fixture: monkeypatch `absence_dashboard.data_fetcher.requests.get` to return the `sample_xlsx` fixture's bytes, and pass a fake `https://fake.sharepoint.example/...` URL to `create_app` instead of the local `sample_xlsx` path (per research.md #2); run the full existing suite and confirm it is still green — this task alone must not change any test's behavior, only how its Flask app is constructed
- [X] T005 Modify `absence_dashboard/data_fetcher.py`: remove `get_workbook()`'s local-file branch entirely; for any source not starting with `http://`/`https://`, raise a clear error (e.g. `ValueError`) stating local-file support has been removed and a SharePoint link is required (per research.md #1); the existing `http(s)://` GET + `openpyxl(read_only=True)` path is unchanged. Confirm T003's new tests now pass and the full suite (via T004's adapted fixture) remains green (depends on T003, T004)

**Checkpoint**: Foundation ready — `get_workbook()` is now genuinely, unconditionally SharePoint-URL-only, with the full test suite still green

---

## Phase 3: User Story 1 - Load the dashboard straight from SharePoint, no local copy needed (Priority: P1) 🎯 MVP

**Goal**: Both manager-facing entry points (the CLI argument and `launch_config.json`) accept only
a SharePoint link, with a clear, specific error when a local path is supplied instead of the prior
silent acceptance.

**Independent Test**: Configure the dashboard (via CLI arg and via `launch_config.json`) with only a
SharePoint link — no local file involved — and confirm it loads; then configure each with a local
path instead and confirm a clear, specific rejection error, not a confusing generic failure.

### Tests for User Story 1 ⚠️

> Write these tests FIRST — confirm they FAIL before implementing T008/T009

- [X] T006 [P] [US1] Add rejection test cases to `tests/unit/test_launch_config.py`: a `launch_config.json` whose `excel_source` is an existing local path (not a URL) raises the same style of error as a missing/invalid source, with a message stating local-file support has been removed
- [X] T007 [P] [US1] Add rejection test cases to the `TestResolveLaunchSource` class in `tests/integration/test_app.py`: a CLI `excel_file` argument that is an existing local path (not a URL) is rejected with the same local-file-removed message, instead of being silently accepted as it is today

### Implementation for User Story 1

- [X] T008 [US1] Modify `absence_dashboard/launch_config.py`: `load_launch_config()` rejects any `excel_source` not starting with `http://`/`https://` — including one that exists on disk — dropping the old `os.path.exists(excel_source)` local-acceptance branch; makes T006 pass (depends on T006, T005)
- [X] T009 [US1] Modify `absence_dashboard/app.py`: rename `create_app`'s `excel_path` parameter to `excel_source` and `app.config["EXCEL_PATH"]` to `app.config["EXCEL_SOURCE"]` (per research.md #3) — including updating the existing reference at `tests/integration/test_app.py:401` (`app.config["EXCEL_PATH"] = new_path`) to use `EXCEL_SOURCE`, or that test will silently mutate a config key the app no longer reads; update `resolve_launch_source()` to reject any non-URL CLI `excel_file` value the same way; simplify `create_app()`'s call-site `except (ConnectionError, FileNotFoundError)` to `except ConnectionError` since `FileNotFoundError` can no longer originate from `get_workbook()`. Makes T007 pass (depends on T007, T008)
- [X] T010 [P] [US1] Update `specs/002-windows-standalone-build/quickstart.md`: remove the local-file-path option from "Configuring the data source" and its troubleshooting table entries, reflecting that `excel_source` is now SharePoint-URL-only (per research.md #4 — this is a living operational doc, unlike feature 002's `spec.md`/`plan.md`/`research.md`/`data-model.md`/`contracts/*.md`, which stay unmodified as historical record)

**Checkpoint**: User Story 1 is fully functional and testable independently — every manager-facing
entry point only accepts a SharePoint link, with a clear error otherwise

---

## Phase 4: User Story 2 - The SharePoint file is never modified by the dashboard (Priority: P1)

**Goal**: The "never writes to the source" guarantee is permanently regression-guarded in the test
suite and confirmed against a real SharePoint file.

**Independent Test**: Exercise every dashboard action against a live SharePoint file and confirm,
via the file's SharePoint version history, that the dashboard never creates a new version.

### Implementation for User Story 2

- [X] T011 [US2] Add a regression-guard unit test to `tests/unit/test_data_fetcher.py` asserting `get_workbook()` never calls `requests.post`/`put`/`patch`/`delete` — only `requests.get` — for any input, permanently guarding FR-002 against a future accidental write path (depends on T005)
- [ ] T012 [US2] Manually verify the read-only guarantee against a real SharePoint file, following `specs/003-sharepoint-direct-connection/quickstart.md`'s "Verifying the read-only guarantee" section: perform every dashboard action (load, reload, add/edit/remove a dependency, skill cluster, and phase), then confirm via SharePoint's version history that no new version was created; record the outcome in `specs/003-sharepoint-direct-connection/read-only-verification.md` (depends on T009, T011)

**Checkpoint**: Both user stories are independently functional — the dashboard is provably
SharePoint-only and provably read-only

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final verification spanning both user stories

- [X] T013 [P] Run the full `pytest` suite and confirm zero regressions from the `data_fetcher.py`/`launch_config.py`/`app.py`/`conftest.py` changes (T005, T008, T009, T004)
- [X] T014 Grep the repository for any remaining local-file-absence-source references in docs/comments/examples (excluding **all** already-shipped features' historical `spec.md`/`plan.md`/`research.md`/`data-model.md`/`contracts/*.md` — this includes `specs/001-absence-dashboard/*` (e.g. FR-016, its `quickstart.md`'s `python app.py path/to/absences.xlsx` example) as well as feature 002's, all intentionally left as-is per research.md #4) and fix any found
- [X] T015 Run `specs/003-sharepoint-direct-connection/quickstart.md`'s local/dev walkthrough end-to-end with a real (or mocked) SharePoint link and confirm the documented steps work (depends on T009)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: No dependency on Setup — BLOCKS both user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (T005) completion
- **User Story 2 (Phase 4)**: Depends on Foundational (T005); independent of US1's own tasks, but sequenced after it since both stories together are needed for a complete, meaningful release
- **Polish (Phase 5)**: Depends on all prior phases

### Within Each User Story

- Tests (T006, T007) MUST be written and confirmed failing before implementation (T008, T009)
- `launch_config.py` (T008) before the `app.py` change (T009) — same overall change, kept in this order for clean incremental commits

### Parallel Opportunities

- T001 and T002 (Setup) can run in parallel
- T003 and T004 (Foundational) can run in parallel — different files, no dependency on each other
- T006 and T007 (US1 tests) can run in parallel — different files
- T010 (002's quickstart.md) can run in parallel with T006–T009 — different file, content is already fully determined by the contract, no execution dependency
- T013 (full test suite) can run in parallel with T014/T015

---

## Parallel Example: Foundational Phase

```bash
# Launch both foundational tasks together:
Task: "Replace TestLocalPath with rejection tests in tests/unit/test_data_fetcher.py"
Task: "Adapt conftest.py's app fixture to mock requests.get with a fake https:// URL"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001, T002)
2. Complete Phase 2: Foundational (T003–T005 — `get_workbook()` becomes SharePoint-only)
3. Complete Phase 3: User Story 1 (T006–T010)
4. **STOP and VALIDATE**: confirm both entry points (CLI arg, `launch_config.json`) only accept a SharePoint link
5. This alone already satisfies the feature's core reason for existing (spec.md US1)

### Incremental Delivery

1. Setup + Foundational → `get_workbook()` is SharePoint-only, full suite green
2. Add User Story 1 → validate both entry points reject local paths clearly → feature usable today (MVP)
3. Add User Story 2 → regression-guard test + real-SharePoint manual verification → confidence the guarantee holds
4. Polish → full regression run + repo-wide stray-reference sweep + documented walkthrough

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Commit after each task or logical group
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
