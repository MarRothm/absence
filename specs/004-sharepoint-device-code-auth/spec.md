# Feature Specification: SharePoint Delegated Device-Code Authentication

**Feature Branch**: `004-sharepoint-device-code-auth`

**Created**: 2026-07-22

**Status**: Draft

**Input**: User description: "Replace the anonymous SharePoint download with authenticated Microsoft Graph API access using delegated OAuth2 login (device-code flow), since the tenant disables anonymous 'Anyone with the link' sharing and app-only client-credential access will not be granted by IT. The manager signs in with their own Barmenia account; the app reads the file with their existing permissions."

## User Scenarios & Testing *(mandatory)*

Context: The prior SharePoint-connection feature assumed a public, anonymous "Anyone with the
link" share URL, matching how this tenant's SharePoint was expected to be configured. In real use,
it was confirmed that this tenant disables anonymous sharing entirely — every available link type
requires the requester to already be a signed-in, authorized identity. An anonymous download can
never work here. This feature replaces that anonymous connection with the manager signing in with
their own account (delegated OAuth2, device-code flow) so the dashboard reads the file with the
manager's own existing SharePoint permissions — while preserving the read-only guarantee the
project has required from the very first SharePoint-related request.

### User Story 1 - Sign in once to unblock the dashboard (Priority: P1)

The manager launches the dashboard for the first time (or after signing out). Since no anonymous
access is possible, the dashboard presents a short code and a verification web address. The manager
opens that address on any device/browser, enters the code, and signs in with their own account. The
dashboard then loads the absence data using the manager's own SharePoint permissions.

**Why this priority**: Without this, the dashboard cannot load any data at all in this tenant — this
is the core capability that unblocks everything else.

**Independent Test**: With no cached session, launch the dashboard; confirm it presents a device
code and verification URL; complete sign-in with an account that has access to the configured file;
confirm the dashboard then loads and displays the absence data.

**Acceptance Scenarios**:

1. **Given** no cached session, **When** the manager launches the dashboard, **Then** a device code and a verification web address are shown, and the dashboard does not proceed until sign-in is completed or the code expires.
2. **Given** the manager completes sign-in with an account that has access to the configured SharePoint file, **When** sign-in finishes, **Then** the dashboard loads and displays the current absence data.

---

### User Story 2 - Stay signed in across normal restarts (Priority: P1)

Once signed in, the manager can close and reopen the dashboard without going through the device-code
process again, for as long as their session remains valid.

**Why this priority**: Matches the existing "one action to launch" expectation from the standalone
package; requiring a fresh sign-in on every single launch would be a serious usability regression
compared to today.

**Independent Test**: Sign in successfully, restart the dashboard, and confirm it loads directly
without any authentication prompt.

**Acceptance Scenarios**:

1. **Given** a previously completed sign-in, **When** the manager restarts the dashboard, **Then** it loads the absence data without prompting for a new device code.

---

### User Story 3 - Graceful re-authentication when the session expires (Priority: P2)

When the manager's cached session is no longer valid (expired, revoked, or never existed), the
dashboard clearly asks them to sign in again rather than failing silently or hanging.

**Why this priority**: Session expiry is a normal, expected event, not an error condition — it needs
to be handled predictably, but it's a secondary concern to getting sign-in working at all (US1) and
keeping it persistent (US2).

**Independent Test**: Invalidate the cached session (e.g., simulate expiry) and relaunch the
dashboard; confirm a new device-code prompt appears instead of a crash, hang, or unexplained error.

**Acceptance Scenarios**:

1. **Given** an expired or invalid cached session, **When** the manager launches the dashboard, **Then** a new device-code sign-in prompt is shown, with no crash or silent failure.

---

### User Story 4 - The read-only guarantee carries forward unchanged (Priority: P2)

Everything the manager does in the dashboard — loading, reloading, and editing dependencies, skill
clusters, and phases — continues to leave the SharePoint file completely untouched, exactly as
guaranteed by the previous SharePoint-connection feature.

**Why this priority**: This is the non-negotiable safety property this project has required since
the very first SharePoint-related request ("must be read only in order not to corrupt the original
file"); switching to authenticated access must not weaken it.

**Independent Test**: Exercise every dashboard action while signed in, then confirm via SharePoint's
version history that no new version was ever created by the dashboard.

**Acceptance Scenarios**:

1. **Given** the dashboard is authenticated and in use, **When** the manager performs any dashboard action, **Then** the SharePoint file's content and version history show no change caused by the dashboard.

---

### Edge Cases

- What happens if the manager closes the browser or abandons the device-code prompt without completing sign-in?
- What happens if the device code expires (typically after a fixed window, e.g. ~15 minutes) before the manager completes sign-in?
- What happens if the manager signs in with an account that does not have access to the configured SharePoint file?
- What happens if the tenant's security policy requires multi-factor authentication or additional verification during sign-in?
- What happens if the machine/session profile is reset between Citrix logins, wiping the cached session (e.g., a non-persistent profile)?
- What happens if the same shared machine is used by more than one person — do their sessions collide, given the dashboard's existing single-manager design?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST authenticate to SharePoint by having the manager sign in with their own account (delegated access), replacing the anonymous download mechanism entirely.
- **FR-002**: Sign-in MUST use the device-code flow — presenting a short code and a verification web address the manager completes on any device or browser — rather than requiring a local browser redirect listener on the dashboard's own machine.
- **FR-003**: The system MUST cache the signed-in session so the manager is not required to sign in again on every launch.
- **FR-004**: The cached session MUST be protected against casual disclosure (not stored as plain readable text), restricted to the manager's own local account at minimum.
- **FR-005**: When the cached session is missing, expired, or revoked, the system MUST prompt the manager to sign in again with a clear message, rather than crashing, hanging, or failing silently.
- **FR-006**: The system MUST request only read-level access — it MUST NOT be able to write, modify, upload, or delete the SharePoint source file, at any time, under any dashboard action, carrying forward the same guarantee as the prior SharePoint-connection feature.
- **FR-007**: The system MUST continue reading the same configured SharePoint file reference the manager already has set up — signing in must not require re-locating or re-identifying the file.
- **FR-008**: If the signed-in account does not have access to the configured file, the system MUST show a clear, actionable error that distinguishes this from a general connection failure.

### Key Entities

- **Signed-In Session**: the manager's authenticated access, obtained via device-code sign-in, used to read the SharePoint file with their own existing permissions. Cached locally, protected from casual access, and re-requested when it expires or is invalid.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A manager with no prior session can go from launching the dashboard — including completing sign-in — to viewing their absence data in under 3 minutes.
- **SC-002**: After a successful sign-in, the dashboard loads with no authentication prompt on at least the next 10 consecutive normal restarts.
- **SC-003**: Across any number of dashboard sessions and actions, the SharePoint file's version history shows zero versions created by the dashboard.
- **SC-004**: Every time sign-in is required (first use or after expiry), the attempt either succeeds with a working dashboard or fails with a message telling the manager what to do next — never a silent hang.

## Assumptions

- A one-time Azure AD (Entra ID) app registration is required for this delegated sign-in flow — a
  public-client registration with no client secret, requesting only a minimal read-only delegated
  permission (e.g., read access to files). This is a substantially lower-privilege, lower-friction
  request than the app-only/client-credentials registration IT already declined, but it still
  requires IT/tenant-admin action (creating the registration, and possibly granting consent for the
  requested permission if user self-consent is disabled tenant-wide) before this feature can be used.
- The manager's own account already has whatever SharePoint permissions are needed to view the
  configured file (true today, since they can already open it in a browser) — this feature reads the
  file with exactly those same permissions, nothing more.
- Device-code flow is chosen over an interactive browser-redirect flow because it needs no local
  redirect listener on the dashboard's machine — a better fit for the locked-down Windows Server
  2016/Citrix session (the standalone-build feature) with no guaranteed default-browser or local-port
  behavior.
- The existing single-manager scope is unchanged; this feature does not add multi-user session
  isolation. If a shared machine is used by more than one person, they share a single cached
  session — solving that is out of scope here.
- The existing configuration (e.g. `launch_config.json` / CLI argument) continues to reference the
  same SharePoint file the manager already has set up; only the underlying fetch mechanism changes
  from an anonymous download to a signed-in, permission-checked read.
