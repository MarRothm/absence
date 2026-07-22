# Research: Restore Local File Data Source

**Phase 0 output** | **Date**: 2026-07-22

No `NEEDS CLARIFICATION` markers remain in the spec. This document records the technical decisions
needed to implement a clean, complete revert.

---

## 1. Scope of the revert: full removal, not a dormant secondary path

**Decision**: Delete `graph_auth.py` outright; remove `msal`/`msal-extensions`/`truststore`/
`requests` from `requirements.txt`; strip all SharePoint/Graph/auth code from `data_fetcher.py`,
`launch_config.py`, and `app.py` rather than gating it behind a config flag.

**Rationale**: Already established in spec.md's Assumptions — IT's decline is permanent, and
keeping confirmed-non-functional authentication machinery "just in case" is exactly the kind of
unjustified complexity the constitution's simplicity principle rules out. A config flag or
dead-but-present code path would still carry the full dependency and test-maintenance weight for a
capability that cannot be exercised in this deployment. The prior implementation remains fully
recoverable from git history if the tenant's policy ever changes.

**Alternatives considered**:
- Keep the SharePoint/auth code behind an opt-in flag: rejected — doubles the maintenance surface
  (two fetch paths, two sets of tests, four extra dependencies) for a path that cannot currently be
  used at all.

## 2. `data_fetcher.get_workbook()`: direct local read, no URL branch at all

**Decision**: `get_workbook(source)` becomes `load_workbook(source, read_only=True, data_only=True)`
directly — no scheme detection, no HTTP client, no Graph endpoint construction.

**Rationale**: With SharePoint access removed entirely (not "removed as default, still detectable"),
there is nothing left to branch on. This is simpler than even the original spec 001 version (which
detected both local paths and URLs) — spec 005's FR-001/FR-006 establish local-file-only, not a
restored dual-support model.

**Alternatives considered**:
- Restore both local-path and URL detection (spec 001's original dual-support): rejected — spec
  005's requirements are explicit that no network/SharePoint access happens under any circumstance,
  which a URL branch would contradict even if it's never reached in practice today.

## 3. `launch_config.json` / CLI argument: existing-local-path validation restored

**Decision**: `load_launch_config()` and `resolve_launch_source()`'s CLI-argument branch both
validate `excel_source`/`excel_file` as an existing local path (`os.path.exists(...)`), raising the
same actionable `FileNotFoundError` pattern used throughout this project for a missing/invalid
value. `client_id`/`tenant_id` are removed from both.

**Rationale**: Restores the validation shape from before feature 003, adapted to the current
`load_launch_config()` return signature. Reusing the exact same error-message pattern (rather than
inventing a new one) keeps the manager-facing experience consistent with every other error case in
this app.

**Alternatives considered**: None — this is a direct, mechanical reversal of feature 003's own
validation change (which itself just flipped the acceptance direction of the exact same check).

## 4. Dependency cleanup: verified `requests` has no other caller

**Decision**: Remove `requests` from `requirements.txt` alongside `truststore`/`msal`/
`msal-extensions`.

**Rationale**: Confirmed via a repo-wide search that `requests` is only imported in
`data_fetcher.py` (and test files being rewritten in lockstep) — once the HTTP fetch path is gone,
nothing else in the codebase needs it. Leaving an unused dependency in `requirements.txt` would be
exactly the kind of needless residue this revert is meant to clean up.

**Alternatives considered**: Leave `requests` in case a future feature needs it again: rejected — if
a future feature needs it, it can be re-added then; carrying unused dependencies "just in case" is
the same anti-pattern decision #1 already rejected, applied to a smaller thing.

## 5. Documentation: living docs updated, historical specs frozen (same precedent as before)

**Decision**: Update `README.md` (always current), `specs/002-windows-standalone-build/quickstart.md`
(operational runbook), and add/update forward-pointing notices in `specs/001-absence-dashboard/
quickstart.md`, `specs/003-sharepoint-direct-connection/quickstart.md`, and `specs/004-sharepoint-
device-code-auth/quickstart.md` — all pointing directly at this feature's `quickstart.md` as current
truth (rather than a multi-hop chain through 003→004→005). Leave every `spec.md`/`plan.md`/
`research.md`/`data-model.md`/`contracts/*.md` of features 002/003/004 untouched as historical
record.

**Rationale**: Identical reasoning to research.md #4 in feature 003 and feature 004's own docs
decision — operational docs a manager might actually be reading must stay accurate; historical
planning records document what was true and decided at the time, and rewriting them would erase
real project history (including the useful lesson of *why* 003 and 004 didn't pan out) for no
operational benefit.

**Alternatives considered**:
- Chain each notice to only the next feature (003→"see 004", 004→"see 005"): rejected in favor of
  pointing every stale doc directly at 005 — with three superseding features now in the chain,
  multi-hop pointers become an unnecessary scavenger hunt for a reader just trying to find current
  setup instructions.
