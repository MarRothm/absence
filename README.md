# Absence Management Dashboard

A local web application that reads a date-grid Excel spreadsheet and displays a Gantt-style
absence timeline with dependency management and skill cluster grouping.

See [specs/001-absence-dashboard/quickstart.md](specs/001-absence-dashboard/quickstart.md) for
full setup and usage instructions.

## Quick start

```bash
pip install -r requirements.txt
python run.py "https://company.sharepoint.com/:x:/s/yoursite/Exxxxxxxxxxxxxxx?e=xxxxxx"
# Open http://localhost:5002
```

A SharePoint "anyone with the link" share URL is the only supported data source — local file paths
are no longer accepted (see
[specs/003-sharepoint-direct-connection/quickstart.md](specs/003-sharepoint-direct-connection/quickstart.md)).

## Standalone Windows Build (Citrix / Server 2016)

A self-contained Windows package is also available — no Python install, no administrator rights,
built automatically via GitHub Actions on every push to `main`. See
[specs/002-windows-standalone-build/quickstart.md](specs/002-windows-standalone-build/quickstart.md)
for how to download, configure, and run it on a Windows Server 2016 / Citrix session.
