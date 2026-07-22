# Data Model: SharePoint Direct Connection

**Phase 1 output** | **Date**: 2026-07-21

This feature tightens validation on an existing value rather than introducing new persisted data.

## SharePoint Source Connection

The single value that identifies where the dashboard reads its absence spreadsheet from. Same
underlying value as before (spec 001's "excel source"), now with a narrowed, stricter contract.

| Field | Type | Required | Notes |
|---|---|---|---|
| source URL | string | Yes | Must start with `http://` or `https://`. Any other value (a filesystem path, a relative path, an empty string, `None`) is rejected. |

**Where it lives**:
- CLI positional argument (`app.py`'s `__main__`, local/dev use) — validated by `resolve_launch_source()`.
- `launch_config.json`'s `excel_source` field (feature 002, packaged/double-click use) — validated by `load_launch_config()`.
- `create_app(excel_source, ...)` / `app.config["EXCEL_SOURCE"]` — the resolved value, always
  already validated as a URL by the time it reaches here.

**Validation rules** (identical at every layer, per research.md #1):
- Missing/empty → rejected with a "not configured" style error.
- Present but not starting with `http://`/`https://` → rejected with an FR-007 message explicitly
  stating local-file support has been removed and a SharePoint link is required.
- No existence/reachability check is performed at validation time (that only happens when
  `get_workbook()` actually issues the GET request and can raise `ConnectionError` for a bad
  response) — validation only checks the *shape* of the value (is it a URL at all).

**State transitions**: None — this is a startup-time value, re-validated fresh on every load/reload,
never mutated by the running application.

## Read-only guarantee (cross-cutting, not a data entity)

Not a data entity, but worth recording precisely since it's this feature's core requirement:
`data_fetcher.get_workbook()` performs exactly one HTTP call (`requests.get`, a GET) per load, and
opens the response bytes with `openpyxl.load_workbook(..., read_only=True, data_only=True)`. There
is no code path anywhere in the application that issues a `PUT`/`POST`/upload request to SharePoint,
or that writes back to the downloaded bytes/workbook object. This was already true before this
feature (spec 001); this feature makes it the *only* possible path (no local-file alternative) and
documents it as an explicit, permanent guarantee (FR-002) rather than an implementation incidental.
