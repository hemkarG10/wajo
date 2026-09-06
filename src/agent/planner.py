from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.agent.llm import LlmAdapter
from src.agent.models import EmailMessage, ProposedAction, Provenance, Situation


class ProposedActionsList(BaseModel):
    actions: list[ProposedAction]


def _derive_provenance(
    val: Any,
    email: EmailMessage,
    trusted_contacts: set[str],
    thread_participants: set[str]
) -> Provenance:
    if not isinstance(val, str):
        return Provenance.SYSTEM
        
    val_lower = val.lower()
    
    # Check if it comes from trusted context
    if any(val_lower in c.lower() for c in trusted_contacts):
        return Provenance.USER
        
    if any(val_lower in p.lower() for p in thread_participants):
        return Provenance.THREAD
        
    # Check if it appears exactly in the untrusted email body
    if val_lower in email.body_text.lower() or (email.body_html and val_lower in email.body_html.lower()):
        return Provenance.UNTRUSTED
        
    # Otherwise assume system-generated
    return Provenance.SYSTEM


def propose_actions(
    situation: Situation,
    email: EmailMessage,
    llm: LlmAdapter,
    trusted_contacts: set[str] | None = None,
    action_registry_keys: list[str] | None = None
) -> list[ProposedAction]:
    if trusted_contacts is None:
        trusted_contacts = set()
    if action_registry_keys is None:
        action_registry_keys = []
        
    prompt_path = Path(__file__).parent / "prompts" / "planner.md"
    with open(prompt_path, "r") as f:
        system = f.read().format(
            registry_keys=", ".join(action_registry_keys),
            participants=", ".join(situation.thread_participants),
            contacts=", ".join(trusted_contacts)
        )
        
    prompt = f"""
Situation:
{situation.model_dump_json(indent=2)}

Original Email:
From: {email.from_addr}
Subject: {email.subject}
Body: {email.body_text}
"""
    import os
    result = llm.generate_structured(
        system=system,
        prompt=prompt,
        response_model=ProposedActionsList,
        model=os.environ.get("AGENT_MODEL_MAIN", "claude-3-5-sonnet-20240620")
    )
    
    actions = result.actions
    
    # Post-processor: mark provenance
    for action in actions:
        action.provenance = {}
        for k, v in action.params.items():
            # In a real app we'd parse URLs/amounts specifically
            action.provenance[k] = _derive_provenance(v, email, trusted_contacts, set(situation.thread_participants))
            
    return actions
