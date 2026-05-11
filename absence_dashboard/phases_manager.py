"""Pure functions for managing project phases (no I/O, no Flask)."""


def update_phase(
    old_name: str,
    phases: list,
    *,
    new_name: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> list:
    """Return a new list with the named phase updated. Does not mutate `phases`.

    Any of new_name, start_date, end_date may be None to keep the current value.
    Raises KeyError if old_name is not found.
    Raises ValueError for a duplicate new_name or end_date < start_date.
    """
    idx = next((i for i, p in enumerate(phases) if p["name"] == old_name), None)
    if idx is None:
        raise KeyError(old_name)

    current = phases[idx]
    resolved_name = new_name if new_name is not None else current["name"]
    resolved_start = start_date if start_date is not None else current["start_date"]
    resolved_end = end_date if end_date is not None else current["end_date"]

    if resolved_name != old_name and any(
        p["name"] == resolved_name for i, p in enumerate(phases) if i != idx
    ):
        raise ValueError(f"Phase '{resolved_name}' already exists.")
    if resolved_end < resolved_start:
        raise ValueError("end_date must be >= start_date.")

    updated = {"name": resolved_name, "start_date": resolved_start, "end_date": resolved_end}
    return phases[:idx] + [updated] + phases[idx + 1:]


def add_phase(name: str, start_date: str, end_date: str, phases: list) -> list:
    """Return a new list with the phase appended. Does not mutate `phases`."""
    if not name or not name.strip():
        raise ValueError("name must not be empty.")
    if end_date < start_date:
        raise ValueError("end_date must be >= start_date.")
    if any(p["name"] == name for p in phases):
        raise ValueError(f"Phase '{name}' already exists.")
    return phases + [{"name": name, "start_date": start_date, "end_date": end_date}]


def remove_phase(name: str, phases: list) -> list:
    """Return a new list with the named phase removed. Does not mutate `phases`."""
    if not any(p["name"] == name for p in phases):
        raise KeyError(name)
    return [p for p in phases if p["name"] != name]
