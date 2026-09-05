from datetime import datetime
from src.agent.models import Decision, Feedback
from src.agent.learn.trust import apply_decay, calculate_lcb
from src.agent.learn.rules import RulesEngine

def process_feedback(
    feedback: Feedback, 
    decision: Decision, 
    policy: dict, 
    rules: RulesEngine, 
    now: datetime, 
    policy_cfg: dict
):
    bucket = decision.policy_reason["bucket"]
    data = policy.get(bucket, {"alpha": 1.0, "beta": 1.0, "last_update": now, "n": 0})
    
    # apply decay
    last_update = data.get("last_update", now)
    if isinstance(last_update, str):
        last_update = datetime.fromisoformat(last_update)
        
    new_a, new_b = apply_decay(
        data["alpha"], 
        data["beta"], 
        last_update, 
        now, 
        policy_cfg.get("half_life_days", 14.0)
    )
    
    # apply feedback
    if feedback.kind in {"approve", "escalate_was_right"}:
        new_a += 1.0
    elif feedback.kind in {"edit", "reject", "undo", "escalate_was_overkill"}:
        # Backoff: reset alpha on rejection to quickly drop trust
        new_a = 1.0
        new_b += 1.0
    elif feedback.kind == "stop_asking":
        rules.add_rule(bucket, "stop_asking")
    elif feedback.kind == "always_ask":
        rules.add_rule(bucket, "always_ask")
        
    data["alpha"] = new_a
    data["beta"] = new_b
    data["n"] = data.get("n", 0) + 1
    data["last_update"] = now.isoformat()
    data["lcb"] = calculate_lcb(new_a, new_b, policy_cfg.get("lcb_confidence", 0.95))
    
    policy[bucket] = data
