# Absence Management Dashboard

A local web application that reads a date-grid Excel spreadsheet and displays a Gantt-style
absence timeline with dependency management and skill cluster grouping.

See [specs/001-absence-dashboard/quickstart.md](specs/001-absence-dashboard/quickstart.md) for
full setup and usage instructions.

## Quick start

```bash
pip install -r requirements.txt
python absence_dashboard/app.py path/to/absences.xlsx
# Open http://localhost:5000
```
