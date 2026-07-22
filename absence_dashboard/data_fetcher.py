import io
import requests
from openpyxl import load_workbook


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
