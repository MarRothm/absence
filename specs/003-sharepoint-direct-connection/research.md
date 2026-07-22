# Research: SharePoint Direct Connection

**Phase 0 output** | **Date**: 2026-07-21

No `NEEDS CLARIFICATION` markers remain (the one open question, FR-004's scope fork, was resolved
with the user during `/speckit-specify`: local-file support is removed entirely). This document
records the technical decisions needed to implement that removal correctly.

---

## 1. Where the "no local file, read-only" guarantee is enforced

**Decision**: Three layers, each with a distinct job:
1. `resolve_launch_source()` (CLI arg, `app.py`) rejects a non-`http(s)://` value before it ever
   reaches `create_app`.
2. `load_launch_config()` (`launch_config.json`, `launch_config.py`) rejects a non-`http(s)://`
   `excel_source` the same way.
3. `data_fetcher.get_workbook()` itself rejects any non-`http(s)://` source as a defensive backstop
   — it should be unreachable in normal operation because (1) and (2) already validate first, but
   it guarantees the invariant holds even if some future code path calls it directly.

**Rationale**: FR-002 ("MUST NOT write... under any dashboard action, at any time") is best
satisfied structurally, not just by front-door validation. Layers 1–2 give the manager a fast,
specific, actionable error (FR-005/FR-007) without ever touching the network; layer 3 is defense in
depth so the "SharePoint-only" invariant can never be silently bypassed by a future caller.
`get_workbook()` already only ever issues a `requests.get()` and opens the result with
`openpyxl(read_only=True)` — there has never been a write/upload code path to remove; this feature
makes the *read source* itself exclusively SharePoint, closing the only route by which the original
file's local copy could previously be substituted.

**Alternatives considered**:
- Validate only at the CLI/`launch_config.json` layer, leave `get_workbook()` permissive: rejected —
  leaves a latent "local file still works if you call the right internal function" capability alive
  in the codebase, which contradicts FR-004's "removed entirely" and is a needless landmine for
  future maintainers.
- Validate only inside `get_workbook()`, drop the CLI/`launch_config.json` checks: rejected — a
  manager would get a lower-level, less specific error instead of the clear FR-007 message at the
  point where they actually made the mistake (their CLI arg or config file).

## 2. Test-suite adaptation: centralize the HTTP mock in `conftest.py`

**Decision**: `tests/conftest.py`'s `app` fixture now mocks `requests.get` (via `monkeypatch`, same
technique already used in `tests/unit/test_data_fetcher.py`) to return the `sample_xlsx` fixture's
bytes, and passes a fake `https://fake.sharepoint.example/...` URL to `create_app` instead of the
local `sample_xlsx` path. Every other fixture (`client`, and the ~100 tests built on top of them) is
unchanged.

**Rationale**: `get_workbook()` becoming genuinely URL-only (research #1) would otherwise break
every route/business-logic test that currently calls `create_app(sample_xlsx, ...)` directly — none
of those tests are actually testing SharePoint-fetching; they use a local file purely as convenient,
deterministic fixture data. Centralizing the mock in the one shared fixture means zero changes to
the ~15 test files that consume `app`/`client`, keeps the suite fast and fully offline, and — unlike
leaving a local-file bypass alive in `get_workbook()` — doesn't compromise the "removed entirely"
guarantee anywhere a manager could reach.

**Alternatives considered**:
- Rewrite every individual test file to mock HTTP itself: rejected as disproportionate — the fixture
  is the single natural seam; touching ~15 files for the same one-line change per file adds cost
  with no benefit over centralizing it.
- Keep a test-only escape hatch (e.g., an env var or private `_allow_local` kwarg on `get_workbook`)
  so tests can keep using local paths directly: rejected — this is exactly the "local-file fallback
  provided... for testing" that FR-004 explicitly rules out, and it's a second validation path to
  keep in sync with the real one (Principle V — simplicity).

## 3. Renaming `excel_path`/`EXCEL_PATH` to `excel_source`/`EXCEL_SOURCE`

**Decision**: `create_app(excel_path: str, ...)` becomes `create_app(excel_source: str, ...)`, and
the Flask `app.config["EXCEL_PATH"]` key becomes `app.config["EXCEL_SOURCE"]`.

**Rationale**: The parameter/config key now only ever holds a SharePoint URL — keeping the name
`excel_path` would actively mislead a future reader into thinking a filesystem path is still valid.
Both call sites (`app.py`'s `__main__`, `tests/conftest.py`) already pass this argument
positionally, so the rename has no other call-site impact.

**Alternatives considered**:
- Leave the name as `excel_path`: rejected — a stale, misleading name is a real (if small) liability
  once local-file support is gone; the rename is free (one internal parameter, two call sites, both
  positional).

## 4. Feature 002 documentation: what gets updated vs. left as history

**Decision**: `specs/002-windows-standalone-build/quickstart.md` (the operational runbook a manager
actually follows to deploy the standalone package) is updated to remove the local-file option and
its associated troubleshooting entries. `specs/002-windows-standalone-build/spec.md`, `plan.md`,
`research.md`, `data-model.md`, and `contracts/launch-config.md` are left untouched as the historical
record of what feature 002 shipped.

**Rationale**: This project's own precedent (see the `testautomation_monitoring` sibling project's
`016-retire-java-backend` feature, which explicitly kept superseded specs "as dated history" while
still updating live-facing docs like `README.md`) draws the line at *operational* docs a user
currently relies on versus the *planning record* of a past feature. `quickstart.md` is exactly the
former — leaving it stating a now-false local-file option would actively mislead a manager. The
`spec.md`/`plan.md`/etc. are the latter — they document what was true and decided when feature 002
shipped, and rewriting them would erase real project history for no benefit, since this feature's
own `spec.md`/`plan.md` already records the change and its rationale going forward.

**Alternatives considered**:
- Leave all of feature 002's docs untouched, including `quickstart.md`: rejected — a manager
  following it today would configure a local file path and hit the new FR-007 rejection error with
  no explanation, since the doc they're reading doesn't mention the change.
- Rewrite feature 002's `spec.md`/`plan.md`/etc. to remove all mention of local-file support:
  rejected — destroys accurate historical record of a past decision for no operational benefit; this
  feature's own documents are where the change and its reasoning belong.
