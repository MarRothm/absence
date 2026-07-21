# Quickstart: Windows Server 2016 (Citrix) Standalone Build

**Phase 1 output** | **Date**: 2026-07-21

---

## Prerequisites

- A Windows Server 2016 session, typically reached via a Citrix-published desktop or application.
- A folder you can write to inside that session (e.g., your redirected home drive, or a local path
  that isn't reset between sessions) — the app needs to write `state/state.json` there.
- No Python install, and no administrator rights, are required.

---

## Getting the package

1. Open the repository's [GitHub Releases](../../../../releases) page.
2. Download `absence-dashboard-windows.zip` from the latest release (tagged `build-<commit-sha>`).
3. Copy the zip into your Citrix session (e.g., via a mapped drive or file transfer) and extract it
   to a writable folder.

---

## Configuring the data source

1. In the extracted folder, open `launch_config.json` in a text editor.
2. Set `excel_source` to either:
   - a local file path reachable from inside the Citrix session (e.g., `absences.xlsx` if you copied
     the file alongside the launcher, or a full path to a mapped drive), or
   - a public ("anyone with the link") SharePoint share URL.
3. Optionally change `port` if `5002` is already in use (see Troubleshooting).
4. Save the file.

```json
{
  "excel_source": "absences.xlsx",
  "port": 5002
}
```

---

## Running the Dashboard

Double-click `run-dashboard.bat`. A console window opens, starts the local server, and the
dashboard opens automatically in your default browser at `http://localhost:<port>`.

Leave the console window open while using the dashboard — closing it stops the server. Use the
**"Show All / Migration Only"** toggle and the rest of the dashboard exactly as in the desktop
version (see [spec 001's quickstart](../001-absence-dashboard/quickstart.md) for feature usage).

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| Console closes immediately / "Error: excel_source not found" | `launch_config.json` missing, malformed, or `excel_source` points to a path/URL that doesn't exist or isn't reachable | Re-open `launch_config.json`, check the JSON is valid, and verify the path/URL works from inside the Citrix session |
| "Port already in use" | Another instance is already running, or another app is using the port | Close the other instance, or change `port` in `launch_config.json` and re-launch |
| Dashboard loads but changes (dependencies/clusters/phases) don't survive a restart | The bundle's folder is read-only or gets reset between Citrix sessions | Move the extracted bundle to a writable, persistent location (e.g., your redirected home drive) |
| "Cannot download from SharePoint URL" | The Citrix session's network policy blocks the request, or the link isn't a public share | Confirm the link opens in a browser without login from inside the same session; check with IT whether outbound HTTPS to SharePoint is allowed |
| Browser doesn't open automatically | Default browser isn't configured in the session, or is blocked | Manually open `http://localhost:<port>` (the port from `launch_config.json`) in a browser |

---

## Rebuilding locally (maintainers)

```bash
pip install -r requirements.txt pyinstaller
scripts/build-windows-standalone.sh
```

Produces `dist/absence-dashboard-windows.zip`. Requires a Windows machine (or Windows CI runner) —
the bundled executable only runs on the OS it was built on.
