import tempfile
from datetime import UTC, datetime
from pathlib import Path

from src.agent.learn.feedback import process_feedback
from src.agent.learn.rules import RulesEngine
from src.agent.learn.store import load_policy, save_policy
from src.agent.models import (
    AutonomyLevel,
    Decision,
    Feedback,
    ProposedAction,
)


def test_process_feedback():
    policy = {}
    rules = RulesEngine()
    now = datetime.now(UTC)
    
    dec = Decision(
        id="d1", msg_id="m1",
        action=ProposedAction(type="archive", params={}, provenance={}, rationale="", confidence=1.0),
        level=AutonomyLevel.ASK, policy_level=AutonomyLevel.ASK, floor=AutonomyLevel.AUTO,
        floor_reasons=[],
        policy_reason={"bucket": "archive_newsletter_newsletter"},
        guard_config_hash="",
        created_at=now
    )
    
    fb = Feedback(decision_id="d1", kind="approve", at=now)
    process_feedback(fb, dec, policy, rules, now, {"half_life_days": 14.0, "lcb_confidence": 0.95})
    
    assert "archive_newsletter_newsletter" in policy
    data = policy["archive_newsletter_newsletter"]
    assert data["n"] == 1
    assert data["alpha"] == 2.0  # 1.0 (prior) + 1.0
    assert data["beta"] == 1.0
    assert data["lcb"] > 0.0

def test_process_feedback_rules():
    policy = {}
    rules = RulesEngine()
    now = datetime.now(UTC)
    
    dec = Decision(
        id="d1", msg_id="m1",
        action=ProposedAction(type="archive", params={}, provenance={}, rationale="", confidence=1.0),
        level=AutonomyLevel.ASK, policy_level=AutonomyLevel.ASK, floor=AutonomyLevel.AUTO,
        floor_reasons=[],
        policy_reason={"bucket": "b1"},
        guard_config_hash="",
        created_at=now
    )
    
    fb = Feedback(decision_id="d1", kind="always_ask", at=now)
    process_feedback(fb, dec, policy, rules, now, {})
    
    assert rules.check("b1") == "always_ask"

def test_save_load_policy():
    policy = {"archive_newsletter_newsletter": {"n": 5, "alpha": 6.0, "beta": 1.0}}
    
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "policy.json"
        save_policy(policy, p)
        
        loaded = load_policy(p)
        assert loaded == policy
        
def test_load_missing_policy():
    assert load_policy("does_not_exist.json") == {}

def test_backoff_buckets():
    from src.agent.decide import make_decision
    from src.agent.models import InjectionSignals, Intent, SenderClass, Situation
    
    policy = {}
    rules = RulesEngine()
    now = datetime.now(UTC)
    
    sit1 = Situation(
        msg_id="x",
        intent=Intent.NEWSLETTER,
        sender_class=SenderClass.KNOWN_CONTACT,
        sensitivity="none", urgency="normal", requested_actions=[], deadline=None,
        thread_participants=[], summary="", llm_confidence=1.0
    )
    dec1 = Decision(
        id="d1", msg_id="m1", situation=sit1,
        action=ProposedAction(type="archive", params={}, provenance={}, rationale="", confidence=1.0),
        level=AutonomyLevel.ASK, policy_level=AutonomyLevel.ASK, floor=AutonomyLevel.AUTO,
        floor_reasons=[], policy_reason={"bucket": "archive_known_contact_newsletter"},
        guard_config_hash="", created_at=now
    )
    
    for i in range(3):
        fb = Feedback(decision_id=f"d{i}", kind="approve", at=now)
        process_feedback(fb, dec1, policy, rules, now, {"half_life_days": 14.0, "lcb_confidence": 0.95})
        
    assert "archive_known_contact" in policy
    assert policy["archive_known_contact"]["n"] == 3
    
    sit2 = Situation(
        msg_id="y",
        intent=Intent.RECEIPT,
        sender_class=SenderClass.KNOWN_CONTACT,
        sensitivity="none", urgency="normal", requested_actions=[], deadline=None,
        thread_participants=[], summary="", llm_confidence=1.0
    )
    
    from src.agent.models import EmailMessage
    email = EmailMessage(
        id="test", thread_id="test", from_addr="a@b.c", to=["c@d.e"], cc=[], subject="test", body_text="test", body_html=None, headers={}, attachments=[], received_at=now
    )
    dec2 = make_decision(
        situation=sit2, email=email,
        action=ProposedAction(type="archive", params={}, provenance={}, rationale="", confidence=1.0),
        injection=InjectionSignals(heuristic_hits=[], llm_judgement="none", score=0.0, suspicious_spans=[]),
        registry={"archive": {"external": False, "reversible": True, "sensitivity_floors": {}}},
        guard_cfg={"floor": {}}, learned_policy=policy, rules=rules, clock=type('MockClock', (), {'now': lambda self: now})(), 
        policy_cfg={"auto_threshold": 0.85, "auto_min_samples": 5, "auto_notify_threshold": 0.40, "auto_notify_min_samples": 2, "ask_threshold": 0.20}
    )
    
    assert dec2.policy_level in (AutonomyLevel.AUTO, AutonomyLevel.AUTO_NOTIFY)

def test_single_noisy_reject_does_not_reset_trust():
    policy = {"archive_newsletter_newsletter": {"n": 10, "alpha": 10.0, "beta": 1.0}}
    rules = RulesEngine()
    now = datetime.now(UTC)
    
    dec = Decision(
        id="d1", msg_id="m1",
        action=ProposedAction(type="archive", params={}, provenance={}, rationale="", confidence=1.0),
        level=AutonomyLevel.ASK, policy_level=AutonomyLevel.ASK, floor=AutonomyLevel.AUTO,
        floor_reasons=[],
        policy_reason={"bucket": "archive_newsletter_newsletter"},
        guard_config_hash="",
        created_at=now
    )
    
    fb = Feedback(decision_id="d1", kind="reject", at=now)
    process_feedback(fb, dec, policy, rules, now, {"half_life_days": 14.0, "lcb_confidence": 0.95})
    
    assert "archive_newsletter_newsletter" in policy
    data = policy["archive_newsletter_newsletter"]
    # 1.0 + (10.0 - 1.0) * 0.5 = 5.5
    assert data["alpha"] == 5.5
    # beta increases by 1
    assert data["beta"] == 2.0
