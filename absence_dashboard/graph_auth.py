import sys

import msal
from msal_extensions import (
    FilePersistence,
    FilePersistenceWithDataProtection,
    PersistedTokenCache,
)

# Only ever request read-only access — see specs/004-sharepoint-device-code-auth
# FR-006 and the constitution's data-integrity spirit: this app must never be able
# to write to the source SharePoint file.
SCOPES = ["Files.Read"]


def _build_persistence(cache_path):
    """Encrypt the token cache at rest via Windows DPAPI (the deployed target).

    Falls back to a plain file on platforms without DPAPI (macOS/Linux dev
    machines) so local development still works without a Windows-only dependency.
    """
    try:
        return FilePersistenceWithDataProtection(cache_path)
    except Exception:
        return FilePersistence(cache_path)


def acquire_token(client_id, tenant_id, cache_path, interactive_fallback=True):
    """Return a valid Microsoft Graph access token for the signed-in manager.

    Tries silent acquisition against the cached session first (fast, no user
    interaction, auto-renews via the cached refresh token if needed). Falls back
    to an interactive device-code sign-in only when interactive_fallback is True
    and silent acquisition fails. post_refresh() (browser-triggered, no console
    to show a device code on) always calls this with interactive_fallback=False.

    Raises RuntimeError with an actionable message if no valid token can be
    obtained.
    """
    try:
        cache = PersistedTokenCache(_build_persistence(cache_path))
        app = msal.PublicClientApplication(
            client_id,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
            token_cache=cache,
        )
    except Exception as e:
        # msal validates client_id/tenant_id against a live Microsoft endpoint at
        # construction time and raises a raw ValueError (or a network exception) on
        # failure — convert to the same actionable-error pattern used everywhere
        # else in this app, instead of letting a raw traceback surface (FR-005/FR-008).
        raise RuntimeError(f"Could not sign in: {e}") from e

    accounts = app.get_accounts()
    result = None
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if result and "access_token" in result:
        return result["access_token"]

    if not interactive_fallback:
        raise RuntimeError(
            "Signed-in session has expired. Restart the dashboard to sign in again."
        )

    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        raise RuntimeError(
            f"Failed to start sign-in: {flow.get('error_description', flow)}"
        )

    print(flow["message"], file=sys.stderr)
    result = app.acquire_token_by_device_flow(flow)

    if not result or "access_token" not in result:
        detail = result.get("error_description", result) if result else "no response"
        raise RuntimeError(f"Sign-in failed: {detail}")

    return result["access_token"]
