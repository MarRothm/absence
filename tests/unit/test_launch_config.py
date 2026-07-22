"""
TDD: Tests for absence_dashboard/launch_config.py
Written BEFORE implementation; confirmed failing before launch_config.py is complete.
"""
import json
import pytest

from absence_dashboard.launch_config import load_launch_config, DEFAULT_PORT

CLIENT_ID = "11111111-1111-1111-1111-111111111111"
TENANT_ID = "22222222-2222-2222-2222-222222222222"


def _write_config(tmp_path, **overrides):
    data = {
        "excel_source": "https://example.com/share?e=1",
        "client_id": CLIENT_ID,
        "tenant_id": TENANT_ID,
        "port": 6000,
    }
    data.update(overrides)
    data = {k: v for k, v in data.items() if v is not _OMIT}
    path = tmp_path / "launch_config.json"
    path.write_text(json.dumps(data))
    return str(path)


_OMIT = object()


class TestLoadLaunchConfig:
    def test_valid_config_returns_source_client_tenant_and_port(self, tmp_path):
        path = _write_config(tmp_path)

        source, client_id, tenant_id, port = load_launch_config(path)

        assert source == "https://example.com/share?e=1"
        assert client_id == CLIENT_ID
        assert tenant_id == TENANT_ID
        assert port == 6000

    def test_url_excel_source_accepted(self, tmp_path):
        path = _write_config(tmp_path, port=5002)

        source, _, _, port = load_launch_config(path)

        assert source == "https://example.com/share?e=1"
        assert port == 5002

    def test_missing_config_file_raises_file_not_found(self, tmp_path):
        path = tmp_path / "missing.json"

        with pytest.raises(FileNotFoundError):
            load_launch_config(str(path))

    def test_missing_excel_source_key_raises_file_not_found(self, tmp_path):
        path = _write_config(tmp_path, excel_source=_OMIT)

        with pytest.raises(FileNotFoundError):
            load_launch_config(path)

    def test_existing_local_excel_source_rejected(self, tmp_path):
        # Local-file support was removed (feature 003) — even a local path that exists
        # on disk must be rejected, with a message stating why.
        xlsx = tmp_path / "absences.xlsx"
        xlsx.write_text("dummy")
        path = _write_config(tmp_path, excel_source=str(xlsx))

        with pytest.raises(FileNotFoundError, match="local-file support has been removed"):
            load_launch_config(path)

    def test_nonexistent_local_excel_source_rejected(self, tmp_path):
        path = _write_config(tmp_path, excel_source=str(tmp_path / "does_not_exist.xlsx"))

        with pytest.raises(FileNotFoundError, match="local-file support has been removed"):
            load_launch_config(path)

    def test_missing_client_id_raises_file_not_found(self, tmp_path):
        path = _write_config(tmp_path, client_id=_OMIT)

        with pytest.raises(FileNotFoundError, match="client_id"):
            load_launch_config(path)

    def test_missing_tenant_id_raises_file_not_found(self, tmp_path):
        path = _write_config(tmp_path, tenant_id=_OMIT)

        with pytest.raises(FileNotFoundError, match="tenant_id"):
            load_launch_config(path)

    def test_missing_port_falls_back_to_default(self, tmp_path):
        path = _write_config(tmp_path, port=_OMIT)

        _, _, _, port = load_launch_config(path)

        assert port == DEFAULT_PORT

    def test_invalid_port_falls_back_to_default_with_warning(self, tmp_path, capsys):
        path = _write_config(tmp_path, port="not-a-number")

        _, _, _, port = load_launch_config(path)

        assert port == DEFAULT_PORT
        captured = capsys.readouterr()
        assert "port" in captured.err.lower()

    def test_negative_port_falls_back_to_default(self, tmp_path):
        path = _write_config(tmp_path, port=-1)

        _, _, _, port = load_launch_config(path)

        assert port == DEFAULT_PORT
