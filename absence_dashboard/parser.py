import re
from dataclasses import dataclass, field
from datetime import date

# Keyed on the first two lowercased characters, so this matches both the abbreviated
# ("Mo", "Di", ...) and full ("Montag", "Dienstag", ...) German weekday names real
# production files have used interchangeably (see specs/005-restore-local-file's
# implementation notes) — all five weekdays have distinct two-letter prefixes.
WEEKDAY_ABBREV = {"mo": 1, "di": 2, "mi": 3, "do": 4, "fr": 5}


@dataclass
class PersonAbsence:
    name: str
    is_migration_member: bool = False
    absence_days: list = field(default_factory=list)
    merged_blocks: list = field(default_factory=list)


@dataclass
class SkippedRow:
    row: int
    reason: str


def build_date_map(ws, year: int = None, today: date = None) -> dict:
    """Map column index (>=6) to its real calendar date, derived from that column's own
    Row 1 (calendar week label, e.g. "KW18") and Row 2 (weekday abbreviation, e.g. "Mo")
    header cells — never assumed from a fixed starting date plus a sequential increment,
    which silently mis-dates every absence whenever the real file's actual date range
    differs from that assumption (a real production bug this replaces).

    Row 1's week-number cell is commonly merged across all 5 weekday columns in real
    files (shown once, spanning Mon-Fri) — a merged cell's value only physically exists
    in its leftmost column, so the week number is forward-filled across the blank cells
    the merge covers (otherwise every day but the first of each week silently drops out
    of the map, which is exactly what happened in production).

    A column whose weekday cell doesn't resolve to a recognized abbreviation, or that has
    no week number yet established (nothing seen so far to forward-fill from), is left out
    of the map entirely. The year is bumped by one internally whenever an explicit week
    number decreases moving left to right, so a sheet spanning a December-January
    boundary is still dated correctly.

    Real files carry no year at all, so when `year` isn't given the starting year is
    inferred: of the previous, current and next year (relative to `today`), the one whose
    week numbers are all valid ISO weeks and whose resulting date span is closest to
    `today` wins (ties go to the earlier year). This keeps a 2026 sheet ending in CW53
    loading correctly in January 2027 — 2027 has no CW53.
    """
    columns = _dated_columns(ws)
    if year is not None:
        return _date_columns(columns, year)

    if today is None:
        today = date.today()
    best, best_distance = {}, None
    for candidate in (today.year - 1, today.year, today.year + 1):
        try:
            result = _date_columns(columns, candidate)
        except ValueError:
            continue  # a week number that doesn't exist in this year (e.g. CW53)
        if not result:
            return result
        first, last = min(result.values()), max(result.values())
        distance = max((first - today).days, (today - last).days, 0)
        if best_distance is None or distance < best_distance:
            best, best_distance = result, distance
    return best


def _dated_columns(ws) -> list:
    """(col_idx, week_number, weekday) for every column that can be dated, in order."""
    max_col = ws.max_column or 5
    if max_col < 6:
        return []

    header_row = next(ws.iter_rows(min_row=1, max_row=1, min_col=1, max_col=max_col, values_only=True))
    weekday_row = next(ws.iter_rows(min_row=2, max_row=2, min_col=1, max_col=max_col, values_only=True))

    columns = []
    last_week = None
    for col_idx in range(6, max_col + 1):
        cw_cell = str(header_row[col_idx - 1] or "")
        wd_cell = str(weekday_row[col_idx - 1] or "").strip().lower()[:2]
        week_digits = re.sub(r"\D", "", cw_cell)

        if week_digits:
            week_number = int(week_digits)
            last_week = week_number
        elif last_week is not None:
            week_number = last_week  # merged cell — carry the last explicit week forward
        else:
            continue  # no week number established yet; can't date this column

        if wd_cell not in WEEKDAY_ABBREV:
            continue
        columns.append((col_idx, week_number, WEEKDAY_ABBREV[wd_cell]))
    return columns


def _date_columns(columns: list, year: int) -> dict:
    """Date each column starting in `year`, rolling over whenever the week number drops.
    Raises ValueError if a week number doesn't exist in its year."""
    result = {}
    last_week = None
    for col_idx, week_number, weekday in columns:
        if last_week is not None and week_number < last_week:
            year += 1
        last_week = week_number
        result[col_idx] = date.fromisocalendar(year, week_number, weekday)
    return result

def parse_members(ws, date_map: dict = None) -> tuple:
    """
    Parse Excel worksheet and return (list[PersonAbsence], list[SkippedRow]).

    Layout (confirmed):
      Row 1: CW labels — used to build the column-to-date map (build_date_map)
      Row 2: Weekday names — used to build the column-to-date map
      Row 3+: Data rows
      Col C (idx 3): "Projekt Migration" — include only rows where value.lower() == "x"
      Col D (idx 4): "Team Mitglied " — person name (stripped)
      Col F+ (idx 6+): Working day columns; "x" (case-insensitive) = absent

    `date_map` can be passed in when the caller already built it (build_date_map).
    Uses iter_rows() so it works correctly with read_only=True workbooks.
    """
    members: dict[str, PersonAbsence] = {}
    skipped: list[SkippedRow] = []
    if date_map is None:
        date_map = build_date_map(ws)

    for row_idx, row in enumerate(ws.iter_rows(min_row=3, values_only=True), start=3):
        name = str(row[3] or "").strip()  # col D = index 3
        filter_val = str(row[2] or "").strip().lower()  # col C = index 2

        if not name:
            if filter_val == "x":
                skipped.append(SkippedRow(row=row_idx, reason="Empty name in Column D"))
            continue

        is_migration = filter_val == "x"

        if name not in members:
            members[name] = PersonAbsence(name=name, is_migration_member=is_migration)
        elif is_migration:
            members[name].is_migration_member = True

        for col_idx, working_day in date_map.items():
            cell_val = row[col_idx - 1] if col_idx - 1 < len(row) else None
            if str(cell_val or "").strip().lower() == "x":
                if working_day not in members[name].absence_days:
                    members[name].absence_days.append(working_day)

    return list(members.values()), skipped
