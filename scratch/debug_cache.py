import os
import json
import yaml
from pathlib import Path

from src.agent.models import EmailMessage
from src.agent.llm import LlmAdapter
from src.agent.injection import scan
from src.agent.triage import extract_situation
from src.agent.planner import propose_actions

def test_cache():
    print("Loading cases...")
    ds_static = []
    scenarios_dir = Path("eval/scenarios")
    for file in scenarios_dir.rglob("*.yaml"):
        with open(file, "r") as f:
            ds_static.append(yaml.safe_load(f))
            
    print(f"Loaded {len(ds_static)} cases. Running first case.")
    
    llm = LlmAdapter(mode="record", mock_responses={})
    
    case = ds_static[0]
    import copy
    from datetime import datetime
    email_data = copy.deepcopy(case["email"])
    email_data["received_at"] = datetime.fromisoformat(email_data["received_at"])
    email = EmailMessage(**email_data)
    
    print("Running scan...")
    inj = scan(email, llm)
    print("Scan done.")
    
    print("Running extract_situation...")
    situation = extract_situation(email, llm)
    print("Extract situation done.")
    
    print("Running propose_actions...")
    with open("config/actions.yaml", "r") as f:
        registry = yaml.safe_load(f)
    proposals = propose_actions(
        situation, email, llm,
        trusted_contacts={"maya@acme.io"},
        action_registry_keys=list(registry.keys())
    )
    print("Propose actions done.")
    print("All done!")

if __name__ == "__main__":
    test_cache()
