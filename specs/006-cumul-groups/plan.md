# Implementation Plan: Cumul Groups (replacing Dependencies)

**Branch**: `006-cumul-groups` | **Date**: 2026-08-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification `specs/006-cumul-groups/spec.md`

## Summary

Retire the directional "dependency" feature (`absence_dashboard/graph.py`'s `DependencyGraph`,
the `/api/dependencies` routes, `AppState.dependencies`, and the `#dependency-panel` UI) and
replace it with a symmetric, named "cumul group" concept. A cumul group is a named set of two or
more resources; a **cumul risk week** exists when every member's own continuous absence block
exceeds 5 calendar days ("critical absence") and those critical absences share at least one common
day within an ISO calendar week. A **sole coverage flag** marks the single member who remains
present while every other member of the group has a critical absence in that week. Cumul groups are
CRUD-managed by unique name (mirroring the existing skill-clusters pattern) rather than the old
edit-by-matching-old-edge pattern dependencies used, and — like dependencies — may optionally be
time-boxed with `active_from`/`active_to`. Risk visibility is delivered by extending the existing
per-member dashboard payload with cumul-risk/sole-coverage data and rendering it with new CSS
classes/badges/tooltips, plus a persistent, always-visible definition of what a cumul is (FR-016).
No new dependencies, no new services, no data migration of old dependency records (discarded per
FR-012).

## Technical Context

**Language/Version**: Python 3.10+ (existing; venv currently 3.14) — no change.

**Primary Dependencies**: Flask (existing). No new backend or frontend dependencies. Frontend
remains vanilla JS (`absence_dashboard/static/main.js`) with no framework/build step.

**Storage**: `state/state.json` — schema change only: the `dependencies` key/field is replaced by a
`cumul_groups` key/field (`AppState.cumul_groups: list`). Old `dependencies` data in existing state
files is not read or migrated (FR-012); it is simply ignored on load. `launch_config.json` is
unaffected.

**Testing**: pytest, following the project's existing two-tier convention — `tests/unit/` for pure
business-logic functions (no I/O; mirrors `tests/unit/test_phases_manager.py` and the parts of
`tests/unit/test_graph.py` being replaced) and `tests/integration/test_app.py` for Flask route
behavior via `app.test_client()`. Tests are written and confirmed failing before implementation
(Constitution Principle II).

**Target Platform**: Unchanged — local Flask web service, plus the existing Windows/Citrix
standalone package (feature 002). No effect on `launch_config.json` or packaging.

**Project Type**: Single-project web application (Flask backend + vanilla JS frontend) — in-place
modification, no new project/service.

**Performance Goals**: Unchanged. Cumul-risk computation is O(groups × weeks × members), the same
order of magnitude as the dependency deadlock/bottleneck computation it replaces, over the same
single-manager-scale dataset.

**Constraints**: Preserve existing zero-network-call, local-only operation (established by feature
005). No new sensitive data fields — cumul groups only reference member names already present in
the dataset.

**Scale/Scope**: Same single-manager scope as prior features. Net change in surface area is roughly
neutral: one module removed (`graph.py`), one module added (`cumul_groups.py`), one route group
replaced (`/api/dependencies` → `/api/cumul-groups`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I — Spec-First Development
**PASS** — `spec.md` is complete with prioritized user stories, acceptance scenarios, functional
requirements (FR-001–FR-016), and measurable success criteria; the 5-day-threshold ambiguity was
resolved via `/speckit-clarify` and no `[NEEDS CLARIFICATION]` markers remain.

### Principle II — Test-Driven Development (NON-NEGOTIABLE)
**PASS (plan-level)** — Phase 2 tasks will require new failing tests in
`tests/unit/test_cumul_groups.py` and updated/new classes in `tests/integration/test_app.py` before
any implementation code changes, following the same red-green-refactor precedent already used for
`phases_manager.py` and `graph.py` in this codebase.

### Principle III — Data Integrity & Accuracy
**PASS** — This feature only adds a derived, computed grouping/risk layer over existing absence
records; it does not create, edit, or delete absence periods, and does not touch the audit trail for
absence data. No overlap-prevention logic is affected.

### Principle IV — Privacy & Compliance
**PASS** — Cumul groups reference only member names that are already loaded and displayed elsewhere
on the dashboard. No new sensitive/personal fields are introduced, and no new external data
transmission occurs (still zero-network per feature 005).

### Principle V — Simplicity & Maintainability
**PASS** — Today the codebase has two different named-entity CRUD styles: dependencies (unnamed,
edited by matching the old edge's exact field values) and clusters/phases (named, edited by
`PUT /<name>`). Cumul groups adopt the named-entity style already used for clusters/phases, so this
change *reduces* the number of distinct patterns in the codebase from two to one instead of adding a
third.

## Project Structure

### Documentation (this feature)

```text
specs/006-cumul-groups/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   └── cumul-groups-api.md   # Phase 1 output — replaces the retired dependencies API
└── tasks.md              # Phase 2 output (/speckit-tasks — NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
absence_dashboard/
├── graph.py                  # DELETED — DependencyGraph (directional pool model) retired
├── cumul_groups.py           # NEW — pure functions, no I/O (mirrors phases_manager.py):
│                              #   add_cumul_group / update_cumul_group / remove_cumul_group
│                              #   critical_absence_days(merged_blocks) -> set[date]
│                              #   compute_cumul_risk_weeks(group, ...) -> list[int]
│                              #   compute_sole_coverage_weeks(group, ...) -> dict[str, list[int]]
├── state.py                   # MODIFIED: AppState.dependencies -> AppState.cumul_groups;
│                               # _migrate_dependencies() removed (no migration, FR-012)
└── app.py                     # MODIFIED: /api/dependencies routes removed entirely;
                                # /api/cumul-groups (GET, POST) and
                                # /api/cumul-groups/<name> (PUT, DELETE) added;
                                # _assemble_dashboard() emits "cumul_groups" (replacing
                                # "dependencies") plus per-member "cumul_risks" /
                                # "sole_coverage" lists; /api/refresh stale-reference
                                # cleanup rewritten for cumul groups (FR-013)

absence_dashboard/static/
├── index.html                 # MODIFIED: #dependency-panel -> #cumul-panel (name + members
│                               # + optional active_from/active_to fields, like the old
│                               # dependency form, but edited by name); persistent cumul
│                               # definition text (FR-016); header button relabeled "Cumul"
├── main.js                    # MODIFIED: renderDependencies() -> renderCumulGroups();
│                               # deadlock/bottleneck rendering paths repurposed for
│                               # cumul-risk / sole-coverage (new CSS classes, badges,
│                               # tooltips carrying the affected group name(s))
└── style.css                  # MODIFIED: .deadlock/.is-bottleneck/.bottleneck-badge/
                                # .phase-has-deadlock renamed/restyled as .cumul-risk/
                                # .is-sole-coverage/.sole-coverage-badge/.phase-has-cumul-risk

tests/
├── unit/
│   ├── test_graph.py          # DELETED
│   ├── test_cumul_groups.py   # NEW — CRUD validation + risk/sole-coverage computation
│   └── test_state.py          # MODIFIED — cumul_groups persistence; no dependency migration
└── integration/
    └── test_app.py            # MODIFIED — TestPostDependencies / TestPutDependencies /
                                 # TestDeleteDependencies / TestPoolDependenciesAPI /
                                 # TestBottleneck deleted; new TestCumulGroupsCRUD /
                                 # TestCumulRiskWeeks / TestSoleCoverage classes added;
                                 # TestRefresh updated for cumul-group stale-cleanup
```

**Structure Decision**: In-place replacement, no new modules beyond `cumul_groups.py` and no new
top-level directories. The change is scoped to the backend module that models the retired feature,
the routes that expose it, and the frontend rendering/markup that visualizes it — consistent with
how features 003→004→005 replaced each other's connection logic in place.

## Complexity Tracking

*No unjustified Constitution Check violations — intentionally empty.*
