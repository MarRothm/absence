from datetime import date, timedelta
from dataclasses import dataclass, field

BASE_DATE = date(2026, 4, 27)  # Monday CW18 — confirmed first date column (Col F, index 6)


@dataclass
class PersonAbsence:
    name: str
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
        while next_d.weekday() >= 5:  # skip Sat (5) and Sun (6)
            next_d += timedelta(days=1)
        working_day = next_d
    return result


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
    """
    date_map = build_date_map(ws)
    members: dict[str, PersonAbsence] = {}
    skipped: list[SkippedRow] = []

    max_row = ws.max_row or 2
    for row_idx in range(3, max_row + 1):
        filter_val = str(ws.cell(row=row_idx, column=3).value or "").strip().lower()
        if filter_val != "x":
            continue

        name = str(ws.cell(row=row_idx, column=4).value or "").strip()
        if not name:
            skipped.append(SkippedRow(row=row_idx, reason="Empty name in Column D"))
            continue

        if name not in members:
            members[name] = PersonAbsence(name=name)

        for col_idx, absence_date in date_map.items():
            cell_val = str(ws.cell(row=row_idx, column=col_idx).value or "").strip().lower()
            if cell_val == "x" and absence_date not in members[name].absence_days:
                members[name].absence_days.append(absence_date)

    return list(members.values()), skipped
