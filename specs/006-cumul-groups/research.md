# Phase 0 Research: Cumul Groups (replacing Dependencies)

No `[NEEDS CLARIFICATION]` markers remain in `spec.md` after `/speckit-clarify` (the 5-day
threshold question was resolved). The decisions below are the plan-level design choices needed to
turn the spec's technology-agnostic requirements into a concrete implementation approach,
grounded in existing precedent already established in this codebase.

## Decision 1: CRUD shape — named entity (like clusters/phases), not edge-matching (like dependencies)

- **Decision**: Cumul groups are identified by a unique `name` and edited via
  `PUT /api/cumul-groups/<name>`, `DELETE /api/cumul-groups/<name>`, matching the existing
  `/api/clusters/<cluster_name>` and `/api/phases/<phase_name>` pattern.
- **Rationale**: FR-004/FR-005/FR-006 require listing, editing by name, and removing cumul groups —
  the old dependency feature had no name and was edited by matching every field of the old edge
  (`old_from`/`old_to_members`/`old_active_from`/`old_active_to` vs. `new_*`), which was more complex
  and error-prone. Cumul groups already require a unique name (FR-003), so the simpler, already-proven
  named-entity pattern applies directly and reduces the number of distinct CRUD patterns in the
  codebase from two to one (Constitution Principle V).
- **Alternatives considered**: Keep dependency-style edit-by-old-value matching — rejected as
  unnecessary complexity now that a unique name is available as a stable key.

## Decision 2: Data model — flat member list, no direction, optional time-boxing

- **Decision**: `{"name": str, "members": [str, ...], "active_from"?: str, "active_to"?: str}`,
  stored as `AppState.cumul_groups: list`, replacing `AppState.dependencies`.
- **Rationale**: FR-001 requires a name plus two-or-more resources with no directionality (unlike
  `from_member`/`to_members`). The Assumptions section explicitly carries forward the old feature's
  optional `active_from`/`active_to` time-boxing, so those fields are preserved verbatim from the
  `DependencyGraph` edge shape.
- **Alternatives considered**: Nested/ordered member roles — rejected; spec explicitly calls the
  group "unordered" (Key Entities: Cumul Group).

## Decision 3: No migration of old dependency data

- **Decision**: On `load_state()`, the old `dependencies` key in existing `state/state.json` files is
  simply not read into `AppState` (no field for it exists anymore); `_migrate_dependencies()` is
  deleted rather than adapted.
- **Rationale**: FR-012 explicitly forbids migration/auto-conversion, since a directional
  `from_member`→`to_members` edge has no reliable one-to-one symmetric equivalent.
- **Alternatives considered**: Best-effort conversion (e.g., `from_member` + `to_members` → one cumul
  group per edge) — explicitly rejected by FR-012 and the Edge Cases section.

## Decision 4: Critical-absence computation reuses existing `merged_blocks`, not raw day sets

- **Decision**: A member's absence block is "critical" when its length in calendar days
  (`(end_date - start_date).days + 1`) exceeds 5. `critical_absence_days(merged_blocks)` filters
  `merger.py`'s existing `AbsencePeriod` list down to only critical blocks and expands them into a
  `set[date]`, reusing the same per-block expansion approach `_assemble_dashboard()` already uses for
  raw absence date sets.
- **Rationale**: `merger.py`'s `merge_periods()` already merges adjacent working-day absences into
  contiguous `AbsencePeriod(start_date, end_date)` spans — exactly the "continuous absence block" unit
  the clarified FR-007 refers to. No new absence-tracking data structure is needed.
- **Alternatives considered**: Counting raw (non-merged) individual absent days per calendar week —
  rejected; the clarification specifically ties the >5-day threshold to a member's own continuous
  block, not to a per-week day count, so merged blocks are the correct unit.

## Decision 5: Cumul risk week requires a *common* critical day; sole coverage does not

- **Decision**:
  - `compute_cumul_risk_weeks(group, member_critical_date_sets, calendar_weeks)`: for each calendar
    week, intersects every member's critical-date set with the week's day set and with each other; the
    week is flagged only if that intersection is non-empty (i.e., all members share at least one
    common critical day in the week).
  - `compute_sole_coverage_weeks(group, member_critical_date_sets, calendar_weeks)`: for each week,
    a member is "present" if none of their critical days fall in that week; if exactly one member is
    present, they are flagged as sole coverage for that group/week (no common-day requirement across
    the absent members, mirroring the old `compute_bottleneck_weights` semantics).
- **Rationale**: User Story 2 Acceptance Scenario 2 explicitly requires a *shared* day for the cumul
  risk flag ("all those critical absences share at least one common day"), which is stricter than the
  old deadlock logic (which only required each member to be absent *sometime* in the week,
  independently). FR-009/Acceptance Scenario 4 describe sole coverage the same way the old bottleneck
  logic worked — per-member presence check within the week, no shared-day requirement — so that part
  of the existing `compute_bottleneck_weights` logic carries over unchanged in shape, just swapped to
  use critical-date sets instead of raw absence-date sets.
- **Alternatives considered**: Using the same "any day in week" rule for both risk and sole coverage
  — rejected because it would make the risk flag looser than what Acceptance Scenario 2 specifies.

## Decision 6: Visibility — extend the existing per-member dashboard payload + persistent definition text

- **Decision**: `_assemble_dashboard()` adds `"cumul_groups": state.cumul_groups` at the top level
  (replacing `"dependencies"`), and each member entry gains `"cumul_risks"` and `"sole_coverage"`
  lists of `{"group": name, "week_number": int}`, giving the frontend enough information to flag
  specific weeks/groups without extra API calls (FR-008, FR-010). The frontend renders these using new
  CSS classes/badges/tooltips (`.cumul-risk`, `.is-sole-coverage`, `.sole-coverage-badge`,
  `.phase-has-cumul-risk`) directly modeled on the retired `.deadlock`/`.is-bottleneck` styling, plus
  an always-visible definition note in the cumul panel and in tooltip text (FR-016) so the flag is
  self-explanatory without external docs.
- **Rationale**: This mirrors the existing `deadlock_weeks` per-member field and the top-level
  `skill_clusters` field already proven in this dashboard, keeping the visibility mechanism
  consistent with prior features while adding the group-attribution the old deadlock flag lacked.
- **Alternatives considered**: A separate `/api/cumul-risks` endpoint — rejected as unnecessary; the
  existing dashboard payload already aggregates all cross-cutting derived state in one response, and
  splitting it would require an extra round trip with no benefit at this data scale.
