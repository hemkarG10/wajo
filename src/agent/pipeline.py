import json
import os

from src.agent.decide import make_decision
from src.agent.execute import Executor
from src.agent.injection import scan
from src.agent.llm import LlmAdapter
from src.agent.models import (
    AutonomyLevel,
    Decision,
    EmailMessage,
    ExecutionOutcome,
    ProposedAction,
)
from src.agent.planner import propose_actions
from src.agent.triage import extract_situation


def _write_audit(decision: Decision, outcome: ExecutionOutcome):
    audit_dir = "eval/results"
    os.makedirs(audit_dir, exist_ok=True)
    row = {
        "decision": decision.model_dump(),
        "outcome": outcome.model_dump()
    }
    row_str = json.dumps(row, default=str)
    with open(f"{audit_dir}/audit.jsonl", "a") as f:
        f.write(row_str + "\n")

def process_email(email: EmailMessage, ctx: dict, llm: LlmAdapter, store: dict, clock, cfg: dict) -> tuple[list[Decision], list[ExecutionOutcome]]:
    executor = Executor(cfg["registry"], clock, dry_run=ctx.get("dry_run", True))
    
    try:
        situation, inj_dict = extract_situation(email, llm, domain=ctx.get("self_domain", "acme.io"))
        inj = scan(email, inj_dict)
            
        proposals = propose_actions(
            situation, email, llm,
            trusted_contacts=ctx.get("contacts", set()),
            action_registry_keys=list(cfg["registry"].keys())
        )
            
        if not proposals:
            proposals = [ProposedAction(type="none", params={}, provenance={}, rationale="No actions proposed", confidence=0.0)]
            
    except Exception as e:  # noqa: BLE001
        import uuid
        decision = Decision(
            id=f"err_{uuid.uuid4().hex[:8]}",
            msg_id=email.id,
            action=ProposedAction(type="none", params={}, provenance={}, rationale=str(e), confidence=0.0),
            level=AutonomyLevel.ESCALATE,
            policy_level=AutonomyLevel.ESCALATE,
            floor=AutonomyLevel.ESCALATE,
            floor_reasons=["error"],
            policy_reason={"error": "planner_invalid"},
            guard_config_hash="",
            created_at=clock.now()
        )
        outcome = executor.execute(decision)
        _write_audit(decision, outcome)
        return [decision], [outcome]

    decisions = []
    outcomes = []
    for action in proposals:
        decision = make_decision(
            situation, email, action, inj,
            cfg["registry"], cfg["guard_cfg"],
            learned_policy=store,
            clock=clock,
            policy_cfg=cfg["policy_cfg"]
        )
        decision.situation = situation
        if ctx.get("disable_guard"):
            decision.level = decision.policy_level
            
        outcome = executor.execute(decision, disable_preflight=ctx.get("disable_guard", False))
        _write_audit(decision, outcome)
        decisions.append(decision)
        outcomes.append(outcome)
        
    return decisions, outcomes
