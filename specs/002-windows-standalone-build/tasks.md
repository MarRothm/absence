---

description: "Task list for Windows Server 2016 (Citrix) Standalone Build"

---

# Tasks: Windows Server 2016 (Citrix) Standalone Build

**Input**: Design documents from `/specs/002-windows-standalone-build/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/launch-config.md,
contracts/build-pipeline.md, quickstart.md

**Tests**: Included — this project's constitution makes Test-Driven Development NON-NEGOTIABLE
(Principle II); new business logic (the `launch_config` loader and `app.py`'s fallback) gets tests
written first. The build script and CI workflow are infrastructure, verified by their own
pass/fail behavior and the manual smoke test, not by pytest (see plan.md Constitution Check).

**Organization**: Tasks are grouped by user story (spec.md priorities P1/P2/P3) to enable
independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths are relative to the repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Repo-level scaffolding needed before any code or build-script work starts

- [X] T001 [P] Add `launch_config.example.json` template at repo root with `excel_source` (empty/placeholder string) and `port` (`5002`) fields, per `specs/002-windows-standalone-build/contracts/launch-config.md`
- [X] T002 [P] Add `launch_config.json` to `.gitignore` (mirrors the existing `state/state.json` runtime-file pattern already there), keeping `launch_config.example.json` tracked

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The build mechanism both US1 (manual build+run) and US2 (CI-triggered build) depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Create `scripts/build-windows-standalone.sh`: run PyInstaller in `--onedir` mode against `absence_dashboard/app.py`, with `--add-data` bundling `absence_dashboard/static` (Windows `;` separator per research.md #5); assemble the bundle into `dist/absence-dashboard-windows/`; generate a `run-dashboard.bat` launcher using the `pushd "%~dp0"` pattern (UNC/network-home-drive safe, per research.md #2) that runs the bundled exe and prints a "Server stopped or failed to start" message on exit; copy `launch_config.example.json` (T001) into the bundle as both `launch_config.example.json` and a working `launch_config.json`; create an empty `state/` directory in the bundle; verify the bundle contains the exe, `run-dashboard.bat`, and `launch_config.example.json` (fail the script if not); zip the bundle to `dist/absence-dashboard-windows.zip`. Model directly on `testautomation_monitoring`'s `scripts/build-python-standalone.sh`. (depends on T001)

**Checkpoint**: Foundation ready — user story implementation can now begin

---

## Phase 3: User Story 1 - Run the dashboard on the Citrix Windows Server 2016 session without installing anything (Priority: P1) 🎯 MVP

**Goal**: A manager can extract the built package on a Windows Server 2016 Citrix session with no
Python installed and no administrator rights, and reach the dashboard with one double-click.

**Independent Test**: Build the package locally with `scripts/build-windows-standalone.sh` (T003)
on a Windows machine, copy the extracted bundle to a machine/session with no Python installed, edit
`launch_config.json` to point at a test spreadsheet, double-click `run-dashboard.bat`, and confirm
the dashboard is reachable in a browser.

### Tests for User Story 1 ⚠️

> Write these tests FIRST — confirm they FAIL before implementing T006/T007

- [X] T004 [P] [US1] Write unit tests for the launch-config loader in `tests/unit/test_launch_config.py`: valid `launch_config.json` returns `(excel_source, port)`; missing/invalid `excel_source` produces the same actionable-error/non-zero-exit behavior as today's existing **file-not-found** case (`app.py`'s `"Error: File not found: {source}"` stderr message + `exit(1)` — not argparse's required-argument error, which only applies to the CLI-arg path and is unrelated here); missing/invalid `port` falls back to `5002` with a printed warning — per the validation rules in `specs/002-windows-standalone-build/data-model.md`
- [X] T005 [P] [US1] Write an integration test in `tests/integration/test_app.py` covering the precedence rule from `specs/002-windows-standalone-build/contracts/launch-config.md`: a supplied `excel_file` CLI argument is used and `launch_config.json` is ignored; when no CLI argument is supplied, `launch_config.json` is read instead

### Implementation for User Story 1

- [X] T006 [US1] Implement `absence_dashboard/launch_config.py` with a `load_launch_config(path)` function returning validated `(excel_source, port)`, reusing the stdlib-`json` load pattern already used in `absence_dashboard/state.py` (no new dependency, per research.md #4); makes T004 pass (depends on T004)
- [X] T007 [US1] Modify `absence_dashboard/app.py`'s `__main__` block: make the `excel_file` positional CLI argument optional; when omitted, call `launch_config.load_launch_config("launch_config.json")` (read relative to the current working directory — the same CWD-relative convention `state.py`'s `state_path` already uses, since `run-dashboard.bat` already `pushd`s into the bundle root before launching); when supplied, keep today's CLI-arg behavior unchanged; makes T005 pass (depends on T006, T005)
- [X] T008 [P] [US1] Add a "Standalone Windows Build (Citrix / Server 2016)" section to root `README.md` linking to `specs/002-windows-standalone-build/quickstart.md`, satisfying FR-010's documentation requirement; while editing this file, also fix the existing Quick Start block's stale port number (`http://localhost:5000` → `http://localhost:5002`, matching `app.py`'s actual `--port` default) so the file doesn't contradict itself

**Checkpoint**: User Story 1 is fully functional and testable independently — the package can be
hand-built and run on a Python-free Windows machine

---

## Phase 4: User Story 2 - Automatic, versioned build via GitHub Actions (Priority: P2)

**Goal**: Every push to `main` automatically builds and publishes the Windows standalone package,
with no manual packaging step, and a failed build never publishes.

**Independent Test**: Push a commit to `main` and confirm a new package is built and attached to a
GitHub Release tied to that commit, with no manual build/upload step; confirm a deliberately broken
build does not publish anything.

### Implementation for User Story 2

- [X] T009 [US2] Create `.github/workflows/release-deployables.yml` per `specs/002-windows-standalone-build/contracts/build-pipeline.md`: triggered on `push` to `main`; a `build-windows-standalone` job (`runs-on: windows-latest`) that checks out, sets up Python 3.12, runs `pip install -r requirements.txt pyinstaller`, runs `scripts/build-windows-standalone.sh` (T003), and uploads `dist/absence-dashboard-windows.zip` as artifact `windows-standalone`; a `publish-release` job (`needs: build-windows-standalone`, `runs-on: ubuntu-latest`, `permissions: contents: write`) that downloads the artifact and publishes it via `softprops/action-gh-release` tagged `build-${{ github.sha }}`, named `Build ${{ github.sha }}`, with `make_latest: true` (depends on T003; also depends on T007 — do not merge/enable this workflow until T007 lands, otherwise a published release's package won't actually launch via double-click)

**Checkpoint**: User Stories 1 AND 2 both work independently — pushes to `main` now produce a
downloadable, runnable package with no manual step

---

## Phase 5: User Story 3 - Same functionality as the local desktop app (Priority: P3)

**Goal**: Every feature available in the locally-run dashboard behaves identically from the
standalone package.

**Independent Test**: Run through spec 001's acceptance scenarios against the built standalone
package and confirm identical behavior to the desktop version.

### Implementation for User Story 3

- [ ] T010 [US3] Run every spec-001 acceptance scenario (absence timeline rendering, dependency add/edit/remove and cycle detection, skill-cluster add/edit/remove, phase add/edit/remove, the Show All/Migration Only toggle, and spreadsheet reload from both a local file and a SharePoint URL) against a locally built standalone package (T003, T007); record pass/fail results in `specs/002-windows-standalone-build/parity-check.md`; file and fix any behavioral gap found before sign-off (depends on T003, T007, T009)

**Checkpoint**: All three user stories are independently functional — the standalone package is a
full, automatically-built, behaviorally-identical replacement for the desktop app on Windows Server
2016/Citrix

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final verification spanning all user stories

- [X] T011 [P] Run the full `pytest` suite and confirm zero regressions introduced by the `app.py`/`launch_config.py` changes (T006, T007)
- [ ] T012 Perform an end-to-end `specs/002-windows-standalone-build/quickstart.md` walkthrough on a Windows machine (build → extract → configure `launch_config.json` → launch via `run-dashboard.bat`) and fix any documentation gap found (depends on T003, T007)
- [ ] T013 Perform the documented manual smoke test on an actual Windows Server 2016 Citrix session (SC-005) and record the outcome in `specs/002-windows-standalone-build/parity-check.md` (depends on T009)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on T001 (Setup) — BLOCKS both user stories that follow
- **User Story 1 (Phase 3)**: Depends on Foundational (T003) completion
- **User Story 2 (Phase 4)**: Depends on Foundational (T003) completion — independent of US1's code changes, but both stories are needed together for a meaningful release
- **User Story 3 (Phase 5)**: Depends on US1 (T007) and US2 (T009) — it verifies the fully-built, fully-automated package, so it necessarily runs last
- **Polish (Phase 6)**: Depends on all prior phases

### Within Each User Story

- Tests (T004, T005) MUST be written and confirmed failing before implementation (T006, T007)
- `launch_config.py` (T006) before the `app.py` change that uses it (T007)

### Parallel Opportunities

- T001 and T002 (Setup) can run in parallel
- T004 and T005 (US1 tests) can run in parallel — different files
- T008 (README) can run in parallel with T004–T007 — different file, no code dependency
- T011 (full test suite) can run in parallel with T012/T013 once T007/T009 are done

---

## Parallel Example: User Story 1

```bash
# Launch both US1 tests together (write first, confirm both fail):
Task: "Unit tests for launch-config loader in tests/unit/test_launch_config.py"
Task: "Integration test for CLI-arg vs launch_config.json precedence in tests/integration/test_app.py"

# README update can happen alongside test-writing:
Task: "Add standalone-build section to README.md"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001, T002)
2. Complete Phase 2: Foundational (T003 — build script)
3. Complete Phase 3: User Story 1 (T004–T008)
4. **STOP and VALIDATE**: hand-build the package and run it on a Python-free Windows machine
5. This alone already satisfies the feature's core reason for existing (spec.md US1)

### Incremental Delivery

1. Setup + Foundational → build mechanism ready
2. Add User Story 1 → validate manually → package is usable today (MVP)
3. Add User Story 2 → validate a real push to `main` publishes a release → packaging is now automatic
4. Add User Story 3 → run the full parity check → confidence the package is a true replacement
5. Polish → full regression run + real Windows Server 2016/Citrix smoke test before calling the feature done

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Commit after each task or logical group
- Avoid: vague tasks, same-file conflicts, cross-story dependencies that break independence
