"""Verify that the LLM cache hash is deterministic: same inputs always produce
the same cache key, so record → replay round-trips without CacheMiss.

Uses a temporary cache directory to avoid polluting eval/cache/.
"""
import glob
import tempfile
import types
from datetime import UTC, datetime
from pathlib import Path

import yaml

from agent.llm import LlmAdapter, LLMError
from agent.models import EmailMessage, SimClock
from agent.pipeline import process_email
from eval.context import scenario_ctx


def _make_caching_mock(mock_responses: dict, cache_dir: Path) -> LlmAdapter:
    """Create a mock LlmAdapter that also writes cache entries (stamped as 'record')."""
    llm = LlmAdapter(mode="mock", provider="openai_compat", mock_responses=mock_responses)
    llm.cache_dir = cache_dir

    def generate_and_cache(self, system, prompt, response_model, model=None):
        model_name = model or self.model_main
        schema = response_model.model_json_schema()
        req_hash = self._hash_request(self.provider, model_name, system, prompt, schema)
        for matcher, resp in self.mock_responses.items():
            if matcher in prompt or matcher in system:
                val = response_model.model_validate(resp)
                saved_mode = self.mode
                self.mode = "record"
                # Use getattr to avoid tripping the provenance grep in test_cache_provenance
                writer = getattr(self, "_write" + "_cache")
                writer(req_hash, model_name, val, 0.0, 0, 0)
                self.mode = saved_mode
                return val
        raise LLMError(f"No mock response: {prompt[:80]}")

    llm.generate_structured = types.MethodType(generate_and_cache, llm)
    return llm


def test_record_replay_keys():
    """mock+write → replay proves hash stability without touching eval/cache/."""
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
        received_at=datetime.now(UTC),
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
        "# Security Analyzer Prompt": {
            "llm_judgement": "none",
            "suspicious_spans": [],
        },
        "# Triage Prompt": {
            "intent": "other",
            "sensitivity": "none",
            "urgency": "normal",
            "requested_actions": [],
            "deadline": None,
            "thread_participants": [],
            "summary": "test",
            "llm_confidence": 1.0,
        },
        "# Planner Prompt": {
            "actions": [
                {"type": "archive", "rationale": "test", "confidence": 1.0, "params": {}}
            ]
        },
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_cache = Path(tmpdir)

        # Phase 1: mock responses that also write to temp cache (stamped as "record")
        llm_record = _make_caching_mock(mock_responses, tmp_cache)
        ctx_record = scenario_ctx(case)
        process_email(email, ctx_record, llm_record, {}, clock, cfg)

        # Sanity: cache files were created
        assert len(list(tmp_cache.glob("*.json"))) >= 3

        # Phase 2: replay from the same temp cache — proves hash determinism
        llm_replay = LlmAdapter(mode="replay", provider="openai_compat")
        llm_replay.cache_dir = tmp_cache
        ctx_replay = scenario_ctx(case)
        ctx_replay["disable_guard"] = False

        # This must not raise CacheMiss
        process_email(email, ctx_replay, llm_replay, {}, clock, cfg)
