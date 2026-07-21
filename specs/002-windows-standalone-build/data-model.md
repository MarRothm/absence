# Data Model: Windows Server 2016 (Citrix) Standalone Build

**Phase 1 output** | **Date**: 2026-07-21

This feature adds no persisted business/domain data (no absence records, no new UI-config fields).
It adds one small startup-parameter file and two process-level artifacts already named in the
spec's Key Entities section.

## Launch Configuration (`launch_config.json`)

Read once, at startup, only when the app is launched without a CLI `excel_file` argument (i.e., the
packaged/double-click case). Never written by the running app — the manager edits it directly.

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `excel_source` | string | Yes | — | Local file path or `http(s)://` SharePoint share URL; same value that would otherwise be passed as the `excel_file` CLI argument. Validated the same way the CLI path is today (existence check for local paths; scheme check for URLs — see `absence_dashboard/data_fetcher.py`). |
| `port` | integer | No | `5002` | Same default and meaning as the existing `--port` CLI flag. |

**Validation rules**:
- Missing `excel_source`, or a value that is neither an existing local path nor an `http(s)://` URL,
  is a startup error (mirrors the existing CLI behavior in `app.py`'s `__main__` block: printed to
  stderr, non-zero exit — no silent fallback).
- `port` must be a positive integer; an invalid value falls back to `5002` with a printed warning
  (matches the "actionable error, not silent failure" principle already applied to the existing
  `--port` conflict message).

**Lifecycle**: created once by the build script (copied from the committed
`launch_config.example.json` template) when the bundle is assembled; thereafter lives next to the
executable and is edited by the manager, not by the app.

## Standalone Package *(process artifact, from spec Key Entities)*

Not a data record — the built, zipped bundle (executable, bundled interpreter/dependencies, static
assets, `.bat` launcher, `launch_config.example.json` + `launch_config.json`, empty `state/`
directory) produced by the build script and attached to a GitHub Release. Identity: the release tag
(`build-<commit-sha>`) it is attached to.

## Build Pipeline *(process artifact, from spec Key Entities)*

Not a data record — the GitHub Actions workflow run that produces a Standalone Package. Identity:
the workflow run ID / triggering commit SHA. No state is persisted between runs beyond the published
release itself.
