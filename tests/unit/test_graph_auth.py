"""
TDD: Tests for absence_dashboard/graph_auth.py
Written BEFORE implementation; confirmed failing before graph_auth.py exists.

All tests mock msal.PublicClientApplication directly — none ever perform a real
device-code flow or reach a real Microsoft endpoint.
"""
import pytest
from unittest.mock import patch, MagicMock


CLIENT_ID = "11111111-1111-1111-1111-111111111111"
TENANT_ID = "22222222-2222-2222-2222-222222222222"


@pytest.fixture
def cache_path(tmp_path):
    return str(tmp_path / "token_cache.bin")


def _mock_app(monkeypatch):
    """Patch graph_auth's msal.PublicClientApplication and cache builder so no real
    file I/O or network call ever happens; return the MagicMock app instance."""
    mock_app_instance = MagicMock()
    monkeypatch.setattr(
        "absence_dashboard.graph_auth.msal.PublicClientApplication",
        MagicMock(return_value=mock_app_instance),
    )
    monkeypatch.setattr("absence_dashboard.graph_auth._build_persistence", MagicMock())
    return mock_app_instance


class TestAcquireToken:
    def test_silent_acquisition_succeeds_no_interactive_call(self, cache_path, monkeypatch):
        from absence_dashboard.graph_auth import acquire_token
        mock_app = _mock_app(monkeypatch)
        mock_app.get_accounts.return_value = [{"username": "manager@barmeniagroup.com"}]
        mock_app.acquire_token_silent.return_value = {"access_token": "silent-token"}

        token = acquire_token(CLIENT_ID, TENANT_ID, cache_path)

        assert token == "silent-token"
        mock_app.initiate_device_flow.assert_not_called()

    def test_silent_fails_interactive_fallback_true_uses_device_flow(self, cache_path, monkeypatch):
        from absence_dashboard.graph_auth import acquire_token
        mock_app = _mock_app(monkeypatch)
        mock_app.get_accounts.return_value = []
        mock_app.initiate_device_flow.return_value = {
            "user_code": "ABCD-EFGH", "message": "Go to https://microsoft.com/devicelogin and enter ABCD-EFGH",
        }
        mock_app.acquire_token_by_device_flow.return_value = {"access_token": "device-token"}

        token = acquire_token(CLIENT_ID, TENANT_ID, cache_path, interactive_fallback=True)

        assert token == "device-token"
        mock_app.initiate_device_flow.assert_called_once()
        mock_app.acquire_token_by_device_flow.assert_called_once()

    def test_silent_fails_interactive_fallback_false_raises_without_device_flow(self, cache_path, monkeypatch):
        from absence_dashboard.graph_auth import acquire_token
        mock_app = _mock_app(monkeypatch)
        mock_app.get_accounts.return_value = []

        with pytest.raises(RuntimeError, match="[Rr]estart the dashboard"):
            acquire_token(CLIENT_ID, TENANT_ID, cache_path, interactive_fallback=False)

        mock_app.initiate_device_flow.assert_not_called()

    def test_silent_returns_no_access_token_falls_back_to_device_flow(self, cache_path, monkeypatch):
        from absence_dashboard.graph_auth import acquire_token
        mock_app = _mock_app(monkeypatch)
        mock_app.get_accounts.return_value = [{"username": "manager@barmeniagroup.com"}]
        mock_app.acquire_token_silent.return_value = {"error": "invalid_grant"}
        mock_app.initiate_device_flow.return_value = {
            "user_code": "ABCD-EFGH", "message": "Go to https://microsoft.com/devicelogin and enter ABCD-EFGH",
        }
        mock_app.acquire_token_by_device_flow.return_value = {"access_token": "device-token"}

        token = acquire_token(CLIENT_ID, TENANT_ID, cache_path)

        assert token == "device-token"

    def test_device_flow_initiation_failure_raises_clear_error(self, cache_path, monkeypatch):
        from absence_dashboard.graph_auth import acquire_token
        mock_app = _mock_app(monkeypatch)
        mock_app.get_accounts.return_value = []
        mock_app.initiate_device_flow.return_value = {"error": "invalid_client", "error_description": "bad client_id"}

        with pytest.raises(RuntimeError, match="bad client_id"):
            acquire_token(CLIENT_ID, TENANT_ID, cache_path)

    def test_device_flow_completion_failure_raises_clear_error(self, cache_path, monkeypatch):
        from absence_dashboard.graph_auth import acquire_token
        mock_app = _mock_app(monkeypatch)
        mock_app.get_accounts.return_value = []
        mock_app.initiate_device_flow.return_value = {
            "user_code": "ABCD-EFGH", "message": "Go to https://microsoft.com/devicelogin and enter ABCD-EFGH",
        }
        mock_app.acquire_token_by_device_flow.return_value = {
            "error": "authorization_declined", "error_description": "the user declined the sign-in",
        }

        with pytest.raises(RuntimeError, match="declined"):
            acquire_token(CLIENT_ID, TENANT_ID, cache_path)

    def test_second_call_reuses_cached_session_no_interactive_fallback(self, cache_path, monkeypatch):
        # Simulates two separate acquire_token() calls sharing the same cache_path —
        # exactly what happens across two separate dashboard launches (US2). The first
        # call has no cached session (falls through to the device-code flow); the
        # second call sees the now-signed-in account and succeeds silently, with no
        # device-code flow triggered — MSAL's own cache is what makes this durable
        # across real launches; here we simulate its effect at the mock boundary.
        from absence_dashboard.graph_auth import acquire_token
        mock_app = _mock_app(monkeypatch)
        mock_app.get_accounts.side_effect = [[], [{"username": "manager@barmeniagroup.com"}]]
        mock_app.acquire_token_silent.return_value = {"access_token": "silent-token"}
        mock_app.initiate_device_flow.return_value = {
            "user_code": "ABCD-EFGH", "message": "Go to https://microsoft.com/devicelogin and enter ABCD-EFGH",
        }
        mock_app.acquire_token_by_device_flow.return_value = {"access_token": "device-token"}

        first_token = acquire_token(CLIENT_ID, TENANT_ID, cache_path)
        assert first_token == "device-token"
        mock_app.initiate_device_flow.assert_called_once()

        second_token = acquire_token(CLIENT_ID, TENANT_ID, cache_path)
        assert second_token == "silent-token"
        mock_app.initiate_device_flow.assert_called_once()  # still just the one call from before

    def test_scope_never_exceeds_files_read(self, cache_path, monkeypatch):
        # Regression guard for FR-006 (feature 004, US4): the token request must never
        # ask for anything beyond read-only access, whichever path (silent or
        # device-code) is used to acquire it.
        from absence_dashboard.graph_auth import acquire_token, SCOPES
        assert SCOPES == ["Files.Read"]

        mock_app = _mock_app(monkeypatch)
        mock_app.get_accounts.return_value = [{"username": "manager@barmeniagroup.com"}]
        mock_app.acquire_token_silent.return_value = {"access_token": "silent-token"}

        acquire_token(CLIENT_ID, TENANT_ID, cache_path)

        called_scopes = mock_app.acquire_token_silent.call_args[0][0]
        assert called_scopes == ["Files.Read"]

    def test_device_flow_scope_never_exceeds_files_read(self, cache_path, monkeypatch):
        from absence_dashboard.graph_auth import acquire_token
        mock_app = _mock_app(monkeypatch)
        mock_app.get_accounts.return_value = []
        mock_app.initiate_device_flow.return_value = {
            "user_code": "ABCD-EFGH", "message": "Go to https://microsoft.com/devicelogin and enter ABCD-EFGH",
        }
        mock_app.acquire_token_by_device_flow.return_value = {"access_token": "device-token"}

        acquire_token(CLIENT_ID, TENANT_ID, cache_path)

        called_scopes = mock_app.initiate_device_flow.call_args[1].get("scopes")
        assert called_scopes == ["Files.Read"]

    def test_invalid_client_id_or_tenant_id_raises_clear_error(self, cache_path, monkeypatch):
        # msal.PublicClientApplication validates client_id/tenant_id against a live
        # Microsoft endpoint at construction time and raises a raw ValueError on failure
        # (discovered via manual testing against the real login.microsoftonline.com) —
        # acquire_token() must convert this to the same clean error pattern used
        # everywhere else, not let a raw traceback surface.
        monkeypatch.setattr(
            "absence_dashboard.graph_auth.msal.PublicClientApplication",
            MagicMock(side_effect=ValueError("Unable to get authority configuration")),
        )
        monkeypatch.setattr("absence_dashboard.graph_auth._build_persistence", MagicMock())

        from absence_dashboard.graph_auth import acquire_token
        with pytest.raises(RuntimeError, match="[Cc]ould not sign in"):
            acquire_token(CLIENT_ID, TENANT_ID, cache_path)
