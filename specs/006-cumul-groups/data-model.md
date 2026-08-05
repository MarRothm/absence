# Phase 1 Data Model: Cumul Groups (replacing Dependencies)

## Cumul Group

Persisted in `state/state.json` under `AppState.cumul_groups: list` (replaces `AppState.dependencies`
and the `"dependencies"` JSON key entirely — old dependency data is never read, per FR-012).

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | yes | Non-empty. Unique across all cumul groups (FR-003). |
| `members` | list[string] | yes | ≥ 2 entries (FR-001/FR-002). Each entry must be a name currently present in the loaded dataset (FR-015). No duplicate entries within one group (Edge Cases). |
| `active_from` | string (`YYYY-MM-DD`) | no | Omitted entirely when not time-boxed (mirrors the old dependency edge shape). Must be provided together with `active_to` or not at all. |
| `active_to` | string (`YYYY-MM-DD`) | no | Must not be before `active_from`. |

**Uniqueness rule (FR-003)**: a create/edit is rejected if, after the change, either (a) another
group already has the same `name`, or (b) another group already has the exact same `frozenset(members)`
— matching the `frozenset(to_members)` uniqueness key already used for dependency pools.

**Validation summary** (enforced in `cumul_groups.py`, no I/O):
- `add_cumul_group(name, members, valid_members, groups, active_from=None, active_to=None) -> list`
- `update_cumul_group(old_name, groups, *, new_name=None, new_members=None, valid_members=None, active_from=..., active_to=...) -> list`
- `remove_cumul_group(name, groups) -> list`

All three return a new list (existing input list/dicts are not mutated), following the
`phases_manager.py` convention. `add_cumul_group`/`update_cumul_group` raise `ValueError` for
validation failures (empty name, <2 members, duplicate member, unknown member, duplicate
name/member-set, `active_from > active_to`, only one of `active_from`/`active_to` given);
`update_cumul_group`/`remove_cumul_group` raise `KeyError` when `old_name`/`name` is not found.

## Critical Absence (derived, not persisted)

Computed per member from the existing `merged_blocks` (`AbsencePeriod` list from `merger.py`) already
produced by `_assemble_dashboard()`. Not a new stored entity — a pure derived value.

- A block is **critical** when `(end_date - start_date).days + 1 > 5`.
- `critical_absence_days(merged_blocks) -> set[date]`: union of all calendar days covered by a
  member's critical blocks only. Non-critical (≤ 5 day) blocks contribute no days.

## Cumul Risk Week (derived, not persisted)

A `(cumul_group, calendar_week)` pair where every member's critical-absence-day set, intersected with
the week's day set, has at least one day in common across *all* members of the group (FR-007).

`compute_cumul_risk_weeks(group: dict, member_critical_date_sets: dict[str, set[date]], calendar_weeks: list) -> list[int]`
— returns the sorted list of `week_number`s where the group is at risk. Respects `active_from`/
`active_to` time-boxing the same way `DependencyGraph._dep_active_in_cw` did.

## Sole Coverage Flag (derived, not persisted)

A `(cumul_group, calendar_week, member)` triple marking the single member who has no critical-absence
day in that week while every other member of the group does (FR-009).

`compute_sole_coverage_weeks(group: dict, member_critical_date_sets: dict[str, set[date]], calendar_weeks: list) -> dict[str, list[int]]`
— maps the sole-covering member's name to the sorted list of `week_number`s they cover alone for that
group. Empty dict if no such week exists. Also respects `active_from`/`active_to`.

## Dashboard Response Shape (additions/changes only)

Top level (`_assemble_dashboard()` return value):

```json
{
  "cumul_groups": [ { "name": "...", "members": ["..."], "active_from": "...", "active_to": "..." } ],
  "members": [
    {
      "name": "Alice",
      "...": "... (unchanged: is_migration_member, merged_blocks, clusters)",
      "cumul_risks": [ { "group": "Backend Coverage", "week_number": 22 } ],
      "sole_coverage": [ { "group": "Backend Coverage", "week_number": 23 } ]
    }
  ]
}
```

Removed: top-level `"dependencies"` key, per-member `"deadlock_weeks"` key and `"is_bottleneck"`
key (replaced by `"cumul_risks"`/`"sole_coverage"`/membership in an at-risk group, computed the same
way `is_bottleneck` was derived from `bottleneck_weights`).

## State Persistence (`state.py`)

```python
@dataclass
class AppState:
    cumul_groups: list = field(default_factory=list)
    clusters: list = field(default_factory=list)
    phases: list = field(default_factory=list)
```

`load_state()`/`save_state()` read/write the `cumul_groups` key; the `dependencies` key, if present in
an old state file, is silently ignored (not an error — old files remain loadable, just without their
retired dependency data). `_migrate_dependencies()` is deleted.
