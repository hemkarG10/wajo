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
from agent.learn.learner import train_policy, save_policy, load_policy

app = typer.Typer()
console = Console()

@app.command()
def run(
    inbox: str = typer.Option(..., help="Path to sample inbox JSON"),
    policy_file: str = typer.Option(None, help="Path to learned policy JSON")
):
    # Load config
    with open("config/actions.yaml", "r") as f:
        registry = yaml.safe_load(f)
    with open("config/guard.yaml", "r") as f:
        guard_cfg = yaml.safe_load(f)

    mailbox = FakeMailbox(inbox)
    llm = LlmAdapter(mode="live")
    executor = Executor(registry, dry_run=True)
    
    learned_policy = load_policy(policy_file) if policy_file else None
    
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
                registry, guard_cfg,
                learned_policy=learned_policy
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

@app.command()
def train(out_file: str = typer.Option("policy.json", help="Path to save learned policy")):
    """Simulate user feedback and train a policy."""
    console.print("[dim]Simulating user feedback...[/dim]")
    history = [
        # 10 successful archives of newsletters from known contacts with high confidence
        {"action_type": "archive", "sender_class": "known_contact", "intent": "newsletter", "planner_confidence": 0.95}
        for _ in range(10)
    ]
    
    policy = train_policy(history)
    save_policy(policy, out_file)
    console.print(f"[green]Trained policy saved to {out_file}[/green]")
    console.print(policy)

@app.command()
def version():
    """Print the version."""
    console.print("Agent v0.1.0")

if __name__ == "__main__":
    app()
