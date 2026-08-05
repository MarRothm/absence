# Contract: Cumul Groups API

Replaces `specs/*/contracts/*dependencies*` surfaces (none formally existed as a contract doc; the
old dependency routes are documented here only to show what is removed). This is the only API
contract change in this feature — `/api/clusters` and `/api/phases` are unaffected.

## Removed entirely

- `GET /api/dependencies`
- `POST /api/dependencies`
- `PUT /api/dependencies`
- `DELETE /api/dependencies`

## New: `GET /api/cumul-groups`

Returns all currently defined cumul groups.

**Response** `200`:
```json
{ "cumul_groups": [ { "name": "Backend Coverage", "members": ["Alice", "Bob"] } ] }
```

## New: `POST /api/cumul-groups`

Creates a cumul group.

**Request body**:
```json
{
  "name": "Backend Coverage",
  "members": ["Alice", "Bob"],
  "active_from": "2026-06-01",
  "active_to": "2026-06-30"
}
```
`active_from`/`active_to` are optional and must be provided together or not at all.

**Responses**:
- `201` — `{ "cumul_groups": [...] }` (full updated list, matching the `/api/clusters` POST convention)
- `400` — validation error (empty name, <2 members, unknown member, only one of
  `active_from`/`active_to`, `active_from > active_to`): `{ "error": "<message>" }`
- `409` — duplicate name or duplicate member set: `{ "error": "<message>" }`

## New: `PUT /api/cumul-groups/<name>`

Edits an existing cumul group's name and/or membership and/or active range, identified by its
current `name` in the URL path (matches `/api/clusters/<cluster_name>` and
`/api/phases/<phase_name>`).

**Request body** (all fields optional; omitted fields keep their current value):
```json
{ "name": "Backend Coverage v2", "members": ["Alice", "Bob", "Carol"], "active_from": null, "active_to": null }
```

**Responses**:
- `200` — `{ "cumul_groups": [...] }`
- `400` — validation error (as above, plus: fewer than 2 members after the edit)
- `404` — `{ "error": "Cumul group '<name>' not found." }`
- `409` — rename collides with another existing group's name or member set

## New: `DELETE /api/cumul-groups/<name>`

**Responses**:
- `200` — `{ "cumul_groups": [...] }` (group removed)
- `404` — `{ "error": "Cumul group '<name>' not found." }`

## Changed: `GET /api/dashboard` (and `POST /api/refresh`, which returns the same shape)

- Top-level `"dependencies"` replaced by `"cumul_groups"` (same shape as the `GET /api/cumul-groups`
  list).
- Each entry in `"members"` gains `"cumul_risks"` and `"sole_coverage"`:
  ```json
  "cumul_risks": [ { "group": "Backend Coverage", "week_number": 22 } ],
  "sole_coverage": [ { "group": "Backend Coverage", "week_number": 23 } ]
  ```
- Per-member `"is_bottleneck"` and `"deadlock_weeks"` are removed; the frontend derives equivalent
  at-a-glance flags from `"cumul_risks"`/`"sole_coverage"` instead.
- `POST /api/refresh`'s `"removed_stale_references"` list gains two new `"type"` values:
  `"cumul_group"` (whole group dropped below the 2-member minimum) and `"cumul_group_member"`
  (single member removed but the group still has ≥ 2 valid members), replacing the old
  `"dependency"` type. The existing `"cluster_member"` type is unchanged.
