import json
import os
from dataclasses import dataclass, field


@dataclass
class AppState:
    cumul_groups: list = field(default_factory=list)
    clusters: list = field(default_factory=list)
    phases: list = field(default_factory=list)


def load_state(path: str) -> AppState:
    if not os.path.exists(path):
        return AppState()
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return AppState(
        cumul_groups=data.get("cumul_groups", []),
        clusters=data.get("clusters", []),
        phases=data.get("phases", []),
    )


def save_state(state: AppState, path: str) -> None:
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            {"cumul_groups": state.cumul_groups, "clusters": state.clusters, "phases": state.phases},
            f, indent=2,
        )
