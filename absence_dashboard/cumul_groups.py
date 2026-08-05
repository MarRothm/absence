"""Pure functions for managing cumul groups (no I/O, no Flask)."""
from datetime import date

UNSET = object()


def _validate_name(name):
    if not name or not name.strip():
        raise ValueError("name must not be empty.")


def _validate_members(members, valid_members):
    if members is None or len(members) < 2:
        raise ValueError("A cumul group requires at least 2 members.")
    if len(set(members)) != len(members):
        raise ValueError("Duplicate member within a cumul group is not allowed.")
    if valid_members is not None:
        for m in members:
            if m not in valid_members:
                raise ValueError(f"Member '{m}' not found in loaded dataset.")


def _validate_active_range(active_from, active_to):
    if (active_from is None) != (active_to is None):
        raise ValueError("active_from and active_to must be provided together.")
    if active_from is not None and active_to is not None and active_to < active_from:
        raise ValueError("active_to must be on or after active_from.")


def _check_uniqueness(name, members, groups, *, skip_index=None):
    member_key = frozenset(members)
    for i, g in enumerate(groups):
        if i == skip_index:
            continue
        if g["name"] == name:
            raise ValueError(f"A cumul group named '{name}' already exists.")
        if frozenset(g["members"]) == member_key:
            raise ValueError("A cumul group with the same members already exists.")


def add_cumul_group(name, members, valid_members, groups, active_from=None, active_to=None) -> list:
    _validate_name(name)
    _validate_members(members, valid_members)
    _validate_active_range(active_from, active_to)
    _check_uniqueness(name, members, groups)

    entry = {"name": name, "members": list(members)}
    if active_from is not None:
        entry["active_from"] = active_from
        entry["active_to"] = active_to
    return groups + [entry]


def update_cumul_group(
    old_name,
    groups,
    *,
    new_name=None,
    new_members=None,
    valid_members=None,
    active_from=UNSET,
    active_to=UNSET,
) -> list:
    idx = next((i for i, g in enumerate(groups) if g["name"] == old_name), None)
    if idx is None:
        raise KeyError(old_name)

    current = groups[idx]
    resolved_name = new_name if new_name is not None else current["name"]
    resolved_members = list(new_members) if new_members is not None else list(current["members"])
    resolved_active_from = current.get("active_from") if active_from is UNSET else active_from
    resolved_active_to = current.get("active_to") if active_to is UNSET else active_to

    _validate_name(resolved_name)
    if new_members is not None:
        _validate_members(resolved_members, valid_members)
    else:
        _validate_members(resolved_members, None)
    _validate_active_range(resolved_active_from, resolved_active_to)
    _check_uniqueness(resolved_name, resolved_members, groups, skip_index=idx)

    updated = {"name": resolved_name, "members": resolved_members}
    if resolved_active_from is not None:
        updated["active_from"] = resolved_active_from
        updated["active_to"] = resolved_active_to
    return groups[:idx] + [updated] + groups[idx + 1:]


def remove_cumul_group(name, groups) -> list:
    if not any(g["name"] == name for g in groups):
        raise KeyError(name)
    return [g for g in groups if g["name"] != name]


CRITICAL_ABSENCE_THRESHOLD_DAYS = 5


def critical_absence_days(merged_blocks) -> set:
    """Union of calendar days covered by absence blocks longer than the critical threshold."""
    days = set()
    for block in merged_blocks:
        span = (block.end_date - block.start_date).days + 1
        if span > CRITICAL_ABSENCE_THRESHOLD_DAYS:
            days.update(
                date.fromordinal(block.start_date.toordinal() + offset)
                for offset in range(span)
            )
    return days


def _cw_days_set(cw: dict) -> set:
    return {date.fromisoformat(d) for d in cw["days"]}


def _group_active_in_cw(group: dict, cw: dict) -> bool:
    af = group.get("active_from")
    at = group.get("active_to")
    if af is None:
        return True
    cw_start = date.fromisoformat(cw["start"])
    cw_end = date.fromisoformat(cw["end"])
    return not (cw_start > date.fromisoformat(at) or cw_end < date.fromisoformat(af))


def compute_cumul_risk_weeks(group: dict, member_critical_date_sets: dict, calendar_weeks: list) -> list:
    risk_weeks = set()
    for cw in calendar_weeks:
        if not _group_active_in_cw(group, cw):
            continue
        cw_days = _cw_days_set(cw)
        if all(
            member_critical_date_sets.get(m, set()) & cw_days
            for m in group["members"]
        ):
            risk_weeks.add(cw["week_number"])
    return sorted(risk_weeks)


def compute_sole_coverage_weeks(group: dict, member_critical_date_sets: dict, calendar_weeks: list) -> dict:
    sole_weeks: dict = {}
    for cw in calendar_weeks:
        if not _group_active_in_cw(group, cw):
            continue
        cw_days = _cw_days_set(cw)
        not_critical = [
            m for m in group["members"]
            if not (member_critical_date_sets.get(m, set()) & cw_days)
        ]
        if len(not_critical) == 1:
            sole = not_critical[0]
            sole_weeks.setdefault(sole, []).append(cw["week_number"])
    return sole_weeks
