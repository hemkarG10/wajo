from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.agent.llm import LlmAdapter
from src.agent.models import EmailMessage, ProposedAction, Provenance, Situation


class PlannerAction(BaseModel):
    type: str
    to: list[str] | None = None
    cc: list[str] | None = None
    body: str | None = None
    label: str | None = None
    amount: float | None = None
    currency: str | None = None
    url: str | None = None
    subject: str | None = None
    rationale: str
    confidence: float
    flag_untrusted_request: str | None = None


class PlannerOut(BaseModel):
    actions: list[PlannerAction]


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
        response_model=PlannerOut,
        model=os.environ.get("AGENT_MODEL_MAIN", "claude-3-5-sonnet-20240620")
    )
    
    actions = []
    
    # Post-processor: map back to ProposedAction
    for plan_act in result.actions:
        params = {}
        if plan_act.to is not None: params["to"] = plan_act.to
        if plan_act.cc is not None: params["cc"] = plan_act.cc
        if plan_act.body is not None: params["body"] = plan_act.body
        if plan_act.label is not None: params["label"] = plan_act.label
        if plan_act.amount is not None: params["amount"] = plan_act.amount
        if plan_act.currency is not None: params["currency"] = plan_act.currency
        if plan_act.url is not None: params["url"] = plan_act.url
        if plan_act.subject is not None: params["subject"] = plan_act.subject
        
        prov = {}
        for k, v in params.items():
            if isinstance(v, list):
                # evaluate first item for provenance, or default to SYSTEM
                if len(v) > 0:
                    prov[k] = _derive_provenance(v[0], email, trusted_contacts, set(situation.thread_participants))
                else:
                    prov[k] = Provenance.SYSTEM
            else:
                prov[k] = _derive_provenance(v, email, trusted_contacts, set(situation.thread_participants))
            
        proposed = ProposedAction(
            type=plan_act.type,
            params=params,
            provenance=prov,
            rationale=plan_act.rationale,
            confidence=plan_act.confidence,
            flag_untrusted_request=plan_act.flag_untrusted_request
        )
        actions.append(proposed)
            
    return actions
