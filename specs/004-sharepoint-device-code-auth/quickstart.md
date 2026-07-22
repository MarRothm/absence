# Quickstart: SharePoint Delegated Device-Code Authentication

**Phase 1 output** | **Date**: 2026-07-22

---

> **Update (feature 005)**: IT declined to create the app registration this feature needed — the
> dashboard reads a local file again, with no sign-in step at all. See
> [specs/005-restore-local-file/quickstart.md](../005-restore-local-file/quickstart.md) for the
> current setup. The rest of this page is kept for history.

## Prerequisite: an Azure AD app registration (one-time, done by IT)

Before this feature can be used, IT/your tenant admin needs to create an Azure AD (Entra ID) app
registration:

1. Register a new app (any name, e.g. "Absence Dashboard").
2. Under **Authentication**, enable **"Allow public client flows"** (required for device-code
   sign-in) — no redirect URI or client secret is needed.
3. Under **API permissions**, add the delegated Microsoft Graph permission **`Files.Read`**. Grant
   admin consent if your tenant requires it for user consent to be skipped.
4. Note the **Application (client) ID** and the **Directory (tenant) ID** — you'll need both for
   `launch_config.json` below.

This is a much smaller ask than an app-only/client-credentials registration (no secret to manage,
read-only scope, acts only with the signed-in manager's own existing permissions).

---

## Configuring `launch_config.json`

```json
{
  "excel_source": "https://company.sharepoint.com/:x:/s/yoursite/Exxxxxxxxxxxxxxx?e=xxxxxx",
  "client_id": "<Application (client) ID from step 4 above>",
  "tenant_id": "<Directory (tenant) ID from step 4 above>",
  "port": 5002
}
```

`excel_source` stays exactly what it already was — the same SharePoint link, whether or not
anonymous sharing works. `client_id`/`tenant_id` are new and required.

---

## Signing in (first launch, or after a session expires)

```bash
python run.py
```

The console shows something like:

```
To sign in, open https://microsoft.com/devicelogin and enter the code: ABCD-EFGH
```

Open that address on **any device/browser** (your phone works fine), enter the code, and sign in
with your own Barmenia account. Once sign-in completes, the console continues and the dashboard
starts — no local browser popup needed on the machine running the dashboard itself.

After this first sign-in, restarting the dashboard does **not** ask you to sign in again, for as
long as your session stays valid (spec SC-002: at least 10 consecutive restarts).

---

## Troubleshooting

| Symptom | Likely Cause | Fix |
|---|---|---|
| A device code and URL appear again, even though you signed in recently | Your cached session expired or was revoked (normal — see spec US3) | Complete the new device-code sign-in the same way as the first time |
| "You do not have access to this file" | Signed in with the wrong account, or that account genuinely lacks access | Confirm you can open the file in a browser with the same account you signed in with |
| Device code expired before you finished signing in | The code has a fixed validity window (typically ~15 minutes) | Restart the dashboard to get a new code |
| Refresh (in the browser) fails with "please restart the dashboard" | The cached session expired while the dashboard was open, and a browser click can't show a new device code | Restart the dashboard from the console to sign in again |
| "client_id"/"tenant_id" missing error | `launch_config.json` doesn't have these fields yet | Add them from the Azure AD app registration (see Prerequisite above) |

---

## Verifying the read-only guarantee still holds

Same check as before (feature 003): perform every dashboard action while signed in, then confirm via
SharePoint's version history that no new version was ever created by the dashboard. Signing in does
not change this — only `Files.Read` (read-only) permission is ever requested.
