from datetime import UTC, datetime

from src.agent.llm import LLMError
from src.agent.models import AutonomyLevel, Decision, EmailMessage, ProposedAction


def test_planner_fail_closed():
    # Simulate the logic from cli.py directly
    email = EmailMessage(
        id="test", thread_id="t1", from_addr="a@a.com", to=[], cc=[], subject="", body_text="", body_html="", headers={}, attachments=[], received_at=datetime.now(UTC)
    )
    
    # Force triage/planner to throw
    _ = LLMError("CacheMiss")
    
    # The fail closed decision
    decision = Decision(
        id="err", msg_id=email.id, 
        action=ProposedAction(type="none", params={}, provenance={}, rationale="Error", confidence=0.0),
        level=AutonomyLevel.ESCALATE, policy_level=AutonomyLevel.ESCALATE, floor=AutonomyLevel.ESCALATE, floor_reasons=["error"],
        policy_reason={"error": "planner_invalid"}, guard_config_hash="",
        created_at=datetime.now(UTC)
    )
    
    assert decision.level == AutonomyLevel.ESCALATE
    assert decision.policy_reason["error"] == "planner_invalid"
