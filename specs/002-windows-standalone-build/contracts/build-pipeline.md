# Contract: Build Pipeline (`release-deployables.yml`)

**Phase 1 output** | **Date**: 2026-07-21

The interface between the repository's `main` branch and GitHub Releases. Modeled directly on
`testautomation_monitoring`'s `.github/workflows/release-deployables.yml`.

## Trigger

`push` to `main`.

## Jobs

### `build-windows-standalone`
- Runs on: `windows-latest`
- Steps: checkout → set up Python 3.12 → `pip install -r requirements.txt pyinstaller` →
  `scripts/build-windows-standalone.sh` → upload `dist/absence-dashboard-windows.zip` as a workflow
  artifact named `windows-standalone`.
- Failure mode: any step failing (including the build script's own bundle-structure verification)
  fails the job. No artifact is uploaded. Per FR-006, this means `publish-release` (below) has
  nothing to consume and does not run.

### `publish-release`
- Needs: `build-windows-standalone`
- Runs on: `ubuntu-latest`
- Steps: download the `windows-standalone` artifact → publish a GitHub Release via
  `softprops/action-gh-release`, tag `build-${{ github.sha }}`, name `Build ${{ github.sha }}`,
  attaching the zip, `make_latest: true`.

## Outputs

| Output | Value |
|---|---|
| Release tag | `build-<commit-sha>` |
| Release asset | `absence-dashboard-windows.zip` |
| `make_latest` | `true` — each successful build supersedes the previous one as "Latest" |

## Guarantees

- A failed build never produces or updates a release (FR-006 / SC-004).
- Every successful push to `main` produces exactly one new release, traceable to its commit (FR-005 / SC-003).
- Previously published releases are never edited or deleted by this pipeline.
