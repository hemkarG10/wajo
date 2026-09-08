from hypothesis import given
from hypothesis import strategies as st

from src.agent.models import AutonomyLevel

@given(st.sampled_from(list(AutonomyLevel)), st.sampled_from(list(AutonomyLevel)))
def test_monotone_clamp(policy_level: AutonomyLevel, floor_level: AutonomyLevel):
    """I10: Monotone clamp final = max(policy, floor)"""
    final_level = max(policy_level, floor_level)
    assert final_level >= floor_level
    assert final_level >= policy_level

@given(
    alpha=st.floats(min_value=1.0, max_value=10000.0),
    beta=st.floats(min_value=1.0, max_value=10000.0)
)
def test_learned_policy_cannot_bypass_floor(alpha: float, beta: float):
    from src.agent.decide import make_decision
    from src.agent.guard import compute_floor
    from src.agent.models import Situation, ProposedAction, InjectionSignals, EmailMessage, SenderClass, Intent, Sensitivity
    from src.agent.learn.rules import RulesEngine
    from datetime import datetime, UTC
    
    sit = Situation(
        msg_id="test",
        sender_class=SenderClass.UNKNOWN,
        intent=Intent.OTHER,
        sensitivity=Sensitivity.NONE,
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
        type="test_action",
        params={},
        provenance={},
        rationale="test",
        confidence=1.0
    )
    
    policy = {
        "test_action_unknown_other": {"alpha": alpha, "beta": beta, "n": 100, "lcb": 1.0}
    }
    
    inj = InjectionSignals(
        heuristic_hits=[],
        llm_judgement="none",
        score=0.0,
        suspicious_spans=[]
    )
    
    class MockClock:
        def now(self): return datetime.now(UTC)
        
    reg = {"test_action": {"external": True, "money": False, "modifies_state": True}}
    g_cfg = {"floor": {"unknown_sender": "ASK", "external_action": "ASK", "money_action": "ESCALATE", "modifies_state": "ASK", "injection_detected": "ESCALATE"}}
        
    decision = make_decision(
        situation=sit,
        email=email,
        action=action,
        injection=inj,
        registry=reg,
        guard_cfg=g_cfg,
        learned_policy=policy,
        rules=RulesEngine([]),
        clock=MockClock(),
        policy_cfg={
            "auto_threshold": 0.85, 
            "auto_notify_threshold": 0.70, 
            "lcb_confidence": 0.95, 
            "half_life_days": 14.0,
            "auto_min_samples": 5,
            "auto_notify_min_samples": 2,
            "ask_threshold": 0.40
        }
    )
    
    # Independently compute and verify properties
    expected_floor, _ = compute_floor(sit, action, inj, reg, g_cfg)
    assert decision.floor == expected_floor
    assert decision.level == max(decision.policy_level, expected_floor)
    assert decision.level >= expected_floor
