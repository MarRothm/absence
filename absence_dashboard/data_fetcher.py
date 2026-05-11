import io
import requests
from openpyxl import load_workbook


def get_workbook(source: str):
    """Return an openpyxl Workbook from a local file path or a public SharePoint share URL.

    URL detection: if source starts with http:// or https://, fetch anonymously
    with ?download=1 appended and load from the response bytes in memory.
    Otherwise open the local file directly.
    """
    if source.startswith(("http://", "https://")):
        sep = "&" if "?" in source else "?"
        download_url = source + sep + "download=1"
        resp = requests.get(download_url, timeout=30)
        if not (200 <= resp.status_code < 300):
            raise ConnectionError(
                f"SharePoint download failed: HTTP {resp.status_code} for {download_url}"
            )
        return load_workbook(io.BytesIO(resp.content), read_only=True, data_only=True)
    return load_workbook(source, read_only=True, data_only=True)
