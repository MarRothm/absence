"""
Unit tests for absence_dashboard/data_fetcher.py
TDD: written BEFORE implementation; confirmed failing before data_fetcher.py exists.
"""
import base64
import pytest
from unittest.mock import patch, MagicMock

ACCESS_TOKEN = "fake-access-token"


class TestLocalPathRejected:
    """Local-file support was removed (feature 003) — SharePoint links are the only
    supported source, enforced here as a defensive backstop (see research.md #1)."""

    def test_existing_local_path_raises_value_error(self, sample_xlsx):
        from absence_dashboard.data_fetcher import get_workbook
        with pytest.raises(ValueError, match="local-file support has been removed"):
            get_workbook(sample_xlsx, ACCESS_TOKEN)

    def test_nonexistent_local_path_raises_value_error(self):
        from absence_dashboard.data_fetcher import get_workbook
        with pytest.raises(ValueError, match="local-file support has been removed"):
            get_workbook("/does/not/exist.xlsx", ACCESS_TOKEN)

    def test_local_path_does_not_call_requests(self, sample_xlsx):
        from absence_dashboard.data_fetcher import get_workbook
        with patch("absence_dashboard.data_fetcher.requests") as mock_req:
            with pytest.raises(ValueError):
                get_workbook(sample_xlsx, ACCESS_TOKEN)
            mock_req.get.assert_not_called()


class TestSharePointURL:
    """get_workbook() resolves the manager's existing sharing URL via Microsoft Graph's
    /shares/{shareIdEncoded}/driveItem/content endpoint (research.md #2, feature 004) —
    the same sharing link as before, now fetched with delegated auth instead of anonymously.
    """

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

    def _expected_share_id(self, url):
        b64 = base64.b64encode(url.encode("utf-8")).decode("ascii")
        b64url = b64.replace("/", "_").replace("+", "-").rstrip("=")
        return "u!" + b64url

    def test_https_url_triggers_requests_get(self, sample_xlsx):
        from absence_dashboard.data_fetcher import get_workbook
        with patch("absence_dashboard.data_fetcher.requests.get",
                   return_value=self._mock_response(self._xlsx_bytes(sample_xlsx))) as mock_get:
            wb = get_workbook(self.SHAREPOINT_URL, ACCESS_TOKEN)
            wb.close()
            mock_get.assert_called_once()

    def test_http_url_triggers_requests_get(self, sample_xlsx):
        from absence_dashboard.data_fetcher import get_workbook
        with patch("absence_dashboard.data_fetcher.requests.get",
                   return_value=self._mock_response(self._xlsx_bytes(sample_xlsx))) as mock_get:
            wb = get_workbook(self.HTTP_URL, ACCESS_TOKEN)
            wb.close()
            mock_get.assert_called_once()

    def test_graph_shares_endpoint_used_with_encoded_share_id(self, sample_xlsx):
        from absence_dashboard.data_fetcher import get_workbook
        with patch("absence_dashboard.data_fetcher.requests.get",
                   return_value=self._mock_response(self._xlsx_bytes(sample_xlsx))) as mock_get:
            wb = get_workbook(self.SHAREPOINT_URL, ACCESS_TOKEN)
            wb.close()
            called_url = mock_get.call_args[0][0]
            expected_share_id = self._expected_share_id(self.SHAREPOINT_URL)
            assert called_url == f"https://graph.microsoft.com/v1.0/shares/{expected_share_id}/driveItem/content"

    def test_bearer_auth_header_included(self, sample_xlsx):
        from absence_dashboard.data_fetcher import get_workbook
        with patch("absence_dashboard.data_fetcher.requests.get",
                   return_value=self._mock_response(self._xlsx_bytes(sample_xlsx))) as mock_get:
            wb = get_workbook(self.SHAREPOINT_URL, ACCESS_TOKEN)
            wb.close()
            call_kwargs = mock_get.call_args[1]
            assert call_kwargs.get("headers", {}).get("Authorization") == f"Bearer {ACCESS_TOKEN}"

    def test_non_2xx_raises_connection_error(self):
        from absence_dashboard.data_fetcher import get_workbook
        with patch("absence_dashboard.data_fetcher.requests.get",
                   return_value=self._mock_response(b"Forbidden", 403)):
            with pytest.raises(ConnectionError, match="403"):
                get_workbook(self.SHAREPOINT_URL, ACCESS_TOKEN)

    def test_valid_url_returns_workbook(self, sample_xlsx):
        from absence_dashboard.data_fetcher import get_workbook
        with patch("absence_dashboard.data_fetcher.requests.get",
                   return_value=self._mock_response(self._xlsx_bytes(sample_xlsx))):
            wb = get_workbook(self.SHAREPOINT_URL, ACCESS_TOKEN)
            assert wb is not None
            assert wb.active is not None
            wb.close()


class TestReadOnlyGuarantee:
    """Regression guard for FR-002/FR-006: get_workbook() must never issue a write/upload
    request to SharePoint — only a GET, now with delegated auth. Permanently guards against
    a future accidental write path (feature 003, extended for the Graph-based path in
    feature 004 — see T017)."""

    SHAREPOINT_URL = "https://company.sharepoint.com/:x:/s/site/Eabcdef?e=12345"

    def _mock_response(self, xlsx_bytes, status_code=200):
        resp = MagicMock()
        resp.status_code = status_code
        resp.content = xlsx_bytes
        return resp

    def test_only_get_is_ever_called(self, sample_xlsx):
        from absence_dashboard.data_fetcher import get_workbook
        with open(sample_xlsx, "rb") as f:
            xlsx_bytes = f.read()
        with patch("absence_dashboard.data_fetcher.requests") as mock_requests:
            mock_requests.get.return_value = self._mock_response(xlsx_bytes)
            wb = get_workbook(self.SHAREPOINT_URL, ACCESS_TOKEN)
            wb.close()

        mock_requests.get.assert_called_once()
        mock_requests.post.assert_not_called()
        mock_requests.put.assert_not_called()
        mock_requests.patch.assert_not_called()
        mock_requests.delete.assert_not_called()
