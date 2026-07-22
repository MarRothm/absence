# Contract: `launch_config.json` (updated — SharePoint URL only)

**Phase 1 output** | **Date**: 2026-07-21

Supersedes `specs/002-windows-standalone-build/contracts/launch-config.md` for the `excel_source`
field. That document is left unmodified as historical record (research.md #4); this document is the
current contract.

## Location

Unchanged: same directory as the executable / `run-dashboard.bat` (the extracted bundle root).

## Schema

```json
{
  "excel_source": "https://company.sharepoint.com/:x:/s/yoursite/Exxxxxxxxxxxxxxx?e=xxxxxx",
  "port": 5002
}
```

| Field | Type | Required | Default |
|---|---|---|---|
| `excel_source` | string — **must start with `http://` or `https://`** | yes | *(none — startup error if absent or not a URL)* |
| `port` | integer | no | `5002` |

**What changed from feature 002's original contract**: `excel_source` no longer accepts a local
file path, even one that exists on disk. A local path now produces the same rejection as a
missing/malformed value — see Precedence below.

## Precedence (unchanged from feature 002)

1. A positional `excel_file` CLI argument (local/dev use), if supplied, is used instead of
   `launch_config.json` — but it too must now be a `http(s)://` URL (see `resolve_launch_source()`
   in `app.py`); a local path supplied this way is rejected the same way.
2. Otherwise, `launch_config.json` is read from the executable's directory.

## Rejection behavior

| Condition | Result |
|---|---|
| `excel_source` missing or empty | Startup error: source not configured |
| `excel_source` present, not `http://`/`https://` (e.g., a local path) | Startup error explicitly stating local-file support has been removed; configure a SharePoint link instead (FR-007) |
| `excel_source` is a valid-looking URL but unreachable | Not caught at config-validation time — surfaces later as a `ConnectionError` when the dashboard actually tries to load it |

No silent fallback in any case — matches FR-005.

## Compatibility

Breaking change for any existing `launch_config.json`/CLI usage that pointed at a local file path;
intentional, per FR-004. Not breaking for any existing SharePoint-URL usage, which is unaffected.
