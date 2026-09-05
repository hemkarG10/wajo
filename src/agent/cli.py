import typer
from rich.console import Console
from rich.panel import Panel
import yaml

from src.agent.ingest import FakeMailbox
from src.agent.llm import LlmAdapter
from src.agent.triage import extract_situation
from src.agent.planner import propose_actions
from src.agent.injection import scan
from src.agent.decide import make_decision
from src.agent.execute import Executor
from src.agent.learn.store import save_policy, load_policy

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

    mailbox = FakeMailbox(inbox)
    llm = LlmAdapter(mode=mode)
    from src.agent.models import SystemClock
    executor = Executor(registry, clock=SystemClock(), dry_run=True)
    
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
        
        # 1. Injection Scan
        inj = scan(email, llm)
        
        # 2. Triage
        console.print("  [dim]Running triage...[/dim]")
        if triage_provider:
            situation = triage_provider.extract(email, {"self_domain": "acme.io", "contacts": trusted_contacts}, llm)
        else:
            situation = extract_situation(email, llm)
        console.print(f"  [green]Situation:[/green] {situation.intent.value}, urgency: {situation.urgency}")
        
        # 3. Planner
        console.print("  [dim]Running planner...[/dim]")
        if planner_provider:
            proposals = planner_provider.propose(situation, email, {"contacts": trusted_contacts}, llm)
        else:
            proposals = propose_actions(
                situation, email, llm,
                trusted_contacts=trusted_contacts,
                action_registry_keys=list(registry.keys())
            )
        
        for action in proposals:
            # 4. Decide
            from src.agent.models import SystemClock
            decision = make_decision(
                situation, email, action, inj,
                registry, guard_cfg,
                clock=SystemClock(),
                learned_policy=learned_policy
            )
            
            # 5. Execute
            outcome = executor.execute(decision)
            
            p = Panel.fit(
                f"Action: {action.type}\n"
                f"Level: {decision.level.name} (Policy: {decision.policy_level.name}, Floor: {decision.floor.name})\n"
                f"Outcome: {outcome.blocked_reason or 'executed'} - {', '.join(outcome.effects)}",
                title="Decision & Outcome",
                border_style="green"
            )
            console.print(p)

@app.command()
def version():
    """Print the version."""
    console.print("Agent v0.1.0")

if __name__ == "__main__":
    app()
