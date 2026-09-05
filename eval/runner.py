import json
from datetime import datetime
import yaml

from src.agent.llm import LlmAdapter
from src.agent.models import EmailMessage, AutonomyLevel
from src.agent.triage import extract_situation
from src.agent.planner import propose_actions
from src.agent.injection import scan
from src.agent.decide import make_decision

from eval.scoring import score_decision

def run_eval():
    with open("eval/dataset.json", "r") as f:
        dataset = json.load(f)
        
    with open("config/actions.yaml", "r") as f:
        registry = yaml.safe_load(f)
    with open("config/guard.yaml", "r") as f:
        guard_cfg = yaml.safe_load(f)
    with open("config/policy.yaml", "r") as f:
        policy_cfg = yaml.safe_load(f)

    # Use a dummy policy to ensure determinism, or simulate learned
    learned_policy = {
        "archive_known_contact_newsletter": {"n": 5, "s": 0.95}
    }

    import os
    mode = os.environ.get("EVAL_MODE", "replay")
    llm = LlmAdapter(mode=mode)
    
    trusted_contacts = {"maya@acme.io"}
    
    results = []
    
    for case in dataset:
        raw_email = case["email"]
        raw_email["received_at"] = datetime.fromisoformat(raw_email["received_at"])
        email = EmailMessage(**raw_email)
        
        expected_level = AutonomyLevel[case["expected_level"]]
        expected_reasons = set(case["expected_reasons"])
        
        inj = scan(email, llm)
        situation = extract_situation(email, llm)
        proposals = propose_actions(
            situation, email, llm,
            trusted_contacts=trusted_contacts,
            action_registry_keys=list(registry.keys())
        )
        
        if not proposals:
            print(f"FAILED {email.id}: no actions proposed")
            continue
            
        action = proposals[0] # Just evaluate the top proposed action
        from src.agent.models import SimClock
        from src.agent.learn.rules import RulesEngine
        decision = make_decision(
            situation, email, action, inj,
            registry, guard_cfg, learned_policy=learned_policy,
            clock=SimClock(email.received_at), rules=RulesEngine(),
            policy_cfg=policy_cfg
        )
        
        passed, msg = score_decision(decision, expected_level, expected_reasons)
        results.append((email.id, passed, msg))
        
    print("\n=== Eval Results ===")
    all_passed = True
    for eid, passed, msg in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        if not passed: all_passed = False
        print(f"{status} | {eid} | {msg}")
        
    if not all_passed:
        exit(1)

if __name__ == "__main__":
    run_eval()
