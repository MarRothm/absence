"""
TDD: Tests for absence_dashboard/merger.py
"""
import pytest
from datetime import date

from absence_dashboard.merger import merge_periods, AbsencePeriod


class TestMergePeriods:
    def test_empty_input_returns_empty(self):
        assert merge_periods([]) == []

    def test_single_day_preserved(self):
        result = merge_periods([date(2026, 5, 4)])
        assert result == [AbsencePeriod(date(2026, 5, 4), date(2026, 5, 4))]

    def test_consecutive_days_merged(self):
        days = [date(2026, 4, 27), date(2026, 4, 28), date(2026, 4, 29)]
        result = merge_periods(days)
        assert len(result) == 1
        assert result[0].start_date == date(2026, 4, 27)
        assert result[0].end_date == date(2026, 4, 29)

    def test_adjacent_working_days_across_weekend_merged(self):
        # Friday → Monday are adjacent working days (should be one period)
        days = [date(2026, 5, 1), date(2026, 5, 4)]  # Fri May1, Mon May4
        result = merge_periods(days)
        assert len(result) == 1
        assert result[0].start_date == date(2026, 5, 1)
        assert result[0].end_date == date(2026, 5, 4)

    def test_non_adjacent_days_kept_separate(self):
        # Mon Apr27, Wed Apr29 — Tue Apr28 is absent, so gap → two periods
        days = [date(2026, 4, 27), date(2026, 4, 29)]
        result = merge_periods(days)
        assert len(result) == 2
        assert result[0] == AbsencePeriod(date(2026, 4, 27), date(2026, 4, 27))
        assert result[1] == AbsencePeriod(date(2026, 4, 29), date(2026, 4, 29))

    def test_multiple_disjoint_spans_sorted(self):
        days = [date(2026, 5, 11), date(2026, 4, 27), date(2026, 4, 28), date(2026, 5, 12)]
        result = merge_periods(days)
        assert len(result) == 2
        assert result[0].start_date == date(2026, 4, 27)
        assert result[0].end_date == date(2026, 4, 28)
        assert result[1].start_date == date(2026, 5, 11)
        assert result[1].end_date == date(2026, 5, 12)

    def test_duplicate_days_deduplicated(self):
        days = [date(2026, 4, 27), date(2026, 4, 27), date(2026, 4, 28)]
        result = merge_periods(days)
        assert len(result) == 1
        assert result[0] == AbsencePeriod(date(2026, 4, 27), date(2026, 4, 28))

    def test_unsorted_input_handled(self):
        days = [date(2026, 4, 29), date(2026, 4, 27), date(2026, 4, 28)]
        result = merge_periods(days)
        assert len(result) == 1
        assert result[0].start_date == date(2026, 4, 27)
        assert result[0].end_date == date(2026, 4, 29)

    def test_five_day_week_all_absent(self):
        week = [
            date(2026, 4, 27),  # Mon
            date(2026, 4, 28),  # Tue
            date(2026, 4, 29),  # Wed
            date(2026, 4, 30),  # Thu
            date(2026, 5, 1),   # Fri
        ]
        result = merge_periods(week)
        assert len(result) == 1
        assert result[0] == AbsencePeriod(date(2026, 4, 27), date(2026, 5, 1))
