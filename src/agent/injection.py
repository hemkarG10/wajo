import re

from src.agent.models import EmailMessage, InjectionSignals

HEURISTIC_PATTERNS = [
    r"(?i)ignore\s+previous\s+instructions",
    r"(?i)system\s+prompt",
    r"(?i)override\s+instructions",
    r"(?i)forget\s+all",
    r"(?i)disregard\s+previous",
    r"(?i)bypass\s+security",
    r"[\u200b-\u200f\u202a-\u202e\u2060-\u206f]",
    r"(?i)display:\s*none",
    r"(?i)font-size:\s*0",
    r"(?i)you\s+are\s+now",
    r"(?i)new\s+instructions",
    r"(?i)as\s+an\s+ai",
    r"((?:[A-Za-z0-9+/]{4}){10,}(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?)",
    r"(?i)(?:wire|gift\s+card).*?(?:urgent|immediately)",
    r"(?i)(?:urgent|immediately).*?(?:wire|gift\s+card)",
]


def scan(email: EmailMessage, inj_dict: dict | None = None) -> InjectionSignals:
    text = (email.subject or "") + "\n" + (email.body_text or "") + "\n" + (email.body_html or "")
    
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
    elif judgement == "suspicious":
        score += 0.25
        
    if heuristic_hits:
        score += min(0.5, len(heuristic_hits) * 0.25)
        
    return InjectionSignals(
        heuristic_hits=heuristic_hits,
        llm_judgement=judgement,
        score=score,
        suspicious_spans=spans
    )
