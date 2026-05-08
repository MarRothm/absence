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
        assert state.dependencies == []
        assert state.clusters == []

    def test_valid_json_deserialised_correctly(self, tmp_path):
        path = str(tmp_path / "state.json")
        data = {
            "dependencies": [{"from_member": "Alice", "to_member": "Bob"}],
            "clusters": [{"name": "Backend", "members": ["Alice", "Bob"]}],
        }
        with open(path, "w") as f:
            json.dump(data, f)
        state = load_state(path)
        assert len(state.dependencies) == 1
        assert state.dependencies[0]["from_member"] == "Alice"
        assert len(state.clusters) == 1
        assert state.clusters[0]["name"] == "Backend"

    def test_missing_keys_default_to_empty(self, tmp_path):
        path = str(tmp_path / "state.json")
        with open(path, "w") as f:
            json.dump({}, f)
        state = load_state(path)
        assert state.dependencies == []
        assert state.clusters == []


class TestSaveState:
    def test_saves_valid_json(self, tmp_path):
        path = str(tmp_path / "state.json")
        state = AppState(
            dependencies=[{"from_member": "Alice", "to_member": "Bob"}],
            clusters=[{"name": "Backend", "members": ["Alice"]}],
        )
        save_state(state, path)
        with open(path) as f:
            data = json.load(f)
        assert data["dependencies"][0]["from_member"] == "Alice"
        assert data["clusters"][0]["name"] == "Backend"

    def test_roundtrip_preserves_data(self, tmp_path):
        path = str(tmp_path / "state.json")
        original = AppState(
            dependencies=[{"from_member": "X", "to_member": "Y"}],
            clusters=[{"name": "C1", "members": ["X", "Y"]}],
        )
        save_state(original, path)
        loaded = load_state(path)
        assert loaded.dependencies == original.dependencies
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
        assert data["dependencies"] == []
        assert data["clusters"] == []
