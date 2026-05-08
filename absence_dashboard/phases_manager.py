"""Pure functions for managing project phases (no I/O, no Flask)."""


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
