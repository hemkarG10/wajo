import typer
import yaml
from rich.console import Console
from rich.panel import Panel

from src.agent.ingest import FakeMailbox
from src.agent.learn.store import load_policy
from src.agent.llm import LlmAdapter

app = typer.Typer()
console = Console()

@app.command()
def run(
    inbox: str = typer.Option(..., help="Path to sample inbox JSON"),
    policy_file: str = typer.Option(None, help="Path to learned policy JSON"),
    mode: str = typer.Option("live", help="LLM cache mode: live, record, or replay"),
    llm_type: str = typer.Option("smart", "--llm", help="Provider: smart or heuristic")
):
    # Load config
    with open("config/actions.yaml", "r") as f:
        registry = yaml.safe_load(f)
    with open("config/guard.yaml", "r") as f:
        guard_cfg = yaml.safe_load(f)
    with open("config/policy.yaml", "r") as f:
        policy_cfg = yaml.safe_load(f)

    mailbox = FakeMailbox(inbox)
    llm = LlmAdapter(mode=mode)
    from src.agent.models import SystemClock
    
    learned_policy = load_policy(policy_file) if policy_file else None
    
    trusted_contacts = {"maya@acme.io"} # hardcoded for demo
    
    if llm_type == "heuristic":
        from src.agent.heuristic import HeuristicTriage, TemplatePlanner
        triage_provider = HeuristicTriage()
        planner_provider = TemplatePlanner()
    else:
        triage_provider = None
        planner_provider = None

    for email in mailbox.new_messages():
        console.print(f"\n[bold blue]Processing Email:[/bold blue] {email.subject} (From: {email.from_addr})")
        
        from src.agent.pipeline import process_email
        
        ctx = {
            "contacts": trusted_contacts,
            "self_domain": "acme.io",
            "triage_provider": triage_provider,
            "planner_provider": planner_provider,
            "dry_run": True
        }
        cfg = {
            "registry": registry,
            "guard_cfg": guard_cfg,
            "policy_cfg": policy_cfg
        }
        from src.agent.models import AutonomyLevel
        store = learned_policy or {}
        
        decisions, outcomes = process_email(email, ctx, llm, store, SystemClock(), cfg)
        
        for decision, outcome in zip(decisions, outcomes):
            p = Panel.fit(
                f"Action: {decision.action.type}\n"
                f"Level: {decision.level.name} (Policy: {decision.policy_level.name}, Floor: {decision.floor.name})\n"
                f"Outcome: {outcome.blocked_reason or 'executed'} - {', '.join(outcome.effects)}",
                title="Decision & Outcome",
                border_style="green" if decision.level != AutonomyLevel.ESCALATE else "red"
            )
            console.print(p)

@app.command()
def version():
    """Print the version."""
    console.print("Agent v0.1.0")

if __name__ == "__main__":
    app()
