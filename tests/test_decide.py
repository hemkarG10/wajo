from datetime import UTC, datetime

from src.agent.decide import make_decision, policy_level
from src.agent.models import (
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
        received_at=datetime.now(UTC)
    )
    
    # Policy says ASK, but floor says ESCALATE due to money=True
    act = ProposedAction(type="pay", params={}, provenance={}, rationale="test", confidence=0.9)
    
    inj = InjectionSignals(heuristic_hits=[], llm_judgement="none", score=0.0, suspicious_spans=[])
    
    registry = {"pay": {"external": True, "money": True, "floor": "ESCALATE"}}
    guard_cfg = {"dlp_patterns": [], "stale_days": 30}
    
    from src.agent.models import SimClock
    clock = SimClock(email.received_at)

    dec = make_decision(sit, email, act, inj, registry, guard_cfg, clock=clock)
    
    assert dec.policy_level == AutonomyLevel.ASK
    assert dec.floor == AutonomyLevel.ESCALATE
    assert dec.level == AutonomyLevel.ESCALATE

def test_policy_level_with_learned_policy():
    sit = Situation(
        msg_id="test",
        sender_class=SenderClass.KNOWN_CONTACT,
        intent=Intent.NEWSLETTER,
        sensitivity=Sensitivity.NONE,
        urgency="normal",
        requested_actions=[],
        deadline=None,
        thread_participants=[],
        summary="Test",
        llm_confidence=1.0
    )
    act = ProposedAction(type="archive", params={}, provenance={}, rationale="test", confidence=1.0)
    
    # 1. No history -> ASK
    level, _ = policy_level(sit, act, learned_policy={})
    assert level == AutonomyLevel.ASK
    
    # 2. History with n=2, lcb=0.8 -> AUTO_NOTIFY
    learned_policy = {"archive_known_contact_newsletter": {"n": 2, "lcb": 0.8}}
    level, _ = policy_level(sit, act, learned_policy=learned_policy)
    assert level == AutonomyLevel.AUTO_NOTIFY
    
    # 3. History with n=5, lcb=0.95 -> AUTO
    learned_policy = {"archive_known_contact_newsletter": {"n": 5, "lcb": 0.95}}
    level, _ = policy_level(sit, act, learned_policy=learned_policy)
    assert level == AutonomyLevel.AUTO
    
    # 4. History with n=10, s=0.3 -> ESCALATE
    learned_policy = {"archive_known_contact_newsletter": {"n": 10, "s": 0.3}}
    level, _ = policy_level(sit, act, learned_policy=learned_policy)
    assert level == AutonomyLevel.ESCALATE
