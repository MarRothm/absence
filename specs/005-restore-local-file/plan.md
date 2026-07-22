# Implementation Plan: Restore Local File Data Source

**Branch**: `005-restore-local-file` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/005-restore-local-file/spec.md`

## Summary

Fully revert the SharePoint direct-connection (feature 003) and delegated device-code sign-in
(feature 004) work: `data_fetcher.get_workbook()` goes back to reading a local `.xlsx` path
directly via `openpyxl.load_workbook()` — no HTTP request, no Graph API, no bearer token, no
network dependency of any kind. `absence_dashboard/graph_auth.py` is deleted outright.
`launch_config.py`/`app.py`'s CLI arg both go back to validating an existing local file path
instead of a SharePoint URL, and drop `client_id`/`tenant_id` entirely. `main()` no longer acquires
a token before `create_app()`, and `post_refresh()` no longer attempts any token renewal. The
now-unused dependencies (`msal`, `msal-extensions`, `truststore`, and `requests` — nothing else in
the codebase uses `requests` once the HTTP fetch path is gone) are removed from `requirements.txt`.
Every test that mocks HTTP/MSAL for this path is rewritten back to simple local-file fixtures —
this actually *simplifies* `tests/conftest.py` back toward its original, pre-003 form. Documentation
follows this project's established precedent: features 003/004's `spec.md`/`plan.md`/`research.md`/
`data-model.md`/`contracts/*.md` stay untouched as historical record of what was attempted and why
it didn't work in this tenant; their (and feature 002's) `quickstart.md` files — living operational
docs — get updated to point at this feature's `quickstart.md` as current truth.

## Technical Context

**Language/Version**: Python 3.10+ (unchanged).

**Primary Dependencies**: Flask 3.x, openpyxl 3.x (unchanged, and now the *only* two runtime
dependencies besides pytest) — `requests`, `truststore`, `msal`, `msal-extensions` are all removed;
nothing in the codebase needs an HTTP client or an OS trust store once there is no outbound network
call anywhere in the application.

**Storage**: `state/state.json` (dependencies/clusters/phases, unchanged). `launch_config.json`
loses `client_id`/`tenant_id`; its encrypted token-cache file (`state/token_cache.bin`, feature 004)
is no longer created or read — nothing else in the codebase touches it.

**Testing**: pytest (existing, unchanged). `tests/unit/test_graph_auth.py` is deleted.
`tests/conftest.py`'s `app`/`client` fixtures drop all `requests`/`graph_auth` mocking and pass a
local file path straight to `create_app()` again. `tests/unit/test_data_fetcher.py`,
`tests/unit/test_launch_config.py`, and the `TestResolveLaunchSource`/`TestMainStartupTokenFlow`/
`TestRefreshExpiredSession` classes in `tests/integration/test_app.py` are rewritten for the
local-path contract; the two Graph-specific integration test classes are deleted outright since
there's no longer a startup-token-flow or silent-refresh-failure behavior to test.

**Target Platform**: Unchanged — local web-service, plus the feature 002 Windows/Citrix standalone
package (whose `launch_config.json` contract and `quickstart.md` both revert to local-path
configuration, dropping the sign-in step entirely).

**Project Type**: Single-project, in-place modification and deletion of existing modules — no new
service, no new dependency.

**Performance Goals**: Unchanged. Removing the network/auth round-trip can only make load/reload
faster, not slower.

**Constraints**: Zero network calls anywhere in the application (FR-001/FR-006); zero sign-in or
IT-provisioned-credential requirement (FR-002/FR-003) — both stronger, simpler constraints than any
prior SharePoint-connection feature had.

**Scale/Scope**: Same single-manager scope as all prior features. Net reduction in surface area:
one file deleted (`graph_auth.py`), four dependencies removed, `launch_config.json`'s schema shrinks
back to two fields, and the test suite gets smaller and simpler, not larger.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I — Spec-First Development
**PASS** — `spec.md` is complete with prioritized user stories, acceptance scenarios, functional
requirements, and measurable success criteria; no open `[NEEDS CLARIFICATION]` markers.

### Principle II — Test-Driven Development
**PASS (plan-level)** — Every reverted behavior (local-path validation, local-path fetch, the
simplified startup flow) gets its test rewritten to assert the new-old behavior first, following
Red-Green-Refactor, exactly as every prior feature in this line has done for its own changes.

### Principle III — Data Integrity & Accuracy
**N/A** — Unaffected; this feature does not touch absence-record logic.

### Principle IV — Privacy & Compliance
**PASS** — This feature *removes* the one sensitive credential (the OAuth token cache) this project
ever introduced, returning to the simpler, lower-risk local-only posture spec 001 always had. No new
privacy surface is introduced; an existing one is eliminated.

### Principle V — Simplicity & Maintainability
**PASS**, explicitly and centrally — this entire feature exists *because of* this principle: keeping
confirmed-non-functional SharePoint/auth machinery (and four dependencies) around for a path IT has
permanently blocked would be exactly the kind of unjustified complexity this principle rules out.
Removing it is the simplification.

## Project Structure

### Documentation (this feature)

```text
specs/005-restore-local-file/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── launch-config.md  # Reverted launch_config.json contract — supersedes
│                          #   specs/004-sharepoint-device-code-auth/contracts/launch-config.md
└── tasks.md              # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

### Source Code (repository root)

```text
absence_dashboard/
├── graph_auth.py            # DELETED (feature 004's module — no longer needed)
├── data_fetcher.py           # MODIFIED: get_workbook(source) reads a local path directly via
│                              #   openpyxl.load_workbook(); no requests/truststore/Graph endpoint
├── launch_config.py          # MODIFIED: load_launch_config() validates excel_source as an
│                              #   existing local path again; client_id/tenant_id fields dropped
└── app.py                    # MODIFIED: _load_excel()/create_app() drop access_token param;
                              #   resolve_launch_source() validates a local CLI path again and
                              #   drops client_id/tenant_id; main() no longer acquires a token;
                              #   post_refresh() no longer attempts token renewal

launch_config.example.json   # MODIFIED: excel_source reverts to a local filename placeholder;
                              #   client_id/tenant_id fields removed

requirements.txt             # MODIFIED: requests, truststore, msal, msal-extensions all removed

specs/002-windows-standalone-build/quickstart.md   # MODIFIED (operational doc): local-path config,
                                                    #   sign-in step removed
specs/001-absence-dashboard/quickstart.md          # MODIFIED: forward-pointer updated to this feature
specs/003-sharepoint-direct-connection/quickstart.md  # MODIFIED: forward-pointer updated to this feature
specs/004-sharepoint-device-code-auth/quickstart.md   # MODIFIED: forward-pointer updated to this feature
# spec.md/plan.md/research.md/data-model.md/contracts/*.md of features 002/003/004 stay
# unmodified as historical record, per this project's established precedent

README.md                    # MODIFIED: Quick Start reverts to local-file usage, no sign-in step

tests/
├── conftest.py                        # MODIFIED: app/client fixtures pass a local file path
│                                       #   directly to create_app() again — no more HTTP/MSAL mocks
├── unit/test_graph_auth.py            # DELETED
├── unit/test_data_fetcher.py          # MODIFIED: local-path success/failure tests restored
├── unit/test_launch_config.py         # MODIFIED: local-path validation tests restored
└── integration/test_app.py            # MODIFIED: TestResolveLaunchSource reverted to 2-tuple;
                                        #   TestMainStartupTokenFlow and TestRefreshExpiredSession
                                        #   deleted (no token flow left to test)
```

**Structure Decision**: In-place modification and net deletion — no new modules, no new
dependencies. This is the one feature in this project's history so far that shrinks the codebase
and its dependency footprint rather than growing them.

## Complexity Tracking

*No unjustified Constitution Check violations — table intentionally empty.*
