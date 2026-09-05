import json
from pathlib import Path

def save_policy(policy: dict[str, dict], path: str | Path):
    with open(path, "w") as f:
        json.dump(policy, f, indent=2)

def load_policy(path: str | Path) -> dict[str, dict]:
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, "r") as f:
        return json.load(f)
