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


class PlannerOut(BaseModel):
    actions: list[PlannerAction]


_RANK = {Provenance.USER: 0, Provenance.SYSTEM: 0, Provenance.THREAD: 1, Provenance.UNTRUSTED: 2}


def _derive_provenance(val: Any, email: EmailMessage, trusted_contacts: set[str],
                       thread_participants: set[str], param_name: str | None = None) -> Provenance:
    if not isinstance(val, str):
        return Provenance.SYSTEM
    v = val.lower().strip()
    contacts = {c.lower() for c in trusted_contacts}
    thread = {p.lower() for p in thread_participants}
    if param_name in ("to", "cc"):
        if v in contacts:
            return Provenance.USER
        if v in thread:
            return Provenance.THREAD
        return Provenance.UNTRUSTED
    if v in contacts:
        return Provenance.USER
    if v in thread:
        return Provenance.THREAD
    body = (email.body_text or "").lower() + " " + (email.body_html or "").lower() + " " + (email.subject or "").lower()
    if len(v) >= 4 and v in body:
        return Provenance.UNTRUSTED
    return Provenance.SYSTEM


def derive_params_provenance(params: dict, email: EmailMessage, trusted_contacts: set[str],
                             thread_participants: set[str]) -> dict[str, Provenance]:
    """Worst provenance across every element of list-valued params (was: first element only)."""
    prov: dict[str, Provenance] = {}
    for k, v in params.items():
        vals = v if isinstance(v, list) else [v]
        worst = Provenance.SYSTEM
        for item in vals:
            p = _derive_provenance(item, email, trusted_contacts, thread_participants, param_name=k)
            if _RANK[p] > _RANK[worst]:
                worst = p
        prov[k] = worst
    return prov


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
        if plan_act.type not in action_registry_keys:
            continue
            
        params = {}
        if plan_act.to is not None: params["to"] = plan_act.to
        if plan_act.cc is not None: params["cc"] = plan_act.cc
        if plan_act.body is not None: params["body"] = plan_act.body
        if plan_act.label is not None: params["label"] = plan_act.label
        if plan_act.amount is not None: params["amount"] = plan_act.amount
        if plan_act.currency is not None: params["currency"] = plan_act.currency
        if plan_act.url is not None: params["url"] = plan_act.url
        if plan_act.subject is not None: params["subject"] = plan_act.subject
        
        prov = derive_params_provenance(params, email, trusted_contacts, set(situation.thread_participants))
            
        untrusted = any(p == Provenance.UNTRUSTED for p in prov.values())
        
        proposed = ProposedAction(
            type=plan_act.type,
            params=params,
            provenance=prov,
            rationale=plan_act.rationale,
            confidence=plan_act.confidence,
            flag_untrusted_request="Parameters contain untrusted data" if untrusted else None
        )
        actions.append(proposed)
            
    return actions
