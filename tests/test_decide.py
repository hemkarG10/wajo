from datetime import datetime, timezone
from agent.decide import policy_level, make_decision
from agent.models import (
    AutonomyLevel,
    EmailMessage,
    InjectionSignals,
    Intent,
    ProposedAction,
    SenderClass,
    Sensitivity,
    Situation,
)

def test_policy_level_baseline():
    sit = Situation(
        msg_id="test",
        sender_class=SenderClass.KNOWN_CONTACT,
        intent=Intent.INFO_REQUEST,
        sensitivity=Sensitivity.NONE,
        urgency="normal",
        requested_actions=[],
        deadline=None,
        thread_participants=[],
        summary="Test",
        llm_confidence=0.9
    )
    
    act_high_conf = ProposedAction(type="archive", params={}, provenance={}, rationale="test", confidence=0.9)
    level, _ = policy_level(sit, act_high_conf)
    assert level == AutonomyLevel.ASK
    
    act_low_conf = ProposedAction(type="archive", params={}, provenance={}, rationale="test", confidence=0.3)
    level, _ = policy_level(sit, act_low_conf)
    assert level == AutonomyLevel.ESCALATE

def test_make_decision_clamps_to_floor():
    sit = Situation(
        msg_id="test",
        sender_class=SenderClass.UNKNOWN,
        intent=Intent.REQUEST_FOR_ACTION,
        sensitivity=Sensitivity.NONE,
        urgency="normal",
        requested_actions=[],
        deadline=None,
        thread_participants=[],
        summary="Test",
        llm_confidence=0.9
    )
    
    email = EmailMessage(
        id="test", thread_id="test", from_addr="a@b.com", to=[], cc=[],
        subject="a", body_text="a", body_html=None, headers={}, attachments=[],
        received_at=datetime.now(timezone.utc)
    )
    
    # Policy says ASK, but floor says ESCALATE due to money=True
    act = ProposedAction(type="pay", params={}, provenance={}, rationale="test", confidence=0.9)
    
    inj = InjectionSignals(heuristic_hits=[], llm_judgement="none", score=0.0, suspicious_spans=[])
    
    registry = {"pay": {"external": True, "money": True, "floor": "ESCALATE"}}
    guard_cfg = {"dlp_patterns": [], "stale_days": 30}
    
    dec = make_decision(sit, email, act, inj, registry, guard_cfg)
    
    assert dec.policy_level == AutonomyLevel.ASK
    assert dec.floor == AutonomyLevel.ESCALATE
    assert dec.level == AutonomyLevel.ESCALATE
