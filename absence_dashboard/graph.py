from datetime import date


class CycleError(Exception):
    pass


class DependencyGraph:
    def __init__(self, edges: list = None):
        self._edges = list(edges or [])

    def edges(self) -> list:
        return list(self._edges)

    def add_edge(self, source: str, target: str, valid_members: set) -> None:
        if source not in valid_members:
            raise ValueError(f"Member '{source}' not in loaded dataset.")
        if target not in valid_members:
            raise ValueError(f"Member '{target}' not in loaded dataset.")
        if source == target:
            raise ValueError("Self-dependencies are not allowed.")
        if any(e["from_member"] == source and e["to_member"] == target for e in self._edges):
            raise ValueError(f"Dependency {source}→{target} already exists.")
        if self._has_cycle_if_added(source, target):
            raise CycleError(f"Adding {source}→{target} would create a dependency cycle.")
        self._edges.append({"from_member": source, "to_member": target})

    def remove_edge(self, source: str, target: str) -> None:
        for i, e in enumerate(self._edges):
            if e["from_member"] == source and e["to_member"] == target:
                self._edges.pop(i)
                return
        raise KeyError(f"Dependency {source}→{target} not found.")

    def _has_cycle_if_added(self, source: str, target: str) -> bool:
        # A cycle forms if target can already reach source through existing edges
        adj = {}
        for e in self._edges:
            adj.setdefault(e["from_member"], []).append(e["to_member"])
        return self._can_reach(target, source, adj)

    @staticmethod
    def _can_reach(start: str, goal: str, adj: dict) -> bool:
        stack = [start]
        visited = {start}
        while stack:
            node = stack.pop()
            if node == goal:
                return True
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    stack.append(neighbor)
        return False

    @staticmethod
    def get_bottlenecks(edges: list) -> set:
        incoming: dict = {}
        for e in edges:
            t = e["to_member"]
            incoming[t] = incoming.get(t, 0) + 1
        return {name for name, count in incoming.items() if count >= 2}

    @staticmethod
    def compute_at_risk_weeks(
        member_name: str,
        edges: list,
        member_blocks_map: dict,
        calendar_weeks: list,
    ) -> list:
        depended_on = [e["to_member"] for e in edges if e["from_member"] == member_name]
        if not depended_on:
            return []

        at_risk = set()
        for cw in calendar_weeks:
            cw_start = date.fromisoformat(cw["start"])
            cw_end = date.fromisoformat(cw["end"])
            for dep in depended_on:
                for block in member_blocks_map.get(dep, []):
                    if block.start_date <= cw_end and block.end_date >= cw_start:
                        at_risk.add(cw["week_number"])
                        break
        return sorted(at_risk)
