from pathlib import Path

from src.agent.llm import LlmAdapter
from src.agent.models import EmailMessage, Situation


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
    return llm.generate_structured(
        system=system,
        prompt=prompt,
        response_model=Situation
    )
