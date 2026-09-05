import hashlib
import json
from datetime import datetime

from agent.guard import floor
from agent.models import (
    AutonomyLevel,
    Decision,
    EmailMessage,
    InjectionSignals,
    ProposedAction,
    Situation,
)

def policy_level(situation: Situation, action: ProposedAction) -> tuple[AutonomyLevel, dict]:
    """
    Day 2 baseline policy level.
    Since there is no learning yet, we just return ASK or ESCALATE depending on confidence.
    """
    conf = action.confidence * situation.llm_confidence
    # Without history, we never go below ASK.
    if conf >= 0.40:
        level = AutonomyLevel.ASK
    else:
        level = AutonomyLevel.ESCALATE
        
    reason = {
        "bucket": f"{action.type}_{situation.sender_class.value}_{situation.intent.value}",
        "n": 0,
        "conf": conf
    }
    return level, reason

def make_decision(
    situation: Situation,
    email: EmailMessage,
    action: ProposedAction,
    injection: InjectionSignals,
    registry: dict,
    guard_cfg: dict,
    now: datetime | None = None
) -> Decision:
    pol_level, pol_reason = policy_level(situation, action)
    grd_level, grd_reasons = floor(situation, email, action, injection, registry, guard_cfg, now=now)
    
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
