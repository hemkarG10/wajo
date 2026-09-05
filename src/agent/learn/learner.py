import json
from collections import defaultdict
from pathlib import Path


def train_policy(history: list[dict]) -> dict[str, dict]:
    """
    Train a policy from a history of approved actions.
    
    Each item in history should be a dictionary containing:
    - action_type (str)
    - sender_class (str)
    - intent (str)
    - planner_confidence (float)
    
    Returns a mapping from bucket key to {"n": int, "s": float}.
    """
    buckets = defaultdict(list)
    
    for item in history:
        # Group by the specified bucket definition
        bucket_key = f"{item['action_type']}_{item['sender_class']}_{item['intent']}"
        buckets[bucket_key].append(item['planner_confidence'])
        
    policy = {}
    for key, confidences in buckets.items():
        n = len(confidences)
        s = sum(confidences) / n if n > 0 else 0.0
        policy[key] = {"n": n, "s": s}
        
    return policy


def save_policy(policy: dict[str, dict], path: str | Path):
    with open(path, "w") as f:
        json.dump(policy, f, indent=2)

def load_policy(path: str | Path) -> dict[str, dict]:
    p = Path(path)
    if not p.exists():
        return {}
    with open(p, "r") as f:
        return json.load(f)
