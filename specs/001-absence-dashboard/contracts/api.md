# API Contract: Absence Management Dashboard

**Phase 1 output** | **Date**: 2026-05-07 | **Plan**: [../plan.md](../plan.md)

Base URL: `http://localhost:5000`  
Content-Type: `application/json` (all request and response bodies)

---

## GET /api/dashboard

Returns the complete data needed to render the dashboard. Called on page load and after refresh.

**Response 200**:

```json
{
  "calendar_weeks": [
    {
      "year": 2026, "week_number": 19, "label": "CW19 | 4 May",
      "start": "2026-05-04", "end": "2026-05-10",
      "days": ["2026-05-04","2026-05-05","2026-05-06","2026-05-07","2026-05-08"]
    }
  ],
  "members": [
    {
      "name": "Alice Müller",
      "cluster": "Backend",
      "is_bottleneck": false,
      "merged_blocks": [
        { "start": "2026-06-01", "end": "2026-06-05" }
      ],
      "at_risk_weeks": [23, 24],
      "depends_on": ["Bob Schmidt"]
    }
  ],
  "clusters": [
    { "name": "Backend", "members": ["Alice Müller", "Bob Schmidt"] }
  ],
  "dependencies": [
    { "from_member": "Alice Müller", "to_member": "Bob Schmidt" }
  ],
  "bottlenecks": ["Bob Schmidt"],
  "phases": [
    { "name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26" },
    { "name": "Sprint 10", "start_date": "2026-06-15", "end_date": "2026-06-26" }
  ],
  "skipped_rows": [
    { "row": 7, "reason": "Missing end date" }
  ]
}
```

---

## POST /api/refresh

Reloads the Excel file and returns updated dashboard data. Preserves all dependencies and clusters;
removes references to names no longer in the filtered Excel data.

**Request body**: none

**Response 200**: Same schema as `GET /api/dashboard`, plus:

```json
{
  "removed_stale_references": [
    { "type": "dependency", "entry": { "from_member": "OldPerson", "to_member": "Bob Schmidt" } }
  ]
}
```

**Response 500**:

```json
{ "error": "Cannot read Excel file", "detail": "<OS error message>" }
```

---

## GET /api/dependencies

Returns all currently stored dependencies.

**Response 200**:

```json
{
  "dependencies": [
    { "from_member": "Alice Müller", "to_member": "Bob Schmidt" }
  ]
}
```

---

## POST /api/dependencies

Adds a single dependency. Validates both member names exist in the loaded Excel data and that
adding the dependency would not create a cycle.

**Request body**:

```json
{ "from_member": "Alice Müller", "to_member": "Bob Schmidt" }
```

**Response 201**: Updated dependency list (same schema as GET /api/dependencies).

**Response 400** — validation error:

```json
{ "error": "Invalid member name", "detail": "'Unknown Person' not in loaded dataset" }
```

**Response 409** — cycle detected:

```json
{ "error": "Cycle detected", "cycle_path": ["Alice Müller", "Bob Schmidt", "Alice Müller"] }
```

**Response 409** — duplicate:

```json
{ "error": "Dependency already exists" }
```

---

## DELETE /api/dependencies

Removes a single dependency.

**Request body**:

```json
{ "from_member": "Alice Müller", "to_member": "Bob Schmidt" }
```

**Response 200**: Updated dependency list.

**Response 404**:

```json
{ "error": "Dependency not found" }
```

---

## GET /api/clusters

Returns all skill clusters.

**Response 200**:

```json
{
  "clusters": [
    { "name": "Backend", "members": ["Alice Müller", "Bob Schmidt"] }
  ]
}
```

---

## POST /api/clusters

Creates a new skill cluster.

**Request body**:

```json
{ "name": "Backend", "members": ["Alice Müller", "Bob Schmidt"] }
```

**Response 201**: Updated cluster list.

**Response 400** — duplicate name:

```json
{ "error": "Cluster name already exists" }
```

**Response 400** — invalid member name:

```json
{ "error": "Invalid member name", "detail": "'Unknown Person' not in loaded dataset" }
```

---

## PUT /api/clusters/{cluster_name}

Updates an existing cluster's member list. The cluster name in the URL is the current name;
to rename, delete and recreate.

**Request body**:

```json
{ "members": ["Alice Müller", "Carol Bauer"] }
```

**Response 200**: Updated cluster.

**Response 404**:

```json
{ "error": "Cluster not found" }
```

**Response 400**: Same schema as POST /api/clusters 400 responses.

---

## DELETE /api/clusters/{cluster_name}

Deletes a skill cluster. Members are not deleted — they become ungrouped.

**Response 200**: Updated cluster list.

**Response 404**:

```json
{ "error": "Cluster not found" }
```

---

## GET /api/phases

Returns all project phases.

**Response 200**:

```json
{
  "phases": [
    { "name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26" }
  ]
}
```

---

## POST /api/phases

Creates a new project phase.

**Request body**:

```json
{ "name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26" }
```

**Response 201**: Updated phases list (same schema as GET /api/phases).

**Response 400** — duplicate name:

```json
{ "error": "Phase 'Go-Live' already exists." }
```

**Response 400** — invalid dates:

```json
{ "error": "end_date must be >= start_date." }
```

---

## DELETE /api/phases/{phase_name}

Deletes a project phase by name.

**Response 200**: Updated phases list.

**Response 404**:

```json
{ "error": "Phase 'Go-Live' not found." }
```

---

## Frontend Static Assets

Flask serves all files under `absence_dashboard/static/` as static assets:

| Route | File | Description |
|-------|------|-------------|
| `GET /` | `absence_dashboard/static/index.html` | Dashboard shell |
| `GET /static/main.js` | `absence_dashboard/static/main.js` | Dashboard JS |
| `GET /static/style.css` | `absence_dashboard/static/style.css` | Stylesheet |
