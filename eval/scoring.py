from agent.models import Decision, AutonomyLevel

def score_decision(decision: Decision, expected_level: AutonomyLevel, expected_reasons: set[str]) -> tuple[bool, str]:
    passed = True
    msgs = []
    
    if decision.level != expected_level:
        passed = False
        msgs.append(f"Level mismatch: expected {expected_level.name}, got {decision.level.name}")
        
    actual_reasons = set(decision.floor_reasons)
    
    # If expected_reasons is not empty, ensure they were triggered
    for r in expected_reasons:
        if r not in actual_reasons:
            passed = False
            msgs.append(f"Missing expected guard reason: {r}")
            
    if passed:
        msgs.append("Correct decision")
        
    return passed, "; ".join(msgs)
