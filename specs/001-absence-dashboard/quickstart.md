# Quickstart: Absence Management Dashboard

**Phase 1 output** | **Date**: 2026-05-07

---

## Prerequisites

- Python 3.11 or later
- pip
- The Excel spreadsheet file with absence data (`.xlsx` format)

Verify Python version:

```bash
python3 --version
# Expected: Python 3.11.x or higher
```

---

## Setup

1. **Clone / navigate to the project directory**:

   ```bash
   cd absence-management
   ```

2. **Create and activate a virtual environment**:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate        # macOS / Linux
   .venv\Scripts\activate           # Windows
   ```

3. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

4. **Place your Excel file** in the project root (or note its path):

   ```bash
   # Example: cp ~/Downloads/absences.xlsx ./absences.xlsx
   ```

---

## Running the Dashboard

**Option A — local Excel file**:

```bash
python app.py path/to/absences.xlsx
```

**Option B — SharePoint public share URL** (the link must be an "anyone with the link" share):

```bash
python app.py "https://company.sharepoint.com/:x:/s/yoursite/ExxxxxxxxxxxxxxQ?e=xxxxxx"
```

The app detects the input type by its `http://`/`https://` scheme. For a SharePoint URL it
appends `?download=1` and downloads the file anonymously before parsing.

Open your browser and navigate to: **http://localhost:5000**

The dashboard loads immediately. If the "Projekt Migration" column is present, only marked
members are shown. The **last loaded date and time** is shown in the top-right corner of the
header (e.g., `"Last loaded: 11 May 2026, 14:32"`) and updates on every successful refresh.

---

## Using the Dashboard

### Timeline View

The main grid shows one row per project member. Columns are organized by calendar week (CW19–CW53
of the current year), with each week subdivided into 5 individual day sub-columns (Mon–Fri).
Each week column header shows the CW number and the Monday date in `"CW22 | 25 May"` format so
the real-world dates are immediately visible. Day sub-columns show only the weekday label (Mon /
Tue / Wed / Thu / Fri). Absence is shown at day-level: only the specific days a person is absent
are colored; a person absent Mon–Wed in CW23 shows 3 colored cells, leaving Thu–Fri unmarked.

**Visual indicators**:
- **Blue day-cell**: Member is absent on that specific working day
- **Orange day-cell**: Member is absent on that day AND is a bottleneck (depended on by 2+)
- **Continuous bar**: Absence spanning multiple consecutive days renders as one unbroken colored
  bar, crossing week-column boundaries without visual interruption
- **Red week band (all 5 day-cells)**: Member is "at risk" for that calendar week — at least one
  day of a person they depend on falls within that week (at-risk indicator is week-granular)
- **Cluster label**: Shown in the row header next to the member name

### Managing Project Phases

1. Click **"Phases"** in the top navigation.
2. Enter a phase name and a start and end date (format: YYYY-MM-DD).
3. Click **"Add Phase"**.
4. Each defined phase appears as a labelled horizontal banner row above all member rows in the
   timeline, spanning its exact date range. Multiple phases with overlapping dates stack as
   separate rows.
5. To edit a phase, click **"Edit"** next to it — the row expands inline with the name, start
   date, and end date all editable. Click **"Save"** to apply or **"Cancel"** to discard. If the
   new end date is before the start date, or the name duplicates an existing phase, an error
   appears inline and the row stays open.
6. To remove a phase, click ✕ next to its name in the list.

### Refreshing Data

Click the **"Reload"** button (top right) to re-read the Excel file (or re-fetch it from the
SharePoint URL if that was the startup source). All dependencies and skill clusters you have
defined are preserved. The **"Last loaded"** timestamp in the header updates to the current time
on every successful refresh.

### Managing Dependencies

1. Click **"Dependencies"** in the top navigation.
2. Select a **"From"** member (the at-risk person) and a **"To"** member (the person depended on).
3. Click **"Add Dependency"**.
4. To edit a dependency, click **"Edit"** next to it — the row expands inline with both the
   "From" and "To" dropdowns editable. Click **"Save"** to apply or **"Cancel"** to discard. If
   the change would create a cycle or duplicate an existing dependency, an error appears inline and
   the row stays open.
5. To remove, click the ✕ next to any existing dependency in the list.

### Managing Skill Clusters

1. Click **"Clusters"** in the top navigation.
2. Enter a cluster name and select member(s) from the dropdown.
3. Click **"Create Cluster"**.
4. To edit a cluster, click **"Edit"** next to it — the row expands inline with both the cluster
   name (text field) and its member list (multi-select) editable. Click **"Save"** to apply or
   **"Cancel"** to discard. If the new name duplicates an existing cluster, or a selected member
   is not in the loaded dataset, an error appears inline and the row stays open.
5. To delete a cluster, click **"Delete"** next to the cluster name.

---

## Running Tests

```bash
pytest tests/ -v
```

Expected output: all tests green. Tests cover Excel parsing, absence merging, dependency cycle
detection, and cluster management. Per the project constitution, tests must be confirmed failing
before implementation and passing after.

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| "No project members found" | No rows with "x" in "Projekt Migration" column | Verify column name and "x" values in the Excel file |
| "Cannot read Excel file" | Wrong file path or file open in Excel | Close Excel and verify the path |
| "Cannot download from SharePoint URL" | URL is not a public share or network is unavailable | Verify the link is "anyone with the link" and accessible in a browser without login |
| Skipped rows warning | Missing or malformed dates in some rows | Review flagged rows in the Excel file |
| Port 5000 already in use | Another process using port 5000 | Run `python app.py path/to/file.xlsx --port 5001` |
| "Column C/D not found" | Excel file has fewer columns than expected | Verify the file is the correct `.xlsx` and has data in columns C, D, and F+ |

---

## Excel file format

The application expects a **fixed-layout date-grid** `.xlsx` file with this structure:

| Location | Content |
|----------|---------|
| Row 1 | Calendar week labels (e.g., "KW18", "KW19" …) |
| Row 2 | Weekday names (Mon–Fri only; no weekend columns) |
| Row 3+ | One data row per person |
| **Column C** | "Projekt Migration" — rows with value `x` (or `X`) are shown on the dashboard |
| **Column D** | "Team Mitglied " — the person's name |
| **Column F** | First working day column = April 27, 2026 (Monday) |
| Column F onward | One column per subsequent working day (Mon–Fri sequence) |
| Absence marker | Cell value `x` (or `X`) in a day column = absent that day |

No other column positions or header names are required. Columns A, B, and E are ignored.
