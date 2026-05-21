"""
TDD: Tests for absence_dashboard/graph.py (pool-based dependency model)
"""
import pytest
from datetime import date

from absence_dashboard.graph import DependencyGraph


MEMBERS = {"Alice", "Bob", "Carol", "Dave", "Eve"}

CW19 = {
    "year": 2026,
    "week_number": 19,
    "label": "CW19",
    "start": "2026-05-04",
    "end": "2026-05-08",
    "days": ["2026-05-04", "2026-05-05", "2026-05-06", "2026-05-07", "2026-05-08"],
}

CW24 = {
    "year": 2026,
    "week_number": 24,
    "label": "CW24",
    "start": "2026-06-08",
    "end": "2026-06-12",
    "days": ["2026-06-08", "2026-06-09", "2026-06-10", "2026-06-11", "2026-06-12"],
}


class TestPoolDependency:
    # ------------------------------------------------------------------ add --

    def test_add_single_pool_member(self):
        g = DependencyGraph()
        g.add_dependency("Alice", ["Bob"], MEMBERS)
        deps = g.edges()
        assert len(deps) == 1
        assert deps[0]["from_member"] == "Alice"
        assert deps[0]["to_members"] == ["Bob"]

    def test_add_multi_member_pool(self):
        g = DependencyGraph()
        g.add_dependency("Alice", ["Bob", "Carol"], MEMBERS)
        deps = g.edges()
        assert len(deps) == 1
        assert set(deps[0]["to_members"]) == {"Bob", "Carol"}

    def test_duplicate_pool_different_order_rejected(self):
        # uniqueness key is frozenset(to_members), so order does not matter
        g = DependencyGraph()
        g.add_dependency("Alice", ["Bob", "Carol"], MEMBERS)
        with pytest.raises(ValueError, match="already exists"):
            g.add_dependency("Alice", ["Carol", "Bob"], MEMBERS)

    def test_empty_pool_rejected(self):
        g = DependencyGraph()
        with pytest.raises(ValueError):
            g.add_dependency("Alice", [], MEMBERS)

    def test_unknown_from_member_rejected(self):
        g = DependencyGraph()
        with pytest.raises(ValueError, match="not in loaded dataset"):
            g.add_dependency("Unknown", ["Bob"], MEMBERS)

    def test_unknown_member_in_pool_rejected(self):
        g = DependencyGraph()
        with pytest.raises(ValueError, match="not in loaded dataset"):
            g.add_dependency("Alice", ["Bob", "Unknown"], MEMBERS)

    def test_add_with_date_range_stores_dates(self):
        g = DependencyGraph()
        g.add_dependency("Alice", ["Bob"], MEMBERS,
                         active_from="2026-06-01", active_to="2026-06-30")
        dep = g.edges()[0]
        assert dep["active_from"] == "2026-06-01"
        assert dep["active_to"] == "2026-06-30"

    def test_add_without_dates_omits_date_fields(self):
        g = DependencyGraph()
        g.add_dependency("Alice", ["Bob"], MEMBERS)
        dep = g.edges()[0]
        assert dep.get("active_from") is None
        assert dep.get("active_to") is None

    def test_only_active_from_raises(self):
        g = DependencyGraph()
        with pytest.raises(ValueError, match="neither"):
            g.add_dependency("Alice", ["Bob"], MEMBERS, active_from="2026-06-01")

    def test_only_active_to_raises(self):
        g = DependencyGraph()
        with pytest.raises(ValueError, match="neither"):
            g.add_dependency("Alice", ["Bob"], MEMBERS, active_to="2026-06-30")

    def test_active_from_after_active_to_raises(self):
        g = DependencyGraph()
        with pytest.raises(ValueError):
            g.add_dependency("Alice", ["Bob"], MEMBERS,
                             active_from="2026-07-01", active_to="2026-06-30")

    def test_same_pool_different_date_ranges_allowed(self):
        g = DependencyGraph()
        g.add_dependency("Alice", ["Bob"], MEMBERS,
                         active_from="2026-06-01", active_to="2026-06-30")
        g.add_dependency("Alice", ["Bob"], MEMBERS,
                         active_from="2026-09-01", active_to="2026-09-30")
        assert len(g.edges()) == 2

    # --------------------------------------------------------------- remove --

    def test_remove_dependency_removes_correct_entry(self):
        g = DependencyGraph()
        g.add_dependency("Alice", ["Bob", "Carol"], MEMBERS)
        g.add_dependency("Alice", ["Dave"], MEMBERS)
        g.remove_dependency("Alice", ["Bob", "Carol"])
        deps = g.edges()
        assert len(deps) == 1
        assert deps[0]["to_members"] == ["Dave"]

    def test_remove_nonexistent_raises_key_error(self):
        g = DependencyGraph()
        with pytest.raises(KeyError):
            g.remove_dependency("Alice", ["Bob"])

    def test_remove_with_dates_matches_correct_entry(self):
        g = DependencyGraph()
        g.add_dependency("Alice", ["Bob"], MEMBERS,
                         active_from="2026-06-01", active_to="2026-06-30")
        g.add_dependency("Alice", ["Bob"], MEMBERS,
                         active_from="2026-09-01", active_to="2026-09-30")
        g.remove_dependency("Alice", ["Bob"],
                             active_from="2026-06-01", active_to="2026-06-30")
        deps = g.edges()
        assert len(deps) == 1
        assert deps[0]["active_from"] == "2026-09-01"

    # ---------------------------------------------------- compute_deadlock ---

    def test_deadlock_when_all_pool_members_absent(self):
        deps = [{"from_member": "Alice", "to_members": ["Bob", "Carol"]}]
        abs_sets = {
            "Bob": {date(2026, 5, 4)},
            "Carol": {date(2026, 5, 7)},
        }
        result = DependencyGraph.compute_deadlock_weeks("Alice", deps, abs_sets, [CW19])
        assert 19 in result

    def test_no_deadlock_when_one_pool_member_present(self):
        deps = [{"from_member": "Alice", "to_members": ["Bob", "Carol"]}]
        abs_sets = {
            "Bob": {date(2026, 5, 4)},
            "Carol": set(),
        }
        result = DependencyGraph.compute_deadlock_weeks("Alice", deps, abs_sets, [CW19])
        assert 19 not in result

    def test_no_deadlock_for_unrelated_member(self):
        deps = [{"from_member": "Alice", "to_members": ["Bob", "Carol"]}]
        abs_sets = {
            "Bob": {date(2026, 5, 4)},
            "Carol": {date(2026, 5, 5)},
        }
        result = DependencyGraph.compute_deadlock_weeks("Dave", deps, abs_sets, [CW19])
        assert 19 not in result

    def test_deadlock_respects_active_range_outside(self):
        deps = [{
            "from_member": "Alice",
            "to_members": ["Bob"],
            "active_from": "2026-06-01",
            "active_to": "2026-06-30",
        }]
        abs_sets = {"Bob": {date(2026, 5, 4)}}
        result = DependencyGraph.compute_deadlock_weeks("Alice", deps, abs_sets, [CW19])
        assert 19 not in result

    def test_deadlock_respects_active_range_inside(self):
        deps = [{
            "from_member": "Alice",
            "to_members": ["Bob"],
            "active_from": "2026-06-01",
            "active_to": "2026-06-30",
        }]
        abs_sets = {"Bob": {date(2026, 6, 8)}}
        result = DependencyGraph.compute_deadlock_weeks("Alice", deps, abs_sets, [CW24])
        assert 24 in result

    def test_no_deps_returns_empty(self):
        result = DependencyGraph.compute_deadlock_weeks("Alice", [], {}, [CW19])
        assert result == []

    # ------------------------------------------------ compute_bottleneck ----

    def test_bottleneck_weight_sole_present_satisfier(self):
        deps = [{"from_member": "Alice", "to_members": ["Bob", "Carol"]}]
        abs_sets = {
            "Bob": set(),
            "Carol": {date(2026, 5, 4), date(2026, 5, 5),
                      date(2026, 5, 6), date(2026, 5, 7), date(2026, 5, 8)},
        }
        weights = DependencyGraph.compute_bottleneck_weights(deps, abs_sets, [CW19])
        assert weights.get("Bob", 0) >= 1
        assert weights.get("Carol", 0) == 0

    def test_bottleneck_weight_zero_when_multiple_present(self):
        deps = [{"from_member": "Alice", "to_members": ["Bob", "Carol"]}]
        abs_sets = {
            "Bob": set(),
            "Carol": set(),
        }
        weights = DependencyGraph.compute_bottleneck_weights(deps, abs_sets, [CW19])
        assert weights.get("Bob", 0) == 0
        assert weights.get("Carol", 0) == 0

    def test_bottleneck_weight_zero_when_deadlock(self):
        deps = [{"from_member": "Alice", "to_members": ["Bob", "Carol"]}]
        abs_sets = {
            "Bob": {date(2026, 5, 4)},
            "Carol": {date(2026, 5, 5)},
        }
        weights = DependencyGraph.compute_bottleneck_weights(deps, abs_sets, [CW19])
        assert weights.get("Bob", 0) == 0
        assert weights.get("Carol", 0) == 0

    def test_bottleneck_weight_accumulates_across_deps(self):
        deps = [
            {"from_member": "Alice", "to_members": ["Bob", "Carol"]},
            {"from_member": "Dave", "to_members": ["Bob", "Eve"]},
        ]
        abs_sets = {
            "Bob": set(),
            "Carol": {date(2026, 5, 4)},
            "Eve": {date(2026, 5, 4)},
        }
        weights = DependencyGraph.compute_bottleneck_weights(deps, abs_sets, [CW19])
        assert weights.get("Bob", 0) >= 2

    def test_bottleneck_weight_accumulates_across_weeks(self):
        deps = [{"from_member": "Alice", "to_members": ["Bob", "Carol"]}]
        abs_sets = {
            "Bob": set(),
            "Carol": {date(2026, 5, 4), date(2026, 6, 8)},
        }
        weights = DependencyGraph.compute_bottleneck_weights(deps, abs_sets, [CW19, CW24])
        assert weights.get("Bob", 0) >= 2
