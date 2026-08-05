import os
import sys
import warnings
from datetime import date, datetime, timedelta

# Suppress urllib3's LibreSSL warning on macOS — harmless for a local-only tool
warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")

from flask import Flask, jsonify, request

from absence_dashboard import data_fetcher
from absence_dashboard.parser import parse_members
from absence_dashboard.merger import merge_periods
from absence_dashboard.state import load_state, save_state, AppState
from absence_dashboard.phases_manager import add_phase, remove_phase, update_phase
from absence_dashboard.cumul_groups import (
    add_cumul_group,
    remove_cumul_group,
    update_cumul_group,
    critical_absence_days,
    compute_cumul_risk_weeks,
    compute_sole_coverage_weeks,
)
from absence_dashboard.launch_config import load_launch_config, DEFAULT_PORT


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

def _load_excel(source: str) -> tuple:
    wb = data_fetcher.get_workbook(source)
    ws = wb.active
    members, skipped = parse_members(ws)
    wb.close()
    for m in members:
        m.merged_blocks = merge_periods(m.absence_days)
    last_loaded = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    return members, skipped, last_loaded


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

    member_critical_date_sets = {m.name: critical_absence_days(m.merged_blocks) for m in members}
    cumul_risks_by_member: dict = {}
    sole_coverage_by_member: dict = {}
    for group in state.cumul_groups:
        for week_number in compute_cumul_risk_weeks(group, member_critical_date_sets, calendar_weeks):
            for member_name in group["members"]:
                cumul_risks_by_member.setdefault(member_name, []).append(
                    {"group": group["name"], "week_number": week_number}
                )
        sole_weeks = compute_sole_coverage_weeks(group, member_critical_date_sets, calendar_weeks)
        for member_name, weeks in sole_weeks.items():
            for week_number in weeks:
                sole_coverage_by_member.setdefault(member_name, []).append(
                    {"group": group["name"], "week_number": week_number}
                )

    result_members = []
    for m in members:
        member_clusters = [c["name"] for c in state.clusters if m.name in c.get("members", [])]
        result_members.append({
            "name": m.name,
            "is_migration_member": m.is_migration_member,
            "merged_blocks": [
                {"start": b.start_date.isoformat(), "end": b.end_date.isoformat()}
                for b in m.merged_blocks
            ],
            "clusters": member_clusters,
            "cumul_risks": cumul_risks_by_member.get(m.name, []),
            "sole_coverage": sole_coverage_by_member.get(m.name, []),
        })

    result_members = _sort_members(result_members, state.clusters)

    return {
        "calendar_weeks": calendar_weeks,
        "members": result_members,
        "skill_clusters": state.clusters,
        "phases": state.phases,
        "cumul_groups": state.cumul_groups,
        "skipped_rows": [
            {"row": s.row, "reason": s.reason}
            for s in app.config["SKIPPED_ROWS"]
        ],
        "last_loaded": app.config.get("LAST_LOADED", ""),
    }


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

def create_app(excel_source: str, state_path: str = "state/state.json") -> Flask:
    app = Flask(__name__, static_folder="static")

    members, skipped, last_loaded = _load_excel(excel_source)
    app.config.update({
        "EXCEL_SOURCE": excel_source,
        "STATE_PATH": state_path,
        "MEMBERS": members,
        "SKIPPED_ROWS": skipped,
        "STATE": load_state(state_path),
        "LAST_LOADED": last_loaded,
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
            members, skipped, last_loaded = _load_excel(app.config["EXCEL_SOURCE"])
        except Exception as e:
            return jsonify({"error": str(e), "stale_data": True}), 422

        new_names = {m.name for m in members}
        state = app.config["STATE"]
        removed = []

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

        new_cumul_groups = []
        for group in state.cumul_groups:
            valid_members = [m for m in group["members"] if m in new_names]
            removed_members = [m for m in group["members"] if m not in new_names]
            if len(valid_members) < 2:
                removed.append({"type": "cumul_group", "entry": group})
                continue
            for rm in removed_members:
                removed.append({
                    "type": "cumul_group_member",
                    "entry": {"group": group["name"], "member": rm},
                })
            new_cumul_groups.append({**group, "members": valid_members})
        state.cumul_groups = new_cumul_groups

        app.config["MEMBERS"] = members
        app.config["SKIPPED_ROWS"] = skipped
        app.config["LAST_LOADED"] = last_loaded
        save_state(state, app.config["STATE_PATH"])

        result = _assemble_dashboard(app)
        result["removed_stale_references"] = removed
        return jsonify(result)

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

    # ------------------------------------------------------------------
    # GET /api/cumul-groups
    # ------------------------------------------------------------------

    @app.route("/api/cumul-groups", methods=["GET"])
    def get_cumul_groups():
        return jsonify({"cumul_groups": app.config["STATE"].cumul_groups})

    # ------------------------------------------------------------------
    # POST /api/cumul-groups
    # ------------------------------------------------------------------

    @app.route("/api/cumul-groups", methods=["POST"])
    def post_cumul_group():
        body = request.get_json(silent=True) or {}
        name = body.get("name", "").strip()
        members = body.get("members", [])
        active_from = body.get("active_from")
        active_to = body.get("active_to")
        valid_names = {m.name for m in app.config["MEMBERS"]}
        state = app.config["STATE"]
        try:
            state.cumul_groups = add_cumul_group(
                name, members, valid_names, state.cumul_groups,
                active_from=active_from, active_to=active_to,
            )
        except ValueError as e:
            msg = str(e)
            status = 409 if "already exists" in msg else 400
            return jsonify({"error": msg}), status
        save_state(state, app.config["STATE_PATH"])
        return jsonify({"cumul_groups": state.cumul_groups}), 201

    # ------------------------------------------------------------------
    # PUT /api/cumul-groups/<name>
    # ------------------------------------------------------------------

    @app.route("/api/cumul-groups/<path:name>", methods=["PUT"])
    def put_cumul_group(name):
        body = request.get_json(silent=True) or {}
        new_name = body.get("name")
        new_members = body.get("members")
        valid_names = {m.name for m in app.config["MEMBERS"]}
        state = app.config["STATE"]
        kwargs = {}
        if "active_from" in body:
            kwargs["active_from"] = body.get("active_from")
        if "active_to" in body:
            kwargs["active_to"] = body.get("active_to")
        try:
            state.cumul_groups = update_cumul_group(
                name, state.cumul_groups,
                new_name=new_name, new_members=new_members, valid_members=valid_names,
                **kwargs,
            )
        except KeyError:
            return jsonify({"error": f"Cumul group '{name}' not found."}), 404
        except ValueError as e:
            msg = str(e)
            status = 409 if "already exists" in msg else 400
            return jsonify({"error": msg}), status
        save_state(state, app.config["STATE_PATH"])
        return jsonify({"cumul_groups": state.cumul_groups})

    # ------------------------------------------------------------------
    # DELETE /api/cumul-groups/<name>
    # ------------------------------------------------------------------

    @app.route("/api/cumul-groups/<path:name>", methods=["DELETE"])
    def delete_cumul_group(name):
        state = app.config["STATE"]
        try:
            state.cumul_groups = remove_cumul_group(name, state.cumul_groups)
        except KeyError:
            return jsonify({"error": f"Cumul group '{name}' not found."}), 404
        save_state(state, app.config["STATE_PATH"])
        return jsonify({"cumul_groups": state.cumul_groups})

    return app


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def resolve_launch_source(excel_file, port_arg, config_path="launch_config.json"):
    """Resolve (source, port) from CLI args, falling back to launch_config.json when
    excel_file is not supplied (the packaged/double-click launch case — see
    specs/002-windows-standalone-build/contracts/launch-config.md). excel_file must be an
    existing local file path — SharePoint access was permanently blocked by IT policy
    (specs/005-restore-local-file/spec.md). Raises FileNotFoundError with an actionable
    message when neither path yields a usable source.
    """
    if excel_file is not None:
        if not os.path.exists(excel_file):
            raise FileNotFoundError(f"File not found: {excel_file}")
        return excel_file, port_arg if port_arg is not None else DEFAULT_PORT

    source, config_port = load_launch_config(config_path)
    return source, port_arg if port_arg is not None else config_port


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Absence Management Dashboard")
    parser.add_argument(
        "excel_file", nargs="?", default=None,
        help="Path to the .xlsx absence spreadsheet (omit to read launch_config.json)",
    )
    parser.add_argument("--port", type=int, default=None, help="Port to listen on (default 5002)")
    args = parser.parse_args()

    try:
        source, port = resolve_launch_source(args.excel_file, args.port)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        application = create_app(source)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        application.run(host="localhost", port=port, debug=False)
    except OSError as e:
        print(f"Port {port} in use — retry with --port <N>", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
