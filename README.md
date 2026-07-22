# Absence Management Dashboard

A local web application that reads a date-grid Excel spreadsheet and displays a Gantt-style
absence timeline with dependency management and skill cluster grouping.

See [specs/001-absence-dashboard/quickstart.md](specs/001-absence-dashboard/quickstart.md) for
full setup and usage instructions.

## Quick start

The dashboard reads a local `.xlsx` file you download from SharePoint yourself — no sign-in, no
network access. See
[specs/005-restore-local-file/quickstart.md](specs/005-restore-local-file/quickstart.md) for full
details.

```bash
pip install -r requirements.txt
python run.py path/to/absences.xlsx
# Open http://localhost:5002
```

## Standalone Windows Build (Citrix / Server 2016)

A self-contained Windows package is also available — no Python install, no administrator rights,
built automatically via GitHub Actions on every push to `main`. See
[specs/002-windows-standalone-build/quickstart.md](specs/002-windows-standalone-build/quickstart.md)
for how to download, configure, and run it on a Windows Server 2016 / Citrix session.
