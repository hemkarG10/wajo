from datetime import datetime

from src.agent.learn.rules import RulesEngine
from src.agent.learn.trust import apply_decay, calculate_lcb
from src.agent.models import Decision, Feedback


def process_feedback(
    feedback: Feedback, 
    decision: Decision, 
    policy: dict, 
    rules: RulesEngine, 
    now: datetime, 
    policy_cfg: dict
):
    """
    Process feedback with an asymmetric update: approvals accumulate linearly; 
    a rejection halves accumulated trust, an undo quarters it — robust to a 
    single noisy reject, unlearns within two real ones.
    """
    if not decision.situation:
        # fallback if situation is somehow missing (e.g. from MockDecision)
        buckets = [decision.policy_reason.get("bucket")]
    else:
        buckets = [
            f"{decision.action.type}_{decision.situation.sender_class.value}_{decision.situation.intent.value}",
            f"{decision.action.type}_{decision.situation.sender_class.value}",
            f"{decision.action.type}"
        ]
        
    for bucket in buckets:
        if not bucket: continue
        
        data = policy.get(bucket, {"alpha": 1.0, "beta": 1.0, "last_update": now.isoformat(), "n": 0})
        
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
        elif feedback.kind in {"reject", "edit", "escalate_was_overkill"}:
            new_a = 1.0 + (new_a - 1.0) * 0.5
            new_b += 1.0
        elif feedback.kind == "undo":
            new_a = 1.0 + (new_a - 1.0) * 0.25
            new_b += 2.0
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
