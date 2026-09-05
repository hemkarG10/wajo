from src.agent.execute import Executor
from src.agent.models import ProposedAction, Decision, AutonomyLevel, SimClock, Provenance
from datetime import datetime, timezone
import pytest

def test_executor_refuses_untrusted_destination():
    registry = {
        "send_reply": {"external": True}
    }
    clock = SimClock(datetime.now(timezone.utc))
    executor = Executor(registry, dry_run=True, clock=clock)
    
    act = ProposedAction(
        type="send_reply",
        params={"to": "hacker@evil.com", "body": "secret"},
        provenance={"to": Provenance.UNTRUSTED},
        rationale="",
        confidence=1.0
    )
    
    dec = Decision(
        id="d1",
        msg_id="m1",
        action=act,
        level=AutonomyLevel.AUTO,
        policy_level=AutonomyLevel.AUTO,
        floor=AutonomyLevel.AUTO,
        floor_reasons=[],
        policy_reason={},
        guard_config_hash="",
        created_at=clock.now()
    )
    
    outcome = executor.execute(dec)
    assert not outcome.executed
    assert outcome.blocked_reason == "untrusted_destination"
    
def test_executor_allows_trusted_destination():
    registry = {
        "send_reply": {"external": True}
    }
    clock = SimClock(datetime.now(timezone.utc))
    executor = Executor(registry, dry_run=True, clock=clock)
    
    act = ProposedAction(
        type="send_reply",
        params={"to": "investor@example.com", "body": "secret"},
        provenance={},
        rationale="",
        confidence=1.0
    )
    
    dec = Decision(
        id="d1",
        msg_id="m1",
        action=act,
        level=AutonomyLevel.AUTO,
        policy_level=AutonomyLevel.AUTO,
        floor=AutonomyLevel.AUTO,
        floor_reasons=[],
        policy_reason={},
        guard_config_hash="",
        created_at=clock.now()
    )
    
    outcome = executor.execute(dec)
    assert not outcome.executed  # Because dry_run=True
    assert outcome.blocked_reason == "dry_run"
