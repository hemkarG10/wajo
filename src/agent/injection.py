import os
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from src.agent.models import EmailMessage, InjectionSignals


HEURISTIC_PATTERNS = [
    r"(?i)ignore\s+previous\s+instructions",
    r"(?i)system\s+prompt",
    r"(?i)override\s+instructions",
    r"(?i)forget\s+all",
    r"(?i)disregard\s+previous",
    r"(?i)bypass\s+security",
]


def scan(email: EmailMessage, inj_dict: dict | None = None) -> InjectionSignals:
    text = email.body_text or ""
    
    # 1. Heuristic Scan
    heuristic_hits = []
    for pat in HEURISTIC_PATTERNS:
        matches = re.findall(pat, text)
        if matches:
            heuristic_hits.extend(matches)
            
    # 2. LLM Scan (provided by combined triage call)
    judgement = "none"
    spans = []
    
    if inj_dict is not None:
        judgement = inj_dict.get("llm_judgement", "none")
        spans = inj_dict.get("suspicious_spans", [])
            
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
