"""
Unit tests for absence_dashboard/data_fetcher.py
TDD: written BEFORE implementation; confirmed failing before data_fetcher.py exists.
"""
import pytest


class TestGetWorkbook:
    """get_workbook() reads a local .xlsx file directly (feature 005 — SharePoint/Graph
    access removed entirely; see specs/005-restore-local-file/research.md #2)."""

    def test_existing_local_path_returns_workbook(self, sample_xlsx):
        from absence_dashboard.data_fetcher import get_workbook
        wb = get_workbook(sample_xlsx)
        assert wb is not None
        assert wb.active is not None
        wb.close()

    def test_nonexistent_local_path_raises_file_not_found(self):
        from absence_dashboard.data_fetcher import get_workbook
        with pytest.raises(FileNotFoundError):
            get_workbook("/does/not/exist.xlsx")
