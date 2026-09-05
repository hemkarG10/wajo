import ast
from pathlib import Path


def test_guard_does_not_import_learn():
    """
    Ensure src/agent/guard.py does not import anything from src/agent/learn/.
    This enforces the strict separation where Guard is a pure floor uninfluenced by learning.
    """
    guard_path = Path(__file__).parent.parent / "src" / "agent" / "guard.py"
    assert guard_path.exists(), "guard.py not found"
    
    with open(guard_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(guard_path))
        
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "learn" not in alias.name, f"guard.py must not import {alias.name}"
                
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                assert "learn" not in node.module, f"guard.py must not import from {node.module}"


def test_pipeline_e2e_heuristic():
    import yaml
    from src.agent.heuristic import HeuristicTriage, TemplatePlanner
    from src.agent.injection import scan
    from src.agent.decide import make_decision
    from src.agent.execute import Executor
    from src.agent.models import EmailMessage, SystemClock
    from datetime import datetime, timezone
    
    with open("config/actions.yaml", "r") as f:
        registry = yaml.safe_load(f)
    with open("config/guard.yaml", "r") as f:
        guard_cfg = yaml.safe_load(f)
        
    email = EmailMessage(
        id="t1", thread_id="t1", from_addr="maya@acme.io", to=["agent@acme.io"], cc=[],
        subject="Hello", body_text="Hi", body_html=None, headers={}, attachments=[],
        received_at=datetime.now(timezone.utc)
    )
    
    inj = scan(email, llm=None)
    
    triage = HeuristicTriage()
    situation = triage.extract(email, {"self_domain": "acme.io", "contacts": {"maya@acme.io"}}, None)
    
    planner = TemplatePlanner()
    proposals = planner.propose(situation, email, {"contacts": {"maya@acme.io"}}, None)
    
    executor = Executor(registry, clock=SystemClock(), dry_run=True)
    outcomes = []
    for action in proposals:
        decision = make_decision(situation, email, action, inj, registry, guard_cfg, clock=SystemClock())
        outcome = executor.execute(decision)
        outcomes.append(outcome)
        
    assert len(outcomes) > 0


def test_pipeline_e2e_mock_llm():
    import yaml
    from src.agent.llm import LlmAdapter
    from src.agent.triage import extract_situation
    from src.agent.planner import propose_actions
    from src.agent.injection import scan
    from src.agent.decide import make_decision
    from src.agent.execute import Executor
    from src.agent.models import EmailMessage, SystemClock
    from datetime import datetime, timezone
    
    with open("config/actions.yaml", "r") as f:
        registry = yaml.safe_load(f)
    with open("config/guard.yaml", "r") as f:
        guard_cfg = yaml.safe_load(f)
        
    email = EmailMessage(
        id="t1", thread_id="t1", from_addr="maya@acme.io", to=["agent@acme.io"], cc=[],
        subject="Hello", body_text="review this", body_html=None, headers={}, attachments=[],
        received_at=datetime.now(timezone.utc)
    )
    
    mock_llm = LlmAdapter(mode="record") # record mode falls back to mock schema generation offline
    
    inj = scan(email, llm=mock_llm)
    
    situation = extract_situation(email, mock_llm)
    
    proposals = propose_actions(situation, email, mock_llm, trusted_contacts={"maya@acme.io"}, action_registry_keys=list(registry.keys()))
    
    executor = Executor(registry, clock=SystemClock(), dry_run=True)
    outcomes = []
    for action in proposals:
        decision = make_decision(situation, email, action, inj, registry, guard_cfg, clock=SystemClock())
        outcome = executor.execute(decision)
        outcomes.append(outcome)
        
    assert len(outcomes) > 0
