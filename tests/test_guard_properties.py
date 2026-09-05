from datetime import datetime, timezone

from hypothesis import given
from hypothesis import strategies as st

from src.agent.guard import floor
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

# Hypothesis strategies for our enums
sender_class_st = st.sampled_from(SenderClass)
intent_st = st.sampled_from(Intent)
sensitivity_st = st.sampled_from(Sensitivity)
urgency_st = st.sampled_from(["low", "normal", "high"])


@st.composite
def situation_strategy(draw):
    return Situation(
        msg_id="test",
        sender_class=draw(sender_class_st),
        intent=draw(intent_st),
        sensitivity=draw(sensitivity_st),
        urgency=draw(urgency_st),
        requested_actions=[],
        deadline=None,
        thread_participants=[],
        summary="Test",
        llm_confidence=draw(st.floats(0.0, 1.0)),
    )


@st.composite
def email_strategy(draw):
    return EmailMessage(
        id="test",
        thread_id="test",
        from_addr="alice@acme.com",
        to=["me@acme.com"],
        cc=[],
        subject="test",
        body_text="test",
        body_html=None,
        headers={},
        attachments=[],
        received_at=datetime.now(timezone.utc)
    )


@st.composite
def action_strategy(draw):
    types = ["archive", "pay", "send_reply_known", "send_reply_unknown", "permanent_delete"]
    return ProposedAction(
        type=draw(st.sampled_from(types)),
        params={},
        provenance={},
        rationale="because",
        confidence=draw(st.floats(0.0, 1.0))
    )


@st.composite
def injection_strategy(draw):
    return InjectionSignals(
        heuristic_hits=[],
        llm_judgement=draw(st.sampled_from(["none", "suspicious", "likely"])),
        score=draw(st.floats(0.0, 1.0)),
        suspicious_spans=[]
    )


@given(situation_strategy(), email_strategy(), action_strategy(), injection_strategy())
def test_floor_properties(sit, email, act, inj):
    registry = {
        "archive": {"reversible": True, "external": False, "money": False, "floor": "AUTO"},
        "pay": {"reversible": False, "external": True, "money": True, "floor": "ESCALATE"},
        "send_reply_known": {"reversible": False, "external": True, "money": False, "floor": "AUTO_NOTIFY"},
        "send_reply_unknown": {"reversible": False, "external": True, "money": False, "floor": "ASK"},
        "permanent_delete": {"reversible": False, "external": False, "money": False, "floor": "ESCALATE"},
    }
    guard_cfg = {"dlp_patterns": [], "stale_days": 30}
    
    level, reasons = floor(sit, email, act, inj, registry, guard_cfg)
    
    assert isinstance(level, AutonomyLevel)
    assert isinstance(reasons, list)
    
    # Check that base floor is respected as a lower bound
    act_def = registry.get(act.type)
    if act_def:
        base_floor = AutonomyLevel[act_def["floor"]]
        assert level >= base_floor
