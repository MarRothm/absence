# Research: SharePoint Delegated Device-Code Authentication

**Phase 0 output** | **Date**: 2026-07-22

No `NEEDS CLARIFICATION` markers remain in the spec. This document records the technical decisions
needed to implement delegated device-code sign-in against Microsoft Graph.

---

## 1. Library choice: `msal` + `msal-extensions`

**Decision**: Use Microsoft's official `msal` (Microsoft Authentication Library for Python) for the
device-code flow, and `msal-extensions` for encrypted, OS-native token-cache persistence.

**Dependency evaluation** (per the constitution's Development Standards): both are Microsoft's own,
MIT-licensed, actively maintained libraries, purpose-built for exactly this scenario (they back
Microsoft's own CLI tools and samples for desktop device-code sign-in). No security or license
concerns.

**Rationale**: Hand-rolling OAuth2 device-code polling, token refresh, and cache encryption would
be a substantial, security-sensitive undertaking with no benefit over the library Microsoft
publishes specifically for this use case (Principle V — simplicity; don't reinvent a security-
critical wheel). `msal-extensions`' `FilePersistenceWithDataProtection` uses Windows DPAPI
(`CryptProtectData`/`CryptUnprotectData`) to encrypt the cache file with a key tied to the manager's
own Windows user account — satisfying FR-004 (cache "protected against casual disclosure... at
minimum, restricted to the manager's own local account") without any custom crypto code.

**Alternatives considered**:
- Hand-rolled `requests`-based OAuth2 device-code implementation: rejected — reinvents token
  refresh, cache format, and encryption; higher risk for a security-relevant flow.
- `requests-oauthlib`: rejected — generic OAuth2 library with no device-code convenience helpers and
  no built-in OS-native cache encryption; `msal` is the Microsoft-endorsed, purpose-fit choice.

## 2. Reading the file: Graph's `/shares` endpoint (not a new file-identification step)

**Decision**: Resolve the SharePoint sharing URL already configured in `launch_config.json` (or
passed via CLI) to a Graph `DriveItem` using `GET /shares/{shareIdEncoded}/driveItem/content`, where
`shareIdEncoded` is the standard base64url encoding of the sharing URL, prefixed `u!` (Microsoft
Graph's documented "share ID" encoding). This is called with `Authorization: Bearer {access_token}`
instead of the old anonymous `?download=1` GET.

**Rationale**: Satisfies FR-007 exactly — the manager's existing sharing link keeps working
unchanged; only the fetch mechanism (authenticated Graph call vs. anonymous download) changes. No
new configuration step to re-locate the file by site/drive/item ID.

**Alternatives considered**:
- Require the manager to reconfigure `excel_source` as a `driveId`/`itemId` pair: rejected — adds a
  manual, error-prone reconfiguration step for zero benefit; the `/shares` endpoint exists
  specifically to avoid this.
- Browse-and-select a file via a Graph site/drive listing at startup: rejected — unnecessary UI
  complexity for a single, already-known file.

## 3. Scope: `Files.Read` only

**Decision**: Request only the delegated `Files.Read` Graph permission.

**Rationale**: `Files.Read` is documented to cover files the signed-in user has access to, including
items shared with them — matching this scenario (the manager can already open the file in a
browser). It is the minimum permission that can satisfy the feature, directly satisfying FR-006
("MUST request only read-level access").

**Residual risk**: If `Files.Read` proves insufficient for this specific site/sharing configuration
during real testing (Graph's exact behavior for cross-site shared-link resolution can vary by
tenant configuration), the fallback is `Sites.Read.All` — still read-only, slightly broader. This
should be validated during implementation against the real tenant, similar to how feature 002 could
not fully validate Windows Server 2016 compatibility from CI alone.

**Alternatives considered**:
- `Files.ReadWrite` or broader: rejected outright — would violate FR-006's read-only guarantee by
  requesting more than is needed, regardless of whether it's ever exercised.

## 4. Token acquisition timing: silent-first, called on every fetch

**Decision**: `graph_auth.acquire_token(...)` always tries `PublicClientApplication.acquire_token_silent()`
first (fast, local cache lookup, auto-renews via the cached refresh token if needed, no user
interaction). Only if silent acquisition fails does it fall back to the interactive device-code flow
(prints the code and verification URL, polls until sign-in completes). This function is called at
**every** fetch — both the initial load in `main()`/`create_app()` and every `/api/refresh` — not
just once at startup.

**Rationale**: The dashboard can stay open far longer than a Graph access token's lifetime (typically
~1 hour); calling silent acquisition on every fetch keeps long-running sessions working without a
restart (spec US2), while still catching genuine expiry/revocation (spec US3).

**Refresh-endpoint constraint**: `/api/refresh` is triggered from the browser, with no console the
manager is watching — there is nowhere to display a device code interactively from inside a Flask
request handler. Decision: `post_refresh()` calls token acquisition in **silent-only** mode (no
interactive fallback); if silent acquisition fails there, it returns a clear error telling the
manager to restart the dashboard (where the console-based device-code prompt can run). The initial
load in `main()`, by contrast, runs on the console and can fall back to the interactive prompt
directly.

**Alternatives considered**:
- Acquire a token once at startup and reuse the same string for the whole run: rejected — would
  silently break on the first refresh after token expiry, regressing US2's "stay signed in across
  normal restarts" into "stay signed in for one hour."
- Attempt an interactive device-code prompt from within the `/api/refresh` handler: rejected — no
  sensible way to surface a device code to the manager from inside a JSON API response; the console
  is the only place this UX works.

## 5. PyInstaller bundling for `msal`/`msal-extensions`

**Decision**: The Windows standalone build (feature 002) needs verification, during implementation,
that PyInstaller correctly bundles `msal`, `msal-extensions`, and their Windows-specific transitive
dependency (`pywin32`, needed for DPAPI access) — a known category of PyInstaller friction, the same
class of issue already found and fixed for `truststore`/the `absence_dashboard` package itself in
this feature line (see feature 003's implementation notes on `run.py`'s import-tracing bug). If the
default build misses modules, `scripts/build-windows-standalone.sh` gets explicit
`--collect-all msal` / `--collect-all msal_extensions` / `--hidden-import win32timezone` flags added
as needed.

**Rationale**: This exact class of "PyInstaller's static analysis misses a module" bug already broke
the standalone build once in this project; treating it as an expected risk to verify — not an
afterthought — avoids repeating it.

**Alternatives considered**: None — this is a verification step, not a design choice.
