"""
Unit tests for absence_dashboard/data_fetcher.py
TDD: written BEFORE implementation; confirmed failing before data_fetcher.py exists.
"""
import pytest
from unittest.mock import patch, MagicMock


class TestLocalPath:
    def test_local_path_returns_workbook(self, sample_xlsx):
        from absence_dashboard.data_fetcher import get_workbook
        wb = get_workbook(sample_xlsx)
        assert wb is not None
        assert wb.active is not None
        wb.close()

    def test_local_path_does_not_call_requests(self, sample_xlsx):
        from absence_dashboard.data_fetcher import get_workbook
        with patch("absence_dashboard.data_fetcher.requests") as mock_req:
            wb = get_workbook(sample_xlsx)
            wb.close()
            mock_req.get.assert_not_called()


class TestSharePointURL:
    SHAREPOINT_URL = "https://company.sharepoint.com/:x:/s/site/Eabcdef?e=12345"
    HTTP_URL = "http://example.com/absences.xlsx"

    def _mock_response(self, xlsx_bytes, status_code=200):
        resp = MagicMock()
        resp.status_code = status_code
        resp.content = xlsx_bytes
        return resp

    def _xlsx_bytes(self, sample_xlsx):
        with open(sample_xlsx, "rb") as f:
            return f.read()

    def test_https_url_triggers_requests_get(self, sample_xlsx):
        from absence_dashboard.data_fetcher import get_workbook
        with patch("absence_dashboard.data_fetcher.requests.get",
                   return_value=self._mock_response(self._xlsx_bytes(sample_xlsx))) as mock_get:
            wb = get_workbook(self.SHAREPOINT_URL)
            wb.close()
            mock_get.assert_called_once()

    def test_http_url_triggers_requests_get(self, sample_xlsx):
        from absence_dashboard.data_fetcher import get_workbook
        with patch("absence_dashboard.data_fetcher.requests.get",
                   return_value=self._mock_response(self._xlsx_bytes(sample_xlsx))) as mock_get:
            wb = get_workbook(self.HTTP_URL)
            wb.close()
            mock_get.assert_called_once()

    def test_download_param_appended(self, sample_xlsx):
        from absence_dashboard.data_fetcher import get_workbook
        with patch("absence_dashboard.data_fetcher.requests.get",
                   return_value=self._mock_response(self._xlsx_bytes(sample_xlsx))) as mock_get:
            wb = get_workbook(self.SHAREPOINT_URL)
            wb.close()
            called_url = mock_get.call_args[0][0]
            assert "download=1" in called_url

    def test_no_auth_headers(self, sample_xlsx):
        from absence_dashboard.data_fetcher import get_workbook
        with patch("absence_dashboard.data_fetcher.requests.get",
                   return_value=self._mock_response(self._xlsx_bytes(sample_xlsx))) as mock_get:
            wb = get_workbook(self.SHAREPOINT_URL)
            wb.close()
            call_kwargs = mock_get.call_args[1]
            assert "Authorization" not in (call_kwargs.get("headers") or {})

    def test_non_2xx_raises_connection_error(self):
        from absence_dashboard.data_fetcher import get_workbook
        with patch("absence_dashboard.data_fetcher.requests.get",
                   return_value=self._mock_response(b"Forbidden", 403)):
            with pytest.raises(ConnectionError, match="403"):
                get_workbook(self.SHAREPOINT_URL)

    def test_valid_url_returns_workbook(self, sample_xlsx):
        from absence_dashboard.data_fetcher import get_workbook
        with patch("absence_dashboard.data_fetcher.requests.get",
                   return_value=self._mock_response(self._xlsx_bytes(sample_xlsx))):
            wb = get_workbook(self.SHAREPOINT_URL)
            assert wb is not None
            assert wb.active is not None
            wb.close()
