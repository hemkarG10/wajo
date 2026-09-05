import hashlib
import json
from datetime import datetime

from src.agent.guard import floor
from src.agent.models import (
    AutonomyLevel,
    Decision,
    EmailMessage,
    InjectionSignals,
    ProposedAction,
    Situation,
)

def policy_level(situation: Situation, action: ProposedAction, learned_policy: dict | None = None) -> tuple[AutonomyLevel, dict]:
    """
    Compute policy level using learned weights (if available) and the thresholds in Section 5.4.
    """
    if learned_policy is None:
        learned_policy = {}
        
    bucket = f"{action.type}_{situation.sender_class.value}_{situation.intent.value}"
    policy_data = learned_policy.get(bucket, {"n": 0, "s": 0.0})
    
    n = policy_data["n"]
    learned_s = policy_data["s"]
    
    # Final confidence is min(learned_s, planner_confidence * triage_confidence)
    # If we have no history (n=0), learned_s is 0, so we default to planner confidence to allow ASK.
    # Wait, if learned_s is 0, min() would be 0, which would force ESCALATE.
    # The spec implies s = min(learned_s, S_plan * S_llm), but cold start needs to work.
    # If n == 0, we should just use S_plan * S_llm so it defaults to ASK.
    base_s = action.confidence * situation.llm_confidence
    if n > 0:
        s = min(learned_s, base_s)
    else:
        s = base_s

    if s >= 0.90 and n >= 5:
        level = AutonomyLevel.AUTO
    elif s >= 0.75 and n >= 2:
        level = AutonomyLevel.AUTO_NOTIFY
    elif s >= 0.40:
        level = AutonomyLevel.ASK
    else:
        level = AutonomyLevel.ESCALATE
        
    reason = {
        "bucket": bucket,
        "n": n,
        "s": s
    }
    return level, reason

def make_decision(
    situation: Situation,
    email: EmailMessage,
    action: ProposedAction,
    injection: InjectionSignals,
    registry: dict,
    guard_cfg: dict,
    now: datetime | None = None,
    recent_action_counts: dict[str, int] | None = None,
    learned_policy: dict | None = None,
) -> Decision:
    pol_level, pol_reason = policy_level(situation, action, learned_policy=learned_policy)
    grd_level, grd_reasons = floor(situation, email, action, injection, registry, guard_cfg, now=now, recent_action_counts=recent_action_counts)
    
    final_level = max(pol_level, grd_level)
    
    # Hash config
    cfg_hash = hashlib.sha256(json.dumps(guard_cfg, sort_keys=True).encode()).hexdigest()
    
    return Decision(
        id=f"dec-{action.type}-{situation.msg_id}",
        msg_id=situation.msg_id,
        action=action,
        level=final_level,
        policy_level=pol_level,
        floor=grd_level,
        floor_reasons=grd_reasons,
        policy_reason=pol_reason,
        guard_config_hash=cfg_hash
    )
