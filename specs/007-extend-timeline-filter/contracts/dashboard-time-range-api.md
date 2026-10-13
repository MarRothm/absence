# Contract: Dashboard Time Range

Changes to the two endpoints that return the dashboard payload. All other routes (`/api/clusters`,
`/api/phases`, `/api/cumul-groups`) are unchanged; phase and cumul-group dates are already accepted
for any year.

## `GET /api/dashboard`

**Query parameters** (optional, both or neither):

| Param | Example | Meaning |
|---|---|---|
| `from` | `01/2027` | First month shown (inclusive) |
| `to` | `03/2027` | Last month shown (inclusive) |

Omitted → rolling 12-month default (current ISO week → week containing today + 1 year).

**Response `200`** (existing fields omitted unless changed):

```json
{
  "calendar_weeks": [
    {
      "key": "2027-W01", "year": 2027, "week_number": 1,
      "label": "CW1 2027 | 4 Jan",
      "start": "2027-01-04", "end": "2027-01-08",
      "days": ["2027-01-04", "2027-01-05", "2027-01-06", "2027-01-07", "2027-01-08"]
    }
  ],
  "time_range": { "start": "2027-01-01", "end": "2027-03-31", "from": "01/2027", "to": "03/2027", "is_default": false },
  "data_in_range": true,
  "members": [
    {
      "name": "Alice",
      "cumul_risks":   [ { "group": "Backend Coverage", "week_key": "2027-W05" } ],
      "sole_coverage": [ { "group": "Backend Coverage", "week_key": "2027-W05" } ]
    }
  ]
}
```

Breaking change for the frontend only: risk entries carry `week_key` instead of `week_number`.

**Response `400`** — `{ "error": "<message>" }`, for:
- only one of `from` / `to` given → `"Both 'from' and 'to' are required (MM/YYYY)."`
- malformed value (e.g. `13/2027`, `2027`, `1/27`) → `"Invalid month '<value>' — expected MM/YYYY."`
- `to` before `from` → `"'To' month must be the same as or later than 'From' month."`

## `POST /api/refresh`

Accepts the same `from` / `to` query parameters with the same validation (400 is returned
**before** the Excel file is reloaded). Success response is the dashboard payload above plus the
existing `removed_stale_references`. Existing `422` (file could not be reloaded) unchanged.

## UI contract (`index.html` / `main.js`)

- Header gains a time-filter group: `#time-from`, `#time-to` (text, placeholder `MM/YYYY`),
  `#btn-time-apply`, `#btn-time-reset`, status `#time-range-status`, inline error `#time-error`.
- `#time-range-status` always shows the applied range: `"Rolling 12 months (CW42 2026 – CW41 2027)"`
  when default, otherwise `"01/2027 – 03/2027"` (FR-009).
- Invalid input → `#time-error` shown, previous range kept (FR-006). Reset → rolling default
  (FR-008).
- `data_in_range === false` → warning banner "The loaded file contains no data for the selected
  range." (FR-013).
