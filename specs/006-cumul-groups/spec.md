# Feature Specification: Cumul Groups (replacing Dependencies)

**Feature Branch**: `006-cumul-groups`

**Created**: 2026-08-05

**Status**: Draft

**Input**: User description: "change the dependency feature to a cumul feature. Allow definition of cumul groups. A cumul group is a group of ressources that when absent together pose a risk to the project flow. The old dependency feature is not needed anymore. A cumul shall be made visible. Suggestions how to make it visible are welcome."

## Clarifications

### Session 2026-08-05

- Q: What does the 5-day threshold measure — each member's own continuous absence block, or the length of the group's simultaneous-overlap window? → A: Each member's own continuous absence block must exceed 5 calendar days to count as "critical"; a cumul risk requires every group member to have such a critical absence overlapping at the same time.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Define a cumul group (Priority: P1)

As a project coordinator, I want to define a "cumul group" — a named set of two or more resources whose simultaneous absence would put project flow at risk — instead of the old one-directional dependency relationship, so that I can capture real-world risk situations that are symmetrical (any subset of the group being absent together is a problem), not just resources depending on a single named person.

**Why this priority**: This is the foundational data model change. Without the ability to define cumul groups, none of the risk-visibility value can be delivered, and the old dependency feature cannot be safely retired.

**Independent Test**: Can be fully tested by creating a cumul group of two or more existing resources and confirming it is saved, listed, editable, and removable — independent of any visibility/highlighting behavior.

**Acceptance Scenarios**:

1. **Given** a loaded roster of resources, **When** a coordinator creates a cumul group with a name and two or more resources from that roster, **Then** the group is saved and appears in the list of cumul groups.
2. **Given** an existing cumul group, **When** a coordinator edits its name or membership, **Then** the updated group replaces the previous definition.
3. **Given** an existing cumul group, **When** a coordinator removes it, **Then** it no longer appears in the list and no longer affects risk visibility.
4. **Given** an attempt to create a group with fewer than two resources, **When** the coordinator submits it, **Then** the system rejects the request and explains that at least two resources are required.
5. **Given** an attempt to create a group whose resource set exactly duplicates an existing group's resource set, **When** the coordinator submits it, **Then** the system rejects the request as a duplicate.

---

### User Story 2 - See cumul risk at a glance (Priority: P1)

As a project coordinator, I want weeks where an entire cumul group is absent together to be immediately obvious on the dashboard, so I can intervene (reschedule, reassign, escalate) before the risk materializes rather than discovering it after the fact.

**Why this priority**: Visibility is the entire point of tracking cumul groups — a correctly modeled but invisible risk delivers no value. This is called out explicitly by the requester.

**Independent Test**: Can be fully tested by setting up absences that fully overlap for all members of a defined cumul group in a given week and confirming the dashboard clearly flags that week for that group, distinctly from weeks with no such overlap.

**Acceptance Scenarios**:

1. **Given** a cumul group whose members are all absent during the same calendar week, **When** the coordinator views the dashboard, **Then** that week is visually flagged as a cumul risk, for every member of that group, without requiring the coordinator to open a separate detail view.
2. **Given** a cumul group whose members are absent on overlapping but not fully coincident days, **When** the coordinator views the dashboard, **Then** the week is only flagged as a cumul risk if every member's own continuous absence block exceeds 5 calendar days and all those critical absences share at least one common day within that week; absences of 5 calendar days or fewer are never counted toward the flag.
3. **Given** multiple cumul groups at risk in the same week, **When** the coordinator views the dashboard, **Then** each affected group's risk is distinguishable (a coordinator can tell which group(s) are at risk, not just that "something" is at risk).
4. **Given** a cumul group where all members but one are absent in a given week, **When** the coordinator views the dashboard, **Then** the one remaining present member is flagged as the sole coverage for that group in that week.

---

### User Story 3 - Cumul groups stay consistent as the roster changes (Priority: P2)

As a project coordinator, I want cumul groups to automatically stay valid when the underlying resource list is refreshed (people added, removed, or renamed in the source data), so that I don't have to manually audit group definitions after every data refresh.

**Why this priority**: This mirrors the existing safety net the old dependency feature had; without it, refreshing data could silently leave broken or misleading cumul groups behind.

**Independent Test**: Can be fully tested by defining a cumul group, refreshing the underlying dataset with one member removed, and confirming the group is corrected or removed and the change is reported to the coordinator.

**Acceptance Scenarios**:

1. **Given** a cumul group referencing a resource, **When** the underlying dataset is refreshed and that resource is no longer present, **Then** the group is automatically removed (or reduced, if removal would still leave two or more valid members) and the coordinator is told what changed.
2. **Given** a data refresh that removes no resources referenced by any cumul group, **When** the refresh completes, **Then** all cumul groups remain unchanged.

---

### Edge Cases

- What happens when a cumul group would be left with only one valid member after a data refresh? It is treated as no longer meeting the minimum group size and is removed automatically, reported the same way other stale references are reported today.
- What happens when the same resource belongs to multiple cumul groups? Each group is evaluated and displayed independently; a resource can be part of any number of groups.
- What happens when a coordinator tries to add the same resource twice within one group? The duplicate is ignored/rejected — a resource appears at most once per group.
- What happens to previously defined dependency relationships when this feature ships? They are retired along with the dependency feature itself; no automatic conversion to cumul groups is performed, since a directional "from/to" relationship has no reliable one-to-one equivalent as a symmetric group.
- What happens when a member's continuous absence block is exactly 5 calendar days? It does not count as "critical" (the threshold is strictly more than 5 calendar days) and never contributes to a cumul risk or a sole coverage flag, even if it overlaps with other members' critical absences.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST allow a coordinator to create a cumul group consisting of a name and two or more resources selected from the currently loaded dataset.
- **FR-002**: System MUST reject creation or edits of a cumul group that would leave it with fewer than two member resources.
- **FR-003**: System MUST reject creation of a cumul group whose name or whose exact set of member resources duplicates an existing cumul group.
- **FR-004**: Users MUST be able to view a list of all currently defined cumul groups and their membership.
- **FR-005**: Users MUST be able to edit an existing cumul group's name and/or membership.
- **FR-006**: Users MUST be able to remove an existing cumul group.
- **FR-007**: System MUST treat a member's continuous absence block as "critical" only when it exceeds 5 calendar days, and MUST determine, for each planning week, whether every member of a cumul group has a critical absence overlapping on at least one common day during that week ("cumul risk week"); absence blocks of 5 calendar days or fewer are never critical and MUST NOT trigger a cumul risk.
- **FR-008**: System MUST visually flag cumul risk weeks on the dashboard for every affected member, without requiring an extra click or navigation to see that a risk exists.
- **FR-009**: System MUST identify weeks in which exactly one member of a cumul group remains present while every other member has a critical (more than 5 calendar day) absence, and flag that member as sole coverage for the group in that week.
- **FR-010**: System MUST allow a coordinator to identify, for any flagged week, which specific cumul group(s) are at risk.
- **FR-011**: System MUST remove the old dependency feature (directional from/to relationships and all of its data-entry, editing, and display surfaces) entirely.
- **FR-012**: System MUST NOT migrate or auto-convert existing dependency data into cumul groups; retiring the feature discards prior dependency definitions.
- **FR-013**: When the underlying resource dataset is refreshed, System MUST automatically remove cumul groups (or the specific members) that reference resources no longer present, and MUST report which groups/members were removed, consistent with how other stale references are reported today.
- **FR-014**: System MUST persist cumul groups so they remain available across sessions until explicitly edited or removed.
- **FR-015**: System MUST validate, when creating or editing a cumul group, that every named member exists in the currently loaded dataset.
- **FR-016**: System MUST display the definition of what constitutes a cumul (every group member simultaneously in a critical, more-than-5-calendar-day absence) as visible explanatory text wherever cumul risk is shown on the dashboard, so a coordinator can interpret the flag without consulting outside documentation.

### Key Entities *(include if feature involves data)*

- **Cumul Group**: A named, unordered set of two or more resources whose simultaneous absence poses a risk to project flow. Replaces the old directional "dependency" relationship.
- **Resource (Member)**: An individual whose absence periods are already tracked by the system; unchanged by this feature except for how it participates in risk grouping.
- **Cumul Risk Week**: A specific calendar week in which every member of a given cumul group has a critical absence (a continuous absence block exceeding 5 calendar days) overlapping on at least one common day.
- **Sole Coverage Flag**: A per-week, per-group indicator marking the single member of a cumul group who remains present while every other member of that group has a critical (more than 5 calendar day) absence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A coordinator can spot every currently at-risk cumul group directly from the main dashboard view, with no extra clicks, within 5 seconds of opening it.
- **SC-002**: A coordinator can define a new, valid cumul group in under 30 seconds.
- **SC-003**: 100% of the old dependency feature's data-entry and display surfaces are removed and replaced by cumul groups; no leftover dependency terminology or controls remain.
- **SC-004**: After any data refresh that removes a resource referenced by a cumul group, 100% of affected groups are automatically corrected and the coordinator is informed of exactly what changed.
- **SC-005**: A coordinator can visually distinguish, without hovering or clicking, between a week with no cumul risk, a week with a single remaining sole-coverage resource, and a week where an entire group is absent together.

## Assumptions

- A cumul group requires a minimum of two member resources; there is no fixed maximum.
- A resource may belong to zero, one, or multiple cumul groups simultaneously.
- "Absent together" for a given week means every member of the group has a critical absence — a continuous absence block exceeding 5 calendar days — that overlaps on at least one common day within that calendar week. Absences of 5 calendar days or fewer are considered non-critical and are excluded from this determination.
- Cumul groups may optionally be scoped to an active date range, mirroring the optional time-boxing the old dependency feature offered; groups without a specified range are always active.
- Existing dependency data is discarded (not converted) when this feature ships, since the old relationship was directional and has no reliable symmetric equivalent.
- Cumul group names must be unique, consistent with how other named groupings (e.g., skill clusters) are handled today.
