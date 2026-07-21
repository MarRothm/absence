# Feature Specification: Windows Server 2016 (Citrix) Standalone Build

**Feature Branch**: `002-windows-standalone-build`

**Created**: 2026-07-21

**Status**: Draft

**Input**: User description: "Create a standalone version for windows server 2016 in Citrix, analogue to testautomation_monitoring project. Build shall be done as Github Action."

## User Scenarios & Testing *(mandatory)*

Context: The dashboard today only runs from a local Python checkout (virtual environment, `pip install`,
`run.sh`). The manager's actual working environment is a Citrix-published Windows Server 2016 session,
where installing Python — or anything else — is typically not possible or not permitted. This feature
produces a self-contained Windows package the manager can copy into that session and run directly, built
and published automatically, mirroring how the sibling `testautomation_monitoring` project already ships
its own standalone Windows package.

### User Story 1 - Run the dashboard on the Citrix Windows Server 2016 session without installing anything (Priority: P1)

The manager opens their Citrix session (Windows Server 2016), extracts a downloaded package into a
folder they can write to, and starts it with a single launcher — no Python install, no administrator
rights, and no internet-based package installation required.

**Why this priority**: This is the entire reason for the feature — without it, the dashboard cannot be
used at all in the manager's real working environment.

**Independent Test**: On a Windows Server 2016 machine/session with no Python installed and standard
(non-administrator) user rights, extract the package and run the launcher; confirm the dashboard becomes
reachable in a browser.

**Acceptance Scenarios**:

1. **Given** a Windows Server 2016 Citrix session with no Python installed and standard user rights, **When** the manager extracts the downloaded package and runs the launcher, **Then** the dashboard starts and is reachable in a browser with no additional installation step.
2. **Given** the running package pointed at the manager's existing absence spreadsheet (local file path or SharePoint URL) and saved configuration, **When** the dashboard loads, **Then** it shows the same absence timeline, dependencies, skill clusters, and phases as the desktop version.

---

### User Story 2 - Automatic, versioned build via GitHub Actions (Priority: P2)

A maintainer pushes a change to the main branch; a GitHub Actions workflow automatically builds the
Windows standalone package and publishes it as a downloadable release artifact, with no manual
packaging or upload step.

**Why this priority**: Keeps the deployable package current with the codebase and removes manual
packaging effort and error, matching how `testautomation_monitoring`'s release pipeline already works.

**Independent Test**: Push a commit to main and confirm a new package is built and attached to a GitHub
Release tied to that commit, without any manual build or upload step.

**Acceptance Scenarios**:

1. **Given** a commit pushed to the main branch, **When** the workflow runs, **Then** a new Windows standalone package is built and attached to a GitHub Release tied to that commit.
2. **Given** the build step fails, **When** the failure occurs, **Then** no broken or partial package is published, and the failure is visible to whoever triggered the run.

---

### User Story 3 - Same functionality as the local desktop app (Priority: P3)

Everything the manager can already do with the locally-run dashboard — view the absence timeline, edit
dependencies/skill clusters/phases, toggle Show All/Migration Only, refresh from the spreadsheet source
— works identically from the standalone package.

**Why this priority**: Lower urgency than getting the package running at all (P1) and automating its
build (P2), but the package must not be a reduced version of the app.

**Independent Test**: Run through the existing dashboard's acceptance scenarios against the standalone
package and confirm identical behavior to the desktop version.

**Acceptance Scenarios**:

1. **Given** the standalone package running on Windows Server 2016, **When** the manager performs any action available in the desktop version (edit a dependency, add a skill cluster, define a phase, toggle Show All/Migration Only, refresh from the spreadsheet), **Then** the outcome matches the desktop version exactly.

---

### Edge Cases

- What happens when the launcher is started a second time while an instance is already running (the local port is already in use)?
- What happens when the extracted package sits in a read-only location, or one that is reset/cleared when the Citrix session ends, so the app cannot save its configuration/state?
- What happens when the configured spreadsheet source is a SharePoint URL but the Citrix session's network policy blocks outbound access to it?
- What happens when the build step fails partway (e.g., a dependency fails to install) — is a stale or partial package ever left published?
- Since hosted CI build machines do not run Windows Server 2016 itself, how is the package's compatibility with the real Windows Server 2016 target confirmed before it is trusted for use?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a self-contained Windows package of the dashboard that runs without requiring Python, or any other runtime/interpreter, to be pre-installed on the target machine.
- **FR-002**: The package MUST be launchable by a standard (non-administrator) Windows user, with no installer step and no elevation prompt.
- **FR-003**: The package MUST run on Windows Server 2016, including when accessed through a Citrix-published desktop or application session.
- **FR-004**: A dedicated GitHub Actions workflow MUST automatically build the Windows standalone package on every push to the main branch, with no manual packaging or upload step by a maintainer.
- **FR-005**: The GitHub Actions workflow MUST publish each successful build as a downloadable artifact attached to a GitHub Release tied to the triggering commit.
- **FR-006**: If the build fails, the workflow MUST NOT publish a package for that run, and the failure MUST be visible to whoever triggered it.
- **FR-007**: The standalone package MUST provide the same functionality as the existing locally-run dashboard — absence timeline view, dependency/skill-cluster/phase management, the Show All/Migration Only toggle, and spreadsheet refresh from a local file or SharePoint URL — with no feature reduced or behaving differently.
- **FR-008**: The standalone package MUST persist the manager's saved configuration (dependencies, skill clusters, phases, UI state) across restarts, the same way the existing desktop app does.
- **FR-009**: Starting the package MUST require at most one user action (e.g., one double-click) to start the local server and open the dashboard.
- **FR-010**: The system MUST document the minimum steps and prerequisites (e.g., an available Windows Server 2016/Citrix session) needed to deploy and run the package.

### Key Entities

- **Standalone Package**: the self-contained, pre-built Windows distribution of the dashboard — application code plus everything needed to run it — that a manager extracts and launches directly, with no separate install step.
- **Build Pipeline**: the automated GitHub Actions workflow that produces and publishes the Standalone Package whenever the main branch changes.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A manager with no Python installed and no administrator rights can go from downloading the package to viewing their absence dashboard in under 5 minutes.
- **SC-002**: Every dashboard feature available in the local desktop app (viewing the absence timeline; editing dependencies, skill clusters, and phases; toggling Show All/Migration Only; refreshing from the spreadsheet) behaves identically when run from the standalone package.
- **SC-003**: Every push to the main branch results in a new downloadable package appearing within that same build run, with zero manual packaging steps.
- **SC-004**: A build that fails never results in a published, downloadable package for that commit.
- **SC-005**: At least once per release, the package is confirmed — via a documented manual check — to start and serve the dashboard on an actual Windows Server 2016 Citrix session.

## Assumptions

- The standalone package remains a single-user tool for the same one manager the existing dashboard already targets; it does not add multi-user or concurrent-session support.
- "Analogue to `testautomation_monitoring`" means matching that project's overall approach: a self-contained, extract-and-run bundle (the app and everything it needs to run, bundled together) with a simple launcher, built and published automatically via GitHub Actions to GitHub Releases — not a rewrite in a different language or framework.
- The package keeps its writable configuration/state file alongside the extracted package folder, consistent with both the existing desktop app and the `testautomation_monitoring` package; the manager's Citrix session is assumed to provide a persistent, writable location for that folder (e.g., a redirected home drive, or a local path that isn't reset between sessions).
- Hosted CI build machines do not offer a Windows Server 2016 image; the package is built on the newest available Windows build machine, and its compatibility with the real Windows Server 2016 target is verified by a manual smoke test rather than by the build itself running on Server 2016.
- Both existing spreadsheet source options (local file path and SharePoint URL) remain supported unchanged; whether the Citrix session's network policy allows the SharePoint option is an environment concern outside this feature's control.
- No new authentication, encryption, or data-retention requirements are introduced; the package inherits the existing app's privacy/compliance posture (localhost-only, single authorized user).
