"""
TDD: Tests for absence_dashboard/timeline.py
"""
import pytest
from datetime import date

from absence_dashboard.timeline import (
    build_calendar_weeks,
    default_range,
    parse_month,
    resolve_range,
)


class TestBuildCalendarWeeks:
    def test_week_dict_has_expected_keys(self):
        weeks = build_calendar_weeks(date(2027, 2, 1), date(2027, 2, 5))
        assert set(weeks[0]) == {"key", "year", "week_number", "label", "start", "end", "days"}

    def test_key_is_iso_week_string(self):
        weeks = build_calendar_weeks(date(2027, 2, 1), date(2027, 2, 5))
        assert weeks[0]["key"] == "2027-W05"

    def test_label_contains_year(self):
        weeks = build_calendar_weeks(date(2027, 2, 1), date(2027, 2, 5))
        assert weeks[0]["label"] == "CW5 2027 | 1 Feb"

    def test_days_are_mon_to_fri(self):
        week = build_calendar_weeks(date(2027, 2, 1), date(2027, 2, 5))[0]
        assert week["days"] == ["2027-02-01", "2027-02-02", "2027-02-03", "2027-02-04", "2027-02-05"]
        assert week["start"] == "2027-02-01"
        assert week["end"] == "2027-02-05"

    def test_week_with_only_weekend_day_in_range_at_start_excluded(self):
        # Sat 1 Aug 2026 is the only in-range day of 2026-W31
        weeks = build_calendar_weeks(date(2026, 8, 1), date(2026, 8, 31))
        assert weeks[0]["key"] == "2026-W32"

    def test_week_with_only_weekend_day_in_range_at_end_excluded(self):
        # Sun 31 May 2026 belongs to 2026-W22; W23 must not appear
        weeks = build_calendar_weeks(date(2026, 5, 1), date(2026, 5, 31))
        assert weeks[-1]["key"] == "2026-W22"

    def test_week_partially_in_range_included(self):
        # Wed 3 Feb 2027 → whole 2027-W05 shown
        weeks = build_calendar_weeks(date(2027, 2, 3), date(2027, 2, 3))
        assert [w["key"] for w in weeks] == ["2027-W05"]

    def test_iso_week_53_and_year_boundary(self):
        weeks = build_calendar_weeks(date(2026, 12, 28), date(2027, 1, 8))
        assert [w["key"] for w in weeks] == ["2026-W53", "2027-W01"]
        assert weeks[0]["year"] == 2026 and weeks[0]["week_number"] == 53
        assert weeks[1]["label"] == "CW1 2027 | 4 Jan"

    def test_two_year_span_is_chronological_without_gaps_or_duplicates(self):
        weeks = build_calendar_weeks(date(2026, 1, 1), date(2027, 12, 31))
        keys = [w["key"] for w in weeks]
        assert len(keys) == len(set(keys))
        mondays = [date.fromisoformat(w["start"]) for w in weeks]
        assert all((b - a).days == 7 for a, b in zip(mondays, mondays[1:]))

    def test_start_after_end_returns_empty(self):
        assert build_calendar_weeks(date(2027, 3, 1), date(2027, 2, 1)) == []


class TestDefaultRange:
    def test_rolling_twelve_months_from_current_week(self):
        assert default_range(date(2026, 10, 13)) == (date(2026, 10, 12), date(2027, 10, 13))

    def test_start_is_monday_of_current_iso_week(self):
        assert default_range(date(2026, 10, 18))[0] == date(2026, 10, 12)  # Sunday

    def test_leap_day_rolls_to_feb_28(self):
        assert default_range(date(2028, 2, 29))[1] == date(2029, 2, 28)

    def test_default_weeks_span_current_week_to_week_containing_date_next_year(self):
        weeks = build_calendar_weeks(*default_range(date(2026, 10, 13)))
        assert weeks[0]["key"] == "2026-W42"
        assert weeks[-1]["key"] == "2027-W41"


class TestParseMonth:
    def test_two_digit_month(self):
        assert parse_month("03/2027") == (2027, 3)

    def test_one_digit_month(self):
        assert parse_month("3/2027") == (2027, 3)

    def test_surrounding_whitespace_ignored(self):
        assert parse_month(" 03/2027 ") == (2027, 3)

    @pytest.mark.parametrize("value", ["13/2027", "00/2027", "2027", "03/27", "03-2027", ""])
    def test_invalid_values_rejected(self, value):
        with pytest.raises(ValueError, match="MM/YYYY"):
            parse_month(value)


class TestResolveRange:
    TODAY = date(2026, 10, 13)

    def test_no_filter_returns_rolling_default(self):
        assert resolve_range(None, None, self.TODAY) == (*default_range(self.TODAY), True)

    def test_empty_strings_treated_as_no_filter(self):
        assert resolve_range("", "", self.TODAY) == (*default_range(self.TODAY), True)

    def test_month_range_is_first_to_last_day(self):
        assert resolve_range("01/2027", "03/2027", self.TODAY) == (
            date(2027, 1, 1), date(2027, 3, 31), False,
        )

    def test_leap_february_ends_on_29th(self):
        assert resolve_range("02/2028", "02/2028", self.TODAY)[1] == date(2028, 2, 29)

    def test_same_month_is_valid(self):
        start, end, _ = resolve_range("01/2027", "01/2027", self.TODAY)
        # Fri 1 Jan 2027 belongs to ISO week 53 of 2026
        assert build_calendar_weeks(start, end)[0]["key"] == "2026-W53"

    def test_only_from_rejected(self):
        with pytest.raises(ValueError, match="Both"):
            resolve_range("01/2027", None, self.TODAY)

    def test_only_to_rejected(self):
        with pytest.raises(ValueError, match="Both"):
            resolve_range(None, "01/2027", self.TODAY)

    def test_to_before_from_rejected(self):
        with pytest.raises(ValueError, match="later"):
            resolve_range("02/2027", "01/2027", self.TODAY)
