"""
TDD: Tests for absence_dashboard/state.py
"""
import json
import os
import pytest

from absence_dashboard.state import load_state, save_state, AppState


class TestLoadState:
    def test_missing_file_returns_empty_appstate(self, tmp_path):
        path = str(tmp_path / "nonexistent.json")
        state = load_state(path)
        assert isinstance(state, AppState)
        assert state.cumul_groups == []
        assert state.clusters == []

    def test_valid_json_deserialised_correctly(self, tmp_path):
        path = str(tmp_path / "state.json")
        data = {
            "cumul_groups": [{"name": "Backend Coverage", "members": ["Alice", "Bob"]}],
            "clusters": [{"name": "Backend", "members": ["Alice", "Bob"]}],
        }
        with open(path, "w") as f:
            json.dump(data, f)
        state = load_state(path)
        assert len(state.cumul_groups) == 1
        assert state.cumul_groups[0]["name"] == "Backend Coverage"
        assert state.cumul_groups[0]["members"] == ["Alice", "Bob"]
        assert len(state.clusters) == 1
        assert state.clusters[0]["name"] == "Backend"

    def test_old_dependencies_key_ignored(self, tmp_path):
        path = str(tmp_path / "state.json")
        data = {"dependencies": [{"from_member": "Alice", "to_member": "Bob"}]}
        with open(path, "w") as f:
            json.dump(data, f)
        state = load_state(path)
        assert state.cumul_groups == []

    def test_missing_keys_default_to_empty(self, tmp_path):
        path = str(tmp_path / "state.json")
        with open(path, "w") as f:
            json.dump({}, f)
        state = load_state(path)
        assert state.cumul_groups == []
        assert state.clusters == []


class TestSaveState:
    def test_saves_valid_json(self, tmp_path):
        path = str(tmp_path / "state.json")
        state = AppState(
            cumul_groups=[{"name": "Backend Coverage", "members": ["Alice", "Bob"]}],
            clusters=[{"name": "Backend", "members": ["Alice"]}],
        )
        save_state(state, path)
        with open(path) as f:
            data = json.load(f)
        assert data["cumul_groups"][0]["name"] == "Backend Coverage"
        assert data["clusters"][0]["name"] == "Backend"

    def test_roundtrip_preserves_data(self, tmp_path):
        path = str(tmp_path / "state.json")
        original = AppState(
            cumul_groups=[{"name": "Backend Coverage", "members": ["X", "Y"]}],
            clusters=[{"name": "C1", "members": ["X", "Y"]}],
        )
        save_state(original, path)
        loaded = load_state(path)
        assert loaded.cumul_groups == original.cumul_groups
        assert loaded.clusters == original.clusters

    def test_creates_directory_if_absent(self, tmp_path):
        path = str(tmp_path / "subdir" / "state.json")
        state = AppState()
        save_state(state, path)
        assert os.path.exists(path)

    def test_empty_state_saves_correctly(self, tmp_path):
        path = str(tmp_path / "state.json")
        save_state(AppState(), path)
        with open(path) as f:
            data = json.load(f)
        assert data["cumul_groups"] == []
        assert data["clusters"] == []
