import json
import os
import sys

DEFAULT_PORT = 5002


def load_launch_config(path):
    """Load (excel_source, port) from a launch_config.json file.

    Raises FileNotFoundError — with the same message style as app.py's existing
    file-not-found path — if the config file is missing or excel_source is missing/invalid.
    An invalid or missing port falls back to DEFAULT_PORT with a warning on stderr.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    excel_source = data.get("excel_source")
    is_url = isinstance(excel_source, str) and excel_source.startswith(("http://", "https://"))
    if not excel_source or (not is_url and not os.path.exists(excel_source)):
        raise FileNotFoundError(f"File not found: {excel_source!r} (excel_source in {path})")

    port = data.get("port", DEFAULT_PORT)
    if not isinstance(port, int) or isinstance(port, bool) or port <= 0:
        print(f"Invalid port {port!r} in {path} — using default {DEFAULT_PORT}", file=sys.stderr)
        port = DEFAULT_PORT

    return excel_source, port
