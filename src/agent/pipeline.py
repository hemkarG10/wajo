import json
import os
from datetime import timedelta

from agent.decide import make_decision
from agent.execute import Executor
from agent.injection import scan
from agent.llm import LlmAdapter
from agent.models import (
    AutonomyLevel,
    Decision,
    EmailMessage,
    ExecutionOutcome,
    ProposedAction,
)
from agent.planner import propose_actions


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


def _recent_action_counts(ctx: dict, now) -> dict[str, int]:
    """Return fixed-window autonomous-action counts for this processing session."""
    state = ctx.setdefault(
        "_rate_state",
        {"window_started": now, "counts": {}},
    )
    started = state.get("window_started", now)
    if now - started >= timedelta(hours=1):
        state["window_started"] = now
        state["counts"] = {}
    return state["counts"]


def _record_autonomous_action(ctx: dict, decision: Decision, outcome: ExecutionOutcome, registry: dict):
    """Record an executed autonomous action against configured hourly counters."""
    if not outcome.executed or decision.level not in {
        AutonomyLevel.AUTO,
        AutonomyLevel.AUTO_NOTIFY,
    }:
        return
    counts = _recent_action_counts(ctx, outcome.at)
    action_def = registry.get(decision.action.type, {})
    if decision.level == AutonomyLevel.AUTO_NOTIFY and action_def.get("external"):
        counts["AUTO_NOTIFY_sends_per_hour"] = counts.get("AUTO_NOTIFY_sends_per_hour", 0) + 1
    if decision.level == AutonomyLevel.AUTO and decision.action.type == "archive":
        counts["AUTO_archives_per_hour"] = counts.get("AUTO_archives_per_hour", 0) + 1

def process_email(email: EmailMessage, ctx: dict, llm: LlmAdapter, store: dict, clock, cfg: dict) -> tuple[list[Decision], list[ExecutionOutcome]]:
    executor = Executor(cfg["registry"], clock, dry_run=ctx.get("dry_run", True))
    
    try:
        from agent.triage import check_injection_llm, extract_situation
        inj_judgement = check_injection_llm(email, llm)
        inj_dict = {
            "llm_judgement": inj_judgement.llm_judgement,
            "suspicious_spans": inj_judgement.suspicious_spans
        }
        inj = scan(email, inj_dict)
        situation = extract_situation(email, llm, domain=ctx.get("self_domain", "acme.io"), contacts=ctx.get("contacts", set()))
            
        proposals = propose_actions(
            situation, email, llm,
            trusted_contacts=ctx.get("contacts", set()),
            action_registry_keys=list(cfg["registry"].keys())
        )
            
        if not proposals:
            proposals = [ProposedAction(type="none", params={}, provenance={}, rationale="No actions proposed", confidence=0.0)]
            
    except Exception as e:
        from agent.llm import LLMError
        if isinstance(e, LLMError):
            raise
        import traceback
        traceback.print_exc()
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
    
    from agent.learn.rules import RulesEngine
    rules = RulesEngine(store.get("_rules", []))
    
    for action in proposals:
        recent_counts = _recent_action_counts(ctx, clock.now())
        decision = make_decision(
            situation, email, action, inj,
            cfg["registry"], cfg["guard_cfg"],
            learned_policy=store,
            rules=rules,
            clock=clock,
            policy_cfg=cfg["policy_cfg"],
            recent_action_counts=recent_counts,
        )
        decision.situation = situation
        outcome = executor.execute(decision)
        _record_autonomous_action(ctx, decision, outcome, cfg["registry"])
        _write_audit(decision, outcome)
        decisions.append(decision)
        outcomes.append(outcome)
        
    return decisions, outcomes
