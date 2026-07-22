# Implementation Plan: SharePoint Delegated Device-Code Authentication

**Branch**: `004-sharepoint-device-code-auth` | **Date**: 2026-07-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-sharepoint-device-code-auth/spec.md`

## Summary

Replace the anonymous SharePoint download (feature 003) with delegated OAuth2 device-code sign-in
via Microsoft's official `msal` library, authenticating as the manager's own Barmenia account. A new
`absence_dashboard/graph_auth.py` module acquires and caches an access token (silent renewal first,
interactive device-code prompt only when silent fails), with the token cache encrypted at rest via
OS-native protection (`msal-extensions`' DPAPI-backed persistence on Windows). `data_fetcher.py`'s
`get_workbook()` gains a required bearer token and switches from the old `?download=1` anonymous
fetch to Microsoft Graph's `/shares/{shareId}/driveItem/content` endpoint, which resolves the exact
same SharePoint sharing URL already configured in `launch_config.json` — no change to how the
manager identifies their file (FR-007). `app.py`'s `main()` acquires a token before starting the
Flask app; both the initial load and the `/api/refresh` endpoint request a fresh token on every
fetch (silent-only for refresh, since a browser-triggered request has no console to show a device
code on) so long-running sessions keep working across normal token expiry without a restart. The
read-only guarantee (FR-006) is preserved structurally: only `Files.Read` (a read-only Graph scope)
is ever requested, and `data_fetcher.py` still only ever issues GET requests.

## Technical Context

**Language/Version**: Python 3.10+ (unchanged).

**Primary Dependencies**: `msal` (Microsoft's official OAuth2/device-code library) and
`msal-extensions` (OS-native encrypted token cache persistence) — both new; Flask/openpyxl/requests
unchanged. `truststore` (feature 003) continues to cover TLS trust for the same corporate-proxy
reason, now also covering Graph API calls.

**Storage**: New — an encrypted token-cache file (e.g., `state/token_cache.bin`) alongside the
existing `state/state.json`/`launch_config.json` pattern, holding the MSAL token cache blob
(encrypted at rest via Windows DPAPI through `msal-extensions`). No change to `state/state.json`'s
own schema.

**Testing**: pytest (existing, unchanged). New tests mock `msal.PublicClientApplication` directly
(matching the existing pattern of mocking `requests`/`launch_config` in features 002/003) — no test
ever performs a real device-code flow or reaches a real Microsoft endpoint.

**Target Platform**: Unchanged — local web-service, plus the feature 002 Windows/Citrix standalone
package. The token-cache encryption approach is OS-native (DPAPI on Windows, Keychain on macOS,
falls back to a plaintext-with-warning cache on Linux via `msal-extensions`' own fallback, though the
target platform here is always Windows).

**Project Type**: Single-project, in-place modification plus one new module
(`absence_dashboard/graph_auth.py`) — no new service.

**Performance Goals**: Unchanged dashboard performance targets. New: first-time sign-in adds a
manual step (spec SC-001: under 3 minutes including sign-in); silent token renewal on every
load/refresh must not perceptibly slow down those existing operations (MSAL's silent acquisition is
a local cache lookup plus, at most, one refresh-token network round-trip).

**Constraints**: No app-only/client-credentials access (declined by IT); only a read-only delegated
Graph scope (`Files.Read`) is ever requested; the token cache must be encrypted at rest, not stored
as plain text (FR-004); device-code flow only — no local redirect listener (FR-002).

**Scale/Scope**: Same single-manager scope as prior features. One new module
(`graph_auth.py`), modifications to `data_fetcher.py`, `app.py`, and `launch_config.json`'s schema
(two new required fields: `client_id`, `tenant_id`), plus a new external dependency: a one-time
Azure AD app registration that must exist before this feature can be used (see spec.md Assumptions).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I — Spec-First Development
**PASS** — `spec.md` is complete with prioritized user stories, acceptance scenarios, functional
requirements, and measurable success criteria; no open `[NEEDS CLARIFICATION]` markers.

### Principle II — Test-Driven Development
**PASS (plan-level)** — `graph_auth.py`'s token-acquisition logic (silent-then-interactive
fallback, cache path handling) and `data_fetcher.py`'s Graph-endpoint construction each get tests
written first, mocking `msal.PublicClientApplication` and `requests` respectively — consistent with
how features 002/003 tested config-loading and fetch logic without ever hitting real external
services.

### Principle III — Data Integrity & Accuracy
**N/A** — Concerns absence-record accuracy/auditability; unaffected by how the source file is
authenticated to.

### Principle IV — Privacy & Compliance
**PASS** — This is the first feature in the project to handle a genuinely sensitive credential (an
OAuth token tied to the manager's real identity), and it is treated accordingly: the constitution's
"sensitive fields MUST be encrypted at rest" is satisfied literally via OS-native DPAPI encryption of
the token cache (`msal-extensions`), not just asserted. Still localhost-only, single-authorized-user;
no new remote party receives data beyond Microsoft's own login/Graph endpoints, which the manager was
already trusting by using SharePoint in a browser.

### Principle V — Simplicity & Maintainability
**PASS** — Uses Microsoft's own official, purpose-built libraries (`msal`, `msal-extensions`) rather
than hand-rolling OAuth2/device-code/token-cache-encryption logic. Token acquisition is centralized
in one new module with a single responsibility (`graph_auth.py`), called from exactly two call sites
(`main()` at startup, `post_refresh()` on reload) — no duplicated auth logic.

## Project Structure

### Documentation (this feature)

```text
specs/004-sharepoint-device-code-auth/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── launch-config.md  # Updated (adds client_id/tenant_id) launch_config.json contract —
│                          #   supersedes specs/003-sharepoint-direct-connection/contracts/
│                          #   launch-config.md for these new fields
└── tasks.md              # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

### Source Code (repository root)

```text
absence_dashboard/
├── graph_auth.py            # NEW: acquire_token(client_id, tenant_id, cache_path) -> str;
│                             #   silent-first, device-code-interactive fallback; encrypted
│                             #   token cache via msal-extensions
├── data_fetcher.py           # MODIFIED: get_workbook(source, access_token) — Graph
│                             #   /shares/{shareId}/driveItem/content endpoint, Bearer auth,
│                             #   instead of the old anonymous ?download=1 GET
├── launch_config.py          # MODIFIED: load_launch_config() also reads/validates
│                             #   client_id and tenant_id
└── app.py                    # MODIFIED: main() acquires a token before create_app(); both
                              #   create_app()'s initial load and post_refresh() request a
                              #   fresh (silently-renewed-if-needed) token per fetch

launch_config.example.json   # MODIFIED: adds client_id/tenant_id placeholder fields

tests/
├── unit/test_graph_auth.py           # NEW: silent/interactive/cache-path logic, mocking msal
├── unit/test_data_fetcher.py         # MODIFIED: Graph-endpoint + Bearer-header cases
├── unit/test_launch_config.py        # MODIFIED: client_id/tenant_id validation cases
├── integration/test_app.py           # MODIFIED: token-acquisition call sites mocked
└── conftest.py                       # MODIFIED: app/client fixtures inject a fake token
                                       #   getter instead of a real graph_auth call
```

**Structure Decision**: In-place modification plus one new, single-responsibility module
(`graph_auth.py`) — no new service, no new top-level source tree. Mirrors the same pattern features
002/003 already used (`launch_config.py`, `data_fetcher.py` as small, independently-testable
modules called from `app.py`'s entry point).

## Complexity Tracking

*No unjustified Constitution Check violations — table intentionally empty.*
