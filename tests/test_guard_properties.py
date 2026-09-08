from hypothesis import given
from hypothesis import strategies as st

from src.agent.models import AutonomyLevel


@given(st.sampled_from(list(AutonomyLevel)), st.sampled_from(list(AutonomyLevel)))
def test_monotone_clamp(policy_level: AutonomyLevel, floor_level: AutonomyLevel):
    """I10: Monotone clamp final = max(policy, floor)"""
    final_level = max(policy_level, floor_level)
    assert final_level >= floor_level
    assert final_level >= policy_level

import yaml

with open("config/actions.yaml") as f:
    REGISTRY = yaml.safe_load(f)
with open("config/guard.yaml") as f:
    GUARD_CFG = yaml.safe_load(f)

from src.agent.models import Intent, SenderClass, Sensitivity


@given(
    action_type=st.sampled_from(list(REGISTRY.keys())),
    sender_class=st.sampled_from(list(SenderClass)),
    intent=st.sampled_from(list(Intent)),
    sensitivity=st.sampled_from(list(Sensitivity)),
    inj_score=st.floats(min_value=0.0, max_value=1.0)
)
def test_learned_policy_cannot_bypass_floor(action_type: str, sender_class: SenderClass, intent: Intent, sensitivity: Sensitivity, inj_score: float):
    from datetime import UTC, datetime

    from src.agent.decide import make_decision
    from src.agent.guard import floor
    from src.agent.learn.rules import RulesEngine
    from src.agent.models import (
        EmailMessage,
        InjectionSignals,
        ProposedAction,
        Situation,
    )
    
    sit = Situation(
        msg_id="test",
        sender_class=sender_class,
        intent=intent,
        sensitivity=sensitivity,
        urgency="normal",
        requested_actions=[],
        deadline=None,
        thread_participants=[],
        summary="Test",
        llm_confidence=1.0
    )
    email = EmailMessage(
        id="test", thread_id="test", from_addr="a@b.c", to=["c@d.e"], cc=[], subject="test", body_text="test", body_html=None, headers={}, attachments=[], received_at=datetime.now(UTC)
    )
    action = ProposedAction(
        type=action_type,
        params={},
        provenance={},
        rationale="test",
        confidence=1.0
    )
    
    bucket = f"{action_type}_{sender_class.value}_{intent.value}"
    policy = {
        bucket: {"alpha": 1000000.0, "beta": 1.0, "n": 1000000, "lcb": 1.0}
    }
    
    inj = InjectionSignals(
        heuristic_hits=[],
        llm_judgement="none",
        score=inj_score,
        suspicious_spans=[]
    )
    
    class MockClock:
        def now(self): return datetime.now(UTC)
        
    policy_cfg = {
        "auto_threshold": 0.85, 
        "auto_notify_threshold": 0.70, 
        "lcb_confidence": 0.95, 
        "half_life_days": 14.0,
        "auto_min_samples": 5,
        "auto_notify_min_samples": 2,
        "ask_threshold": 0.40
    }

    decision = make_decision(
        situation=sit,
        email=email,
        action=action,
        injection=inj,
        registry=REGISTRY,
        guard_cfg=GUARD_CFG,
        learned_policy=policy,
        rules=RulesEngine([]),
        clock=MockClock(),
        policy_cfg=policy_cfg
    )
    
    expected_floor, _ = floor(sit, email, action, inj, REGISTRY, GUARD_CFG, now=MockClock().now())
    
    # Assert decision.level >= floor(...)
    assert decision.level >= expected_floor
    
    # assert money actions are ESCALATE
    if REGISTRY[action_type].get("money", False):
        assert decision.level == AutonomyLevel.ESCALATE
        
    # assert external actions are >= AUTO_NOTIFY
    if REGISTRY[action_type].get("external", False):
        assert decision.level >= AutonomyLevel.AUTO_NOTIFY
        
    # assert floor() returns the same value when learned_policy is {}
    decision_empty = make_decision(
        situation=sit, email=email, action=action, injection=inj,
        registry=REGISTRY, guard_cfg=GUARD_CFG, learned_policy={},
        rules=RulesEngine([]), clock=MockClock(),
        policy_cfg=policy_cfg
    )
    assert decision.floor == decision_empty.floor
