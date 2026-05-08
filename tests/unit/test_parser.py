"""
TDD: Tests for absence_dashboard/parser.py
Write BEFORE implementation; confirm they FAIL before writing parser.py.
"""
import pytest
from datetime import date
from openpyxl import Workbook

from absence_dashboard.parser import build_date_map, parse_members, PersonAbsence, SkippedRow


# ---------------------------------------------------------------------------
# build_date_map
# ---------------------------------------------------------------------------

class TestBuildDateMap:
    def _make_ws(self, max_col: int):
        wb = Workbook()
        ws = wb.active
        # Set max_column by writing a value in the last column
        ws.cell(row=1, column=max_col, value="end")
        return ws

    def test_col_f_is_base_date(self):
        ws = self._make_ws(6)
        dm = build_date_map(ws)
        assert dm[6] == date(2026, 4, 27)

    def test_col_g_is_next_working_day(self):
        ws = self._make_ws(7)
        dm = build_date_map(ws)
        assert dm[7] == date(2026, 4, 28)  # Tuesday

    def test_col_k_skips_weekend(self):
        # Col 6=Mon Apr27, 7=Tue Apr28, 8=Wed Apr29, 9=Thu Apr30,
        # 10=Fri May1, 11=Mon May4 (skip Sat May2 + Sun May3)
        ws = self._make_ws(11)
        dm = build_date_map(ws)
        assert dm[10] == date(2026, 5, 1)   # Friday
        assert dm[11] == date(2026, 5, 4)   # Monday (weekend skipped)

    def test_no_columns_below_6(self):
        ws = self._make_ws(5)
        dm = build_date_map(ws)
        assert 5 not in dm
        assert 6 not in dm

    def test_returns_all_columns_from_6(self):
        ws = self._make_ws(8)
        dm = build_date_map(ws)
        assert set(dm.keys()) == {6, 7, 8}


# ---------------------------------------------------------------------------
# parse_members
# ---------------------------------------------------------------------------

class TestParseMembers:
    def test_only_marked_rows_included(self, sample_workbook):
        ws = sample_workbook.active
        members, _ = parse_members(ws)
        names = {m.name for m in members}
        assert "Alice" in names
        assert "Bob" in names
        assert "Carol" in names
        assert "Dave" not in names
        assert "Eve" not in names

    def test_exactly_three_members(self, sample_workbook):
        ws = sample_workbook.active
        members, _ = parse_members(ws)
        assert len(members) == 3

    def test_x_detection_case_insensitive(self):
        wb = Workbook()
        ws = wb.active
        ws.cell(row=1, column=6, value="KW18")
        ws.cell(row=2, column=6, value="Mo")
        ws.cell(row=3, column=3, value="X")   # uppercase X in filter
        ws.cell(row=3, column=4, value="Frank")
        ws.cell(row=3, column=6, value="X")   # uppercase absence marker
        members, _ = parse_members(ws)
        assert len(members) == 1
        assert members[0].name == "Frank"
        assert date(2026, 4, 27) in members[0].absence_days

    def test_name_whitespace_stripped(self, sample_workbook):
        ws = sample_workbook.active
        members, _ = parse_members(ws)
        names = {m.name for m in members}
        # "Alice " (row 8) should be stripped and merged with "Alice" (row 3)
        assert "Alice" in names
        assert "Alice " not in names

    def test_multi_row_same_name_aggregated(self, sample_workbook):
        ws = sample_workbook.active
        members, _ = parse_members(ws)
        alice = next(m for m in members if m.name == "Alice")
        # Row 3: Apr27, Apr28; Row 8: May4 (after name strip, same person)
        assert date(2026, 4, 27) in alice.absence_days
        assert date(2026, 4, 28) in alice.absence_days
        assert date(2026, 5, 4) in alice.absence_days

    def test_empty_name_row_skipped(self, sample_workbook):
        ws = sample_workbook.active
        _, skipped = parse_members(ws)
        assert len(skipped) == 1
        assert skipped[0].row == 9

    def test_rows_1_and_2_skipped(self):
        wb = Workbook()
        ws = wb.active
        # Put "x" in col C row 1 and row 2 — should be ignored
        ws.cell(row=1, column=3, value="x")
        ws.cell(row=1, column=4, value="HeaderPerson")
        ws.cell(row=2, column=3, value="x")
        ws.cell(row=2, column=4, value="HeaderPerson2")
        members, _ = parse_members(ws)
        assert len(members) == 0

    def test_bob_has_correct_absence_days(self, sample_workbook):
        ws = sample_workbook.active
        members, _ = parse_members(ws)
        bob = next(m for m in members if m.name == "Bob")
        assert date(2026, 4, 29) in bob.absence_days
        assert date(2026, 4, 30) in bob.absence_days
        assert date(2026, 5, 1) in bob.absence_days
        assert len(bob.absence_days) == 3

    def test_carol_has_no_absence_days(self, sample_workbook):
        ws = sample_workbook.active
        members, _ = parse_members(ws)
        carol = next(m for m in members if m.name == "Carol")
        assert carol.absence_days == []

    def test_returns_person_absence_and_skipped_row_types(self, sample_workbook):
        ws = sample_workbook.active
        members, skipped = parse_members(ws)
        assert all(isinstance(m, PersonAbsence) for m in members)
        assert all(isinstance(s, SkippedRow) for s in skipped)
