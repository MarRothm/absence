import os
import sys
from datetime import date, timedelta

from flask import Flask, jsonify, request

from absence_dashboard.parser import parse_members
from absence_dashboard.merger import merge_periods
from absence_dashboard.state import load_state, save_state, AppState
from absence_dashboard.graph import DependencyGraph, CycleError
from absence_dashboard.phases_manager import add_phase, remove_phase, update_phase


# ---------------------------------------------------------------------------
# Calendar week helpers
# ---------------------------------------------------------------------------

def _last_iso_week(year: int) -> int:
    return date(year, 12, 28).isocalendar().week


def _build_calendar_weeks(today: date = None) -> list:
    if today is None:
        today = date.today()
    last_week = _last_iso_week(2026)
    iso = today.isocalendar()
    year, week = iso.year, iso.week
    weeks = []
    while (year < 2026) or (year == 2026 and week <= last_week):
        monday = date.fromisocalendar(year, week, 1)
        friday = monday + timedelta(days=4)
        days = [(monday + timedelta(days=i)).isoformat() for i in range(5)]
        weeks.append({
            "year": year,
            "week_number": week,
            "label": f"CW{week} | {monday.day} {monday.strftime('%b')}",
            "start": monday.isoformat(),
            "end": friday.isoformat(),
            "days": days,
        })
        next_monday = monday + timedelta(weeks=1)
        next_iso = next_monday.isocalendar()
        year, week = next_iso.year, next_iso.week
    return weeks


# ---------------------------------------------------------------------------
# Excel loading helper
# ---------------------------------------------------------------------------

def _load_excel(excel_path: str) -> tuple:
    from openpyxl import load_workbook
    wb = load_workbook(excel_path, read_only=True, data_only=True)
    ws = wb.active
    members, skipped = parse_members(ws)
    wb.close()
    for m in members:
        m.merged_blocks = merge_periods(m.absence_days)
    return members, skipped


# ---------------------------------------------------------------------------
# Member sorting
# ---------------------------------------------------------------------------

def _sort_members(members_data: list, clusters: list) -> list:
    cluster_order = {c["name"]: i for i, c in enumerate(clusters)}

    def sort_key(m):
        mc = m["clusters"]
        if not mc:
            return (len(clusters), m["name"])
        first_idx = min(cluster_order.get(c, len(clusters)) for c in mc)
        return (first_idx, m["name"])

    return sorted(members_data, key=sort_key)


# ---------------------------------------------------------------------------
# Dashboard assembler
# ---------------------------------------------------------------------------

def _assemble_dashboard(app) -> dict:
    members = app.config["MEMBERS"]
    state = app.config["STATE"]
    calendar_weeks = _build_calendar_weeks()
    edges = state.dependencies
    bottlenecks = DependencyGraph.get_bottlenecks(edges)
    member_blocks_map = {m.name: m.merged_blocks for m in members}

    result_members = []
    for m in members:
        at_risk = DependencyGraph.compute_at_risk_weeks(
            m.name, edges, member_blocks_map, calendar_weeks
        )
        member_clusters = [c["name"] for c in state.clusters if m.name in c.get("members", [])]
        depends_on = [e["to_member"] for e in edges if e["from_member"] == m.name]
        result_members.append({
            "name": m.name,
            "is_bottleneck": m.name in bottlenecks,
            "merged_blocks": [
                {"start": b.start_date.isoformat(), "end": b.end_date.isoformat()}
                for b in m.merged_blocks
            ],
            "at_risk_weeks": at_risk,
            "depends_on": depends_on,
            "clusters": member_clusters,
        })

    result_members = _sort_members(result_members, state.clusters)

    return {
        "calendar_weeks": calendar_weeks,
        "members": result_members,
        "dependencies": edges,
        "skill_clusters": state.clusters,
        "bottlenecks": sorted(bottlenecks),
        "phases": state.phases,
        "skipped_rows": [
            {"row": s.row, "reason": s.reason}
            for s in app.config["SKIPPED_ROWS"]
        ],
    }


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app(excel_path: str, state_path: str = "state/state.json") -> Flask:
    app = Flask(__name__, static_folder="static")

    members, skipped = _load_excel(excel_path)
    app.config.update({
        "EXCEL_PATH": excel_path,
        "STATE_PATH": state_path,
        "MEMBERS": members,
        "SKIPPED_ROWS": skipped,
        "STATE": load_state(state_path),
    })

    # ------------------------------------------------------------------
    # Static / root
    # ------------------------------------------------------------------

    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    # ------------------------------------------------------------------
    # GET /api/dashboard
    # ------------------------------------------------------------------

    @app.route("/api/dashboard")
    def get_dashboard():
        return jsonify(_assemble_dashboard(app))

    # ------------------------------------------------------------------
    # POST /api/refresh
    # ------------------------------------------------------------------

    @app.route("/api/refresh", methods=["POST"])
    def post_refresh():
        try:
            members, skipped = _load_excel(app.config["EXCEL_PATH"])
        except Exception as e:
            return jsonify({"error": str(e), "stale_data": True}), 422

        new_names = {m.name for m in members}
        state = app.config["STATE"]
        removed = []

        new_deps = []
        for dep in state.dependencies:
            if dep["from_member"] not in new_names or dep["to_member"] not in new_names:
                removed.append({"type": "dependency", "entry": dep})
            else:
                new_deps.append(dep)
        state.dependencies = new_deps

        new_clusters = []
        for cluster in state.clusters:
            valid_members = [m for m in cluster.get("members", []) if m in new_names]
            removed_members = [m for m in cluster.get("members", []) if m not in new_names]
            for rm in removed_members:
                removed.append({
                    "type": "cluster_member",
                    "entry": {"cluster": cluster["name"], "member": rm},
                })
            new_clusters.append({"name": cluster["name"], "members": valid_members})
        state.clusters = new_clusters

        app.config["MEMBERS"] = members
        app.config["SKIPPED_ROWS"] = skipped
        save_state(state, app.config["STATE_PATH"])

        result = _assemble_dashboard(app)
        result["removed_stale_references"] = removed
        return jsonify(result)

    # ------------------------------------------------------------------
    # GET /api/dependencies
    # ------------------------------------------------------------------

    @app.route("/api/dependencies", methods=["GET"])
    def get_dependencies():
        return jsonify({"dependencies": app.config["STATE"].dependencies})

    # ------------------------------------------------------------------
    # POST /api/dependencies
    # ------------------------------------------------------------------

    @app.route("/api/dependencies", methods=["POST"])
    def post_dependency():
        body = request.get_json(silent=True) or {}
        source = body.get("from_member", "")
        target = body.get("to_member", "")
        valid_names = {m.name for m in app.config["MEMBERS"]}
        state = app.config["STATE"]
        graph = DependencyGraph(state.dependencies)
        try:
            graph.add_edge(source, target, valid_names)
        except CycleError as e:
            return jsonify({"error": str(e)}), 409
        except ValueError as e:
            msg = str(e)
            if "already exists" in msg:
                return jsonify({"error": msg}), 409
            return jsonify({"error": msg}), 400
        state.dependencies = graph.edges()
        save_state(state, app.config["STATE_PATH"])
        return jsonify({"dependencies": state.dependencies}), 201

    # ------------------------------------------------------------------
    # PUT /api/dependencies
    # ------------------------------------------------------------------

    @app.route("/api/dependencies", methods=["PUT"])
    def put_dependency():
        body = request.get_json(silent=True) or {}
        old_from = body.get("old_from", "")
        old_to = body.get("old_to", "")
        new_from = body.get("new_from", "")
        new_to = body.get("new_to", "")
        valid_names = {m.name for m in app.config["MEMBERS"]}
        state = app.config["STATE"]

        if new_from not in valid_names or new_to not in valid_names:
            return jsonify({"error": f"Invalid member name"}), 400

        old_pair = {"from_member": old_from, "to_member": old_to}
        if old_pair not in state.dependencies:
            return jsonify({"error": "Dependency not found"}), 404

        remaining = [d for d in state.dependencies if d != old_pair]
        graph = DependencyGraph(remaining)
        try:
            graph.add_edge(new_from, new_to, valid_names)
        except CycleError as e:
            return jsonify({"error": str(e)}), 409
        except ValueError as e:
            msg = str(e)
            if "already exists" in msg:
                return jsonify({"error": msg}), 409
            return jsonify({"error": msg}), 400

        state.dependencies = graph.edges()
        save_state(state, app.config["STATE_PATH"])
        return jsonify({"dependencies": state.dependencies})

    # ------------------------------------------------------------------
    # DELETE /api/dependencies
    # ------------------------------------------------------------------

    @app.route("/api/dependencies", methods=["DELETE"])
    def delete_dependency():
        body = request.get_json(silent=True) or {}
        source = body.get("from_member", "")
        target = body.get("to_member", "")
        state = app.config["STATE"]
        graph = DependencyGraph(state.dependencies)
        try:
            graph.remove_edge(source, target)
        except KeyError as e:
            return jsonify({"error": str(e)}), 404
        state.dependencies = graph.edges()
        save_state(state, app.config["STATE_PATH"])
        return jsonify({"dependencies": state.dependencies})

    # ------------------------------------------------------------------
    # GET /api/clusters
    # ------------------------------------------------------------------

    @app.route("/api/clusters", methods=["GET"])
    def get_clusters():
        return jsonify({"clusters": app.config["STATE"].clusters})

    # ------------------------------------------------------------------
    # POST /api/clusters
    # ------------------------------------------------------------------

    @app.route("/api/clusters", methods=["POST"])
    def post_cluster():
        body = request.get_json(silent=True) or {}
        name = body.get("name", "").strip()
        members_list = body.get("members", [])
        if not name:
            return jsonify({"error": "Cluster name must not be empty."}), 400
        valid_names = {m.name for m in app.config["MEMBERS"]}
        state = app.config["STATE"]
        if any(c["name"] == name for c in state.clusters):
            return jsonify({"error": f"Cluster '{name}' already exists."}), 400
        for m in members_list:
            if m not in valid_names:
                return jsonify({"error": f"Member '{m}' not in loaded dataset."}), 400
        state.clusters.append({"name": name, "members": list(members_list)})
        save_state(state, app.config["STATE_PATH"])
        return jsonify({"clusters": state.clusters}), 201

    # ------------------------------------------------------------------
    # PUT /api/clusters/<cluster_name>
    # ------------------------------------------------------------------

    @app.route("/api/clusters/<cluster_name>", methods=["PUT"])
    def put_cluster(cluster_name):
        body = request.get_json(silent=True) or {}
        new_name = body.get("name")
        members_list = body.get("members")
        valid_names = {m.name for m in app.config["MEMBERS"]}
        state = app.config["STATE"]
        cluster = next((c for c in state.clusters if c["name"] == cluster_name), None)
        if cluster is None:
            return jsonify({"error": f"Cluster '{cluster_name}' not found."}), 404
        if new_name is not None and new_name != cluster_name:
            if any(c["name"] == new_name for c in state.clusters):
                return jsonify({"error": f"Cluster name already exists"}), 400
            cluster["name"] = new_name
        if members_list is not None:
            for m in members_list:
                if m not in valid_names:
                    return jsonify({"error": f"Member '{m}' not in loaded dataset."}), 400
            cluster["members"] = list(members_list)
        save_state(state, app.config["STATE_PATH"])
        return jsonify({"clusters": state.clusters})

    # ------------------------------------------------------------------
    # DELETE /api/clusters/<cluster_name>
    # ------------------------------------------------------------------

    @app.route("/api/clusters/<cluster_name>", methods=["DELETE"])
    def delete_cluster(cluster_name):
        state = app.config["STATE"]
        original_len = len(state.clusters)
        state.clusters = [c for c in state.clusters if c["name"] != cluster_name]
        if len(state.clusters) == original_len:
            return jsonify({"error": f"Cluster '{cluster_name}' not found."}), 404
        save_state(state, app.config["STATE_PATH"])
        return jsonify({"clusters": state.clusters})

    # ------------------------------------------------------------------
    # GET /api/phases
    # ------------------------------------------------------------------

    @app.route("/api/phases", methods=["GET"])
    def get_phases():
        return jsonify({"phases": app.config["STATE"].phases})

    # ------------------------------------------------------------------
    # POST /api/phases
    # ------------------------------------------------------------------

    @app.route("/api/phases", methods=["POST"])
    def post_phase():
        body = request.get_json(silent=True) or {}
        name = body.get("name", "").strip()
        start_date = body.get("start_date", "")
        end_date = body.get("end_date", "")
        state = app.config["STATE"]
        try:
            state.phases = add_phase(name, start_date, end_date, state.phases)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        save_state(state, app.config["STATE_PATH"])
        return jsonify({"phases": state.phases}), 201

    # ------------------------------------------------------------------
    # PUT /api/phases/<phase_name>
    # ------------------------------------------------------------------

    @app.route("/api/phases/<path:phase_name>", methods=["PUT"])
    def put_phase(phase_name):
        body = request.get_json(silent=True) or {}
        new_name = body.get("name")
        start_date = body.get("start_date")
        end_date = body.get("end_date")
        state = app.config["STATE"]
        try:
            state.phases = update_phase(
                phase_name, state.phases,
                new_name=new_name, start_date=start_date, end_date=end_date,
            )
        except KeyError:
            return jsonify({"error": f"Phase '{phase_name}' not found."}), 404
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        save_state(state, app.config["STATE_PATH"])
        return jsonify({"phases": state.phases})

    # ------------------------------------------------------------------
    # DELETE /api/phases/<phase_name>
    # ------------------------------------------------------------------

    @app.route("/api/phases/<path:phase_name>", methods=["DELETE"])
    def delete_phase(phase_name):
        state = app.config["STATE"]
        try:
            state.phases = remove_phase(phase_name, state.phases)
        except KeyError:
            return jsonify({"error": f"Phase '{phase_name}' not found."}), 404
        save_state(state, app.config["STATE_PATH"])
        return jsonify({"phases": state.phases})

    return app


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Absence Management Dashboard")
    parser.add_argument("excel_file", help="Path to the .xlsx absence spreadsheet")
    parser.add_argument("--port", type=int, default=5002, help="Port to listen on (default 5002)")
    args = parser.parse_args()

    if not os.path.exists(args.excel_file):
        print(f"Error: File not found: {args.excel_file}", file=sys.stderr)
        sys.exit(1)

    application = create_app(args.excel_file)
    try:
        application.run(host="localhost", port=args.port, debug=False)
    except OSError as e:
        print(f"Port {args.port} in use — retry with --port <N>", file=sys.stderr)
        sys.exit(1)
