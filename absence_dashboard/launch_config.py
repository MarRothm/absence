import json
import os
import sys

DEFAULT_PORT = 5002


def load_launch_config(path):
    """Load (excel_source, client_id, tenant_id, port) from a launch_config.json file.

    excel_source must be a SharePoint link (http:// or https://) — local-file paths are no
    longer supported (feature 003), even ones that exist on disk. client_id/tenant_id
    identify the Azure AD app registration used for delegated sign-in (feature 004) and
    are both required. Raises FileNotFoundError if the config file is missing, or any of
    excel_source/client_id/tenant_id is missing/invalid. An invalid or missing port falls
    back to DEFAULT_PORT with a warning on stderr.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    excel_source = data.get("excel_source")
    if not excel_source:
        raise FileNotFoundError(f"'excel_source' is missing from {path}.")
    if not isinstance(excel_source, str) or not excel_source.startswith(("http://", "https://")):
        raise FileNotFoundError(
            f"'excel_source' in {path} ({excel_source!r}) is not a SharePoint link — "
            "local-file support has been removed. Set excel_source to a SharePoint share "
            "URL (http:// or https://) instead."
        )

    client_id = data.get("client_id")
    if not client_id:
        raise FileNotFoundError(f"'client_id' is missing from {path}.")

    tenant_id = data.get("tenant_id")
    if not tenant_id:
        raise FileNotFoundError(f"'tenant_id' is missing from {path}.")

    port = data.get("port", DEFAULT_PORT)
    if not isinstance(port, int) or isinstance(port, bool) or port <= 0:
        print(f"Invalid port {port!r} in {path} — using default {DEFAULT_PORT}", file=sys.stderr)
        port = DEFAULT_PORT

    return excel_source, client_id, tenant_id, port
