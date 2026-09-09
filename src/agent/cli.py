import json
from datetime import UTC, datetime

import typer
import yaml
from rich.console import Console
from rich.panel import Panel

from src.agent.ingest import FakeMailbox
from src.agent.learn.feedback import process_feedback
from src.agent.learn.rules import RulesEngine
from src.agent.learn.store import load_policy, save_policy
from src.agent.llm import LlmAdapter
from src.agent.models import AutonomyLevel, Decision, Feedback, SystemClock

app = typer.Typer()
console = Console()

def load_configs():
    with open("config/actions.yaml", "r") as f:
        registry = yaml.safe_load(f)
    with open("config/guard.yaml", "r") as f:
        guard_cfg = yaml.safe_load(f)
    with open("config/policy.yaml", "r") as f:
        policy_cfg = yaml.safe_load(f)
    return registry, guard_cfg, policy_cfg

@app.command()
def run(
    inbox: str = typer.Option(..., help="Path to sample inbox JSON"),
    policy_file: str = typer.Option("state/policy.json", help="Path to learned policy JSON"),
    mode: str = typer.Option("live", help="LLM cache mode: live, record, or replay"),
    llm_type: str = typer.Option("smart", "--llm", help="Provider: smart or heuristic"),
    interactive: bool = typer.Option(False, "--interactive", help="Prompt for feedback live")
):
    registry, guard_cfg, policy_cfg = load_configs()
    mailbox = FakeMailbox(inbox)
    llm = LlmAdapter(mode=mode, provider=llm_type)
    
    learned_policy = load_policy(policy_file) if policy_file else {}
    rules_engine = RulesEngine(learned_policy.get("_rules", []))
    
    trusted_contacts = {"maya@acme.io"} # hardcoded for demo
    
    for email in mailbox.new_messages():
        console.print(f"\n[bold blue]Processing Email:[/bold blue] {email.subject} (From: {email.from_addr})")
        
        from src.agent.pipeline import process_email
        
        ctx = {
            "contacts": trusted_contacts,
            "self_domain": "acme.io",
            "dry_run": not interactive,
            "thread_participants": [email.from_addr]
        }
        cfg = {
            "registry": registry,
            "guard_cfg": guard_cfg,
            "policy_cfg": policy_cfg
        }
        
        decisions, outcomes = process_email(email, ctx, llm, learned_policy, SystemClock(), cfg)
        
        for decision, outcome in zip(decisions, outcomes):
            p = Panel.fit(
                f"ID: {decision.id}\n"
                f"Action: {decision.action.type}\n"
                f"Level: {decision.level.name} (Policy: {decision.policy_level.name}, Floor: {decision.floor.name})\n"
                f"Outcome: {outcome.blocked_reason or 'executed'} - {', '.join(outcome.effects)}",
                title="Decision & Outcome",
                border_style="green" if decision.level != AutonomyLevel.ESCALATE else "red"
            )
            console.print(p)

            # Dump decision for feedback command
            import os
            os.makedirs("state/decisions", exist_ok=True)
            with open(f"state/decisions/{decision.id}.json", "w") as f:
                f.write(decision.model_dump_json())

            if interactive and decision.level in (AutonomyLevel.ASK, AutonomyLevel.ESCALATE):
                feedback_str = typer.prompt("Feedback (approve/reject/edit/undo/stop_asking/always_ask) [skip]", default="skip")
                if feedback_str != "skip":
                    if feedback_str not in ["approve", "reject", "edit", "undo", "stop_asking", "always_ask"]:
                        console.print("[bold red]Invalid feedback kind[/bold red]")
                    else:
                        fb = Feedback(decision_id=decision.id, kind=feedback_str, at=datetime.now(UTC))
                        process_feedback(fb, decision, learned_policy, rules_engine, datetime.now(UTC), policy_cfg)

    learned_policy["_rules"] = rules_engine.rules
    save_policy(learned_policy, policy_file)
    console.print(f"[bold green]Saved policy to {policy_file}[/bold green]")
        
@app.command()
def feedback(
    decision_id: str = typer.Option(..., help="Decision ID"),
    kind: str = typer.Option(..., help="Feedback kind: approve, reject, edit, undo, stop_asking, always_ask"),
    policy_file: str = typer.Option("state/policy.json", help="Path to learned policy JSON")
):
    registry, guard_cfg, policy_cfg = load_configs()
    learned_policy = load_policy(policy_file) or {}
    rules_engine = RulesEngine(learned_policy.get("_rules", []))
    
    if kind not in ["approve", "reject", "edit", "undo", "stop_asking", "always_ask"]:
        console.print(f"[bold red]Invalid feedback kind: {kind}[/bold red]")
        raise typer.Exit(1)
        
    try:
        with open(f"state/decisions/{decision_id}.json", "r") as f:
            d_dict = json.load(f)
            decision = Decision.model_validate(d_dict)
    except FileNotFoundError:
        console.print(f"[bold red]Decision {decision_id} not found in state/decisions/[/bold red]")
        raise typer.Exit(1)
        
    fb = Feedback(decision_id=decision_id, kind=kind, at=datetime.now(UTC))
    
    process_feedback(fb, decision, learned_policy, rules_engine, datetime.now(UTC), policy_cfg)
    learned_policy["_rules"] = rules_engine.rules
    save_policy(learned_policy, policy_file)
    console.print(f"[bold green]Applied feedback {kind} to decision {decision_id}[/bold green]")

@app.command()
def version():
    """Print the version."""
    console.print("Agent v0.1.0")

if __name__ == "__main__":
    app()
