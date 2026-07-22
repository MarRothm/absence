# Data Model: SharePoint Delegated Device-Code Authentication

**Phase 1 output** | **Date**: 2026-07-22

## App Registration Reference (new `launch_config.json` fields)

Identifies which Azure AD app registration the dashboard signs in as. Static, provided once by
IT/tenant-admin after creating the registration (see spec.md Assumptions).

| Field | Type | Required | Notes |
|---|---|---|---|
| `client_id` | string (GUID) | Yes | The app registration's Application (client) ID. |
| `tenant_id` | string (GUID or domain) | Yes | The Barmenia Entra ID tenant ID, or the tenant's verified domain (e.g. `barmeniagroup.onmicrosoft.com`). Used to build the authority URL (`https://login.microsoftonline.com/{tenant_id}`). |

**Validation rules**:
- Both fields are required whenever `excel_source` is present (i.e., whenever the app needs to fetch
  a file) — missing either produces a startup error naming the missing field, mirroring the existing
  "clear, actionable error" pattern for a missing/invalid `excel_source`.
- No format validation beyond "non-empty string" — an invalid ID surfaces naturally as a sign-in
  failure from Microsoft's own endpoint, with Microsoft's own error message.

## Signed-In Session (token cache)

Not a manager-facing configuration value — an opaque, encrypted cache file MSAL manages.

| Field | Type | Notes |
|---|---|---|
| Cache file path | string | e.g. `state/token_cache.bin`, alongside `state/state.json` |
| Cache contents | encrypted binary blob | MSAL's serialized token cache (access token, refresh token, account metadata), encrypted at rest via `msal-extensions`' DPAPI-backed persistence (Windows) |

**Lifecycle**:
- Created on first successful device-code sign-in.
- Read and updated on every token acquisition (silent renewal writes the refreshed token back).
- Never read or written by any code path other than `graph_auth.py`.
- Deleting this file forces a fresh interactive sign-in on the next launch (no separate "sign out"
  feature is introduced — the file itself is the sign-out mechanism, kept simple per Principle V).

**Validation rules**: None at the application level — MSAL owns the cache's internal format and
validity checks entirely; `graph_auth.py` never parses or trusts its contents directly, only calls
MSAL's own `acquire_token_silent()`/device-code APIs against it.

## Compatibility with feature 003's data model

`launch_config.json`'s `excel_source` field is unchanged in meaning and validation (still must be an
`http(s)://` SharePoint link) — this feature only adds `client_id`/`tenant_id` alongside it and
changes what happens internally when the file is fetched.
