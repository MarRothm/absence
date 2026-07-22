import json
import os
import sys

DEFAULT_PORT = 5002


def load_launch_config(path):
    """Load (excel_source, port) from a launch_config.json file.

    excel_source must be an existing local file path — SharePoint access was permanently
    blocked by IT policy (see specs/005-restore-local-file/spec.md), so this app has no
    network dependency at all. Raises FileNotFoundError if the config file is missing,
    excel_source is missing, or excel_source doesn't point to an existing file. An invalid
    or missing port falls back to DEFAULT_PORT with a warning on stderr.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            # The most common cause on Windows: a raw file path with single backslashes
            # (e.g. copy-pasted from Explorer) — JSON requires backslashes to be doubled.
            raise FileNotFoundError(
                f"{path} is not valid JSON: {e}. If excel_source contains a Windows file "
                "path, double every backslash (\\\\) or use forward slashes (/) instead — "
                "e.g. \"C:/Users/you/absences.xlsx\", or just \"absences.xlsx\" if the file "
                "is right next to the launcher."
            ) from e

    excel_source = data.get("excel_source")
    if not excel_source or not os.path.exists(excel_source):
        raise FileNotFoundError(f"File not found: {excel_source!r} (excel_source in {path})")

    port = data.get("port", DEFAULT_PORT)
    if not isinstance(port, int) or isinstance(port, bool) or port <= 0:
        print(f"Invalid port {port!r} in {path} — using default {DEFAULT_PORT}", file=sys.stderr)
        port = DEFAULT_PORT

    return excel_source, port
