from agent.execute import Executor
from agent.models import AutonomyLevel, Decision, ProposedAction, Provenance


def test_executor_refuses_untrusted_destination():
    registry = {
        "send_reply": {"external": True}
    }
    executor = Executor(registry, dry_run=True)
    
    action = ProposedAction(
        type="send_reply",
        params={"to": "hacker@evil.com"},
        provenance={"to": Provenance.UNTRUSTED},
        rationale="test",
        confidence=0.9
    )
    
    # Even if approved to AUTO_NOTIFY
    decision = Decision(
        id="test",
        msg_id="test",
        action=action,
        level=AutonomyLevel.AUTO_NOTIFY,
        policy_level=AutonomyLevel.AUTO_NOTIFY,
        floor=AutonomyLevel.AUTO_NOTIFY,
        floor_reasons=[],
        policy_reason={},
        guard_config_hash="abc"
    )
    
    outcome = executor.execute(decision)
    assert outcome["status"] == "blocked"
    assert "UNTRUSTED provenance" in outcome["reason"]


def test_executor_allows_trusted_destination():
    registry = {
        "send_reply": {"external": True}
    }
    executor = Executor(registry, dry_run=True)
    
    action = ProposedAction(
        type="send_reply",
        params={"to": "friend@acme.com"},
        provenance={"to": Provenance.THREAD},
        rationale="test",
        confidence=0.9
    )
    
    decision = Decision(
        id="test",
        msg_id="test",
        action=action,
        level=AutonomyLevel.AUTO_NOTIFY,
        policy_level=AutonomyLevel.AUTO_NOTIFY,
        floor=AutonomyLevel.AUTO_NOTIFY,
        floor_reasons=[],
        policy_reason={},
        guard_config_hash="abc"
    )
    
    outcome = executor.execute(decision)
    assert outcome["status"] == "dry_run"
