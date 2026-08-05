"""
TDD: Tests for absence_dashboard/cumul_groups.py
"""
import pytest
from datetime import date

from absence_dashboard.cumul_groups import (
    add_cumul_group,
    update_cumul_group,
    remove_cumul_group,
    critical_absence_days,
    compute_cumul_risk_weeks,
    compute_sole_coverage_weeks,
)
from absence_dashboard.merger import AbsencePeriod

VALID = {"Alice", "Bob", "Carol", "Dave"}


def _week(year, week_number, days):
    return {
        "year": year,
        "week_number": week_number,
        "label": f"KW{week_number}",
        "start": days[0].isoformat(),
        "end": days[-1].isoformat(),
        "days": [d.isoformat() for d in days],
    }


CALENDAR_WEEKS = [
    _week(2026, 18, [date(2026, 4, 27), date(2026, 4, 28), date(2026, 4, 29), date(2026, 4, 30), date(2026, 5, 1)]),
    _week(2026, 19, [date(2026, 5, 4), date(2026, 5, 5), date(2026, 5, 6), date(2026, 5, 7), date(2026, 5, 8)]),
    _week(2026, 20, [date(2026, 5, 11), date(2026, 5, 12), date(2026, 5, 13), date(2026, 5, 14), date(2026, 5, 15)]),
]


class TestAddCumulGroup:
    def test_returns_new_list_with_entry(self):
        groups = add_cumul_group("Backend Coverage", ["Alice", "Bob"], VALID, [])
        assert len(groups) == 1
        assert groups[0]["name"] == "Backend Coverage"
        assert groups[0]["members"] == ["Alice", "Bob"]

    def test_does_not_mutate_input_list(self):
        original = []
        add_cumul_group("Backend Coverage", ["Alice", "Bob"], VALID, original)
        assert original == []

    def test_empty_name_rejected(self):
        with pytest.raises(ValueError):
            add_cumul_group("", ["Alice", "Bob"], VALID, [])

    def test_fewer_than_two_members_rejected(self):
        with pytest.raises(ValueError):
            add_cumul_group("Solo", ["Alice"], VALID, [])

    def test_duplicate_member_within_group_rejected(self):
        with pytest.raises(ValueError):
            add_cumul_group("Dup", ["Alice", "Alice"], VALID, [])

    def test_unknown_member_rejected(self):
        with pytest.raises(ValueError):
            add_cumul_group("Unknown", ["Alice", "Zed"], VALID, [])

    def test_duplicate_name_rejected(self):
        groups = add_cumul_group("Backend Coverage", ["Alice", "Bob"], VALID, [])
        with pytest.raises(ValueError):
            add_cumul_group("Backend Coverage", ["Carol", "Dave"], VALID, groups)

    def test_duplicate_member_set_rejected(self):
        groups = add_cumul_group("Backend Coverage", ["Alice", "Bob"], VALID, [])
        with pytest.raises(ValueError):
            add_cumul_group("Backend Coverage v2", ["Bob", "Alice"], VALID, groups)

    def test_active_from_without_active_to_rejected(self):
        with pytest.raises(ValueError):
            add_cumul_group(
                "Timeboxed", ["Alice", "Bob"], VALID, [],
                active_from="2026-06-01",
            )

    def test_active_to_without_active_from_rejected(self):
        with pytest.raises(ValueError):
            add_cumul_group(
                "Timeboxed", ["Alice", "Bob"], VALID, [],
                active_to="2026-06-30",
            )

    def test_active_to_before_active_from_rejected(self):
        with pytest.raises(ValueError):
            add_cumul_group(
                "Timeboxed", ["Alice", "Bob"], VALID, [],
                active_from="2026-06-30", active_to="2026-06-01",
            )

    def test_active_range_stored_on_entry(self):
        groups = add_cumul_group(
            "Timeboxed", ["Alice", "Bob"], VALID, [],
            active_from="2026-06-01", active_to="2026-06-30",
        )
        assert groups[0]["active_from"] == "2026-06-01"
        assert groups[0]["active_to"] == "2026-06-30"


class TestUpdateCumulGroup:
    def test_unknown_old_name_raises_key_error(self):
        with pytest.raises(KeyError):
            update_cumul_group("Nonexistent", [], new_name="X")

    def test_rename_only(self):
        groups = add_cumul_group("Backend Coverage", ["Alice", "Bob"], VALID, [])
        updated = update_cumul_group("Backend Coverage", groups, new_name="Backend Coverage v2")
        assert updated[0]["name"] == "Backend Coverage v2"
        assert updated[0]["members"] == ["Alice", "Bob"]

    def test_does_not_mutate_input_list(self):
        groups = add_cumul_group("Backend Coverage", ["Alice", "Bob"], VALID, [])
        original_copy = [dict(g) for g in groups]
        update_cumul_group("Backend Coverage", groups, new_name="Renamed")
        assert groups == original_copy

    def test_update_members(self):
        groups = add_cumul_group("Backend Coverage", ["Alice", "Bob"], VALID, [])
        updated = update_cumul_group(
            "Backend Coverage", groups, new_members=["Carol", "Dave"], valid_members=VALID,
        )
        assert updated[0]["members"] == ["Carol", "Dave"]

    def test_update_members_fewer_than_two_rejected(self):
        groups = add_cumul_group("Backend Coverage", ["Alice", "Bob"], VALID, [])
        with pytest.raises(ValueError):
            update_cumul_group(
                "Backend Coverage", groups, new_members=["Alice"], valid_members=VALID,
            )

    def test_update_members_unknown_member_rejected(self):
        groups = add_cumul_group("Backend Coverage", ["Alice", "Bob"], VALID, [])
        with pytest.raises(ValueError):
            update_cumul_group(
                "Backend Coverage", groups, new_members=["Alice", "Zed"], valid_members=VALID,
            )

    def test_rename_to_duplicate_name_rejected(self):
        groups = add_cumul_group("Backend Coverage", ["Alice", "Bob"], VALID, [])
        groups = add_cumul_group("Frontend Coverage", ["Carol", "Dave"], VALID, groups)
        with pytest.raises(ValueError):
            update_cumul_group("Backend Coverage", groups, new_name="Frontend Coverage")

    def test_rename_to_same_name_is_ok(self):
        groups = add_cumul_group("Backend Coverage", ["Alice", "Bob"], VALID, [])
        updated = update_cumul_group("Backend Coverage", groups, new_name="Backend Coverage")
        assert updated[0]["name"] == "Backend Coverage"

    def test_update_active_range(self):
        groups = add_cumul_group("Backend Coverage", ["Alice", "Bob"], VALID, [])
        updated = update_cumul_group(
            "Backend Coverage", groups,
            active_from="2026-06-01", active_to="2026-06-30",
        )
        assert updated[0]["active_from"] == "2026-06-01"
        assert updated[0]["active_to"] == "2026-06-30"

    def test_clear_active_range(self):
        groups = add_cumul_group(
            "Backend Coverage", ["Alice", "Bob"], VALID, [],
            active_from="2026-06-01", active_to="2026-06-30",
        )
        updated = update_cumul_group(
            "Backend Coverage", groups,
            active_from=None, active_to=None,
        )
        assert "active_from" not in updated[0] or updated[0]["active_from"] is None

    def test_active_from_without_active_to_rejected(self):
        groups = add_cumul_group("Backend Coverage", ["Alice", "Bob"], VALID, [])
        with pytest.raises(ValueError):
            update_cumul_group("Backend Coverage", groups, active_from="2026-06-01")

    def test_active_to_before_active_from_rejected(self):
        groups = add_cumul_group("Backend Coverage", ["Alice", "Bob"], VALID, [])
        with pytest.raises(ValueError):
            update_cumul_group(
                "Backend Coverage", groups,
                active_from="2026-06-30", active_to="2026-06-01",
            )


class TestRemoveCumulGroup:
    def test_removes_named_group(self):
        groups = add_cumul_group("Backend Coverage", ["Alice", "Bob"], VALID, [])
        updated = remove_cumul_group("Backend Coverage", groups)
        assert updated == []

    def test_does_not_mutate_input_list(self):
        groups = add_cumul_group("Backend Coverage", ["Alice", "Bob"], VALID, [])
        original_copy = [dict(g) for g in groups]
        remove_cumul_group("Backend Coverage", groups)
        assert groups == original_copy

    def test_unknown_name_raises_key_error(self):
        with pytest.raises(KeyError):
            remove_cumul_group("Nonexistent", [])


class TestCriticalAbsenceDays:
    def test_block_over_5_days_is_critical(self):
        blocks = [AbsencePeriod(date(2026, 4, 27), date(2026, 5, 4))]
        days = critical_absence_days(blocks)
        assert date(2026, 4, 27) in days
        assert date(2026, 5, 4) in days
        assert len(days) == 8

    def test_block_exactly_5_days_not_critical(self):
        blocks = [AbsencePeriod(date(2026, 4, 27), date(2026, 5, 1))]
        assert critical_absence_days(blocks) == set()

    def test_block_under_5_days_not_critical(self):
        blocks = [AbsencePeriod(date(2026, 4, 27), date(2026, 4, 28))]
        assert critical_absence_days(blocks) == set()

    def test_multiple_blocks_only_critical_ones_included(self):
        blocks = [
            AbsencePeriod(date(2026, 4, 27), date(2026, 4, 28)),
            AbsencePeriod(date(2026, 5, 4), date(2026, 5, 11)),
        ]
        days = critical_absence_days(blocks)
        assert date(2026, 4, 27) not in days
        assert date(2026, 5, 4) in days
        assert len(days) == 8

    def test_empty_blocks_returns_empty_set(self):
        assert critical_absence_days([]) == set()


class TestComputeCumulRiskWeeks:
    def test_flags_week_with_shared_critical_day(self):
        group = {"name": "Risk Group", "members": ["Alice", "Bob"]}
        alice_critical = critical_absence_days(
            [AbsencePeriod(date(2026, 4, 27), date(2026, 5, 4))]
        )
        bob_critical = critical_absence_days(
            [AbsencePeriod(date(2026, 5, 4), date(2026, 5, 11))]
        )
        member_critical_date_sets = {"Alice": alice_critical, "Bob": bob_critical}
        weeks = compute_cumul_risk_weeks(group, member_critical_date_sets, CALENDAR_WEEKS)
        assert weeks == [19]

    def test_no_overlap_no_risk(self):
        group = {"name": "No Risk", "members": ["Alice", "Bob"]}
        alice_critical = critical_absence_days(
            [AbsencePeriod(date(2026, 4, 27), date(2026, 5, 4))]
        )
        member_critical_date_sets = {"Alice": alice_critical, "Bob": set()}
        weeks = compute_cumul_risk_weeks(group, member_critical_date_sets, CALENDAR_WEEKS)
        assert weeks == []

    def test_member_with_no_critical_days_blocks_risk(self):
        group = {"name": "Three Way", "members": ["Alice", "Bob", "Carol"]}
        alice_critical = critical_absence_days(
            [AbsencePeriod(date(2026, 4, 27), date(2026, 5, 4))]
        )
        bob_critical = critical_absence_days(
            [AbsencePeriod(date(2026, 5, 4), date(2026, 5, 11))]
        )
        member_critical_date_sets = {
            "Alice": alice_critical, "Bob": bob_critical, "Carol": set(),
        }
        weeks = compute_cumul_risk_weeks(group, member_critical_date_sets, CALENDAR_WEEKS)
        assert weeks == []


class TestComputeSoleCoverageWeeks:
    def test_two_member_group_sole_coverage_both_directions(self):
        group = {"name": "Risk Group", "members": ["Alice", "Bob"]}
        alice_critical = critical_absence_days(
            [AbsencePeriod(date(2026, 4, 27), date(2026, 5, 4))]
        )
        bob_critical = critical_absence_days(
            [AbsencePeriod(date(2026, 5, 4), date(2026, 5, 11))]
        )
        member_critical_date_sets = {"Alice": alice_critical, "Bob": bob_critical}
        result = compute_sole_coverage_weeks(group, member_critical_date_sets, CALENDAR_WEEKS)
        assert result.get("Bob") == [18]
        assert result.get("Alice") == [20]
        assert 19 not in result.get("Alice", [])
        assert 19 not in result.get("Bob", [])

    def test_three_member_group_flags_sole_present_member(self):
        group = {"name": "Sole Group", "members": ["Alice", "Bob", "Carol"]}
        alice_critical = critical_absence_days(
            [AbsencePeriod(date(2026, 4, 27), date(2026, 5, 4))]
        )
        bob_critical = critical_absence_days(
            [AbsencePeriod(date(2026, 5, 4), date(2026, 5, 11))]
        )
        member_critical_date_sets = {
            "Alice": alice_critical, "Bob": bob_critical, "Carol": set(),
        }
        result = compute_sole_coverage_weeks(group, member_critical_date_sets, CALENDAR_WEEKS)
        assert result.get("Carol") == [19]
        assert 18 not in result.get("Carol", [])
        assert 20 not in result.get("Carol", [])

    def test_no_flag_when_all_members_critical(self):
        group = {"name": "All Critical", "members": ["Alice", "Bob"]}
        alice_critical = critical_absence_days(
            [AbsencePeriod(date(2026, 5, 4), date(2026, 5, 11))]
        )
        bob_critical = critical_absence_days(
            [AbsencePeriod(date(2026, 5, 4), date(2026, 5, 11))]
        )
        member_critical_date_sets = {"Alice": alice_critical, "Bob": bob_critical}
        result = compute_sole_coverage_weeks(group, member_critical_date_sets, CALENDAR_WEEKS)
        assert result == {}
