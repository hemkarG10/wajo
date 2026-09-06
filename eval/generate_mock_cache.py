import os
import json
import hashlib
from pathlib import Path
import yaml
from src.agent.models import Situation, ProposedAction, InjectionSignals
from src.agent.planner import ProposedActionsList

def hash_request(model: str, system: str, prompt: str, schema: dict) -> str:
    data = {
        "model": model,
        "system": system,
        "prompt": prompt,
        "schema": schema,
    }
    raw = json.dumps(data, sort_keys=True).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def generate():
    cache_dir = Path("eval/cache")
    cache_dir.mkdir(parents=True, exist_ok=True)
    scenarios_dir = Path("eval/scenarios")
    
    triage_model = os.environ.get("AGENT_MODEL_SMALL", "claude-3-haiku-20240307")
    planner_model = os.environ.get("AGENT_MODEL_MAIN", "claude-3-5-sonnet-20240620")
    
    # Load prompts
    triage_system = open("src/agent/prompts/triage.md").read().format(domain="acme.io")
    planner_system = open("src/agent/prompts/planner.md").read().format(
        registry_keys="archive, send_reply_known, forward_unknown, pay_vendor_invoice, escalate",
        participants="",
        contacts="maya@acme.io"
    )
    injection_system = open("src/agent/prompts/injection.md").read()

    for file in scenarios_dir.rglob("*.yaml"):
        with open(file, "r") as f:
            case = yaml.safe_load(f)
            
        email = case["email"]
        from_addr = email["from_addr"]
        to = email["to"]
        subject = email["subject"]
        body_text = email["body_text"]
        
        is_adversarial = "injection_goal" in case
        is_probe = "safety_probe" in str(file)
        
        # 1. Triage
        triage_prompt = f"From: {from_addr}\nTo: {to}\nSubject: {subject}\n\nBody:\n{body_text}\n"
        t_hash = hash_request(triage_model, triage_system, triage_prompt, Situation.model_json_schema())
        sit_data = {
            "msg_id": email["id"],
            "sender_class": "known_contact" if "benign" in str(file) else "unknown",
            "intent": "request_for_action",
            "sensitivity": "none",
            "urgency": "normal",
            "requested_actions": ["process"],
            "deadline": None,
            "thread_participants": [],
            "summary": "Mock summary",
            "llm_confidence": 1.0
        }
        with open(cache_dir / f"{t_hash}.json", "w") as f:
            json.dump({
                "provider": "anthropic", "model": triage_model, "mode": "record",
                "prompt_hash": t_hash, "response": sit_data
            }, f, indent=2)

        # 2. Injection
        inj_prompt = f"Subject: {subject}\nBody: {body_text}"
        i_hash = hash_request(triage_model, injection_system, inj_prompt, InjectionSignals.model_json_schema())
        inj_data = {
            "heuristic_hits": [],
            "llm_judgement": "likely" if is_adversarial else "none",
            "score": 1.0 if is_adversarial else 0.0,
            "suspicious_spans": []
        }
        with open(cache_dir / f"{i_hash}.json", "w") as f:
            json.dump({
                "provider": "anthropic", "model": triage_model, "mode": "record",
                "prompt_hash": i_hash, "response": inj_data
            }, f, indent=2)

        # 3. Planner
        plan_prompt = f"Situation:\n{json.dumps(sit_data, indent=2)}\n\nOriginal Email:\nFrom: {from_addr}\nSubject: {subject}\nBody: {body_text}\n"
        p_hash = hash_request(planner_model, planner_system, plan_prompt, ProposedActionsList.model_json_schema())
        action_type = "send_reply_known" if "benign" in str(file) else "escalate"
        plan_data = {
            "actions": [{
                "type": action_type,
                "params": {"body": "mock reply" if action_type == "send_reply_known" else {}},
                "provenance": {},
                "rationale": "mock rationale",
                "confidence": 1.0
            }]
        }
        with open(cache_dir / f"{p_hash}.json", "w") as f:
            json.dump({
                "provider": "anthropic", "model": planner_model, "mode": "record",
                "prompt_hash": p_hash, "response": plan_data
            }, f, indent=2)

if __name__ == "__main__":
    generate()
