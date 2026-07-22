# Implementation Plan: SharePoint Direct Connection

**Branch**: `003-sharepoint-direct-connection` | **Date**: 2026-07-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-sharepoint-direct-connection/spec.md`

## Summary

Remove local-file loading entirely so the dashboard's only supported data source is a SharePoint
share URL, and make the "never writes to the source" guarantee structural rather than incidental:
`data_fetcher.get_workbook()` rejects any non-`http(s)://` source outright (it already only ever
issues a GET and opens with `openpyxl(read_only=True)` — no write path exists or is added). Both
manager-facing entry points — the CLI positional argument (`resolve_launch_source` in `app.py`) and
`launch_config.json` (`launch_config.py`, from feature 002) — validate the source is a SharePoint
URL *before* it ever reaches `create_app`/`get_workbook`, giving a clear, specific error (FR-007)
instead of a confusing failure. `create_app`'s `excel_path` parameter and `EXCEL_PATH` config key are
renamed to `excel_source`/`EXCEL_SOURCE` for clarity now that a local path is never valid there. The
existing ~100-test integration suite (built around `conftest.py`'s `app`/`client` fixtures, which
currently pass a local fixture file straight into `create_app`) is adapted in one place — the
fixture mocks `requests.get` to serve the fixture's bytes over a fake `https://` URL — so the whole
suite keeps running fast and offline while `get_workbook` becomes honestly URL-only everywhere,
with no hidden local-file bypass left anywhere in the codebase.

## Technical Context

**Language/Version**: Python 3.10+ (unchanged).

**Primary Dependencies**: Flask 3.x, openpyxl 3.x, requests 2.x (all unchanged — no new dependency;
test-suite adaptation uses `pytest`'s built-in `monkeypatch`, matching the mocking style already
used in `tests/unit/test_data_fetcher.py`).

**Storage**: No change — `state/state.json` (dependencies/clusters/phases) and `launch_config.json`
(from feature 002) are unaffected in structure; only `launch_config.json`'s `excel_source` field
gains a stricter validation rule (URL-only).

**Testing**: pytest (existing, unchanged). `tests/conftest.py`'s `app`/`client` fixtures are updated
to mock the HTTP fetch instead of passing a local path to `create_app`, so all existing route/logic
tests keep working unmodified; `tests/unit/test_data_fetcher.py`'s `TestLocalPath` class is replaced
with tests asserting local paths are rejected; `tests/unit/test_launch_config.py` and the
`TestResolveLaunchSource` tests in `tests/integration/test_app.py` (both from feature 002) gain
cases for local-path rejection with the FR-007 message.

**Target Platform**: Unchanged — local web-service, plus the feature 002 Windows/Citrix standalone
package (whose `launch_config.json` contract is updated by this feature, not re-architected).

**Project Type**: Single-project, in-place modification of existing modules — no new service, no new
top-level source tree.

**Performance Goals**: Unchanged from spec 001/002. No new performance requirement.

**Constraints**: Zero write/upload requests to SharePoint anywhere in the codebase (FR-002); no
local-file fallback anywhere, including for the standalone package (FR-004); clear, specific error
when a leftover local-file configuration is encountered (FR-007).

**Scale/Scope**: Same single-manager scope as spec 001/002. Three source files change
(`data_fetcher.py`, `app.py`, `launch_config.py`), one config template file, one central test
fixture, two feature-002-owned test files gain cases, and one feature-002 *operational* doc
(`quickstart.md`) is corrected — feature 002's `spec.md`/`plan.md`/`research.md`/`data-model.md`/
`contracts/*.md` are left as historical record (see research.md #4 for why).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I — Spec-First Development
**PASS** — `spec.md` is complete with prioritized user stories, acceptance scenarios, functional
requirements, and measurable success criteria; the one clarification needed (FR-004's scope fork)
was resolved with the user before planning began.

### Principle II — Test-Driven Development
**PASS (plan-level)** — Every behavior change (rejection in `get_workbook`, `load_launch_config`,
`resolve_launch_source`) gets a test written first, following Red-Green-Refactor. The existing
~100-test suite is preserved intact via the `conftest.py` fixture change, not weakened or skipped.

### Principle III — Data Integrity & Accuracy
**N/A** — This principle concerns the accuracy/auditability of absence records themselves; this
feature does not touch absence-record logic. Its "don't corrupt the source" goal is about an
external system's file, not this application's own data integrity, so it's covered as an explicit
functional requirement (FR-002) rather than this constitution principle.

### Principle IV — Privacy & Compliance
**JUSTIFIED DEVIATION (inherited from spec 001/002)** — Same localhost-only, single-authorized-user
posture. No new personal or sensitive data is introduced; the SharePoint URL is the same kind of
value already accepted and stored today.

### Principle V — Simplicity & Maintainability
**PASS** — Validation logic lives in exactly three places, each with a clear, distinct
responsibility (CLI arg, `launch_config.json`, and a defensive backstop in `get_workbook` itself) —
no duplicated or scattered checks. The test-suite adaptation is centralized in one fixture rather
than touching every test file. No new dependency is introduced.

## Project Structure

### Documentation (this feature)

```text
specs/003-sharepoint-direct-connection/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── launch-config.md  # Updated (URL-only) launch_config.json contract — supersedes
│                          #   specs/002-windows-standalone-build/contracts/launch-config.md
│                          #   for the excel_source field
└── tasks.md              # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

### Source Code (repository root)

```text
absence_dashboard/
├── data_fetcher.py         # MODIFIED: get_workbook() rejects any non-http(s) source; local-file
│                            #   branch removed entirely
├── app.py                  # MODIFIED: create_app()'s excel_path -> excel_source param and
│                            #   EXCEL_PATH -> EXCEL_SOURCE config key rename; resolve_launch_source()
│                            #   rejects non-URL CLI args with an FR-007 message; create_app()'s
│                            #   except clause drops the now-unreachable FileNotFoundError case
└── launch_config.py         # MODIFIED: load_launch_config() rejects non-URL excel_source with an
                             #   FR-007 message instead of accepting an existing local path

launch_config.example.json  # MODIFIED: placeholder value becomes a SharePoint URL example

specs/002-windows-standalone-build/
└── quickstart.md            # MODIFIED (operational doc, kept current — see research.md #4);
                              #   spec.md/plan.md/research.md/data-model.md/contracts/*.md left
                              #   as historical record, unmodified

tests/
├── conftest.py                       # MODIFIED: app/client fixtures mock requests.get and pass a
│                                      #   fake https:// URL instead of a local path to create_app
├── unit/test_data_fetcher.py         # MODIFIED: TestLocalPath replaced with rejection tests
├── unit/test_launch_config.py        # MODIFIED: add local-path-rejection cases
└── integration/test_app.py           # MODIFIED: TestResolveLaunchSource gains rejection cases
```

**Structure Decision**: In-place modification of the existing single-project layout — no new
modules, no new top-level directories. The one structural test change (mocking HTTP in
`conftest.py`) is deliberately centralized so the ~100 existing route/logic tests require zero
per-file changes.

## Complexity Tracking

*No unjustified Constitution Check violations — table intentionally empty.*
