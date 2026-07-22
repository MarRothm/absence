from openpyxl import load_workbook


def get_workbook(source: str):
    """Return a read-only openpyxl Workbook loaded from a local .xlsx file.

    The manager downloads the current file from SharePoint themselves (features 003/004's
    direct/authenticated SharePoint connection were both permanently blocked by IT policy —
    see specs/005-restore-local-file/spec.md); this app has no network dependency at all.
    """
    return load_workbook(source, read_only=True, data_only=True)
