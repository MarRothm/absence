# Research: Windows Server 2016 (Citrix) Standalone Build

**Phase 0 output** | **Date**: 2026-07-21

No `NEEDS CLARIFICATION` markers remain in the spec or Technical Context. This document records the
technical decisions made to turn the spec's requirements into a concrete approach, each modeled on
the sibling `testautomation_monitoring` project's already-shipped standalone-build feature.

---

## 1. Packaging tool and layout

**Decision**: PyInstaller, `--onedir` mode (a folder containing the interpreter, dependencies, and
an executable — not a single self-extracting `--onefile` exe).

**Rationale**: `testautomation_monitoring` already ships this exact approach for the same problem
(old/locked-down Windows target, no Python allowed). `--onedir` starts faster than `--onefile`
(which re-extracts to a temp directory on every launch) and needs no install step — matching FR-002
(no installer, no elevation) and FR-009 (one action to start).

**Alternatives considered**:
- `--onefile`: rejected — slower cold start on every launch, and no benefit here since the bundle is
  already delivered as a zip.
- A different packager (cx_Freeze, Nuitka): rejected — no reason to diverge from the analogue
  project's already-proven, already-understood tool choice (Principle V — simplicity).

**Dependency evaluation** (per the constitution's Development Standards — third-party dependencies
must be evaluated for security and license compatibility before adoption): PyInstaller is
build-time-only (never shipped as a runtime import, never added to `requirements.txt`). It is
licensed under GPL-2.0-or-later, but its bootloader carries an explicit linking exception that
permits distributing the bundled application under any license — the packaged app is not made GPL
by using it. `testautomation_monitoring` already ships production releases built with it, giving an
existing security track record inside this organization's own toolchain. No further evaluation is
needed before adoption.

## 2. Build script and CI workflow shape

**Decision**: A bash build script (`scripts/build-windows-standalone.sh`) run under git-bash on a
`windows-latest` GitHub Actions runner, invoked by a two-job workflow
(`.github/workflows/release-deployables.yml`): a `build-windows-standalone` job that builds and
uploads the zip as a workflow artifact, and a `publish-release` job that downloads it and publishes
a GitHub Release tagged `build-${{ github.sha }}`.

**Rationale**: Directly mirrors `testautomation_monitoring`'s `scripts/build-python-standalone.sh`
and `release-deployables.yml`, which already solves: PyInstaller invocation, `--add-data` for static
assets, a `.bat` launcher using `pushd "%~dp0"` (so it works from a UNC/network home-drive path, common
in Citrix profile setups), a bundle-structure verification step, and a `zip`/`Compress-Archive`
fallback since `windows-latest` git-bash has no `zip` on `PATH`. Reusing this pattern satisfies
FR-004/FR-005/FR-006 with no new design risk.

**Alternatives considered**:
- Trigger on tags/releases instead of every push to `main`: rejected — spec FR-004 and the
  analogue's existing behavior both call for a build on every push to `main`.
- A PowerShell build script instead of bash: rejected — the analogue's bash script already handles
  the Windows-runner quirks (separator character for `--add-data`, missing `zip`); no reason to
  rewrite a working script in a different shell.

## 3. No Windows Server 2016 CI runner image

**Decision**: Build on `windows-latest` (currently a newer Windows Server release than 2016);
compatibility with the real Windows Server 2016 target is verified by a documented manual smoke
test on an actual Citrix session, once per release (spec SC-005) — not by CI.

**Rationale**: GitHub-hosted runners do not offer a Windows Server 2016 image, so CI cannot validate
against the literal target OS. `testautomation_monitoring` faces the identical gap and has not
needed anything more than `windows-latest` plus real-world use for its own old-Windows target.
Python 3.10+ and PyInstaller's Windows bundles depend only on the Universal C Runtime, which ships
built into Windows Server 2016 (unlike Windows 7/8, which need a Windows Update backport) — so the
residual risk is low, not zero.

**Alternatives considered**:
- Self-hosted Windows Server 2016 runner: rejected as disproportionate — stands up and maintains
  dedicated infrastructure for a single-manager tool; the manual smoke test (SC-005) already gives
  the needed confidence at far lower cost.

## 4. Supplying the excel source and port to a double-clicked executable

**Decision**: Add `launch_config.json` (a small JSON file with `excel_source` and `port`) that
`app.py`'s `__main__` block reads when no `excel_file` CLI argument is supplied. The existing
CLI-argument path (`python app.py path/to/file.xlsx`) is untouched for local development. The build
script copies a committed `launch_config.example.json` into the bundle as a working
`launch_config.json` (pre-filled with a sensible placeholder), the same "ship a real, working default
next to the `.example`" pattern the analogue uses for its `.env`.

**Rationale**: The `.bat` launcher runs the exe with no arguments (FR-009 — one double-click, no
console interaction), so the CLI's required positional argument can't be satisfied interactively.
A config file next to the executable is also what the analogue project already does for its own
startup parameter (`PORT` in `.env`), and reusing `state.py`'s existing stdlib-`json`
load/parse/write pattern avoids introducing a new dependency (e.g., `python-dotenv`) for a
two-field file (Principle V).

**Alternatives considered**:
- Requiring the manager to edit the `.bat` launcher to embed their file path: rejected — fragile,
  error-prone to edit a script, and breaks on every re-extraction of a fresh package.
- An interactive console prompt on startup: rejected — contradicts FR-009's one-action requirement
  and the existing app's non-interactive design.
- Reusing `state/state.json` for the source path/port: rejected — `state.json` is the *saved UI
  configuration* (dependencies/clusters/phases) that already has well-defined semantics and tests;
  overloading it with a startup-only parameter conflates two different lifecycles (created once at
  install-time vs. mutated continuously by the running app).

## 5. Bundling static frontend assets

**Decision**: `--add-data "absence_dashboard/static;absence_dashboard/static"` (Windows path
separator), matching Flask's `static_folder="static"` lookup relative to the package.

**Rationale**: Directly matches how the analogue project bundles its own `src/api/static` — PyInstaller
needs an explicit `--add-data` entry for any non-Python file Flask serves at runtime.

**Alternatives considered**: None — this is a mechanical requirement of using PyInstaller with Flask's
`static_folder`, not a judgment call.
