"""Pure functions for the dashboard's visible time range and calendar weeks (no I/O, no Flask)."""
import calendar
import re
from datetime import date, timedelta

_MONTH_RE = re.compile(r"^(\d{1,2})/(\d{4})$")


# ---------------------------------------------------------------------------
# Visible range
# ---------------------------------------------------------------------------

def default_range(today: date) -> tuple:
    """Rolling 12 months: Monday of today's ISO week to the same date one year later."""
    start = today - timedelta(days=today.weekday())
    try:
        end = today.replace(year=today.year + 1)
    except ValueError:  # 29 Feb → 28 Feb
        end = today.replace(year=today.year + 1, day=28)
    return start, end


def parse_month(value: str) -> tuple:
    """"MM/YYYY" (or "M/YYYY") → (year, month). Raises ValueError otherwise."""
    match = _MONTH_RE.match((value or "").strip())
    if not match or not 1 <= int(match.group(1)) <= 12:
        raise ValueError(f"Invalid month '{value}' — expected MM/YYYY.")
    return int(match.group(2)), int(match.group(1))


def resolve_range(from_s, to_s, today: date) -> tuple:
    """(start, end, is_default) for the requested month range, or the rolling default when
    neither month is given. Raises ValueError for an incomplete, malformed or reversed range."""
    if not from_s and not to_s:
        return (*default_range(today), True)
    if not from_s or not to_s:
        raise ValueError("Both 'from' and 'to' are required (MM/YYYY).")
    from_year, from_month = parse_month(from_s)
    to_year, to_month = parse_month(to_s)
    if (to_year, to_month) < (from_year, from_month):
        raise ValueError("'To' month must be the same as or later than 'From' month.")
    last_day = calendar.monthrange(to_year, to_month)[1]
    return date(from_year, from_month, 1), date(to_year, to_month, last_day), False


# ---------------------------------------------------------------------------
# Calendar weeks
# ---------------------------------------------------------------------------

def build_calendar_weeks(start: date, end: date) -> list:
    """Every ISO week with at least one Mon–Fri day inside [start, end], in order.

    Each week carries a year-unique `key` ("YYYY-Www") so weeks with the same number in
    different years never share markers.
    """
    weeks = []
    monday = start - timedelta(days=start.weekday())
    while monday <= end:
        friday = monday + timedelta(days=4)
        if friday >= start:
            iso = monday.isocalendar()
            weeks.append({
                "key": f"{iso.year}-W{iso.week:02d}",
                "year": iso.year,
                "week_number": iso.week,
                "label": f"CW{iso.week} {iso.year} | {monday.day} {monday.strftime('%b')}",
                "start": monday.isoformat(),
                "end": friday.isoformat(),
                "days": [(monday + timedelta(days=i)).isoformat() for i in range(5)],
            })
        monday += timedelta(weeks=1)
    return weeks
