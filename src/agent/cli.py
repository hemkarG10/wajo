import typer
from rich.console import Console
from rich.panel import Panel
import yaml

from agent.ingest import FakeMailbox
from agent.llm import LlmAdapter
from agent.triage import extract_situation
from agent.planner import propose_actions
from agent.injection import scan
from agent.decide import make_decision
from agent.execute import Executor

app = typer.Typer()
console = Console()

@app.command()
def run(inbox: str = typer.Option(..., help="Path to sample inbox JSON")):
    # Load config
    with open("config/actions.yaml", "r") as f:
        registry = yaml.safe_load(f)
    with open("config/guard.yaml", "r") as f:
        guard_cfg = yaml.safe_load(f)

    mailbox = FakeMailbox(inbox)
    llm = LlmAdapter(mode="live")
    executor = Executor(registry, dry_run=True)
    
    trusted_contacts = {"maya@acme.io"} # hardcoded for demo

    for email in mailbox.new_messages():
        console.print(f"\n[bold blue]Processing Email:[/bold blue] {email.subject} (From: {email.from_addr})")
        
        # 1. Injection Scan
        inj = scan(email)
        
        # 2. Triage
        console.print("  [dim]Running triage...[/dim]")
        situation = extract_situation(email, llm)
        console.print(f"  [green]Situation:[/green] {situation.intent.value}, urgency: {situation.urgency}")
        
        # 3. Planner
        console.print("  [dim]Running planner...[/dim]")
        proposals = propose_actions(
            situation, email, llm,
            trusted_contacts=trusted_contacts,
            action_registry_keys=list(registry.keys())
        )
        
        for action in proposals:
            # 4. Decide
            decision = make_decision(
                situation, email, action, inj,
                registry, guard_cfg
            )
            
            # 5. Execute
            outcome = executor.execute(decision)
            
            p = Panel.fit(
                f"Action: {action.type}\n"
                f"Level: {decision.level.name} (Policy: {decision.policy_level.name}, Floor: {decision.floor.name})\n"
                f"Outcome: {outcome['status']} - {outcome.get('reason', '')}",
                title="Decision & Outcome",
                border_style="green"
            )
            console.print(p)

if __name__ == "__main__":
    app()
