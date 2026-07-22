# Quickstart: Restore Local File Data Source

**Phase 1 output** | **Date**: 2026-07-22

---

## What changed

The dashboard no longer connects to SharePoint at all, in any form — no sign-in, no device code, no
IT-provisioned app registration. It reads a local `.xlsx` file you download from SharePoint
yourself, whenever you want the dashboard to reflect current data.

---

## Local / development use

```bash
pip install -r requirements.txt
python run.py path/to/absences.xlsx
# Open http://localhost:5002
```

No sign-in prompt, no network access — the dashboard starts immediately from the local file.

---

## Standalone Windows package (feature 002)

Edit `launch_config.json` next to the executable:

```json
{
  "excel_source": "absences.xlsx",
  "port": 5002
}
```

Place your downloaded `.xlsx` file at that path (relative paths are resolved next to the
executable). No `client_id`/`tenant_id` fields are needed anymore — remove them if you have an old
`launch_config.json` from feature 004.

---

## Keeping the dashboard up to date

1. Open the file in SharePoint in your browser (you're already signed in there).
2. Download a copy — **File → Download a Copy**, or the download icon in the toolbar.
3. Replace the local file at the path configured above with the new download.
4. Click **Reload** in the dashboard (or restart it).

The **"Last loaded"** timestamp in the dashboard's header tells you how current the displayed data
is — there's no automatic staleness warning beyond that, so check it if you're unsure whether you're
looking at today's numbers.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "File not found" at startup | `excel_source` in `launch_config.json` (or the CLI argument) points to a path that doesn't exist | Confirm you downloaded the file to that exact path |
| Dashboard shows old data after replacing the file | Forgot to click Reload | Click Reload, or restart the dashboard |
| "Cannot read Excel file" | The file is open in Excel, or isn't a valid `.xlsx` | Close Excel and confirm the file downloaded correctly |

---

## What's gone

There is no sign-in step, no device code, no `client_id`/`tenant_id` configuration, and no network
call to SharePoint anywhere in the application — features 003 and 004 explored a direct connection,
but this tenant's policies made that permanently unworkable. See
[specs/004-sharepoint-device-code-auth/spec.md](../004-sharepoint-device-code-auth/spec.md) for the
history of what was tried and why.
