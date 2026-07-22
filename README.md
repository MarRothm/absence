# Absence Management Dashboard

A local web application that reads a date-grid Excel spreadsheet and displays a Gantt-style
absence timeline with dependency management and skill cluster grouping.

See [specs/001-absence-dashboard/quickstart.md](specs/001-absence-dashboard/quickstart.md) for
full setup and usage instructions.

## Quick start

The dashboard reads its absence spreadsheet directly from SharePoint and signs in as you (delegated
OAuth2 device-code flow) — there is no anonymous or local-file data source. A one-time Azure AD app
registration is required first; see
[specs/004-sharepoint-device-code-auth/quickstart.md](specs/004-sharepoint-device-code-auth/quickstart.md).

```bash
pip install -r requirements.txt
# Add client_id/tenant_id to launch_config.json (see quickstart above), then:
python run.py
# Follow the device-code sign-in prompt, then open http://localhost:5002
```

## Standalone Windows Build (Citrix / Server 2016)

A self-contained Windows package is also available — no Python install, no administrator rights,
built automatically via GitHub Actions on every push to `main`. See
[specs/002-windows-standalone-build/quickstart.md](specs/002-windows-standalone-build/quickstart.md)
for how to download, configure, and run it on a Windows Server 2016 / Citrix session.
