import pytest
from datetime import datetime, timezone
from src.agent.guard import floor
from src.agent.models import EmailMessage, ProposedAction, Situation, InjectionSignals, SenderClass, Intent, Sensitivity, AutonomyLevel

def test_injection_error_floor():
    email = EmailMessage(
        id="test", thread_id="t", from_addr="a@a.com", to=[], cc=[], subject="", body_text="", body_html="", headers={}, attachments=[], received_at=datetime.now(timezone.utc)
    )
    sit = Situation(
        msg_id="test", sender_class=SenderClass.KNOWN_CONTACT, intent=Intent.REQUEST_FOR_ACTION, sensitivity=Sensitivity.NONE, urgency="normal", requested_actions=[], deadline=None, thread_participants=[], summary="", llm_confidence=1.0
    )
    act = ProposedAction(type="pay", params={}, provenance={}, rationale="", confidence=1.0)
    
    registry = {"pay": {"external": True, "money": True, "floor": "ESCALATE"}}
    inj = InjectionSignals(heuristic_hits=[], llm_judgement="error", score=0.0, suspicious_spans=[])
    
    guard_cfg = {"llm_judgement_error_floor": "ASK"}
    
    level, reasons = floor(sit, email, act, inj, registry, guard_cfg)
    
    assert "I6_ERROR" in reasons
    # Since money=True, base is ESCALATE anyway, but I6_ERROR should be present.
    
    # Test a non-money external action that normally allows AUTO_NOTIFY
    act_reply = ProposedAction(type="send_reply", params={}, provenance={}, rationale="", confidence=1.0)
    registry_reply = {"send_reply": {"external": True, "floor": "AUTO_NOTIFY"}}
    
    level2, reasons2 = floor(sit, email, act_reply, inj, registry_reply, guard_cfg)
    assert level2 == AutonomyLevel.ASK
    assert "I6_ERROR" in reasons2
