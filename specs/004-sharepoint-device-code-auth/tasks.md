---

description: "Task list for SharePoint Delegated Device-Code Authentication"

---

# Tasks: SharePoint Delegated Device-Code Authentication

**Input**: Design documents from `/specs/004-sharepoint-device-code-auth/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/launch-config.md,
quickstart.md

**Tests**: Included — this project's constitution makes Test-Driven Development NON-NEGOTIABLE
(Principle II); every behavior change gets a test written first, mocking `msal.PublicClientApplication`
and `requests` (never a real device-code flow or a real Microsoft endpoint in any test).

**Organization**: Tasks are grouped by user story (spec.md priorities — US1/US2 are P1, US3/US4 are
P2). US1 delivers the MVP (sign-in unblocks the dashboard); US2–US4 build on it.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- File paths are relative to the repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: New dependencies and config scaffolding, independent of the auth logic itself

- [X] T001 [P] Add `msal>=1.28` and `msal-extensions>=1.1` to `requirements.txt`
- [X] T002 [P] Add `client_id` and `tenant_id` placeholder fields to `launch_config.example.json`, per `specs/004-sharepoint-device-code-auth/contracts/launch-config.md`
- [X] T003 [P] Add the token-cache file (e.g. `state/token_cache.bin`) to `.gitignore`, mirroring the existing `state/state.json`/`launch_config.json` runtime-file pattern

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The core token-acquisition module and config validation both user stories build on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 [P] Write unit tests for `graph_auth.acquire_token()` in `tests/unit/test_graph_auth.py`, mocking `msal.PublicClientApplication`: silent acquisition succeeds → returns the token with no interactive call attempted; silent fails with `interactive_fallback=True` → the device-code flow is invoked and its result returned; silent fails with `interactive_fallback=False` → raises a clear error, no device-code flow attempted; the device-code flow itself fails/times out → raises a clear error. Confirm these FAIL (module doesn't exist yet)
- [X] T005 [P] Write unit tests for `launch_config.py`'s new `client_id`/`tenant_id` validation in `tests/unit/test_launch_config.py`: missing `client_id` raises a clear error naming that field; missing `tenant_id` likewise; a valid config returns `excel_source`, `client_id`, `tenant_id`, and `port` together. Confirm these FAIL against the current code (which doesn't read these fields yet)
- [X] T006 Implement `absence_dashboard/graph_auth.py`: `acquire_token(client_id, tenant_id, cache_path, interactive_fallback=True) -> str`, using `msal.PublicClientApplication` with an `msal_extensions`-backed (DPAPI-encrypted) persistent cache; try `acquire_token_silent()` first, fall back to the device-code flow only when `interactive_fallback` is `True` and silent acquisition fails (per research.md #1 and #4). Makes T004 pass (depends on T004)
- [X] T007 Modify `absence_dashboard/launch_config.py`: `load_launch_config()` also reads and validates `client_id`/`tenant_id`, raising the same `FileNotFoundError`-style, field-naming error used for a missing `excel_source` (per data-model.md). Makes T005 pass (depends on T005)

**Checkpoint**: Foundation ready — token acquisition and config validation both work standalone;
nothing in `app.py`/`data_fetcher.py` touched yet

---

## Phase 3: User Story 1 - Sign in once to unblock the dashboard (Priority: P1) 🎯 MVP

**Goal**: The dashboard authenticates via device-code sign-in and loads the SharePoint file through
Microsoft Graph, replacing the anonymous download that this tenant blocks entirely.

**Independent Test**: With no cached session, run the dashboard's startup flow (mocked sign-in);
confirm the device-code flow is attempted, a token is acquired, and the dashboard then loads data
via the Graph endpoint using that token.

### Tests for User Story 1 ⚠️

> Write these tests FIRST — confirm they FAIL before implementing T010/T011

- [X] T008 [P] [US1] Write unit tests for the Graph-based fetch in `tests/unit/test_data_fetcher.py`: `get_workbook(source, access_token)` builds the `GET /shares/{shareIdEncoded}/driveItem/content` URL from the existing sharing URL (share-ID encoding per research.md #2) and sends `Authorization: Bearer {access_token}`; the old anonymous `?download=1` path is gone entirely. Confirm FAIL
- [X] T009 [P] [US1] Write an integration test in `tests/integration/test_app.py` for `main()`'s startup sequence: token acquisition (mocked, interactive fallback allowed) happens before `create_app()` is called; a failed acquisition prints a clear error to stderr and exits non-zero rather than crashing with a traceback. Confirm FAIL

### Implementation for User Story 1

- [X] T010 [US1] Modify `absence_dashboard/data_fetcher.py`: `get_workbook(source, access_token)` — build and call the Graph `/shares/.../driveItem/content` URL with `Authorization: Bearer {access_token}`; remove the old anonymous `?download=1` fetch path entirely. Makes T008 pass (depends on T008)
- [X] T011 [US1] Modify `absence_dashboard/app.py`: `main()` calls `graph_auth.acquire_token(client_id, tenant_id, cache_path)` (interactive fallback allowed) before `create_app()`; `create_app()` gains an `access_token` parameter and threads it through `_load_excel()` into `get_workbook()`. Makes T009 pass (depends on T009, T007, T010)
- [X] T012 [US1] Update `tests/conftest.py`'s `app`/`client` fixtures: monkeypatch `absence_dashboard.graph_auth.acquire_token` to return a fixed dummy token, and pass it into `create_app(...)` per its new signature from T011, so the ~120+ existing route/business-logic tests keep working without any real MSAL/network call. Run the full suite and confirm it is green again (depends on T011)

**Checkpoint**: User Story 1 is fully functional and testable independently — a manager can sign in
and see their dashboard (MVP)

---

## Phase 4: User Story 2 - Stay signed in across normal restarts (Priority: P1)

**Goal**: Once signed in, the manager is not prompted again on every subsequent launch, for as long
as the session stays valid.

**Independent Test**: Acquire a token once against a real temporary cache file (mocked MSAL, real
file I/O), then acquire again with the same cache path and confirm the second call succeeds via
silent acquisition alone, with no device-code flow triggered.

### Implementation for User Story 2

- [X] T013 [US2] Add a persistence test to `tests/unit/test_graph_auth.py`: two sequential `acquire_token()` calls against the same `cache_path` — the first goes through the (mocked) device-code flow, the second succeeds via silent acquisition alone with no interactive fallback attempted (depends on T006)

**Checkpoint**: User Story 2 is independently verified — session persistence works across separate
`acquire_token()` calls sharing a cache file

---

## Phase 5: User Story 3 - Graceful re-authentication when the session expires (Priority: P2)

**Goal**: A browser-triggered refresh fails cleanly with a "please restart" message when the cached
session can no longer be silently renewed; the console-based startup flow still falls back to an
interactive device-code prompt.

**Independent Test**: Simulate an expired/invalid cached session and trigger `/api/refresh`; confirm
a clear JSON error telling the manager to restart the dashboard, with a non-200 status — not an
unhandled exception or hang.

### Tests for User Story 3 ⚠️

> Write this test FIRST — confirm it FAILS before implementing T015

- [X] T014 [P] [US3] Write a test for `post_refresh()` in `tests/integration/test_app.py`: when silent-only token acquisition (`interactive_fallback=False`) fails, the endpoint returns a clear JSON error telling the manager to restart the dashboard, with a non-200 HTTP status. Confirm FAIL

### Implementation for User Story 3

- [X] T015 [US3] Modify `post_refresh()` in `absence_dashboard/app.py`: acquire a token with `graph_auth.acquire_token(..., interactive_fallback=False)` before re-fetching; on failure, return the clear "restart the dashboard to sign in again" error response instead of letting the exception propagate as a generic 422. Makes T014 pass (depends on T014, T011) — **note**: this was already implemented as part of T011, since `graph_auth.acquire_token`'s own error message already satisfies the "restart the dashboard" requirement when caught by `post_refresh()`'s existing exception handler; T014's test confirmed this passes with no additional code change needed

**Checkpoint**: User Story 3 is independently verified — expired sessions are handled gracefully at
both the console (interactive fallback) and browser (clear restart message) layers

---

## Phase 6: User Story 4 - The read-only guarantee carries forward unchanged (Priority: P2)

**Goal**: The switch to authenticated Graph access requests only read-level permission and never
issues a write-capable request, preserving the guarantee from the prior SharePoint-connection
feature.

**Independent Test**: Inspect the constructed MSAL token request and the Graph HTTP calls made by
`get_workbook()`; confirm only the `Files.Read` scope is ever requested and only `GET` is ever used.

### Implementation for User Story 4

- [X] T016 [P] [US4] Add a regression-guard test to `tests/unit/test_graph_auth.py`: the `PublicClientApplication`/token-request scope list passed by `acquire_token()` never includes anything beyond `Files.Read` (depends on T006)
- [X] T017 [US4] Extend the existing `TestReadOnlyGuarantee` class (feature 003) in `tests/unit/test_data_fetcher.py` to also cover the Graph-based path: `get_workbook(source, access_token)` never calls `requests.post`/`put`/`patch`/`delete` — only `requests.get` (depends on T010) — **note**: already satisfied by T008's rewrite of this class to the new `(source, access_token)` signature; verified passing, no additional test needed

**Checkpoint**: All four user stories are independently functional — sign-in works, persists,
degrades gracefully, and stays strictly read-only

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final verification spanning all user stories

- [X] T018 [P] Update root `README.md` (and feature 003's `quickstart.md`, an operational doc similarly superseded — per this project's established precedent, spec.md/plan.md/research.md stay frozen as history) (and any other stale mention of the anonymous-download flow this feature replaces) to reflect sign-in-based access
- [X] T019 Run the full `pytest` suite and confirm zero regressions from the `graph_auth.py`/`data_fetcher.py`/`app.py`/`launch_config.py`/`conftest.py` changes (depends on T012, T015, T017)
- [X] T020 Verify PyInstaller bundles `msal` and `msal-extensions` (and their Windows-specific transitive dependencies) correctly in a local rebuild of `scripts/build-windows-standalone.sh`'s output; add `--collect-all`/`--hidden-import` flags if the build's warning log shows missing modules for them (per research.md #5), using the `PYZ-00.toc` inspection technique already established during feature 003's implementation
- [ ] T021 Manually verify the full device-code sign-in flow against the real Barmenia tenant on the actual Windows Server 2016 Citrix session, once the Azure AD app registration exists (spec.md Assumptions) — requires real IT-provisioned `client_id`/`tenant_id`, not executable without them
- [ ] T022 Run `specs/004-sharepoint-device-code-auth/quickstart.md`'s walkthrough end-to-end once real credentials/app registration are available, and fix any documentation gap found (depends on T021)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: No dependency on Setup — BLOCKS all four user stories
- **User Story 1 (Phase 3)**: Depends on Foundational (T006, T007) completion
- **User Story 2 (Phase 4)**: Depends on Foundational (T006) only — independent of US1's own app.py/data_fetcher.py wiring, but sequenced after it since a working end-to-end sign-in (US1) is what makes persistence meaningful to demonstrate
- **User Story 3 (Phase 5)**: Depends on US1 (T011) — `post_refresh()` doesn't exist in its new form until US1 wires token acquisition into `app.py`
- **User Story 4 (Phase 6)**: Depends on Foundational (T006) and US1 (T010) — needs both the token-request logic and the Graph-fetch logic to exist before their read-only-ness can be tested
- **Polish (Phase 7)**: Depends on all prior phases

### Within Each User Story

- Tests (T004/T005, T008/T009, T014) MUST be written and confirmed failing before their implementation (T006/T007, T010/T011, T015)
- Within US1: `data_fetcher.py` (T010) before `app.py` (T011) before the `conftest.py` fixture update (T012), since the fixture needs to match the final signatures both introduce

### Parallel Opportunities

- T001, T002, T003 (Setup) can all run in parallel
- T004 and T005 (Foundational tests) can run in parallel — different files, no mutual dependency
- T008 and T009 (US1 tests) can run in parallel — different files
- T016 (US4 scope test) can run in parallel with T013 (US2 persistence test) and T014 (US3 refresh test) — all depend only on already-completed Foundational/US1 work, different files
- T018 (README) can run in parallel with T019–T022

---

## Parallel Example: Foundational Phase

```bash
# Launch both foundational test-writing tasks together:
Task: "Unit tests for graph_auth.acquire_token() in tests/unit/test_graph_auth.py"
Task: "Unit tests for launch_config.py's client_id/tenant_id validation in tests/unit/test_launch_config.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001–T003)
2. Complete Phase 2: Foundational (T004–T007 — `graph_auth.py` works standalone)
3. Complete Phase 3: User Story 1 (T008–T012)
4. **STOP and VALIDATE**: confirm a manager can sign in via device code and see their dashboard (mocked in tests; real validation needs T021's live tenant check)
5. This alone already satisfies the feature's core reason for existing (spec.md US1)

### Incremental Delivery

1. Setup + Foundational → token acquisition and config validation both work standalone
2. Add User Story 1 → sign-in unblocks the dashboard end-to-end → MVP
3. Add User Story 2 → confirm sessions persist across restarts → daily-use friction removed
4. Add User Story 3 → confirm graceful re-authentication → long-running sessions handled safely
5. Add User Story 4 → confirm the read-only guarantee explicitly holds for the new auth path
6. Polish → full regression run + real PyInstaller bundling check + real-tenant verification once IT provisions the app registration

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Commit after each task or logical group
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
