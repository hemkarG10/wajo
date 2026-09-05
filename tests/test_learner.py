import os
import tempfile
from pathlib import Path

from src.agent.learn.learner import load_policy, save_policy, train_policy


def test_train_policy():
    history = [
        {"action_type": "archive", "sender_class": "known_contact", "intent": "newsletter", "planner_confidence": 0.8},
        {"action_type": "archive", "sender_class": "known_contact", "intent": "newsletter", "planner_confidence": 1.0},
        {"action_type": "send_reply_known", "sender_class": "known_contact", "intent": "request_for_action", "planner_confidence": 0.5},
    ]
    
    policy = train_policy(history)
    
    # Should create two buckets
    assert len(policy) == 2
    
    archive_bucket = policy["archive_known_contact_newsletter"]
    assert archive_bucket["n"] == 2
    assert archive_bucket["s"] == 0.9  # (0.8 + 1.0) / 2
    
    reply_bucket = policy["send_reply_known_known_contact_request_for_action"]
    assert reply_bucket["n"] == 1
    assert reply_bucket["s"] == 0.5

def test_save_load_policy():
    policy = {"archive_known_contact_newsletter": {"n": 5, "s": 0.95}}
    
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "policy.json"
        save_policy(policy, p)
        
        loaded = load_policy(p)
        assert loaded == policy
        
def test_load_missing_policy():
    assert load_policy("does_not_exist.json") == {}
