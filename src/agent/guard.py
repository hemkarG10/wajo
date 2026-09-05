import os
import re
from datetime import datetime, timezone
from typing import Any

from src.agent.models import (
    AutonomyLevel,
    EmailMessage,
    InjectionSignals,
    Intent,
    ProposedAction,
    Provenance,
    SenderClass,
    Sensitivity,
    Situation,
)


def _check_dlp(action: ProposedAction, patterns: list[str]) -> bool:
    """Check action string parameters against DLP regex patterns."""
    for val in action.params.values():
        if isinstance(val, str):
            for pat in patterns:
                if re.search(pat, val):
                    return True
    return False


def floor(
    situation: Situation,
    email: EmailMessage,
    action: ProposedAction,
    injection: InjectionSignals,
    action_registry: dict[str, dict[str, Any]],
    guard_config: dict[str, Any],
    is_paused: bool = False,
    now: datetime | None = None,
    recent_action_counts: dict[str, int] | None = None,
) -> tuple[AutonomyLevel, list[str]]:
    """
    Computes the hard safety floor for an action.
    Returns (minimum_autonomy_level, list_of_invariant_ids_triggered).
    """
    if now is None:
        now = datetime.now(timezone.utc)
    if recent_action_counts is None:
        recent_action_counts = {}
        
    action_def = action_registry.get(action.type)
    if not action_def:
        # Unknown action type -> fallback safely
        return AutonomyLevel.ESCALATE, ["I0_UNKNOWN_ACTION"]
        
    reasons = []
    
    # Base floor from registry (I1, I2, I3 effectively encoded here, but we re-check explicitly)
    base_floor_str = action_def.get("floor", "ESCALATE")
    current_floor = AutonomyLevel[base_floor_str]
    if current_floor != AutonomyLevel.AUTO:
        reasons.append("BASE_REGISTRY")

    is_external = action_def.get("external", False)
    is_money = action_def.get("money", False)

    # I1 Money never moves autonomously
    if is_money:
        current_floor = max(current_floor, AutonomyLevel.ESCALATE)
        reasons.append("I1")

    # I2 Irreversible & destructive -> ESCALATE (mostly handled by registry, but double check)
    if not action_def.get("reversible", False) and not is_external and "delete" in action.type:
        current_floor = max(current_floor, AutonomyLevel.ESCALATE)
        reasons.append("I2")

    # I3 External sends are never silent
    if is_external:
        current_floor = max(current_floor, AutonomyLevel.AUTO_NOTIFY)
        reasons.append("I3")

    # I4 New external recipients require a human
    # For simplicity, if sender is unknown and intent is REQUEST_FOR_ACTION -> ASK
    # Also if action is send_new or send_reply_unknown
    if situation.sender_class == SenderClass.UNKNOWN and situation.intent == Intent.REQUEST_FOR_ACTION:
        current_floor = max(current_floor, AutonomyLevel.ASK)
        reasons.append("I4")

    # I5 Untrusted provenance cannot steer external actions
    if is_external:
        has_untrusted_dest = any(
            prov == Provenance.UNTRUSTED for param, prov in action.provenance.items()
        )
        if has_untrusted_dest:
            current_floor = max(current_floor, AutonomyLevel.ESCALATE)
            reasons.append("I5")

    # I6 Suspected injection freezes outbound
    if injection.score >= 0.5 or injection.llm_judgement == "likely":
        if is_external:
            current_floor = max(current_floor, AutonomyLevel.ESCALATE)
        else:
            current_floor = max(current_floor, AutonomyLevel.ASK)
        reasons.append("I6")

    # I7 Sensitive categories stay human
    if situation.intent in {Intent.LEGAL_HR, Intent.FINANCIAL, Intent.SECURITY_ALERT}:
        if is_external:
            current_floor = max(current_floor, AutonomyLevel.ESCALATE)
        else:
            current_floor = max(current_floor, AutonomyLevel.ASK)
        reasons.append("I7")
        
    if situation.sensitivity == Sensitivity.REGULATED and is_external:
        current_floor = max(current_floor, AutonomyLevel.ESCALATE)
        reasons.append("I7")

    # I8 DLP on egress
    if is_external and _check_dlp(action, guard_config.get("dlp_patterns", [])):
        current_floor = max(current_floor, AutonomyLevel.ESCALATE)
        reasons.append("I8")

    # I9 Rate caps (stale days check and frequency limits)
    stale_days = guard_config.get("stale_days", 30)
    if (now - email.received_at).days > stale_days:
        current_floor = max(current_floor, AutonomyLevel.ASK)
        reasons.append("I9")
        
    rate_caps = guard_config.get("rate_caps", {})
    for metric, limit in rate_caps.items():
        if recent_action_counts.get(metric, 0) > limit:
            current_floor = max(current_floor, AutonomyLevel.ASK)
            reasons.append("I9")

    # I11 Kill switch
    if is_paused or os.environ.get("AGENT_PAUSED") == "1":
        current_floor = max(current_floor, AutonomyLevel.ASK)
        reasons.append("I11")

    return current_floor, reasons
