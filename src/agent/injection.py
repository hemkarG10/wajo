from agent.models import EmailMessage, InjectionSignals

def scan(email: EmailMessage) -> InjectionSignals:
    # Dummy implementation for Day 2 pipeline
    return InjectionSignals(
        heuristic_hits=[],
        llm_judgement="none",
        score=0.0,
        suspicious_spans=[]
    )
