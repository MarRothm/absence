from datetime import date


class DependencyGraph:
    def __init__(self, edges: list = None):
        self._edges = list(edges or [])

    def edges(self) -> list:
        return list(self._edges)

    def add_dependency(
        self,
        from_member: str,
        to_members: list,
        valid_members: set,
        active_from: str = None,
        active_to: str = None,
    ) -> None:
        if from_member not in valid_members:
            raise ValueError(f"Member '{from_member}' not in loaded dataset.")
        if not to_members:
            raise ValueError("to_members must not be empty.")
        for m in to_members:
            if m not in valid_members:
                raise ValueError(f"Member '{m}' not in loaded dataset.")
        if (active_from is None) != (active_to is None):
            raise ValueError("Provide both active_from and active_to, or neither.")
        if active_from is not None and active_from > active_to:
            raise ValueError(
                f"active_from ({active_from}) must not be after active_to ({active_to})."
            )
        pool_key = frozenset(to_members)
        if any(
            e["from_member"] == from_member
            and frozenset(e["to_members"]) == pool_key
            and e.get("active_from") == active_from
            and e.get("active_to") == active_to
            for e in self._edges
        ):
            raise ValueError(
                f"Dependency {from_member}→{sorted(to_members)} already exists."
            )
        edge: dict = {"from_member": from_member, "to_members": list(to_members)}
        if active_from is not None:
            edge["active_from"] = active_from
            edge["active_to"] = active_to
        self._edges.append(edge)

    def remove_dependency(
        self,
        from_member: str,
        to_members: list,
        active_from: str = None,
        active_to: str = None,
    ) -> None:
        pool_key = frozenset(to_members)
        for i, e in enumerate(self._edges):
            if (
                e["from_member"] == from_member
                and frozenset(e["to_members"]) == pool_key
                and e.get("active_from") == active_from
                and e.get("active_to") == active_to
            ):
                self._edges.pop(i)
                return
        raise KeyError(f"Dependency {from_member}→{sorted(to_members)} not found.")

    @staticmethod
    def _cw_days_set(cw: dict) -> set:
        return {date.fromisoformat(d) for d in cw["days"]}

    @staticmethod
    def _dep_active_in_cw(dep: dict, cw: dict) -> bool:
        af = dep.get("active_from")
        at = dep.get("active_to")
        if af is None:
            return True
        cw_start = date.fromisoformat(cw["start"])
        cw_end = date.fromisoformat(cw["end"])
        return not (cw_start > date.fromisoformat(at) or cw_end < date.fromisoformat(af))

    @staticmethod
    def _member_absent_in_cw(member: str, absence_date_sets: dict, cw_days: set) -> bool:
        return bool(absence_date_sets.get(member, set()) & cw_days)

    @staticmethod
    def compute_deadlock_weeks(
        from_member: str,
        deps: list,
        member_absence_date_sets: dict,
        calendar_weeks: list,
    ) -> list:
        relevant = [d for d in deps if d["from_member"] == from_member]
        if not relevant:
            return []
        deadlock = set()
        for cw in calendar_weeks:
            cw_days = DependencyGraph._cw_days_set(cw)
            for dep in relevant:
                if not DependencyGraph._dep_active_in_cw(dep, cw):
                    continue
                if all(
                    DependencyGraph._member_absent_in_cw(m, member_absence_date_sets, cw_days)
                    for m in dep["to_members"]
                ):
                    deadlock.add(cw["week_number"])
        return sorted(deadlock)

    @staticmethod
    def compute_bottleneck_weights(
        deps: list,
        member_absence_date_sets: dict,
        calendar_weeks: list,
    ) -> dict:
        weights: dict = {}
        for cw in calendar_weeks:
            cw_days = DependencyGraph._cw_days_set(cw)
            for dep in deps:
                if not DependencyGraph._dep_active_in_cw(dep, cw):
                    continue
                present = [
                    m for m in dep["to_members"]
                    if not DependencyGraph._member_absent_in_cw(
                        m, member_absence_date_sets, cw_days
                    )
                ]
                if len(present) == 1:
                    sole = present[0]
                    weights[sole] = weights.get(sole, 0) + 1
        return weights
