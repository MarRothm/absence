from datetime import date, timedelta
from dataclasses import dataclass


@dataclass
class AbsencePeriod:
    start_date: date
    end_date: date


def merge_periods(days: list) -> list:
    """
    Merge a list of individual absence dates into non-overlapping AbsencePeriod spans.
    Adjacent working days (e.g. Friday → Monday) are merged into one period.
    """
    if not days:
        return []

    sorted_days = sorted(set(days))
    periods = []
    start = sorted_days[0]
    end = sorted_days[0]

    for d in sorted_days[1:]:
        if d <= _next_working_day(end):
            end = d
        else:
            periods.append(AbsencePeriod(start_date=start, end_date=end))
            start = d
            end = d

    periods.append(AbsencePeriod(start_date=start, end_date=end))
    return periods


def _next_working_day(d: date) -> date:
    next_d = d + timedelta(days=1)
    while next_d.weekday() >= 5:
        next_d += timedelta(days=1)
    return next_d
