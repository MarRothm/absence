# Contract: `launch_config.json` (reverted — local path, no auth fields)

**Phase 1 output** | **Date**: 2026-07-22

Supersedes `specs/004-sharepoint-device-code-auth/contracts/launch-config.md`. That document (and
feature 003's before it) are left unmodified as historical record; this document is the current
contract.

## Schema

```json
{
  "excel_source": "absences.xlsx",
  "port": 5002
}
```

| Field | Type | Required | Default |
|---|---|---|---|
| `excel_source` | string — local filesystem path (absolute, or relative to the executable's directory) | yes | *(none — startup error if absent or the path doesn't exist)* |
| `port` | integer | no | `5002` |

## What changed from feature 004's contract

`client_id` and `tenant_id` are removed entirely — there is no sign-in, so no app registration to
reference. `excel_source` reverts from "must be an `http(s)://` URL" to "must be an existing local
file path" — the exact opposite validation direction from feature 003/004, restoring feature 002's
original behavior.

## Precedence (unchanged shape, simplified content)

1. A positional `excel_file` CLI argument, if supplied, is used instead of `launch_config.json` —
   and, like `excel_source`, must be an existing local path.
2. Otherwise, `excel_source`/`port` are read from `launch_config.json`.

There is no longer any field that's "always read from `launch_config.json` regardless of the CLI
argument" (client_id/tenant_id's special rule from feature 004 no longer applies to anything).

## Rejection behavior

| Condition | Result |
|---|---|
| `excel_source` missing or empty | Startup error: source not configured |
| `excel_source` (or the CLI argument) points to a path that doesn't exist | Startup error: file not found |

No silent fallback in any case — matches FR-005.

## Compatibility

Breaking change for any `launch_config.json` still holding `client_id`/`tenant_id`/a SharePoint URL
from feature 003/004 — those fields are now ignored (`client_id`/`tenant_id`) or rejected
(`excel_source` as a URL, since it no longer resolves to an existing local path). Intentional, per
FR-001/FR-002/FR-003.
