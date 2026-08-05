# Quickstart: Cumul Groups (replacing Dependencies)

**Phase 1 output** | **Date**: 2026-08-05

---

## What changed

The "Dependencies" feature is gone. In its place: **Cumul Groups** — named groups of two or more
people whose absence *at the same time* is a risk to the project. The dashboard now tells you, at a
glance, which weeks put a cumul group at risk, and who's covering solo when everyone else in a group
is out.

---

## Defining a cumul group

1. Click **Cumul** in the header to open the panel (replaces the old "Dependencies" button).
2. Enter a group name, pick two or more members, optionally set an active date range.
3. Click **Create Cumul Group**.

Edit or remove a group directly from the list in the same panel — both act on the group by name, the
same way editing a Skill Cluster does today.

---

## What counts as a "cumul"

A group is flagged at risk for a given week only when **every member's own absence block is longer
than 5 calendar days** (a short, ≤5-day absence is never treated as critical) **and** those critical
absences overlap on **at least one shared day** within that week. This definition is shown directly
in the Cumul panel and in the risk tooltip on the dashboard — you don't need to remember it or look
it up elsewhere (FR-016).

If every member but one has a critical absence in a given week, the remaining present member is
flagged as **sole coverage** for that group/week.

---

## Reading the dashboard

| Signal | Meaning |
|---|---|
| Highlighted day cell + tooltip naming the group | That day falls in a cumul risk week for that group |
| Sole-coverage badge on a member's row | That member is the only one still present while their cumul group is critically absent |
| Multiple groups at risk in the same week | Each is named individually in the tooltip — never just "something's wrong" |

---

## Data refresh behavior

When you click **Reload**, if the underlying roster changes:

- A member removed from the dataset is also removed from any cumul group they belonged to.
- If a group would drop below 2 valid members, the whole group is removed automatically.
- Either way, the change is reported the same way stale cluster references are reported today.

---

## What's gone

No more directional "from/to" dependency edges, no `/api/dependencies` routes, no dependency panel.
Existing dependency data is **not** converted to cumul groups — it's discarded when this feature
ships, since a one-directional relationship has no reliable symmetric equivalent (see
[spec.md](./spec.md#assumptions)).
