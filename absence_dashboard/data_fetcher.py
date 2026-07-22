import base64
import io
import requests
import truststore
from openpyxl import load_workbook

# Corporate networks commonly run a TLS-inspecting proxy that re-signs HTTPS traffic with
# an internal root CA. Windows trusts that CA in its own certificate store, but requests'
# bundled certifi CA list does not — inject the OS-native trust store (SChannel on Windows,
# Security framework on macOS, system OpenSSL config on Linux) so SharePoint downloads work
# on networks like that, without disabling certificate verification.
truststore.inject_into_ssl()

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"


def _encode_share_id(url: str) -> str:
    """Encode a SharePoint sharing URL into a Microsoft Graph share ID.

    Per Microsoft's documented algorithm: base64-encode the URL, convert to unpadded
    base64url, and prefix with "u!".
    """
    b64 = base64.b64encode(url.encode("utf-8")).decode("ascii")
    b64url = b64.replace("/", "_").replace("+", "-").rstrip("=")
    return "u!" + b64url


def get_workbook(source: str, access_token: str):
    """Return a read-only openpyxl Workbook fetched from the manager's SharePoint share
    URL via Microsoft Graph, using their own delegated permissions (feature 004).

    Resolves the same sharing URL already configured (excel_source) through Graph's
    /shares/{shareIdEncoded}/driveItem/content endpoint — no separate file-identification
    step. This function only ever issues a GET request and opens the response with
    openpyxl's read_only mode, so there is no code path here capable of writing back to
    the source file (FR-002/FR-006).
    """
    if not isinstance(source, str) or not source.startswith(("http://", "https://")):
        raise ValueError(
            f"{source!r} is not a SharePoint link — local-file support has been removed. "
            "Pass a SharePoint share URL (http:// or https://) instead."
        )
    url = f"{GRAPH_BASE_URL}/shares/{_encode_share_id(source)}/driveItem/content"
    resp = requests.get(url, headers={"Authorization": f"Bearer {access_token}"}, timeout=30)
    if not (200 <= resp.status_code < 300):
        raise ConnectionError(
            f"SharePoint download failed: HTTP {resp.status_code} for {url}"
        )
    return load_workbook(io.BytesIO(resp.content), read_only=True, data_only=True)
