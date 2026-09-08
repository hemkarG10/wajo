import hashlib
import json
from typing import Any

from src.agent.guard import floor
from src.agent.models import (
    AutonomyLevel,
    Clock,
    Decision,
    EmailMessage,
    InjectionSignals,
    ProposedAction,
    Situation,
)


def policy_level(
    situation: Situation, 
    action: ProposedAction, 
    learned_policy: dict | None = None,
    rules: Any = None,
    policy_cfg: dict | None = None
) -> tuple[AutonomyLevel, dict]:
    """
    Compute policy level using learned weights (if available) and the thresholds in config/policy.yaml.
    """
    if learned_policy is None:
        learned_policy = {}
    if policy_cfg is None:
        policy_cfg = {
            "auto_threshold": 0.90, "auto_min_samples": 5,
            "auto_notify_threshold": 0.75, "auto_notify_min_samples": 2,
            "ask_threshold": 0.40
        }
        
    bucket_fine = f"{action.type}_{situation.sender_class.value}_{situation.intent.value}"
    bucket_med = f"{action.type}_{situation.sender_class.value}"
    bucket_coarse = f"{action.type}"
    
    bucket = bucket_fine
    policy_data = learned_policy.get(bucket_fine)
    
    min_samples_for_backoff = policy_cfg.get("auto_notify_min_samples", 2)
    
    if not policy_data or policy_data.get("n", 0) < min_samples_for_backoff:
        med_data = learned_policy.get(bucket_med)
        if med_data and med_data.get("n", 0) >= min_samples_for_backoff:
            bucket = bucket_med
            policy_data = med_data
        else:
            coarse_data = learned_policy.get(bucket_coarse)
            if coarse_data and coarse_data.get("n", 0) >= min_samples_for_backoff:
                bucket = bucket_coarse
                policy_data = coarse_data
                
    if not policy_data:
        policy_data = learned_policy.get(bucket_fine, {"n": 0, "alpha": 1.0, "beta": 1.0, "lcb": 0.0})
    
    n = policy_data.get("n", 0)
    lcb = policy_data.get("lcb", 0.0)
    
    # We use planner confidence * LLM confidence as a base if no history
    base_s = action.confidence * situation.llm_confidence
    s = lcb if n >= policy_cfg.get("auto_notify_min_samples", 2) else base_s

    # Check explicit rules first
    rule_status = rules.check(bucket) if rules else "none"
    if rule_status == "stop_asking":
        level = AutonomyLevel.AUTO
    elif rule_status == "always_ask":
        level = AutonomyLevel.ASK
    else:
        # Standard threshold logic
        if s >= policy_cfg["auto_threshold"] and n >= policy_cfg["auto_min_samples"]:
            level = AutonomyLevel.AUTO
        elif s >= policy_cfg["auto_notify_threshold"] and n >= policy_cfg["auto_notify_min_samples"]:
            level = AutonomyLevel.AUTO_NOTIFY
        elif s >= policy_cfg["ask_threshold"]:
            level = AutonomyLevel.ASK
        else:
            level = AutonomyLevel.ESCALATE
        
    reason = {
        "bucket": bucket,
        "n": n,
        "lcb": lcb,
        "s": s,
        "llm_conf": situation.llm_confidence,
        "planner_conf": action.confidence
    }
    return level, reason

def make_decision(
    situation: Situation,
    email: EmailMessage,
    action: ProposedAction,
    injection: InjectionSignals,
    registry: dict,
    guard_cfg: dict,
    clock: Clock,
    recent_action_counts: dict[str, int] | None = None,
    learned_policy: dict | None = None,
    rules: Any = None,
    policy_cfg: dict | None = None,
    is_paused: bool = False,
) -> Decision:
    pol_level, pol_reason = policy_level(situation, action, learned_policy=learned_policy, rules=rules, policy_cfg=policy_cfg)
    
    now = clock.now()
    grd_level, grd_reasons = floor(
        situation, 
        email, 
        action, 
        injection, 
        registry, 
        guard_cfg, 
        is_paused=is_paused,
        now=now, 
        recent_action_counts=recent_action_counts
    )
    
    final_level = max(pol_level, grd_level)
    
    # Hash config
    cfg_hash = hashlib.sha256(json.dumps(guard_cfg, sort_keys=True).encode()).hexdigest()
    
    return Decision(
        id=f"dec-{action.type}-{situation.msg_id}",
        msg_id=situation.msg_id,
        action=action,
        injection=injection,
        level=final_level,
        policy_level=pol_level,
        floor=grd_level,
        floor_reasons=grd_reasons,
        policy_reason=pol_reason,
        guard_config_hash=cfg_hash,
        created_at=now
    )
