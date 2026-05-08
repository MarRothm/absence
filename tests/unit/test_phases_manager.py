"""
Unit tests for absence_dashboard/phases_manager.py.
TDD: Written BEFORE implementation; confirmed failing before phases_manager.py is complete.
"""
import pytest
from absence_dashboard.phases_manager import add_phase, remove_phase


class TestAddPhase:
    def test_add_valid_phase_returns_updated_list(self):
        result = add_phase("Go-Live", "2026-06-22", "2026-06-26", [])
        assert len(result) == 1
        assert result[0]["name"] == "Go-Live"
        assert result[0]["start_date"] == "2026-06-22"
        assert result[0]["end_date"] == "2026-06-26"

    def test_add_second_phase_appends(self):
        existing = [{"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"}]
        result = add_phase("Sprint 10", "2026-06-15", "2026-06-21", existing)
        assert len(result) == 2
        names = {p["name"] for p in result}
        assert names == {"Go-Live", "Sprint 10"}

    def test_add_phase_single_day_allowed(self):
        result = add_phase("Kickoff", "2026-06-01", "2026-06-01", [])
        assert result[0]["start_date"] == "2026-06-01"
        assert result[0]["end_date"] == "2026-06-01"

    def test_add_duplicate_name_raises_value_error(self):
        existing = [{"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"}]
        with pytest.raises(ValueError, match="already exists"):
            add_phase("Go-Live", "2026-07-01", "2026-07-05", existing)

    def test_add_end_before_start_raises_value_error(self):
        with pytest.raises(ValueError, match="end_date"):
            add_phase("Bad Phase", "2026-07-10", "2026-07-05", [])

    def test_add_empty_name_raises_value_error(self):
        with pytest.raises(ValueError, match="name"):
            add_phase("", "2026-07-01", "2026-07-05", [])

    def test_original_list_not_mutated(self):
        original = []
        add_phase("Test", "2026-06-01", "2026-06-05", original)
        assert original == []

    def test_overlapping_phases_allowed(self):
        existing = [{"name": "Sprint 10", "start_date": "2026-06-15", "end_date": "2026-06-26"}]
        result = add_phase("Go-Live", "2026-06-22", "2026-06-26", existing)
        assert len(result) == 2


class TestRemovePhase:
    def test_remove_existing_phase(self):
        existing = [
            {"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"},
            {"name": "Sprint 10", "start_date": "2026-06-15", "end_date": "2026-06-21"},
        ]
        result = remove_phase("Go-Live", existing)
        assert len(result) == 1
        assert result[0]["name"] == "Sprint 10"

    def test_remove_only_phase_returns_empty(self):
        existing = [{"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"}]
        result = remove_phase("Go-Live", existing)
        assert result == []

    def test_remove_missing_phase_raises_key_error(self):
        with pytest.raises(KeyError):
            remove_phase("Nonexistent", [])

    def test_original_list_not_mutated(self):
        original = [{"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"}]
        remove_phase("Go-Live", original)
        assert len(original) == 1
