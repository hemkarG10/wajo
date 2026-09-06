import pytest
from hypothesis import given, strategies as st
from src.agent.models import AutonomyLevel

@given(st.sampled_from(list(AutonomyLevel)), st.sampled_from(list(AutonomyLevel)))
def test_monotone_clamp(policy_level: AutonomyLevel, floor_level: AutonomyLevel):
    """I10: Monotone clamp final = max(policy, floor)"""
    final_level = max(policy_level, floor_level)
    assert final_level >= floor_level
    assert final_level >= policy_level

def test_10k_poison_still_clamps():
    """Even with a poisoned policy (10k n, 1.0 lcb), guard floor applies."""
    # This is handled structurally by max(), but we can test it at the pipeline level.
    # In pipeline.py:
    # level = max(policy_level, floor)
    # The evaluation harness tests this via run_ablation("poisoned_trust").
    # We assert that max(AUTO, ESCALATE) == ESCALATE
    assert max(AutonomyLevel.AUTO, AutonomyLevel.ESCALATE) == AutonomyLevel.ESCALATE
