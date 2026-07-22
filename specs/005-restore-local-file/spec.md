# Feature Specification: Restore Local File Data Source

**Feature Branch**: `005-restore-local-file`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Reintroduce local-file support as the dashboard's data source. IT has permanently declined both anonymous SharePoint sharing and a delegated OAuth2 app registration, so direct/authenticated SharePoint access is not viable in this tenant. Instead, the manager will periodically download/export the absence spreadsheet from SharePoint themselves (via their own already-authenticated browser session) and point the dashboard at that local file, the same way it worked before the SharePoint-direct-connection feature removed local-file support."

## User Scenarios & Testing *(mandatory)*

Context: Two prior features attempted a direct, live connection from the dashboard to SharePoint —
first anonymously, then via delegated sign-in — and both are now confirmed permanently blocked by
IT policy: this tenant disables anonymous sharing entirely, and IT has declined to create even the
minimal, read-only app registration the sign-in approach needed. There is no remaining technical
path for the dashboard itself to reach SharePoint directly. This feature reverts to the dashboard
reading a local `.xlsx` file the manager maintains themselves — downloading a fresh copy from
SharePoint in their own browser (where they're already signed in) whenever they want the dashboard
to reflect current data, exactly as the dashboard originally worked before the SharePoint-connection
work began.

### User Story 1 - Load the dashboard from a local file, no sign-in required (Priority: P1)

The manager downloads the current absence spreadsheet from SharePoint using their own browser,
saves it locally, and points the dashboard at that file. The dashboard loads immediately — no
device code, no sign-in prompt, no SharePoint connection of any kind.

**Why this priority**: This is the entire reason for the feature — with both SharePoint connection
paths permanently blocked, this is the only way the dashboard can be used at all going forward.

**Independent Test**: With no SharePoint credentials, network access, or prior sign-in of any kind
available, configure the dashboard with a local file path and confirm it loads and displays the
absence data.

**Acceptance Scenarios**:

1. **Given** a local `.xlsx` file path configured as the data source, **When** the manager starts the dashboard, **Then** it loads and displays the file's absence data without any sign-in step or network call to SharePoint.
2. **Given** the dashboard is running, **When** the manager clicks Reload, **Then** it re-reads the same local file — no SharePoint connection is attempted.

---

### User Story 2 - Refresh data by downloading a new copy (Priority: P2)

When the manager wants the dashboard to reflect newer changes, they download a fresh copy from
SharePoint themselves (in their browser, where they're already signed in) and replace the local
file, then reload the dashboard.

**Why this priority**: Keeps the dashboard usable for ongoing work, but is secondary to simply
getting it running again at all (Story 1).

**Independent Test**: Replace the configured local file with an updated version and confirm the
dashboard shows the updated content after a Reload — no re-configuration needed.

**Acceptance Scenarios**:

1. **Given** the manager has replaced the local file at the configured path with a newer export, **When** they click Reload, **Then** the dashboard shows the updated content.

---

### Edge Cases

- What happens when the configured local file doesn't exist or isn't readable (e.g., wrong path, file not yet downloaded)?
- What happens when the local file is open in Excel at the moment the dashboard tries to read it?
- What happens when the manager forgets to refresh the local file for a long time — how does the dashboard make clear how old the displayed data is?
- On the Windows/Citrix standalone package specifically: how does the manager get a freshly downloaded file into the session running the dashboard (e.g., a redirected drive or file transfer), given local file placement already had to work there before any SharePoint-connection feature existed?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST read absence data from a local file path the manager configures, with no SharePoint connection, sign-in, or network dependency required to load or reload the dashboard.
- **FR-002**: The system MUST NOT prompt the manager for any sign-in, device code, or SharePoint authentication step, at any point.
- **FR-003**: The system MUST NOT require any IT/administrative action (app registration, granted permissions, or similar) to be usable.
- **FR-004**: The system MUST continue to show when the currently displayed data was last loaded, so the manager can judge how current it is (existing "last loaded" behavior, now the primary signal of data freshness since there is no live connection).
- **FR-005**: When the configured local file cannot be found or read, the system MUST show a clear, actionable error rather than a blank or broken dashboard.
- **FR-006**: Reload MUST re-read the same configured local file path — it MUST NOT attempt any SharePoint or network access.

### Key Entities

- **Local Data File**: the `.xlsx` file the manager downloads from SharePoint themselves and points the dashboard at; the dashboard's sole data source, entirely disconnected from SharePoint at runtime.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A manager can go from having a downloaded spreadsheet to viewing the dashboard in under 2 minutes, with zero sign-in steps.
- **SC-002**: The dashboard is fully usable with zero IT-provisioned credentials, app registrations, or granted permissions.
- **SC-003**: Replacing the local file and clicking Reload shows the updated content within 5 seconds (matching the existing refresh performance target).
- **SC-004**: 100% of dashboard operations (load, reload, every management action) complete with no attempt to reach SharePoint or any external network service.

## Assumptions

- **This is a full revert, not an additional option**: the SharePoint direct-connection and
  delegated-sign-in mechanisms (the prior two features) are removed entirely, not kept as a dormant
  secondary path. Rationale: IT's decline is described as permanent, the user's own request framing
  ("the same way it worked before... removed local-file support") signals a clean revert, and
  keeping confirmed-non-functional authentication machinery (and its dependencies) around "in case
  policy changes later" adds real, ongoing complexity for no current benefit — contrary to this
  project's simplicity principle. If IT's position ever changes, that work is fully recoverable from
  git history.
- The "must be read-only to avoid corrupting the original file" concern that drove the SharePoint
  work is now moot by construction: the dashboard only ever reads a local copy the manager made
  themselves: it has no code path to the original SharePoint file at all, so accidental corruption
  of the source is structurally impossible, not just guarded against.
- The manager is responsible for remembering to re-download and refresh the local file; the system
  is not required to detect or warn that the file has become stale beyond showing the existing "last
  loaded" timestamp.
- The Windows/Citrix standalone package (an earlier feature) continues to exist and needs its
  configuration/documentation updated to match (local file path instead of a SharePoint link,
  authentication fields removed) — this is expected follow-up work for the implementation, not a
  new decision requiring clarification here.
- No new privacy/compliance concerns are introduced; if anything, this reduces the system's
  footprint back to its original, simpler local-only posture.
