"""
TDD: Tests for absence_dashboard/graph.py
"""
import pytest
from datetime import date

from absence_dashboard.graph import DependencyGraph, CycleError
from absence_dashboard.merger import AbsencePeriod


MEMBERS = {"Alice", "Bob", "Carol", "Dave", "Eve"}


class TestAddEdge:
    def test_add_valid_edge(self):
        g = DependencyGraph()
        g.add_edge("Alice", "Bob", MEMBERS)
        assert {"from_member": "Alice", "to_member": "Bob"} in g.edges()

    def test_self_loop_rejected(self):
        g = DependencyGraph()
        with pytest.raises(ValueError, match="Self"):
            g.add_edge("Alice", "Alice", MEMBERS)

    def test_duplicate_edge_rejected(self):
        g = DependencyGraph()
        g.add_edge("Alice", "Bob", MEMBERS)
        with pytest.raises(ValueError, match="already exists"):
            g.add_edge("Alice", "Bob", MEMBERS)

    def test_unknown_source_rejected(self):
        g = DependencyGraph()
        with pytest.raises(ValueError, match="not in loaded dataset"):
            g.add_edge("Unknown", "Bob", MEMBERS)

    def test_unknown_target_rejected(self):
        g = DependencyGraph()
        with pytest.raises(ValueError, match="not in loaded dataset"):
            g.add_edge("Alice", "Unknown", MEMBERS)

    def test_direct_cycle_rejected(self):
        g = DependencyGraph()
        g.add_edge("Alice", "Bob", MEMBERS)
        with pytest.raises(CycleError):
            g.add_edge("Bob", "Alice", MEMBERS)

    def test_indirect_cycle_rejected(self):
        g = DependencyGraph()
        g.add_edge("Alice", "Bob", MEMBERS)
        g.add_edge("Bob", "Carol", MEMBERS)
        with pytest.raises(CycleError):
            g.add_edge("Carol", "Alice", MEMBERS)


class TestRemoveEdge:
    def test_remove_existing_edge(self):
        g = DependencyGraph()
        g.add_edge("Alice", "Bob", MEMBERS)
        g.remove_edge("Alice", "Bob")
        assert g.edges() == []

    def test_remove_nonexistent_edge_raises(self):
        g = DependencyGraph()
        with pytest.raises(KeyError):
            g.remove_edge("Alice", "Bob")


class TestGetBottlenecks:
    def test_member_with_two_incoming_is_bottleneck(self):
        edges = [
            {"from_member": "Alice", "to_member": "Bob"},
            {"from_member": "Carol", "to_member": "Bob"},
        ]
        assert "Bob" in DependencyGraph.get_bottlenecks(edges)

    def test_member_with_one_incoming_is_not_bottleneck(self):
        edges = [{"from_member": "Alice", "to_member": "Bob"}]
        assert "Bob" not in DependencyGraph.get_bottlenecks(edges)

    def test_member_with_zero_incoming_is_not_bottleneck(self):
        edges = [{"from_member": "Alice", "to_member": "Bob"}]
        assert "Alice" not in DependencyGraph.get_bottlenecks(edges)

    def test_empty_edges_returns_empty_set(self):
        assert DependencyGraph.get_bottlenecks([]) == set()

    def test_three_incoming_is_bottleneck(self):
        edges = [
            {"from_member": "A", "to_member": "Bob"},
            {"from_member": "B", "to_member": "Bob"},
            {"from_member": "C", "to_member": "Bob"},
        ]
        assert "Bob" in DependencyGraph.get_bottlenecks(edges)


class TestComputeAtRiskWeeks:
    def _make_cw(self, week_number, start_str, end_str):
        return {
            "year": 2026,
            "week_number": week_number,
            "label": f"CW{week_number}",
            "start": start_str,
            "end": end_str,
        }

    def test_at_risk_when_dependency_absent(self):
        edges = [{"from_member": "Alice", "to_member": "Bob"}]
        bob_blocks = [AbsencePeriod(date(2026, 5, 4), date(2026, 5, 8))]
        member_blocks_map = {"Bob": bob_blocks, "Alice": []}
        cws = [self._make_cw(19, "2026-05-04", "2026-05-08")]

        result = DependencyGraph.compute_at_risk_weeks("Alice", edges, member_blocks_map, cws)
        assert 19 in result

    def test_not_at_risk_when_dependency_present(self):
        edges = [{"from_member": "Alice", "to_member": "Bob"}]
        member_blocks_map = {"Bob": [], "Alice": []}
        cws = [{"year": 2026, "week_number": 19, "label": "CW19",
                "start": "2026-05-04", "end": "2026-05-08"}]

        result = DependencyGraph.compute_at_risk_weeks("Alice", edges, member_blocks_map, cws)
        assert 19 not in result

    def test_no_dependencies_returns_empty(self):
        result = DependencyGraph.compute_at_risk_weeks("Alice", [], {}, [])
        assert result == []

    def test_at_risk_week_partial_overlap(self):
        # Absence starts mid-week — still at risk that week
        edges = [{"from_member": "Alice", "to_member": "Bob"}]
        bob_blocks = [AbsencePeriod(date(2026, 5, 6), date(2026, 5, 6))]  # Wednesday only
        member_blocks_map = {"Bob": bob_blocks, "Alice": []}
        cws = [{"year": 2026, "week_number": 19, "label": "CW19",
                "start": "2026-05-04", "end": "2026-05-08"}]

        result = DependencyGraph.compute_at_risk_weeks("Alice", edges, member_blocks_map, cws)
        assert 19 in result


# ---------------------------------------------------------------------------
# Date-bounded dependencies  (Phase 14 / FR-005 / FR-006 / FR-007)
# ---------------------------------------------------------------------------

class TestDateBoundedDependencies:
    def test_edge_with_dates_stores_date_fields(self):
        g = DependencyGraph()
        g.add_edge("Alice", "Bob", MEMBERS, active_from="2026-06-01", active_to="2026-06-30")
        edge = g.edges()[0]
        assert edge["active_from"] == "2026-06-01"
        assert edge["active_to"] == "2026-06-30"

    def test_edge_without_dates_omits_date_fields(self):
        g = DependencyGraph()
        g.add_edge("Alice", "Bob", MEMBERS)
        edge = g.edges()[0]
        assert edge.get("active_from") is None
        assert edge.get("active_to") is None

    def test_only_active_from_raises(self):
        g = DependencyGraph()
        with pytest.raises(ValueError, match="neither"):
            g.add_edge("Alice", "Bob", MEMBERS, active_from="2026-06-01")

    def test_only_active_to_raises(self):
        g = DependencyGraph()
        with pytest.raises(ValueError, match="neither"):
            g.add_edge("Alice", "Bob", MEMBERS, active_to="2026-06-30")

    def test_active_from_after_active_to_raises(self):
        g = DependencyGraph()
        with pytest.raises(ValueError):
            g.add_edge("Alice", "Bob", MEMBERS,
                       active_from="2026-07-01", active_to="2026-06-30")

    def test_same_pair_different_date_ranges_allowed(self):
        g = DependencyGraph()
        g.add_edge("Alice", "Bob", MEMBERS, active_from="2026-06-01", active_to="2026-06-30")
        g.add_edge("Alice", "Bob", MEMBERS, active_from="2026-09-01", active_to="2026-09-30")
        assert len(g.edges()) == 2

    def test_identical_tuple_rejected(self):
        g = DependencyGraph()
        g.add_edge("Alice", "Bob", MEMBERS, active_from="2026-06-01", active_to="2026-06-30")
        with pytest.raises(ValueError, match="already exists"):
            g.add_edge("Alice", "Bob", MEMBERS,
                       active_from="2026-06-01", active_to="2026-06-30")

    def test_remove_edge_with_dates_removes_correct_entry(self):
        g = DependencyGraph()
        g.add_edge("Alice", "Bob", MEMBERS, active_from="2026-06-01", active_to="2026-06-30")
        g.add_edge("Alice", "Bob", MEMBERS, active_from="2026-09-01", active_to="2026-09-30")
        g.remove_edge("Alice", "Bob", active_from="2026-06-01", active_to="2026-06-30")
        edges = g.edges()
        assert len(edges) == 1
        assert edges[0]["active_from"] == "2026-09-01"

    def test_at_risk_only_within_active_range(self):
        # Bob absent in CW28 (Jul), but dependency active only in June → no at-risk
        edges = [{"from_member": "Alice", "to_member": "Bob",
                  "active_from": "2026-06-01", "active_to": "2026-06-30"}]
        bob_blocks = [AbsencePeriod(date(2026, 7, 6), date(2026, 7, 10))]
        member_blocks_map = {"Bob": bob_blocks, "Alice": []}
        cws = [{"year": 2026, "week_number": 28, "label": "CW28",
                "start": "2026-07-06", "end": "2026-07-10"}]
        result = DependencyGraph.compute_at_risk_weeks("Alice", edges, member_blocks_map, cws)
        assert 28 not in result

    def test_at_risk_within_active_range_when_dep_absent(self):
        # Bob absent in CW24 (Jun), dependency active in June → at-risk
        edges = [{"from_member": "Alice", "to_member": "Bob",
                  "active_from": "2026-06-01", "active_to": "2026-06-30"}]
        bob_blocks = [AbsencePeriod(date(2026, 6, 8), date(2026, 6, 12))]
        member_blocks_map = {"Bob": bob_blocks, "Alice": []}
        cws = [{"year": 2026, "week_number": 24, "label": "CW24",
                "start": "2026-06-08", "end": "2026-06-12"}]
        result = DependencyGraph.compute_at_risk_weeks("Alice", edges, member_blocks_map, cws)
        assert 24 in result

    def test_indefinite_dependency_unchanged(self):
        # No dates → at-risk for all weeks where dep is absent (existing behaviour)
        edges = [{"from_member": "Alice", "to_member": "Bob"}]
        bob_blocks = [AbsencePeriod(date(2026, 7, 6), date(2026, 7, 10))]
        member_blocks_map = {"Bob": bob_blocks, "Alice": []}
        cws = [{"year": 2026, "week_number": 28, "label": "CW28",
                "start": "2026-07-06", "end": "2026-07-10"}]
        result = DependencyGraph.compute_at_risk_weeks("Alice", edges, member_blocks_map, cws)
        assert 28 in result
