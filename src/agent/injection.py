import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from src.agent.llm import LlmAdapter
from src.agent.models import EmailMessage, InjectionSignals


class InjectionLLMOutput(BaseModel):
    llm_judgement: Literal["likely", "unlikely", "none"]
    suspicious_spans: list[str]


HEURISTIC_PATTERNS = [
    r"(?i)ignore\s+previous\s+instructions",
    r"(?i)system\s+prompt",
    r"(?i)override\s+instructions",
    r"(?i)forget\s+all",
    r"(?i)disregard\s+previous",
    r"(?i)bypass\s+security",
]


def scan(email: EmailMessage, llm: LlmAdapter | None = None) -> InjectionSignals:
    text = email.body_text or ""
    
    # 1. Heuristic Scan
    heuristic_hits = []
    for pat in HEURISTIC_PATTERNS:
        matches = re.findall(pat, text)
        if matches:
            heuristic_hits.extend(matches)
            
    # 2. LLM Scan
    judgement = "none"
    spans = []
    
    if llm is not None:
        prompt_path = Path(__file__).parent / "prompts" / "injection.md"
        with open(prompt_path, "r") as f:
            system = f.read()
            
        prompt = f"Email Body:\n{text}"
        
        try:
            llm_out = llm.generate_structured(
                system=system,
                prompt=prompt,
                response_model=InjectionLLMOutput,
                model="claude-3-5-haiku-latest" # injection judge doesn't need to be huge
            )
            judgement = llm_out.llm_judgement
            spans = llm_out.suspicious_spans
        except Exception:  # noqa: BLE001
            # If LLM fails, we fall back to heuristics safely
            judgement = "error"
            
    # 3. Compute score (0.0 to 1.0)
    score = 0.0
    if judgement == "likely":
        score += 0.5
    elif judgement == "none":
        pass
        
    if heuristic_hits:
        score += min(0.5, len(heuristic_hits) * 0.25)
        
    return InjectionSignals(
        heuristic_hits=heuristic_hits,
        llm_judgement=judgement,
        score=score,
        suspicious_spans=spans
    )
