import glob
from datetime import UTC, datetime

import yaml

from eval.context import scenario_ctx
from src.agent.llm import LlmAdapter
from src.agent.models import EmailMessage, SimClock
from src.agent.pipeline import process_email


def test_record_replay_keys():
    with open(sorted(glob.glob("eval/scenarios/benign/*.yaml"))[0]) as f:
        case = yaml.safe_load(f)
        raw = case.get("incoming", [case.get("email")])[0]
    email = EmailMessage(
        id="test_msg",
        thread_id="test_thread",
        from_addr=raw.get("from", raw.get("from_addr", "")),
        to=raw.get("to", []),
        cc=raw.get("cc", []),
        subject=raw["subject"],
        body_text=raw.get("body", raw.get("body_text", "")),
        body_html=None,
        headers={},
        attachments=[],
        received_at=datetime.now(UTC)
    )
    
    with open("config/actions.yaml") as f:
        registry = yaml.safe_load(f)
    with open("config/guard.yaml") as f:
        guard_cfg = yaml.safe_load(f)
    with open("config/policy.yaml") as f:
        policy_cfg = yaml.safe_load(f)
        
    cfg = {"registry": registry, "guard_cfg": guard_cfg, "policy_cfg": policy_cfg}
    clock = SimClock(datetime.now(UTC))
    
    mock_responses = {
        "Analyze the following email": {
            "sender_class": "unknown", 
            "intent": "other", 
            "sensitivity": "none", 
            "urgency": "normal", 
            "requested_actions": [], 
            "summary": "test", 
            "llm_confidence": 1.0, 
            "llm_judgement": "none"
        },
        "Based on the situation": {
            "actions": [{"type": "archive", "rationale": "test", "confidence": 1.0, "params": {}}]
        }
    }
    
    ctx_record = scenario_ctx(case)
    llm_record = LlmAdapter(mode="mock", provider="openai_compat", mock_responses=mock_responses)
    process_email(email, ctx_record, llm_record, {}, clock, cfg)
    
    ctx_replay = scenario_ctx(case)
    ctx_replay["disable_guard"] = False
    llm_replay = LlmAdapter(mode="replay", provider="openai_compat")
    
    # This should not raise CacheMiss
    process_email(email, ctx_replay, llm_replay, {}, clock, cfg)
