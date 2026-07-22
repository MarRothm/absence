"""
TDD: Tests for absence_dashboard/launch_config.py
Written BEFORE implementation; confirmed failing before launch_config.py is complete.
"""
import json
import pytest

from absence_dashboard.launch_config import load_launch_config, DEFAULT_PORT


class TestLoadLaunchConfig:
    def test_malformed_json_raises_actionable_error(self, tmp_path):
        # Real-world failure (found via manual testing on Windows): a raw Windows path
        # with single backslashes, e.g. copy-pasted from Explorer, is invalid JSON.
        path = tmp_path / "launch_config.json"
        path.write_text('{\n  "excel_source": "C:\\Users\\me\\absences.xlsx"\n}')

        with pytest.raises(FileNotFoundError, match="backslash"):
            load_launch_config(str(path))

    def test_valid_config_returns_source_and_port(self, tmp_path):
        xlsx = tmp_path / "absences.xlsx"
        xlsx.write_text("dummy")
        path = tmp_path / "launch_config.json"
        path.write_text(json.dumps({"excel_source": str(xlsx), "port": 6000}))

        source, port = load_launch_config(str(path))

        assert source == str(xlsx)
        assert port == 6000

    def test_missing_config_file_raises_file_not_found(self, tmp_path):
        path = tmp_path / "missing.json"

        with pytest.raises(FileNotFoundError):
            load_launch_config(str(path))

    def test_missing_excel_source_key_raises_file_not_found(self, tmp_path):
        path = tmp_path / "launch_config.json"
        path.write_text(json.dumps({"port": 5002}))

        with pytest.raises(FileNotFoundError):
            load_launch_config(str(path))

    def test_nonexistent_local_excel_source_raises_file_not_found(self, tmp_path):
        path = tmp_path / "launch_config.json"
        path.write_text(json.dumps({"excel_source": str(tmp_path / "does_not_exist.xlsx")}))

        with pytest.raises(FileNotFoundError):
            load_launch_config(str(path))

    def test_missing_port_falls_back_to_default(self, tmp_path):
        xlsx = tmp_path / "absences.xlsx"
        xlsx.write_text("dummy")
        path = tmp_path / "launch_config.json"
        path.write_text(json.dumps({"excel_source": str(xlsx)}))

        _, port = load_launch_config(str(path))

        assert port == DEFAULT_PORT

    def test_invalid_port_falls_back_to_default_with_warning(self, tmp_path, capsys):
        xlsx = tmp_path / "absences.xlsx"
        xlsx.write_text("dummy")
        path = tmp_path / "launch_config.json"
        path.write_text(json.dumps({"excel_source": str(xlsx), "port": "not-a-number"}))

        _, port = load_launch_config(str(path))

        assert port == DEFAULT_PORT
        captured = capsys.readouterr()
        assert "port" in captured.err.lower()

    def test_negative_port_falls_back_to_default(self, tmp_path):
        xlsx = tmp_path / "absences.xlsx"
        xlsx.write_text("dummy")
        path = tmp_path / "launch_config.json"
        path.write_text(json.dumps({"excel_source": str(xlsx), "port": -1}))

        _, port = load_launch_config(str(path))

        assert port == DEFAULT_PORT
