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


def get_workbook(source: str):
    """Return a read-only openpyxl Workbook fetched directly from a public SharePoint share URL.

    Local-file paths are not supported (removed in feature 003) — this function only ever
    issues a GET request and opens the response with openpyxl's read_only mode, so there is
    no code path here capable of writing back to the source file.
    """
    if not isinstance(source, str) or not source.startswith(("http://", "https://")):
        raise ValueError(
            f"{source!r} is not a SharePoint link — local-file support has been removed. "
            "Pass a SharePoint share URL (http:// or https://) instead."
        )
    sep = "&" if "?" in source else "?"
    download_url = source + sep + "download=1"
    resp = requests.get(download_url, timeout=30)
    if not (200 <= resp.status_code < 300):
        raise ConnectionError(
            f"SharePoint download failed: HTTP {resp.status_code} for {download_url}"
        )
    return load_workbook(io.BytesIO(resp.content), read_only=True, data_only=True)
