from datetime import date, timedelta
from dataclasses import dataclass, field

BASE_DATE = date(2026, 4, 27)  # Monday CW18 — confirmed first date column (Col F, index 6)


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


def build_date_map(ws) -> dict:
    """Map column index (>=6) to the corresponding working date starting from BASE_DATE."""
    result = {}
    working_day = BASE_DATE
    max_col = ws.max_column or 5
    for col_idx in range(6, max_col + 1):
        result[col_idx] = working_day
        next_d = working_day + timedelta(days=1)
        while next_d.weekday() >= 5:
            next_d += timedelta(days=1)
        working_day = next_d
    return result


def _next_working_day(d: date) -> date:
    d += timedelta(days=1)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def parse_members(ws) -> tuple:
    """
    Parse Excel worksheet and return (list[PersonAbsence], list[SkippedRow]).

    Layout (confirmed):
      Row 1: CW labels — skipped
      Row 2: Weekday names — skipped
      Row 3+: Data rows
      Col C (idx 3): "Projekt Migration" — include only rows where value.lower() == "x"
      Col D (idx 4): "Team Mitglied " — person name (stripped)
      Col F+ (idx 6+): Working day columns; "x" (case-insensitive) = absent

    Uses iter_rows() so it works correctly with read_only=True workbooks.
    """
    members: dict[str, PersonAbsence] = {}
    skipped: list[SkippedRow] = []

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

        # Build date map on-the-fly for columns F+ (index 5 onward)
        working_day = BASE_DATE
        for col_offset, cell_val in enumerate(row[5:], start=0):
            if str(cell_val or "").strip().lower() == "x":
                if working_day not in members[name].absence_days:
                    members[name].absence_days.append(working_day)
            working_day = _next_working_day(working_day)

    return list(members.values()), skipped
