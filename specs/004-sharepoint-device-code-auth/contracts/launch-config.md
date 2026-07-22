# Contract: `launch_config.json` (updated — adds `client_id`/`tenant_id`)

**Phase 1 output** | **Date**: 2026-07-22

Supersedes `specs/003-sharepoint-direct-connection/contracts/launch-config.md` for the two new
fields below; that document (and feature 002's original) are left unmodified as historical record.
`excel_source`'s own contract (must be an `http(s)://` SharePoint link) is unchanged.

## Schema

```json
{
  "excel_source": "https://company.sharepoint.com/:x:/s/yoursite/Exxxxxxxxxxxxxxx?e=xxxxxx",
  "client_id": "00000000-0000-0000-0000-000000000000",
  "tenant_id": "00000000-0000-0000-0000-000000000000",
  "port": 5002
}
```

| Field | Type | Required | Default |
|---|---|---|---|
| `excel_source` | string — must start with `http://` or `https://` | yes | *(none — startup error if absent or not a URL)* |
| `client_id` | string | yes | *(none — startup error if absent)* |
| `tenant_id` | string | yes | *(none — startup error if absent)* |
| `port` | integer | no | `5002` |

## What changed from feature 003's contract

Two new required fields, `client_id` and `tenant_id`, identifying the Azure AD app registration the
dashboard signs in as (see data-model.md). Both must be obtained from IT/tenant-admin once the app
registration exists (spec.md Assumptions) and are the same for every manager using this
organization's deployment — not personal credentials.

## Precedence (unchanged from features 002/003)

1. A positional `excel_file` CLI argument, if supplied, is used instead of `launch_config.json` for
   the file source — but `client_id`/`tenant_id` are **always** read from `launch_config.json`
   regardless of whether the CLI argument is used, since there is no CLI-argument equivalent for
   them.
2. Otherwise, everything (`excel_source`, `client_id`, `tenant_id`, `port`) is read from
   `launch_config.json`.

## Rejection behavior

| Condition | Result |
|---|---|
| `client_id` or `tenant_id` missing/empty | Startup error naming the missing field |
| `client_id`/`tenant_id` present but invalid (wrong GUID, wrong tenant) | Not caught at config-validation time — surfaces as a sign-in failure from Microsoft's own endpoint when the device-code flow is attempted |

No silent fallback in any case — matches FR-005/FR-008.

## Compatibility

Breaking change for any deployment that doesn't yet have `client_id`/`tenant_id` set — intentional,
since the feature cannot function without them (no Azure AD app registration means no sign-in is
possible at all). Not breaking for `excel_source`'s own format or meaning.
