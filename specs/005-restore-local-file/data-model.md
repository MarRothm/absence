# Data Model: Restore Local File Data Source

**Phase 1 output** | **Date**: 2026-07-22

This feature removes two data concepts introduced by feature 004 (the App Registration Reference
and the Signed-In Session/token cache) and restores one from before feature 003.

## Local Data File (restored)

The `.xlsx` file the manager downloads from SharePoint themselves and points the dashboard at —
identical in spirit to spec 001's original design, now the dashboard's *only* data source (not one
of two options).

| Field | Type | Required | Notes |
|---|---|---|---|
| `excel_source` | string (local filesystem path) | Yes | Must be an existing, readable file at startup. No `http(s)://` value is accepted — there is no network fetch path to accept one. |

**Validation rules**:
- Missing `excel_source` → startup error naming the missing field.
- `excel_source` present but the path doesn't exist → the same actionable "File not found" error
  pattern used everywhere else in this app.

**Lifecycle**: read once at startup (or CLI-arg-supplied) and again on every Reload — always from
the same configured path, always synchronously from local disk, never cached or copied elsewhere by
the application.

## Removed entities (feature 004, no longer part of the data model)

- **App Registration Reference** (`client_id`/`tenant_id`): removed from `launch_config.json`
  entirely — there is no Azure AD app to reference.
- **Signed-In Session** (the encrypted token cache, `state/token_cache.bin`): removed — no sign-in
  occurs, so nothing is cached. Any leftover file from a prior installation is simply ignored (not
  read, not deleted automatically).
