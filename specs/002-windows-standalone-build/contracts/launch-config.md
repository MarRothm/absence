# Contract: `launch_config.json`

**Phase 1 output** | **Date**: 2026-07-21

The interface between a manager deploying the standalone package and the packaged app's startup
logic. This file is only consulted when the app is started with no `excel_file` CLI argument (the
`.bat` launcher always starts it this way); the existing CLI-argument path is unaffected and takes
precedence when an argument is supplied.

## Location

Same directory as the executable / `run-dashboard.bat` (the extracted bundle root).

## Schema

```json
{
  "excel_source": "absences.xlsx",
  "port": 5002
}
```

| Field | Type | Required | Default |
|---|---|---|---|
| `excel_source` | string | yes | *(none — startup error if absent)* |
| `port` | integer | no | `5002` |

`excel_source` accepts the same two forms the CLI argument already accepts:
- a local file path (absolute, or relative to the executable's directory), or
- an `http://` / `https://` SharePoint "anyone with the link" share URL.

## Precedence

1. If the app is invoked with a positional `excel_file` CLI argument (local/dev use), that value is
   used and `launch_config.json` is ignored entirely.
2. Otherwise (packaged/double-click use), `launch_config.json` is read from the executable's
   directory. If it is missing or `excel_source` is absent/invalid, startup fails with a message
   printed to the console the `.bat` launcher stays open on (see `run-dashboard.bat`'s existing
   "Server stopped or failed to start. See any error above." pattern) — no silent fallback.

## Compatibility

Adding this file is purely additive: it introduces no change to `absence_dashboard/app.py`'s
existing CLI-argument behavior, `state/state.json` schema, or any HTTP API route.
