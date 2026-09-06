from datetime import UTC, datetime

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
        received_at=datetime.now(UTC)
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

from src.agent.decide import make_decision


def test_poisoned_history_cannot_violate_floor():
    registry = {
        "send_reply_known": {"reversible": False, "external": True, "money": False, "floor": "AUTO_NOTIFY"},
        "pay": {"reversible": False, "external": True, "money": True, "floor": "ESCALATE"},
    }
    guard_cfg = {"dlp_patterns": [], "stale_days": 30}
    policy_cfg = {
        "auto_threshold": 0.8,
        "auto_min_samples": 5,
        "auto_notify_threshold": 0.5,
        "auto_notify_min_samples": 2,
        "ask_threshold": 0.0
    }
    
    # 10k approvals in the bucket (highly confident, wanting to do it AUTO)
    poisoned_policy = {
        "pay_unknown_financial": {"n": 10000, "lcb": 0.99, "alpha": 10000, "beta": 1.0},
        "send_reply_known_known_contact_request_for_action": {"n": 10000, "lcb": 0.99, "alpha": 10000, "beta": 1.0}
    }
    
    sit = Situation(
        msg_id="test", sender_class="unknown", intent="financial", sensitivity="none", urgency="high",
        requested_actions=[], deadline=None, thread_participants=[], summary="test", llm_confidence=1.0
    )
    email = EmailMessage(
        id="t", thread_id="t", from_addr="a@a.com", to=["b@b.com"], cc=[], subject="a", body_text="a", body_html=None,
        headers={}, attachments=[], received_at=datetime.now(UTC)
    )
    act = ProposedAction(type="pay", params={}, provenance={}, rationale="x", confidence=1.0)
    inj = InjectionSignals(heuristic_hits=[], llm_judgement="none", score=0.0, suspicious_spans=[])
    
    from src.agent.learn.rules import RulesEngine
    from src.agent.models import SimClock
    
    decision = make_decision(sit, email, act, inj, registry, guard_cfg, clock=SimClock(email.received_at), learned_policy=poisoned_policy, rules=RulesEngine(), policy_cfg=policy_cfg)
    
    # The policy wants AUTO (0.99 > 0.8), but the Guard enforces ESCALATE
    assert decision.policy_level == AutonomyLevel.AUTO
    assert decision.level == AutonomyLevel.ESCALATE
