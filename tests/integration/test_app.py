"""
Integration tests for absence_dashboard/app.py Flask routes.
TDD: Written BEFORE implementation; confirmed failing before app.py is complete.
"""
import json
import pytest
from datetime import date


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

    def test_exactly_three_members(self, client):
        data = client.get("/api/dashboard").get_json()
        assert len(data["members"]) == 3

    def test_member_names_correct(self, client):
        data = client.get("/api/dashboard").get_json()
        names = {m["name"] for m in data["members"]}
        assert names == {"Alice", "Bob", "Carol"}

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

    def test_initial_no_bottlenecks(self, client):
        data = client.get("/api/dashboard").get_json()
        assert data["bottlenecks"] == []

    def test_member_fields_present(self, client):
        data = client.get("/api/dashboard").get_json()
        for m in data["members"]:
            assert "name" in m
            assert "is_bottleneck" in m
            assert "merged_blocks" in m
            assert "at_risk_weeks" in m
            assert "depends_on" in m
            assert "clusters" in m


# ---------------------------------------------------------------------------
# POST /api/dependencies  (T022 / US2)
# ---------------------------------------------------------------------------

class TestPostDependencies:
    def test_add_valid_dependency_returns_201(self, client):
        rv = client.post("/api/dependencies",
                         json={"from_member": "Alice", "to_member": "Bob"})
        assert rv.status_code == 201

    def test_add_valid_dependency_in_response(self, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        data = client.get("/api/dashboard").get_json()
        assert {"from_member": "Alice", "to_member": "Bob"} in data["dependencies"]

    def test_unknown_source_returns_400(self, client):
        rv = client.post("/api/dependencies",
                         json={"from_member": "Unknown", "to_member": "Bob"})
        assert rv.status_code == 400

    def test_unknown_target_returns_400(self, client):
        rv = client.post("/api/dependencies",
                         json={"from_member": "Alice", "to_member": "Unknown"})
        assert rv.status_code == 400

    def test_cycle_returns_409(self, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        rv = client.post("/api/dependencies", json={"from_member": "Bob", "to_member": "Alice"})
        assert rv.status_code == 409
        assert "cycle" in rv.get_json().get("error", "").lower()

    def test_duplicate_returns_409(self, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        rv = client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        assert rv.status_code == 409

    def test_state_persisted_after_add(self, app, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        state = app.config["STATE"]
        assert {"from_member": "Alice", "to_member": "Bob"} in state.dependencies


class TestDeleteDependencies:
    def test_delete_existing_returns_200(self, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        rv = client.delete("/api/dependencies",
                           json={"from_member": "Alice", "to_member": "Bob"})
        assert rv.status_code == 200

    def test_delete_removes_from_state(self, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        client.delete("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        data = client.get("/api/dashboard").get_json()
        assert {"from_member": "Alice", "to_member": "Bob"} not in data["dependencies"]

    def test_delete_nonexistent_returns_404(self, client):
        rv = client.delete("/api/dependencies",
                           json={"from_member": "Alice", "to_member": "Bob"})
        assert rv.status_code == 404


# ---------------------------------------------------------------------------
# Bottleneck via dashboard  (T026 / US3)
# ---------------------------------------------------------------------------

class TestBottleneck:
    def test_member_with_two_incoming_marked_bottleneck(self, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        client.post("/api/dependencies", json={"from_member": "Carol", "to_member": "Bob"})
        data = client.get("/api/dashboard").get_json()
        assert "Bob" in data["bottlenecks"]
        bob = get_member(data, "Bob")
        assert bob["is_bottleneck"] is True

    def test_member_with_one_incoming_not_bottleneck(self, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        data = client.get("/api/dashboard").get_json()
        assert "Bob" not in data["bottlenecks"]

    def test_alice_carol_not_bottleneck_when_bob_is(self, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        client.post("/api/dependencies", json={"from_member": "Carol", "to_member": "Bob"})
        data = client.get("/api/dashboard").get_json()
        alice = get_member(data, "Alice")
        carol = get_member(data, "Carol")
        assert alice["is_bottleneck"] is False
        assert carol["is_bottleneck"] is False


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
        client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        client.post("/api/refresh")
        data = client.get("/api/dashboard").get_json()
        assert {"from_member": "Alice", "to_member": "Bob"} in data["dependencies"]

    def test_refresh_preserves_clusters(self, client):
        client.post("/api/clusters", json={"name": "Backend", "members": ["Alice"]})
        client.post("/api/refresh")
        data = client.get("/api/dashboard").get_json()
        alice = get_member(data, "Alice")
        assert "Backend" in alice["clusters"]

    def test_refresh_stale_dependency_removed(self, app, client, tmp_path):
        # Add a dependency, then replace the Excel with a file that has no "Alice"
        client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
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
        new_path = str(tmp_path / "updated.xlsx")
        wb.save(new_path)
        app.config["EXCEL_PATH"] = new_path
        rv = client.post("/api/refresh")
        assert rv.status_code == 200
        result = rv.get_json()
        assert len(result.get("removed_stale_references", [])) > 0
        data = client.get("/api/dashboard").get_json()
        assert {"from_member": "Alice", "to_member": "Bob"} not in data["dependencies"]


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
        client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        rv = client.put("/api/dependencies",
                        json={"old_from": "Alice", "old_to": "Bob",
                              "new_from": "Alice", "new_to": "Carol"})
        assert rv.status_code == 200

    def test_valid_replace_updates_list(self, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        client.put("/api/dependencies",
                   json={"old_from": "Alice", "old_to": "Bob",
                         "new_from": "Alice", "new_to": "Carol"})
        data = client.get("/api/dependencies").get_json()
        deps = data["dependencies"]
        assert {"from_member": "Alice", "to_member": "Carol"} in deps
        assert {"from_member": "Alice", "to_member": "Bob"} not in deps

    def test_old_pair_not_found_returns_404(self, client):
        rv = client.put("/api/dependencies",
                        json={"old_from": "Alice", "old_to": "Bob",
                              "new_from": "Alice", "new_to": "Carol"})
        assert rv.status_code == 404

    def test_cycle_returns_409(self, client):
        # Bob→Carol exists; replacing Alice→Bob with Carol→Bob creates Bob→Carol + Carol→Bob cycle
        client.post("/api/dependencies", json={"from_member": "Bob", "to_member": "Carol"})
        client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        rv = client.put("/api/dependencies",
                        json={"old_from": "Alice", "old_to": "Bob",
                              "new_from": "Carol", "new_to": "Bob"})
        assert rv.status_code == 409

    def test_duplicate_new_pair_returns_409(self, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        client.post("/api/dependencies", json={"from_member": "Carol", "to_member": "Bob"})
        rv = client.put("/api/dependencies",
                        json={"old_from": "Alice", "old_to": "Bob",
                              "new_from": "Carol", "new_to": "Bob"})
        assert rv.status_code == 409

    def test_invalid_member_returns_400(self, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        rv = client.put("/api/dependencies",
                        json={"old_from": "Alice", "old_to": "Bob",
                              "new_from": "Alice", "new_to": "Unknown"})
        assert rv.status_code == 400

    def test_state_persisted_after_replace(self, app, client):
        client.post("/api/dependencies", json={"from_member": "Alice", "to_member": "Bob"})
        client.put("/api/dependencies",
                   json={"old_from": "Alice", "old_to": "Bob",
                         "new_from": "Alice", "new_to": "Carol"})
        state = app.config["STATE"]
        assert {"from_member": "Alice", "to_member": "Carol"} in state.dependencies
        assert {"from_member": "Alice", "to_member": "Bob"} not in state.dependencies


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
