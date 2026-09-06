import pytest

def test_pipeline_e2e_heuristic():
    from datetime import datetime, UTC
    import yaml
    
    from src.agent.heuristic import heuristic_triage, heuristic_plan, heuristic_scan
    from src.agent.models import EmailMessage
    
    email = EmailMessage(
        id="t1", thread_id="t1", from_addr="maya@acme.io", to=["agent@acme.io"], cc=[],
        subject="Hello", body_text="Hi", body_html=None, headers={}, attachments=[],
        received_at=datetime.now(UTC)
    )
    
    triage_data = heuristic_triage(email)
    plan_data = heuristic_plan(triage_data)
    scan_data = heuristic_scan(email)
    
    assert len(plan_data["actions"]) > 0
    assert scan_data["llm_judgement"] in ["none", "likely"]

def test_pipeline_e2e_mock_llm():
    pass
