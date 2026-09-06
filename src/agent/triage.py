from pathlib import Path
from typing import Literal
from datetime import datetime

from pydantic import BaseModel

from src.agent.llm import LlmAdapter
from src.agent.models import EmailMessage, Situation, SenderClass, Intent, Sensitivity


class TriageOut(BaseModel):
    msg_id: str
    sender_class: SenderClass
    intent: Intent
    sensitivity: Sensitivity
    urgency: Literal["low", "normal", "high"]
    requested_actions: list[str]
    deadline: str | None
    thread_participants: list[str]
    summary: str
    llm_confidence: float


def extract_situation(
    email: EmailMessage,
    llm: LlmAdapter,
    domain: str = "acme.io"
) -> Situation:
    prompt_path = Path(__file__).parent / "prompts" / "triage.md"
    with open(prompt_path, "r") as f:
        system = f.read().format(domain=domain)
        
    prompt = f"""
From: {email.from_addr}
To: {email.to}
Subject: {email.subject}

Body:
{email.body_text}
"""
    import os
    t_out = llm.generate_structured(
        system=system,
        prompt=prompt,
        response_model=TriageOut,
        model=os.environ.get("AGENT_MODEL_SMALL", "claude-3-haiku-20240307")
    )
    
    parsed_deadline = None
    if t_out.deadline:
        try:
            # We assume ISO format from LLM
            parsed_deadline = datetime.fromisoformat(t_out.deadline.replace('Z', '+00:00'))
        except ValueError:
            parsed_deadline = None
            
    return Situation(
        msg_id=t_out.msg_id,
        sender_class=t_out.sender_class,
        intent=t_out.intent,
        sensitivity=t_out.sensitivity,
        urgency=t_out.urgency,
        requested_actions=t_out.requested_actions,
        deadline=parsed_deadline,
        thread_participants=t_out.thread_participants,
        summary=t_out.summary,
        llm_confidence=t_out.llm_confidence
    )
