# Feature Specification: SharePoint Direct Connection

**Feature Branch**: `003-sharepoint-direct-connection`

**Created**: 2026-07-21

**Status**: Draft

**Input**: User description: "instead of using a local file connect directly to the sharepoint file. Must be read only in order not to corrupt the original file."

## User Scenarios & Testing *(mandatory)*

Context: The dashboard currently loads absence data either from a local `.xlsx` file path or by
downloading a public SharePoint share URL (spec 001, FR-016/FR-024) — both already supported. Today
the manager typically points the dashboard at a local copy of the spreadsheet. This feature makes
the dashboard connect directly to the live SharePoint file as its primary source, removing the need
to maintain a local copy, while guaranteeing the connection can never write to or otherwise modify
the original SharePoint file.

### User Story 1 - Load the dashboard straight from SharePoint, no local copy needed (Priority: P1)

The manager configures the dashboard with a SharePoint file link. The dashboard loads the current
absence timeline directly from that link — no separate download step, no local copy to keep in
sync.

**Why this priority**: This is the core of the request — eliminating the local-file step and its
staleness/maintenance burden is the entire reason for this feature.

**Independent Test**: Configure the dashboard with only a SharePoint link (no local file involved),
load the dashboard, and confirm it shows the SharePoint file's current content.

**Acceptance Scenarios**:

1. **Given** a SharePoint file link configured as the data source, **When** the manager opens the dashboard, **Then** the absence timeline reflects the SharePoint file's current content without any local file having been downloaded or placed by the manager.
2. **Given** the SharePoint file has been edited by someone else since the dashboard last loaded, **When** the manager clicks Reload, **Then** the dashboard shows the updated content from SharePoint.

---

### User Story 2 - The SharePoint file is never modified by the dashboard (Priority: P1)

Whatever the manager does in the dashboard — loading, refreshing, editing dependencies, skill
clusters, or phases — the original SharePoint file is left completely untouched.

**Why this priority**: This is the explicit safety requirement driving the feature — a shared,
authoritative HR data source must not be at risk of accidental corruption from the dashboard tool.
Equal priority to Story 1: connecting directly is only acceptable if it's provably safe.

**Independent Test**: Exercise every dashboard action (initial load, reload, adding/editing/removing
a dependency, skill cluster, and phase) against a live SharePoint file, then confirm — via the
file's SharePoint version history — that no new version was created and its content is unchanged.

**Acceptance Scenarios**:

1. **Given** a dashboard connected to a SharePoint file, **When** the manager performs any action available in the dashboard, **Then** the SharePoint file's content and version history show no change caused by the dashboard.
2. **Given** the dashboard has been used across many sessions over time, **When** the SharePoint file's version history is reviewed, **Then** every change present was made outside the dashboard (by someone editing the source file directly), never by the dashboard itself.

---

### Edge Cases

- What happens when the SharePoint link becomes unreachable (network blocked, link revoked, or sharing permission removed)?
- What happens when the SharePoint file is renamed or moved to a different location — does the configured link still resolve, or does the manager see a clear error?
- What happens when someone else has the SharePoint file open for editing at the exact moment the dashboard reads it?
- What happens on a locked-down network (e.g., the Windows Server 2016/Citrix standalone package from feature 002) where outbound access to SharePoint is blocked? With local-file support removed (FR-004), there is no fallback — the manager sees the clear error required by FR-005 and cannot use the dashboard until SharePoint access is restored.
- What happens when a manager's existing setup still has a local file path configured from before this change? Covered by FR-007 — a clear, specific error rather than a confusing generic failure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST load absence data by connecting directly to a configured SharePoint file link, without requiring the manager to first download or maintain a separate local copy.
- **FR-002**: The system MUST NOT write, modify, upload, delete, or otherwise alter the SharePoint source file, under any dashboard action, at any time.
- **FR-003**: Every load and reload of the SharePoint file MUST fetch its current content at that moment — never a stale, locally cached copy from a previous session.
- **FR-004**: Local-file-path loading (spec 001, FR-016) MUST be removed — a SharePoint file link is the only supported data source going forward. No local-file fallback is provided for development, testing, or offline/network-restricted use.
- **FR-005**: When the SharePoint file cannot be reached or read (link revoked, network blocked, file moved), the system MUST show the manager a clear, actionable error — never silently falling back to stale or incorrect data.
- **FR-006**: The configured SharePoint link MUST persist across restarts so the manager does not need to re-enter it every time the dashboard is started.
- **FR-007**: If an existing configuration still points at a local file path (from before this change), the system MUST show a clear error explaining that local-file support has been removed and a SharePoint link must be configured instead — not a generic or confusing failure.

### Key Entities

- **SharePoint Source Connection**: the configured link the dashboard reads the absence spreadsheet from — read-only by design, with no corresponding write/upload capability anywhere in the system.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A manager can view a fully populated absence dashboard using only a SharePoint link — no local file download or placement step required.
- **SC-002**: Across any number of dashboard sessions and actions, the SharePoint file's version history shows zero versions created by the dashboard.
- **SC-003**: When the SharePoint file is updated by someone else, clicking Reload shows the updated content within 5 seconds (matching the existing refresh performance target).
- **SC-004**: When the SharePoint file is unreachable, the manager sees a clear error message within 5 seconds rather than a blank or broken dashboard.

## Assumptions

- The dashboard continues to use a public ("anyone with the link") SharePoint share URL, the same mechanism already implemented in spec 001 — no new authentication/API integration is introduced, consistent with the project's existing single-manager, no-auth-required scope.
- "Read-only" is achieved by the system never issuing any write/upload request to SharePoint — the existing fetch mechanism (an anonymous download request, parsed without saving back) already behaves this way; this feature makes that behavior an explicit, permanent guarantee rather than an implementation incidental.
- No SharePoint-side write permissions are ever requested or required by the dashboard.
- This feature does not change how dependencies, skill clusters, or phases are stored (`state/state.json` on the machine running the dashboard) — only how the absence spreadsheet itself is sourced.
- Removing local-file support (FR-004) is a breaking change for anyone currently pointing the dashboard at a local copy, including feature 002's Windows/Citrix standalone package (`launch_config.json`'s `excel_source` currently accepts a local path or a URL) and any local-file-based tests or sample data checked into the repository (e.g., `absences.xlsx`). Updating those to SharePoint-URL-only is in scope for this feature's implementation, not a separate follow-up.
- Losing SharePoint connectivity means losing dashboard access entirely (no offline mode) — an accepted tradeoff of this feature, per FR-004's explicit removal of the local-file fallback.
