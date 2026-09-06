import random

from eval.personas import Persona
from src.agent.models import AutonomyLevel, Feedback, ProposedAction, Situation


def simulate_episode(persona: Persona, dataset: list[dict], decider_fn):
    """
    Simulates a learning episode for a given persona over a dataset of emails.
    decider_fn: Callable[[Situation, list[ProposedAction], dict], list[Decision]]
    """
    history_log = []
    current_policy = {}
    from src.agent.learn.rules import RulesEngine
    rules = RulesEngine()
    
    for case in dataset:
        sit_data = case.get("situation", {})
        if not sit_data:
            continue
            
        sit = Situation(**sit_data)
        actions = [ProposedAction(**a) for a in case.get("proposals", [])]
        
        decisions = decider_fn(sit, actions, current_policy, rules)
        for dec in decisions:
            print(f"DEBUG: Msg={sit.msg_id}, Action={dec.action.type}, Level={dec.level.name}")
            is_noise = random.random() < persona.noise
            
            feedback_kind = None
            if dec.level == AutonomyLevel.AUTO_NOTIFY:
                should_undo = persona.undo_policy(sit, dec.action)
                if is_noise:
                    should_undo = not should_undo
                    
                if should_undo:
                    feedback_kind = "undo"
                else:
                    feedback_kind = "approve"
                    
            elif dec.level in {AutonomyLevel.ASK, AutonomyLevel.ESCALATE}:
                policy_response = persona.approve_policy(sit, dec.action)
                
                if policy_response == "approve" and is_noise:
                    policy_response = "reject"
                elif policy_response == "reject" and is_noise:
                    policy_response = "approve"
                    
                if policy_response == "approve":
                    feedback_kind = "approve"
                elif policy_response == "reject":
                    feedback_kind = "reject"
                elif policy_response == "edit":
                    feedback_kind = "edit"
            
            if feedback_kind in {"approve", "edit", "reject", "undo", "stop_asking", "always_ask"}:
                feedback_obj = Feedback(
                    decision_id=dec.id,
                    kind=feedback_kind,
                    at=dec.created_at
                )
                from src.agent.learn.feedback import process_feedback
                process_feedback(feedback_obj, dec, current_policy, rules, dec.created_at, {"half_life_days": 14.0})
                
            history_log.append({
                "msg_id": sit.msg_id,
                "action": dec.action.type,
                "level": dec.level.name,
                "feedback": feedback_kind
            })
            
    return history_log, current_policy
