import json
from src.agent.models import EmailMessage, InjectionSignals
from src.agent.triage import TriageOut
from src.agent.planner import PlannerOut
from src.agent.llm import LlmAdapter

def run():
    with open("sample_inbox.json") as f:
        inbox = json.load(f)
        
    phishing = None
    for item in inbox:
        if "phishing" in item.get("id", "").lower() or "suspicious" in item.get("body", "").lower() or "verify your account" in item.get("subject", "").lower() or "urgent" in item.get("subject", "").lower():
            phishing = item
            break
            
    if not phishing:
        phishing = inbox[0]  # fallback
        
    email = EmailMessage(
        id=phishing["id"],
        thread_id=phishing["thread_id"],
        from_addr=phishing["from_addr"],
        to=phishing["to"],
        cc=phishing.get("cc", []),
        subject=phishing["subject"],
        body_text=phishing["body_text"],
        body_html=None,
        headers=phishing.get("headers", {}),
        attachments=[],
        received_at="2026-09-06T00:00:00Z"
    )
    
    llm = LlmAdapter(mode="live")
    
    print("--- JUDGE ---")
    try:
        from src.agent.injection import scan
        res1 = scan(email, llm)
        print(res1.model_dump_json(indent=2))
    except Exception as e:
        print(e)
        
    print("\n--- TRIAGE ---")
    try:
        from src.agent.triage import extract_situation
        res2 = extract_situation(email, llm)
        print(res2.model_dump_json(indent=2))
    except Exception as e:
        print(e)
        
    print("\n--- PLANNER ---")
    try:
        from src.agent.planner import propose_actions
        # fake situation
        if 'res2' in locals():
            sit = res2
        else:
            raise Exception("no situation")
        res3 = propose_actions(sit, email, llm)
        print(json.dumps([a.model_dump() for a in res3], indent=2))
    except Exception as e:
        print(e)

if __name__ == "__main__":
    run()
