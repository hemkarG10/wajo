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
