# Quickstart: SharePoint Direct Connection

**Phase 1 output** | **Date**: 2026-07-21

---

> **Update (feature 004)**: anonymous "anyone with the link" access (described below) no longer
> works — this tenant disables it entirely. The dashboard now signs in as the manager via delegated
> OAuth2 device-code sign-in. See
> [specs/004-sharepoint-device-code-auth/quickstart.md](../004-sharepoint-device-code-auth/quickstart.md)
> for current setup steps. The rest of this page is kept for history; the "no local file" guarantee
> it introduced is still accurate — only the "anonymous" part is superseded.

## What changed

The dashboard no longer accepts a local `.xlsx` file path — a SharePoint file link is the only
supported data source, for both local/dev use and the Windows standalone package (feature 002).

---

## Local / development use

```bash
pip install -r requirements.txt
python run.py "https://company.sharepoint.com/:x:/s/yoursite/Exxxxxxxxxxxxxxx?e=xxxxxx"
# Open http://localhost:5002
```

The link must be a public ("anyone with the link") SharePoint share URL — the same kind already
supported since spec 001. A local file path (e.g. `python run.py absences.xlsx`) now fails with a
clear error explaining that local-file support has been removed.

---

## Standalone Windows package (feature 002)

Edit `launch_config.json` next to the executable:

```json
{
  "excel_source": "https://company.sharepoint.com/:x:/s/yoursite/Exxxxxxxxxxxxxxx?e=xxxxxx",
  "port": 5002
}
```

`excel_source` must be a SharePoint link. If it's left as a local file path from before this change,
`run-dashboard.bat` will show a clear error explaining local-file support has been removed, instead
of a confusing generic failure.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "local-file support has been removed" error | `excel_source` (or the CLI argument) is a local path, not a URL | Replace it with a SharePoint share link |
| "Cannot download from SharePoint URL" / connection error | Link isn't a public share, or network is unavailable | Confirm the link opens in a browser without login from the same machine/session |
| Dashboard was working, now shows a startup error after upgrading | An old `launch_config.json` or script still has a local path configured | Update it to a SharePoint link — see above |

---

## Verifying the read-only guarantee

To confirm the dashboard never modifies the SharePoint file: check the file's version history in
SharePoint before and after using the dashboard (loading, reloading, and editing dependencies/skill
clusters/phases). No new version should ever be created by the dashboard — every version present
was created by someone editing the file directly, never by this application.
