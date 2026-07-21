# Implementation Plan: Windows Server 2016 (Citrix) Standalone Build

**Branch**: `002-windows-standalone-build` | **Date**: 2026-07-21 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/002-windows-standalone-build/spec.md`

## Summary

Package the existing Flask/openpyxl dashboard as a self-contained Windows bundle (interpreter and
all dependencies included) that a manager can extract and run on a Windows Server 2016 Citrix
session with no Python install and no administrator rights — mirroring the sibling
`testautomation_monitoring` project's PyInstaller `--onedir` bundle + `.bat` launcher approach.
A new `.github/workflows/release-deployables.yml` builds the bundle on every push to `main` on a
`windows-latest` runner (no Windows Server 2016 CI image exists) and publishes it to GitHub
Releases, tagged to the triggering commit. Because the packaged app is launched by double-clicking
a `.bat` file (no interactive CLI), `app.py`'s `__main__` entry point gains a fallback: when no
`excel_file` CLI argument is given, it reads the absence-source path/URL and port from a new
`launch_config.json` file next to the executable, reusing the app's existing stdlib-`json`
config-file pattern (`state.py`) rather than adding a new config-parsing dependency. No existing
CLI-driven, local-dev workflow changes.

## Technical Context

**Language/Version**: Python 3.10+ (unchanged runtime target); build-time packaging runs under
Python 3.12 on the CI runner, matching `testautomation_monitoring`'s build.

**Primary Dependencies**: Flask 3.x, openpyxl 3.x, requests 2.x (unchanged runtime deps); PyInstaller
(new, build-time only — not a runtime dependency, not added to `requirements.txt`).

**Storage**: existing `state/state.json` (dependencies/clusters/phases, unchanged); new
`launch_config.json` (excel source path/URL + port) read once at startup, living next to the
executable so it survives bundle re-extraction and stays manager-editable.

**Testing**: pytest (existing, unchanged) plus unit tests for the new launch-config loader; a
build-script file-existence check (mirroring the analogue's bundle-structure verification) run in
CI; a documented manual smoke test on a real Windows Server 2016 Citrix session per release
(SC-005) — not automatable, since no such CI runner image exists.

**Target Platform**: Windows Server 2016, accessed via a Citrix-published desktop or application
session; built on GitHub-hosted `windows-latest` runners.

**Project Type**: Packaging/build addition to the existing single-project local web-service — no
new frontend/backend split, no new service.

**Performance Goals**: Existing dashboard performance targets (spec 001) are unchanged. Added
budget: launcher double-click to browser-reachable dashboard ≤10s, comfortably inside the 5-minute
first-run budget in SC-001 (which also covers download and extraction).

**Constraints**: No installer, no elevation/admin rights, no bundled Python-install step, no
additional runtime network access beyond the existing SharePoint-fetch path; the folder the bundle
runs from must remain writable for `state/state.json` and `launch_config.json`.

**Scale/Scope**: Same single-manager scope as spec 001. One new GitHub Actions workflow (build job
+ publish job), one new build script, one new downloadable Windows artifact per successful build.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I — Spec-First Development
**PASS** — `spec.md` is complete with prioritized user stories, acceptance scenarios, functional
requirements, and measurable success criteria.

### Principle II — Test-Driven Development
**PASS (plan-level)** — The new `launch_config.json` loader is small, pure logic (parse/validate a
JSON file with two fields) and gets unit tests written first, following Red-Green-Refactor. The
build script and workflow are verified by their own pass/fail behavior (CI job fails the run on a
bad build) plus the documented manual smoke test; these are infrastructure, not business logic, so
they are not pytest-covered — consistent with how the existing `run.sh` entry point is untested.

### Principle III — Data Integrity & Accuracy
**N/A** — This feature only changes how the existing read-only app is packaged and started. No
absence-record logic, merge algorithm, or write path is touched.

### Principle IV — Privacy & Compliance
**JUSTIFIED DEVIATION (inherited from spec 001)** — Same localhost-only, single-authorized-user
posture as the existing app. `launch_config.json` stores only a file path/URL and a port number —
no personal or sensitive data. No new deviation introduced by this feature.

### Principle V — Simplicity & Maintainability
**PASS** — Reuses the existing JSON config-file pattern (`state.py`) instead of introducing a new
parsing dependency (e.g., `python-dotenv`). The build script and workflow are a direct structural
mirror of `testautomation_monitoring`'s already-proven `scripts/build-python-standalone.sh` and
`.github/workflows/release-deployables.yml` — no novel packaging approach is introduced.

## Project Structure

### Documentation (this feature)

```text
specs/002-windows-standalone-build/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   ├── launch-config.md  # launch_config.json schema/contract
│   └── build-pipeline.md # GitHub Actions workflow contract
└── tasks.md              # Phase 2 output (/speckit-tasks — not created by /speckit-plan)
```

### Source Code (repository root)

```text
absence_dashboard/
├── app.py                 # MODIFIED: __main__ falls back to launch_config.json when no
│                           #   excel_file CLI arg is given (packaged/double-click launch)
├── launch_config.py        # NEW: load/validate launch_config.json (excel_source, port)
└── ...                     # unchanged (parser.py, merger.py, graph.py, phases_manager.py,
                             #   state.py, data_fetcher.py, static/)

launch_config.example.json  # NEW: template committed at repo root, copied into the bundle
scripts/
└── build-windows-standalone.sh  # NEW: PyInstaller --onedir build + bundle assembly + zip,
                                   #   modeled directly on testautomation_monitoring's
                                   #   scripts/build-python-standalone.sh

.github/
└── workflows/
    └── release-deployables.yml  # NEW: build (windows-latest) + publish-release jobs

tests/
└── unit/
    └── test_launch_config.py    # NEW: launch_config.json load/validate/fallback tests
```

**Structure Decision**: Single-project layout, unchanged. The feature adds one small new module
(`launch_config.py`) beside the existing flat `absence_dashboard/` modules, one new top-level
`scripts/` build script, and a standard `.github/workflows/` CI file — no new service, no new
top-level source tree.

## Complexity Tracking

*No unjustified Constitution Check violations — table intentionally empty.*
