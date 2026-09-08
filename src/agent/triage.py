import os
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from src.agent.llm import LlmAdapter
from src.agent.models import EmailMessage, Intent, SenderClass, Sensitivity, Situation, TriageOutput, InjectionJudgement


def compute_sender_class(email: EmailMessage, contacts: set[str], self_domain: str) -> SenderClass:
    if email.headers and ("List-Unsubscribe" in email.headers or email.headers.get("Precedence") == "bulk"):
        return SenderClass.NEWSLETTER
    from_domain = email.from_addr.split("@")[-1] if "@" in email.from_addr else ""
    if from_domain == self_domain:
        return SenderClass.SELF_DOMAIN
    if email.from_addr in contacts:
        return SenderClass.KNOWN_CONTACT
    for c in contacts:
        if "@" in c and c.split("@")[-1] == from_domain:
            return SenderClass.KNOWN_ORG
    return SenderClass.UNKNOWN


def check_injection_llm(email: EmailMessage, llm: LlmAdapter) -> InjectionJudgement:
    prompt_path = Path(__file__).parent / "prompts" / "injection.md"
    with open(prompt_path, "r") as f:
        system = f.read()
        
    prompt = f"Subject: {email.subject}\n\nBody:\n{email.body_text}"
    return llm.generate_structured(
        system=system,
        prompt=prompt,
        response_model=InjectionJudgement,
        model=llm.model_small
    )


def extract_situation(
    email: EmailMessage,
    llm: LlmAdapter,
    domain: str = "acme.io",
    contacts: set[str] | None = None
) -> Situation:
    contacts = contacts or set()
    sender_class = compute_sender_class(email, contacts, domain)
    
    prompt_path = Path(__file__).parent / "prompts" / "triage.md"
    with open(prompt_path, "r") as f:
        system = f.read().format(domain=domain)
        
    prompt = f"From: {email.from_addr}\nTo: {email.to}\nSubject: {email.subject}\n\nBody:\n{email.body_text}"
    
    t_out = llm.generate_structured(
        system=system,
        prompt=prompt,
        response_model=TriageOutput,
        model=llm.model_small
    )
    
    parsed_deadline = None
    if t_out.deadline:
        try:
            parsed_deadline = datetime.fromisoformat(t_out.deadline.replace('Z', '+00:00'))
        except ValueError:
            parsed_deadline = None
            
    return Situation(
        msg_id=email.id,
        sender_class=sender_class,
        intent=t_out.intent,
        sensitivity=t_out.sensitivity,
        urgency=t_out.urgency,
        requested_actions=t_out.requested_actions,
        deadline=parsed_deadline,
        thread_participants=t_out.thread_participants,
        summary=t_out.summary,
        llm_confidence=t_out.llm_confidence
    )
