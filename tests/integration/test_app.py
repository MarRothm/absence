"""
Integration tests for absence_dashboard/app.py Flask routes.
TDD: Written BEFORE implementation; confirmed failing before app.py is complete.
"""
import json
import sys
import pytest
from datetime import date
from unittest.mock import MagicMock


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_member(data, name):
    return next((m for m in data["members"] if m["name"] == name), None)


# ---------------------------------------------------------------------------
# GET /api/dashboard  (T014 / US1)
# ---------------------------------------------------------------------------

class TestGetDashboard:
    def test_status_200(self, client):
        rv = client.get("/api/dashboard")
        assert rv.status_code == 200

    def test_exactly_five_members(self, client):
        data = client.get("/api/dashboard").get_json()
        assert len(data["members"]) == 5

    def test_member_names_correct(self, client):
        data = client.get("/api/dashboard").get_json()
        names = {m["name"] for m in data["members"]}
        assert names == {"Alice", "Bob", "Carol", "Dave", "Eve"}

    def test_alice_merged_blocks(self, client):
        data = client.get("/api/dashboard").get_json()
        alice = get_member(data, "Alice")
        assert alice is not None
        # Row 3: Apr27-28; Row 8 (same person): May4 → two non-overlapping blocks
        starts = {b["start"] for b in alice["merged_blocks"]}
        assert "2026-04-27" in starts
        assert "2026-05-04" in starts

    def test_alice_first_block_end(self, client):
        data = client.get("/api/dashboard").get_json()
        alice = get_member(data, "Alice")
        block_27 = next(b for b in alice["merged_blocks"] if b["start"] == "2026-04-27")
        assert block_27["end"] == "2026-04-28"

    def test_bob_single_merged_block(self, client):
        data = client.get("/api/dashboard").get_json()
        bob = get_member(data, "Bob")
        assert len(bob["merged_blocks"]) == 1
        assert bob["merged_blocks"][0]["start"] == "2026-04-29"
        assert bob["merged_blocks"][0]["end"] == "2026-05-01"

    def test_carol_no_merged_blocks(self, client):
        data = client.get("/api/dashboard").get_json()
        carol = get_member(data, "Carol")
        assert carol["merged_blocks"] == []

    def test_merged_blocks_non_overlapping(self, client):
        data = client.get("/api/dashboard").get_json()
        for member in data["members"]:
            blocks = sorted(member["merged_blocks"], key=lambda b: b["start"])
            for i in range(len(blocks) - 1):
                assert blocks[i]["end"] < blocks[i + 1]["start"]

    def test_calendar_weeks_starts_at_current_week(self, client):
        data = client.get("/api/dashboard").get_json()
        weeks = data["calendar_weeks"]
        assert len(weeks) > 0
        today = date.today()
        iso = today.isocalendar()
        assert weeks[0]["year"] == iso.year
        assert weeks[0]["week_number"] == iso.week

    def test_calendar_weeks_ends_at_cw53_2026(self, client):
        data = client.get("/api/dashboard").get_json()
        weeks = data["calendar_weeks"]
        assert weeks[-1]["year"] == 2026
        assert weeks[-1]["week_number"] == 53

    def test_no_duplicate_calendar_weeks(self, client):
        data = client.get("/api/dashboard").get_json()
        keys = [(w["year"], w["week_number"]) for w in data["calendar_weeks"]]
        assert len(keys) == len(set(keys))

    def test_calendar_weeks_have_days_field(self, client):
        data = client.get("/api/dashboard").get_json()
        for week in data["calendar_weeks"]:
            assert "days" in week, f"CW{week['week_number']} missing 'days' field"
            assert len(week["days"]) == 5, f"CW{week['week_number']} should have 5 days"

    def test_calendar_week_days_are_mon_to_fri(self, client):
        from datetime import date, datetime
        data = client.get("/api/dashboard").get_json()
        first_week = data["calendar_weeks"][0]
        days = first_week["days"]
        for i, day_str in enumerate(days):
            d = date.fromisoformat(day_str)
            assert d.weekday() == i, f"Day {i} should be weekday {i}, got {d.weekday()}"

    def test_calendar_week_days_match_start(self, client):
        data = client.get("/api/dashboard").get_json()
        for week in data["calendar_weeks"]:
            assert week["days"][0] == week["start"], (
                f"First day should equal start for {week['label']}"
            )

    def test_calendar_week_label_format(self, client):
        import re
        data = client.get("/api/dashboard").get_json()
        pattern = re.compile(r"^CW\d{1,2} \| \d{1,2} [A-Z][a-z]{2}$")
        for week in data["calendar_weeks"]:
            assert pattern.match(week["label"]), (
                f"Label '{week['label']}' does not match 'CW[N] | D Mon' format"
            )

    def test_skipped_rows_present(self, client):
        data = client.get("/api/dashboard").get_json()
        assert "skipped_rows" in data
        assert len(data["skipped_rows"]) == 1

    def test_initial_no_dependencies(self, client):
        data = client.get("/api/dashboard").get_json()
        assert data["dependencies"] == []

    def test_initial_no_member_is_bottleneck(self, client):
        data = client.get("/api/dashboard").get_json()
        for m in data["members"]:
            assert m["is_bottleneck"] is False

    def test_member_fields_present(self, client):
        data = client.get("/api/dashboard").get_json()
        for m in data["members"]:
            assert "name" in m
            assert "is_bottleneck" in m
            assert "merged_blocks" in m
            assert "deadlock_weeks" in m
            assert "clusters" in m

    def test_is_migration_member_field_present(self, client):
        data = client.get("/api/dashboard").get_json()
        for m in data["members"]:
            assert "is_migration_member" in m, f"{m['name']} missing is_migration_member"

    def test_migration_members_have_true_flag(self, client):
        data = client.get("/api/dashboard").get_json()
        migration_names = {"Alice", "Bob", "Carol"}
        for m in data["members"]:
            if m["name"] in migration_names:
                assert m["is_migration_member"] is True

    def test_non_migration_members_have_false_flag(self, client):
        data = client.get("/api/dashboard").get_json()
        non_migration_names = {"Dave", "Eve"}
        for m in data["members"]:
            if m["name"] in non_migration_names:
                assert m["is_migration_member"] is False

    def test_all_five_members_returned(self, client):
        data = client.get("/api/dashboard").get_json()
        names = {m["name"] for m in data["members"]}
        assert "Dave" in names
        assert "Eve" in names


# ---------------------------------------------------------------------------
# POST /api/dependencies  (T022 / US2)
# ---------------------------------------------------------------------------

class TestPostDependencies:
    def test_add_single_pool_returns_201(self, client):
        rv = client.post("/api/dependencies",
                         json={"from_member": "Alice", "to_members": ["Bob"]})
        assert rv.status_code == 201

    def test_add_multi_pool_returns_201(self, client):
        rv = client.post("/api/dependencies",
                         json={"from_member": "Alice", "to_members": ["Bob", "Carol"]})
        assert rv.status_code == 201

    def test_add_dependency_appears_in_response(self, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_members": ["Bob"]})
        data = client.get("/api/dashboard").get_json()
        deps = data["dependencies"]
        assert any(
            d["from_member"] == "Alice" and d["to_members"] == ["Bob"]
            for d in deps
        )

    def test_unknown_source_returns_400(self, client):
        rv = client.post("/api/dependencies",
                         json={"from_member": "Unknown", "to_members": ["Bob"]})
        assert rv.status_code == 400

    def test_unknown_pool_member_returns_400(self, client):
        rv = client.post("/api/dependencies",
                         json={"from_member": "Alice", "to_members": ["Unknown"]})
        assert rv.status_code == 400

    def test_empty_pool_returns_400(self, client):
        rv = client.post("/api/dependencies",
                         json={"from_member": "Alice", "to_members": []})
        assert rv.status_code == 400

    def test_duplicate_returns_409(self, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_members": ["Bob"]})
        rv = client.post("/api/dependencies", json={"from_member": "Alice", "to_members": ["Bob"]})
        assert rv.status_code == 409

    def test_state_persisted_after_add(self, app, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_members": ["Bob"]})
        state = app.config["STATE"]
        assert any(
            d["from_member"] == "Alice" and d["to_members"] == ["Bob"]
            for d in state.dependencies
        )


class TestDeleteDependencies:
    def test_delete_existing_returns_200(self, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_members": ["Bob"]})
        rv = client.delete("/api/dependencies",
                           json={"from_member": "Alice", "to_members": ["Bob"]})
        assert rv.status_code == 200

    def test_delete_removes_from_state(self, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_members": ["Bob"]})
        client.delete("/api/dependencies", json={"from_member": "Alice", "to_members": ["Bob"]})
        data = client.get("/api/dashboard").get_json()
        assert not any(
            d["from_member"] == "Alice" and "Bob" in d["to_members"]
            for d in data["dependencies"]
        )

    def test_delete_nonexistent_returns_404(self, client):
        rv = client.delete("/api/dependencies",
                           json={"from_member": "Alice", "to_members": ["Bob"]})
        assert rv.status_code == 404


# ---------------------------------------------------------------------------
# Bottleneck via dashboard  (T026 / US3)
# ---------------------------------------------------------------------------

class TestBottleneck:
    def test_sole_satisfier_is_bottleneck(self, client):
        # Alice depends on [Bob] only; Bob is present in most CWs → sole satisfier → weight > 0
        client.post("/api/dependencies", json={"from_member": "Alice", "to_members": ["Bob"]})
        data = client.get("/api/dashboard").get_json()
        bob = get_member(data, "Bob")
        assert bob["is_bottleneck"] is True

    def test_shared_pool_not_bottleneck_for_both_present(self, client):
        # Alice→[Bob, Carol]; Carol always present, Bob too (most CWs) → neither sole satisfier
        client.post("/api/dependencies",
                    json={"from_member": "Alice", "to_members": ["Bob", "Carol"]})
        data = client.get("/api/dashboard").get_json()
        bob = get_member(data, "Bob")
        assert bob["is_bottleneck"] is False

    def test_no_deps_no_bottleneck(self, client):
        data = client.get("/api/dashboard").get_json()
        for m in data["members"]:
            assert m["is_bottleneck"] is False


# ---------------------------------------------------------------------------
# Cluster endpoints  (T029 / US4)
# ---------------------------------------------------------------------------

class TestPostClusters:
    def test_create_cluster_returns_201(self, client):
        rv = client.post("/api/clusters",
                         json={"name": "Backend", "members": ["Alice", "Bob"]})
        assert rv.status_code == 201

    def test_cluster_appears_in_dashboard(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        data = client.get("/api/dashboard").get_json()
        alice = get_member(data, "Alice")
        assert "Backend" in alice["clusters"]

    def test_duplicate_cluster_name_returns_400(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        rv = client.post("/api/clusters", json={"name": "Backend", "members": ["Bob"]})
        assert rv.status_code == 400

    def test_unknown_member_returns_400(self, client):
        rv = client.post("/api/clusters",
                         json={"name": "Backend", "members": ["Unknown"]})
        assert rv.status_code == 400


class TestPutClusters:
    def test_update_cluster_members(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        rv = client.put("/api/clusters/Backend", json={"members": ["Alice", "Bob"]})
        assert rv.status_code == 200
        data = client.get("/api/dashboard").get_json()
        bob = get_member(data, "Bob")
        assert "Backend" in bob["clusters"]

    def test_update_unknown_cluster_returns_404(self, client):
        rv = client.put("/api/clusters/Nonexistent", json={"members": ["Alice"]})
        assert rv.status_code == 404

    def test_update_with_unknown_member_returns_400(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        rv = client.put("/api/clusters/Backend", json={"members": ["Unknown"]})
        assert rv.status_code == 400


class TestDeleteClusters:
    def test_delete_existing_cluster_returns_200(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        rv = client.delete("/api/clusters/Backend")
        assert rv.status_code == 200

    def test_delete_removes_cluster_from_dashboard(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        client.delete("/api/clusters/Backend")
        data = client.get("/api/dashboard").get_json()
        alice = get_member(data, "Alice")
        assert "Backend" not in alice["clusters"]

    def test_delete_unknown_cluster_returns_404(self, client):
        rv = client.delete("/api/clusters/Nonexistent")
        assert rv.status_code == 404


class TestMemberInMultipleClusters:
    def test_member_in_two_clusters_appears_in_both(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        client.post("/api/clusters", json={"name": "DevOps", "members": ["Alice"]})
        data = client.get("/api/dashboard").get_json()
        alice = get_member(data, "Alice")
        assert "Backend" in alice["clusters"]
        assert "DevOps" in alice["clusters"]


# ---------------------------------------------------------------------------
# GET /api/dependencies, GET /api/clusters  (T037, T038 / Polish)
# ---------------------------------------------------------------------------

class TestGetEndpoints:
    def test_get_dependencies_returns_200(self, client):
        rv = client.get("/api/dependencies")
        assert rv.status_code == 200
        assert "dependencies" in rv.get_json()

    def test_get_clusters_returns_200(self, client):
        rv = client.get("/api/clusters")
        assert rv.status_code == 200
        assert "clusters" in rv.get_json()


# ---------------------------------------------------------------------------
# POST /api/refresh  (T034 / US5)
# ---------------------------------------------------------------------------

class TestRefresh:
    def test_refresh_returns_200(self, client):
        rv = client.post("/api/refresh")
        assert rv.status_code == 200

    def test_refresh_preserves_dependencies(self, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_members": ["Bob"]})
        client.post("/api/refresh")
        data = client.get("/api/dashboard").get_json()
        assert any(
            d["from_member"] == "Alice" and d["to_members"] == ["Bob"]
            for d in data["dependencies"]
        )

    def test_refresh_preserves_clusters(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        client.post("/api/refresh")
        data = client.get("/api/dashboard").get_json()
        alice = get_member(data, "Alice")
        assert "Backend" in alice["clusters"]

    def test_refresh_stale_dependency_removed(self, app, client, tmp_path, monkeypatch):
        # Add a dependency, then replace the Excel with a file that has no "Alice"
        client.post("/api/dependencies", json={"from_member": "Alice", "to_members": ["Bob"]})
        # Build a minimal workbook with only Bob and Carol
        from openpyxl import Workbook
        wb = Workbook()
        ws = wb.active
        ws.cell(row=1, column=6, value="KW18")
        ws.cell(row=2, column=6, value="Mo")
        ws.cell(row=3, column=3, value="x")
        ws.cell(row=3, column=4, value="Bob")
        ws.cell(row=4, column=3, value="x")
        ws.cell(row=4, column=4, value="Carol")
        new_path = tmp_path / "updated.xlsx"
        wb.save(str(new_path))
        # get_workbook() only accepts SharePoint (http/https) sources (feature 003) — mock the
        # fetch instead of pointing EXCEL_SOURCE at a local path (same technique as conftest.py's
        # app fixture).
        monkeypatch.setattr(
            "absence_dashboard.data_fetcher.requests.get",
            lambda *args, **kwargs: type(
                "_FakeResponse", (), {"content": new_path.read_bytes(), "status_code": 200}
            )(),
        )
        app.config["EXCEL_SOURCE"] = "https://fake.sharepoint.example/updated.xlsx?e=test"
        rv = client.post("/api/refresh")
        assert rv.status_code == 200
        result = rv.get_json()
        assert len(result.get("removed_stale_references", [])) > 0
        data = client.get("/api/dashboard").get_json()
        assert not any(
            d["from_member"] == "Alice" for d in data["dependencies"]
        )


class TestRefreshExpiredSession:
    """post_refresh() only attempts silent token renewal (no console to show a device
    code on from a browser-triggered request) — when that fails, it must return a clear
    "restart the dashboard" error, not an unhandled exception (feature 004, US3)."""

    def test_expired_session_returns_clear_restart_message(self, app, client, monkeypatch):
        def failing_acquire_token(client_id, tenant_id, cache_path, interactive_fallback=True):
            assert interactive_fallback is False
            raise RuntimeError("Signed-in session has expired. Restart the dashboard to sign in again.")

        monkeypatch.setattr("absence_dashboard.graph_auth.acquire_token", failing_acquire_token)

        rv = client.post("/api/refresh")

        assert rv.status_code != 200
        data = rv.get_json()
        assert "restart the dashboard" in data["error"].lower()


# ---------------------------------------------------------------------------
# Phase endpoints  (T047 / US6)
# ---------------------------------------------------------------------------

class TestGetPhases:
    def test_get_phases_returns_200(self, client):
        rv = client.get("/api/phases")
        assert rv.status_code == 200

    def test_get_phases_has_phases_key(self, client):
        rv = client.get("/api/phases")
        assert "phases" in rv.get_json()

    def test_initial_phases_empty(self, client):
        rv = client.get("/api/phases")
        assert rv.get_json()["phases"] == []


class TestPostPhases:
    def test_add_valid_phase_returns_201(self, client):
        rv = client.post("/api/phases",
                         json={"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        assert rv.status_code == 201

    def test_add_valid_phase_appears_in_list(self, client):
        client.post("/api/phases",
                    json={"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        rv = client.get("/api/phases")
        phases = rv.get_json()["phases"]
        assert any(p["name"] == "Go-Live" for p in phases)

    def test_add_phase_duplicate_name_returns_400(self, client):
        client.post("/api/phases",
                    json={"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        rv = client.post("/api/phases",
                         json={"name": "Go-Live", "start_date": "2026-07-01", "end_date": "2026-07-05"})
        assert rv.status_code == 400

    def test_add_phase_end_before_start_returns_400(self, client):
        rv = client.post("/api/phases",
                         json={"name": "BadPhase", "start_date": "2026-07-10", "end_date": "2026-07-05"})
        assert rv.status_code == 400

    def test_add_phase_single_day_returns_201(self, client):
        rv = client.post("/api/phases",
                         json={"name": "Kickoff", "start_date": "2026-06-01", "end_date": "2026-06-01"})
        assert rv.status_code == 201

    def test_add_phase_overlapping_allowed(self, client):
        client.post("/api/phases",
                    json={"name": "Sprint 10", "start_date": "2026-06-15", "end_date": "2026-06-26"})
        rv = client.post("/api/phases",
                         json={"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        assert rv.status_code == 201


class TestDeletePhase:
    def test_delete_existing_phase_returns_200(self, client):
        client.post("/api/phases",
                    json={"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        rv = client.delete("/api/phases/Go-Live")
        assert rv.status_code == 200

    def test_delete_removes_phase(self, client):
        client.post("/api/phases",
                    json={"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        client.delete("/api/phases/Go-Live")
        rv = client.get("/api/phases")
        phases = rv.get_json()["phases"]
        assert not any(p["name"] == "Go-Live" for p in phases)

    def test_delete_nonexistent_phase_returns_404(self, client):
        rv = client.delete("/api/phases/Nonexistent")
        assert rv.status_code == 404

    def test_delete_url_encoded_name(self, client):
        client.post("/api/phases",
                    json={"name": "Go Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        import urllib.parse
        encoded = urllib.parse.quote("Go Live")
        rv = client.delete(f"/api/phases/{encoded}")
        assert rv.status_code == 200


class TestDashboardIncludesPhases:
    def test_dashboard_has_phases_key(self, client):
        data = client.get("/api/dashboard").get_json()
        assert "phases" in data

    def test_dashboard_phases_initially_empty(self, client):
        data = client.get("/api/dashboard").get_json()
        assert data["phases"] == []

    def test_dashboard_reflects_added_phase(self, client):
        client.post("/api/phases",
                    json={"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        data = client.get("/api/dashboard").get_json()
        assert any(p["name"] == "Go-Live" for p in data["phases"])


class TestRefreshPreservesPhases:
    def test_refresh_preserves_phases(self, client):
        client.post("/api/phases",
                    json={"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        client.post("/api/refresh")
        data = client.get("/api/dashboard").get_json()
        assert any(p["name"] == "Go-Live" for p in data["phases"])


# ---------------------------------------------------------------------------
# PUT /api/dependencies  (T056 / Phase 11)
# ---------------------------------------------------------------------------

class TestPutDependencies:
    def test_valid_replace_returns_200(self, client):
        client.post("/api/dependencies",
                    json={"from_member": "Alice", "to_members": ["Bob"]})
        rv = client.put("/api/dependencies",
                        json={"old_from": "Alice", "old_to_members": ["Bob"],
                              "new_from": "Alice", "new_to_members": ["Carol"]})
        assert rv.status_code == 200

    def test_valid_replace_updates_list(self, client):
        client.post("/api/dependencies",
                    json={"from_member": "Alice", "to_members": ["Bob"]})
        client.put("/api/dependencies",
                   json={"old_from": "Alice", "old_to_members": ["Bob"],
                         "new_from": "Alice", "new_to_members": ["Carol"]})
        data = client.get("/api/dependencies").get_json()
        deps = data["dependencies"]
        assert any(d["from_member"] == "Alice" and d["to_members"] == ["Carol"] for d in deps)
        assert not any(d["from_member"] == "Alice" and d["to_members"] == ["Bob"] for d in deps)

    def test_old_pair_not_found_returns_404(self, client):
        rv = client.put("/api/dependencies",
                        json={"old_from": "Alice", "old_to_members": ["Bob"],
                              "new_from": "Alice", "new_to_members": ["Carol"]})
        assert rv.status_code == 404

    def test_duplicate_new_pair_returns_409(self, client):
        client.post("/api/dependencies",
                    json={"from_member": "Alice", "to_members": ["Bob"]})
        client.post("/api/dependencies",
                    json={"from_member": "Carol", "to_members": ["Bob"]})
        rv = client.put("/api/dependencies",
                        json={"old_from": "Carol", "old_to_members": ["Bob"],
                              "new_from": "Alice", "new_to_members": ["Bob"]})
        assert rv.status_code == 409

    def test_invalid_member_returns_400(self, client):
        client.post("/api/dependencies",
                    json={"from_member": "Alice", "to_members": ["Bob"]})
        rv = client.put("/api/dependencies",
                        json={"old_from": "Alice", "old_to_members": ["Bob"],
                              "new_from": "Alice", "new_to_members": ["Unknown"]})
        assert rv.status_code == 400

    def test_state_persisted_after_replace(self, app, client):
        client.post("/api/dependencies",
                    json={"from_member": "Alice", "to_members": ["Bob"]})
        client.put("/api/dependencies",
                   json={"old_from": "Alice", "old_to_members": ["Bob"],
                         "new_from": "Alice", "new_to_members": ["Carol"]})
        state = app.config["STATE"]
        assert any(
            d["from_member"] == "Alice" and d["to_members"] == ["Carol"]
            for d in state.dependencies
        )
        assert not any(
            d["from_member"] == "Alice" and d["to_members"] == ["Bob"]
            for d in state.dependencies
        )


# ---------------------------------------------------------------------------
# PUT /api/clusters/<name> with rename  (T057 / Phase 11)
# ---------------------------------------------------------------------------

class TestPutClustersWithRename:
    def test_rename_only_returns_200(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        rv = client.put("/api/clusters/Backend", json={"name": "Core"})
        assert rv.status_code == 200

    def test_rename_updates_cluster_name(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        client.put("/api/clusters/Backend", json={"name": "Core"})
        data = client.get("/api/clusters").get_json()
        names = [c["name"] for c in data["clusters"]]
        assert "Core" in names
        assert "Backend" not in names

    def test_rename_preserves_members(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice", "Bob"]})
        client.put("/api/clusters/Backend", json={"name": "Core"})
        data = client.get("/api/clusters").get_json()
        core = next(c for c in data["clusters"] if c["name"] == "Core")
        assert set(core["members"]) == {"Alice", "Bob"}

    def test_update_members_only_returns_200(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        rv = client.put("/api/clusters/Backend", json={"members": ["Alice", "Carol"]})
        assert rv.status_code == 200

    def test_update_members_only_preserves_name(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        client.put("/api/clusters/Backend", json={"members": ["Alice", "Carol"]})
        data = client.get("/api/clusters").get_json()
        assert any(c["name"] == "Backend" for c in data["clusters"])

    def test_rename_and_update_members(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        rv = client.put("/api/clusters/Backend", json={"name": "Core", "members": ["Carol"]})
        assert rv.status_code == 200
        data = client.get("/api/clusters").get_json()
        core = next(c for c in data["clusters"] if c["name"] == "Core")
        assert core["members"] == ["Carol"]

    def test_rename_to_duplicate_name_returns_400(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        client.post("/api/clusters", json={"name": "Frontend", "members": ["Bob"]})
        rv = client.put("/api/clusters/Backend", json={"name": "Frontend"})
        assert rv.status_code == 400

    def test_rename_to_same_name_is_ok(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        rv = client.put("/api/clusters/Backend", json={"name": "Backend"})
        assert rv.status_code == 200

    def test_unknown_cluster_returns_404(self, client):
        rv = client.put("/api/clusters/Nonexistent", json={"name": "X"})
        assert rv.status_code == 404

    def test_invalid_member_returns_400(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        rv = client.put("/api/clusters/Backend", json={"members": ["Unknown"]})
        assert rv.status_code == 400

    def test_dashboard_reflects_rename(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        client.put("/api/clusters/Backend", json={"name": "Core"})
        data = client.get("/api/dashboard").get_json()
        alice = get_member(data, "Alice")
        assert "Core" in alice["clusters"]
        assert "Backend" not in alice["clusters"]


# ---------------------------------------------------------------------------
# PUT /api/phases/<name>  (T058 / Phase 11)
# ---------------------------------------------------------------------------

class TestPutPhases:
    def test_update_name_only_returns_200(self, client):
        client.post("/api/phases",
                    json={"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        rv = client.put("/api/phases/Go-Live", json={"name": "Launch"})
        assert rv.status_code == 200

    def test_update_name_only_renames_phase(self, client):
        client.post("/api/phases",
                    json={"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        client.put("/api/phases/Go-Live", json={"name": "Launch"})
        phases = client.get("/api/phases").get_json()["phases"]
        names = [p["name"] for p in phases]
        assert "Launch" in names
        assert "Go-Live" not in names

    def test_update_dates_only_returns_200(self, client):
        client.post("/api/phases",
                    json={"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        rv = client.put("/api/phases/Go-Live",
                        json={"start_date": "2026-06-23", "end_date": "2026-06-27"})
        assert rv.status_code == 200

    def test_update_dates_only_changes_dates(self, client):
        client.post("/api/phases",
                    json={"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        client.put("/api/phases/Go-Live",
                   json={"start_date": "2026-06-23", "end_date": "2026-06-27"})
        phases = client.get("/api/phases").get_json()["phases"]
        go_live = next(p for p in phases if p["name"] == "Go-Live")
        assert go_live["start_date"] == "2026-06-23"
        assert go_live["end_date"] == "2026-06-27"

    def test_update_all_fields(self, client):
        client.post("/api/phases",
                    json={"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        rv = client.put("/api/phases/Go-Live",
                        json={"name": "Launch", "start_date": "2026-07-01",
                              "end_date": "2026-07-05"})
        assert rv.status_code == 200
        phases = client.get("/api/phases").get_json()["phases"]
        launch = next(p for p in phases if p["name"] == "Launch")
        assert launch["start_date"] == "2026-07-01"
        assert launch["end_date"] == "2026-07-05"

    def test_duplicate_name_returns_400(self, client):
        client.post("/api/phases",
                    json={"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        client.post("/api/phases",
                    json={"name": "Sprint 10", "start_date": "2026-06-15", "end_date": "2026-06-21"})
        rv = client.put("/api/phases/Go-Live", json={"name": "Sprint 10"})
        assert rv.status_code == 400

    def test_end_before_start_returns_400(self, client):
        client.post("/api/phases",
                    json={"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        rv = client.put("/api/phases/Go-Live",
                        json={"start_date": "2026-07-10", "end_date": "2026-07-05"})
        assert rv.status_code == 400

    def test_unknown_phase_returns_404(self, client):
        rv = client.put("/api/phases/Nonexistent", json={"name": "X"})
        assert rv.status_code == 404

    def test_state_persisted_after_update(self, app, client):
        client.post("/api/phases",
                    json={"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        client.put("/api/phases/Go-Live", json={"name": "Launch"})
        state = app.config["STATE"]
        assert any(p["name"] == "Launch" for p in state.phases)
        assert not any(p["name"] == "Go-Live" for p in state.phases)

    def test_dashboard_reflects_phase_update(self, client):
        client.post("/api/phases",
                    json={"name": "Go-Live", "start_date": "2026-06-22", "end_date": "2026-06-26"})
        client.put("/api/phases/Go-Live", json={"name": "Launch"})
        data = client.get("/api/dashboard").get_json()
        assert any(p["name"] == "Launch" for p in data["phases"])
        assert not any(p["name"] == "Go-Live" for p in data["phases"])


# ---------------------------------------------------------------------------
# last_loaded timestamp  (T068 / FR-025)
# ---------------------------------------------------------------------------

class TestLastLoaded:
    def test_dashboard_has_last_loaded(self, client):
        data = client.get("/api/dashboard").get_json()
        assert "last_loaded" in data

    def test_last_loaded_is_iso_datetime_string(self, client):
        from datetime import datetime
        data = client.get("/api/dashboard").get_json()
        ll = data["last_loaded"]
        assert isinstance(ll, str)
        dt = datetime.strptime(ll, "%Y-%m-%dT%H:%M:%S")
        assert dt is not None

    def test_refresh_includes_last_loaded(self, client):
        rv = client.post("/api/refresh")
        assert rv.status_code == 200
        data = rv.get_json()
        assert "last_loaded" in data

    def test_refresh_last_loaded_is_iso_datetime_string(self, client):
        from datetime import datetime
        rv = client.post("/api/refresh")
        ll = rv.get_json()["last_loaded"]
        dt = datetime.strptime(ll, "%Y-%m-%dT%H:%M:%S")
        assert dt is not None

    def test_refresh_last_loaded_not_earlier_than_initial(self, client):
        data1 = client.get("/api/dashboard").get_json()
        ll1 = data1["last_loaded"]
        data2 = client.post("/api/refresh").get_json()
        ll2 = data2["last_loaded"]
        assert ll2 >= ll1


# ---------------------------------------------------------------------------
# Pool-based dependencies  (T086 / Phase 15)
# ---------------------------------------------------------------------------

class TestPoolDependenciesAPI:
    def test_post_multi_pool_returns_201(self, client):
        rv = client.post("/api/dependencies", json={
            "from_member": "Alice", "to_members": ["Bob", "Carol"],
        })
        assert rv.status_code == 201

    def test_post_date_range_stored_on_pool_entry(self, client):
        client.post("/api/dependencies", json={
            "from_member": "Alice", "to_members": ["Bob"],
            "active_from": "2026-06-01", "active_to": "2026-06-30",
        })
        deps = client.get("/api/dependencies").get_json()["dependencies"]
        match = next((d for d in deps if d["from_member"] == "Alice"), None)
        assert match is not None
        assert match["active_from"] == "2026-06-01"
        assert match["active_to"] == "2026-06-30"

    def test_post_only_active_from_returns_400(self, client):
        rv = client.post("/api/dependencies", json={
            "from_member": "Alice", "to_members": ["Bob"],
            "active_from": "2026-06-01",
        })
        assert rv.status_code == 400

    def test_post_active_from_after_active_to_returns_400(self, client):
        rv = client.post("/api/dependencies", json={
            "from_member": "Alice", "to_members": ["Bob"],
            "active_from": "2026-07-01", "active_to": "2026-06-30",
        })
        assert rv.status_code == 400

    def test_same_pool_different_date_ranges_both_accepted(self, client):
        rv1 = client.post("/api/dependencies", json={
            "from_member": "Alice", "to_members": ["Bob"],
            "active_from": "2026-06-01", "active_to": "2026-06-30",
        })
        rv2 = client.post("/api/dependencies", json={
            "from_member": "Alice", "to_members": ["Bob"],
            "active_from": "2026-09-01", "active_to": "2026-09-30",
        })
        assert rv1.status_code == 201
        assert rv2.status_code == 201
        deps = client.get("/api/dependencies").get_json()["dependencies"]
        alice_deps = [d for d in deps if d["from_member"] == "Alice"]
        assert len(alice_deps) == 2

    def test_identical_pool_tuple_returns_409(self, client):
        client.post("/api/dependencies", json={
            "from_member": "Alice", "to_members": ["Bob"],
            "active_from": "2026-06-01", "active_to": "2026-06-30",
        })
        rv = client.post("/api/dependencies", json={
            "from_member": "Alice", "to_members": ["Bob"],
            "active_from": "2026-06-01", "active_to": "2026-06-30",
        })
        assert rv.status_code == 409

    def test_delete_removes_correct_pool_tuple_only(self, client):
        client.post("/api/dependencies", json={
            "from_member": "Alice", "to_members": ["Bob"],
            "active_from": "2026-06-01", "active_to": "2026-06-30",
        })
        client.post("/api/dependencies", json={
            "from_member": "Alice", "to_members": ["Bob"],
            "active_from": "2026-09-01", "active_to": "2026-09-30",
        })
        rv = client.delete("/api/dependencies", json={
            "from_member": "Alice", "to_members": ["Bob"],
            "active_from": "2026-06-01", "active_to": "2026-06-30",
        })
        assert rv.status_code == 200
        deps = rv.get_json()["dependencies"]
        alice_deps = [d for d in deps if d["from_member"] == "Alice"]
        assert len(alice_deps) == 1
        assert alice_deps[0]["active_from"] == "2026-09-01"

    def test_dashboard_has_deadlock_weeks_not_at_risk(self, client):
        data = client.get("/api/dashboard").get_json()
        for m in data["members"]:
            assert "deadlock_weeks" in m
            assert "at_risk_weeks" not in m

    def test_dashboard_deadlock_weeks_field_present(self, client):
        # deadlock_weeks must be present and a list for every member
        client.post("/api/dependencies", json={"from_member": "Alice", "to_members": ["Bob"]})
        data = client.get("/api/dashboard").get_json()
        for m in data["members"]:
            assert isinstance(m["deadlock_weeks"], list)

    def test_dashboard_no_deadlock_when_partial_pool_absent(self, client):
        # Alice→[Bob, Carol]; Carol has no absences → never deadlock
        client.post("/api/dependencies",
                    json={"from_member": "Alice", "to_members": ["Bob", "Carol"]})
        data = client.get("/api/dashboard").get_json()
        alice = next(m for m in data["members"] if m["name"] == "Alice")
        assert alice["deadlock_weeks"] == []

    def test_is_bottleneck_sole_satisfier(self, client):
        # Alice→[Bob]: Bob present in most CWs → weight > 0 → is_bottleneck=true
        client.post("/api/dependencies", json={"from_member": "Alice", "to_members": ["Bob"]})
        data = client.get("/api/dashboard").get_json()
        bob = next(m for m in data["members"] if m["name"] == "Bob")
        assert bob["is_bottleneck"] is True

    def test_put_pool_dependency_replaces_correctly(self, client):
        client.post("/api/dependencies", json={
            "from_member": "Alice", "to_members": ["Bob"],
            "active_from": "2026-06-01", "active_to": "2026-06-30",
        })
        rv = client.put("/api/dependencies", json={
            "old_from": "Alice", "old_to_members": ["Bob"],
            "old_active_from": "2026-06-01", "old_active_to": "2026-06-30",
            "new_from": "Alice", "new_to_members": ["Carol"],
            "new_active_from": "2026-07-01", "new_active_to": "2026-07-31",
        })
        assert rv.status_code == 200
        deps = rv.get_json()["dependencies"]
        assert not any(
            d["from_member"] == "Alice" and "Bob" in d["to_members"]
            for d in deps
        )
        new_dep = next(d for d in deps if d["from_member"] == "Alice")
        assert new_dep["to_members"] == ["Carol"]
        assert new_dep["active_from"] == "2026-07-01"


# ---------------------------------------------------------------------------
# resolve_launch_source() — CLI arg vs launch_config.json precedence (feature 002)
# ---------------------------------------------------------------------------

class TestResolveLaunchSource:
    """resolve_launch_source() always reads launch_config.json for client_id/tenant_id
    (feature 004) — there is no CLI-argument equivalent for them (contracts/launch-config.md).
    Only the file source itself may be overridden by the CLI argument."""

    CLIENT_ID = "11111111-1111-1111-1111-111111111111"
    TENANT_ID = "22222222-2222-2222-2222-222222222222"

    def _write_config(self, tmp_path, **overrides):
        data = {
            "excel_source": "https://config.example.com/share?e=1",
            "client_id": self.CLIENT_ID,
            "tenant_id": self.TENANT_ID,
        }
        data.update(overrides)
        path = tmp_path / "launch_config.json"
        path.write_text(json.dumps(data))
        return str(path)

    def test_cli_arg_takes_precedence_over_launch_config_source(self, tmp_path):
        config_path = self._write_config(tmp_path, port=9999)

        from absence_dashboard.app import resolve_launch_source
        source, client_id, tenant_id, port = resolve_launch_source(
            "https://cli.example.com/share?e=1", None, config_path=config_path
        )

        assert source == "https://cli.example.com/share?e=1"
        # launch_config.json is now always read (for client_id/tenant_id), so its port
        # applies too unless an explicit --port flag overrides it (see next test).
        assert port == 9999
        # client_id/tenant_id still come from launch_config.json even when the CLI
        # argument overrides the file source — there's no CLI equivalent for them.
        assert client_id == self.CLIENT_ID
        assert tenant_id == self.TENANT_ID

    def test_no_cli_arg_falls_back_to_launch_config(self, tmp_path):
        config_path = self._write_config(
            tmp_path, excel_source="https://example.com/share?e=1", port=6100
        )

        from absence_dashboard.app import resolve_launch_source
        source, client_id, tenant_id, port = resolve_launch_source(None, None, config_path=config_path)

        assert source == "https://example.com/share?e=1"
        assert port == 6100
        assert client_id == self.CLIENT_ID
        assert tenant_id == self.TENANT_ID

    def test_explicit_cli_port_overrides_launch_config_port(self, tmp_path):
        config_path = self._write_config(tmp_path, port=6100)

        from absence_dashboard.app import resolve_launch_source
        _, _, _, port = resolve_launch_source(None, 7000, config_path=config_path)

        assert port == 7000

    def test_no_cli_arg_and_missing_launch_config_raises(self, tmp_path):
        config_path = tmp_path / "missing.json"

        from absence_dashboard.app import resolve_launch_source
        with pytest.raises(FileNotFoundError):
            resolve_launch_source(None, None, config_path=str(config_path))

    def test_existing_local_cli_path_rejected(self, tmp_path):
        # Local-file support was removed (feature 003) — even an existing local path
        # supplied via the CLI must be rejected, not silently accepted as it is today.
        cli_xlsx = tmp_path / "cli.xlsx"
        cli_xlsx.write_text("dummy")
        config_path = self._write_config(tmp_path)

        from absence_dashboard.app import resolve_launch_source
        with pytest.raises(FileNotFoundError, match="local-file support has been removed"):
            resolve_launch_source(str(cli_xlsx), None, config_path=config_path)

    def test_nonexistent_local_cli_path_rejected(self, tmp_path):
        config_path = self._write_config(tmp_path)

        from absence_dashboard.app import resolve_launch_source
        with pytest.raises(FileNotFoundError, match="local-file support has been removed"):
            resolve_launch_source(
                str(tmp_path / "does_not_exist.xlsx"), None, config_path=config_path
            )

    def test_local_launch_config_source_rejected(self, tmp_path):
        # No CLI arg given; launch_config.json itself has a local (not URL) excel_source.
        xlsx = tmp_path / "absences.xlsx"
        xlsx.write_text("dummy")
        config_path = self._write_config(tmp_path, excel_source=str(xlsx))

        from absence_dashboard.app import resolve_launch_source
        with pytest.raises(FileNotFoundError, match="local-file support has been removed"):
            resolve_launch_source(None, None, config_path=config_path)


# ---------------------------------------------------------------------------
# main() startup — token acquisition happens before create_app() (feature 004, US1)
# ---------------------------------------------------------------------------

class TestMainStartupTokenFlow:
    CLIENT_ID = "11111111-1111-1111-1111-111111111111"
    TENANT_ID = "22222222-2222-2222-2222-222222222222"

    def _write_config(self, tmp_path, **overrides):
        data = {
            "excel_source": "https://example.com/share?e=1",
            "client_id": self.CLIENT_ID,
            "tenant_id": self.TENANT_ID,
            "port": 5002,
        }
        data.update(overrides)
        path = tmp_path / "launch_config.json"
        path.write_text(json.dumps(data))
        return path

    def test_token_acquired_before_create_app(self, tmp_path, monkeypatch):
        self._write_config(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["run.py"])

        call_order = []
        fake_app = MagicMock()

        def fake_acquire_token(client_id, tenant_id, cache_path, interactive_fallback=True):
            call_order.append("acquire_token")
            assert client_id == self.CLIENT_ID
            assert tenant_id == self.TENANT_ID
            return "token-abc"

        def fake_create_app(source, access_token, client_id, tenant_id, state_path="state/state.json"):
            call_order.append("create_app")
            assert access_token == "token-abc"
            assert client_id == self.CLIENT_ID
            assert tenant_id == self.TENANT_ID
            return fake_app

        from absence_dashboard import app as app_module
        monkeypatch.setattr(app_module.graph_auth, "acquire_token", fake_acquire_token)
        monkeypatch.setattr(app_module, "create_app", fake_create_app)

        app_module.main()

        assert call_order == ["acquire_token", "create_app"]
        fake_app.run.assert_called_once()

    def test_token_acquisition_failure_exits_cleanly(self, tmp_path, monkeypatch, capsys):
        self._write_config(tmp_path)
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(sys, "argv", ["run.py"])

        from absence_dashboard import app as app_module

        def failing_acquire_token(*args, **kwargs):
            raise RuntimeError("Signed-in session has expired. Restart the dashboard to sign in again.")

        create_app_called = []
        monkeypatch.setattr(app_module.graph_auth, "acquire_token", failing_acquire_token)
        monkeypatch.setattr(app_module, "create_app", lambda *a, **k: create_app_called.append(1))

        with pytest.raises(SystemExit) as exc_info:
            app_module.main()

        assert exc_info.value.code == 1
        assert not create_app_called
        captured = capsys.readouterr()
        assert "restart the dashboard" in captured.err.lower()
