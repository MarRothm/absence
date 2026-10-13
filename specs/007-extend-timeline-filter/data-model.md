# Data Model: Extended Timeline with Month-Range Filter

No persisted data changes. `state/state.json` and `launch_config.json` are untouched; existing
phases, cumul groups and clusters remain valid as-is. All entities below are computed per request.

## Calendar week (payload `calendar_weeks[]`) — modified

| Field | Type | Change | Notes |
|---|---|---|---|
| `key` | string | **new** | ISO week string `"YYYY-Www"`, e.g. `"2027-W05"`. Unique identity of the week (FR-002). |
| `year` | int | unchanged | ISO year (may differ from the calendar year of Monday for week 1 / week 53). |
| `week_number` | int | unchanged | ISO week number 1–53. |
| `label` | string | **changed** | `"CW{week} {year} \| {day} {Mon}"`, e.g. `"CW5 2027 \| 1 Feb"` (FR-003). |
| `start` / `end` | ISO date | unchanged | Monday / Friday. |
| `days` | ISO date[5] | unchanged | Mon–Fri. |

**Inclusion rule**: a week is in the list iff at least one of its `days` is within the resolved
range `[start, end]` (FR-005). Weeks are ordered chronologically, no duplicates, no gaps.

## Time range (request + payload `time_range`) — new

Request (query parameters on `GET /api/dashboard`, `POST /api/refresh`):

| Param | Format | Rule |
|---|---|---|
| `from` | `MM/YYYY` (or `M/YYYY`) | month 1–12, 4-digit year |
| `to` | `MM/YYYY` (or `M/YYYY`) | same; `to` ≥ `from` |

Both absent → rolling default. Exactly one present, malformed value, or `to` < `from` → 400.

Resolution:
- **Default** (`is_default = true`): `start` = Monday of today's ISO week; `end` = today + 1 year
  (29 Feb → 28 Feb).
- **Filtered** (`is_default = false`): `start` = 1st day of `from` month; `end` = last day of `to`
  month.

Payload:

```json
"time_range": { "start": "2026-10-12", "end": "2027-10-13", "from": "10/2026", "to": "10/2027", "is_default": true }
```

`from`/`to` in the payload are the months of `start`/`end` (for the filtered case, exactly what
the manager entered, normalised to two-digit months).

## Data coverage — new

`DATA_RANGE` (app config, set on load/refresh): `(first_date, last_date)` of the Excel date map, or
`None` if the file has no dated columns.

Payload: `"data_in_range": bool` — true iff `DATA_RANGE` overlaps `[time_range.start, time_range.end]`.

## Member risk entries (payload `members[].cumul_risks[]`, `members[].sole_coverage[]`) — modified

| Field | Type | Change |
|---|---|---|
| `group` | string | unchanged |
| `week_key` | string | **replaces `week_number`** — matches `calendar_weeks[].key` |

Only weeks in the visible list produce entries. Critical-absence detection uses each member's full,
unclipped merged blocks (FR-010).

## Excel date map (parser) — behaviour change

`build_date_map(ws, year=None, today=None)`: when `year` is `None`, the starting year is inferred
(see research R4) instead of assumed to be `today.year`. `today` is injectable for tests.
