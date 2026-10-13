# Quickstart: Extended Timeline with Month-Range Filter

**Phase 1 output** | **Date**: 2026-10-13

---

## What changed

- The timeline no longer stops at December 2026. By default it shows a **rolling 12 months**: from
  the current week to the week containing the same date next year, moving forward automatically.
- Week labels now include the year (`CW5 2027 | 1 Feb`), so weeks with the same number in
  different years can't be confused — and cumul-risk / sole-coverage markers always land in the
  right year.
- The Excel file has no year in it, only week numbers. The app now works out which year the file
  covers from today's date, so a 2026 file keeps loading correctly in January 2027 (before, it would
  have been dated a year late or failed to load because of CW53).

---

## Using the time filter

1. In the header, type a **From** month and a **To** month as `MM/YYYY` (e.g. `03/2027` and
   `08/2027`).
2. Click **Apply**. Only weeks with at least one working day in that range are shown.
3. The status next to the filter always shows what you're looking at — either
   `Rolling 12 months (…)` or the range you applied.
4. Click **Reset** to go back to the rolling 12 months.

The filter stays applied when you click **Reload** or edit phases, cumul groups or clusters. It is
forgotten when you reload the browser page or restart the app.

If you enter something invalid (`13/2027`, a To month before the From month), you get a message and
the view you had stays as it was.

If the Excel file has no data at all for the range you chose, a notice tells you so.

---

## What the filter does *not* change

- Risk calculation: a 10-day absence that starts before your From month still counts as a critical
  absence in the visible weeks.
- Phases: a phase that runs past the edge of the range is drawn up to the edge; hover it to see its
  full dates. Phases completely outside the range are hidden from the timeline but still listed in
  the **Phases** panel.

---

## Verifying (manual)

```bash
.venv/bin/python -m pytest            # full suite must pass
.venv/bin/python run.py absences.xlsx # then open the dashboard
```

1. Without touching the filter: first week is the current CW, last is the week containing today's
   date next year; labels show years.
2. Apply `11/2026` – `02/2027`: weeks around the year change appear once each, in order.
3. Apply `01/2025` – `12/2026` (24 months): timeline renders in under 2 s (SC-003).
4. Apply `02/2027` – `01/2027`: error shown, previous view kept.
5. Apply a range after the last week in `absences.xlsx`: "no data" notice appears.
