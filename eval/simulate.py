import json
from src.agent.models import Situation, ProposedAction, Decision, AutonomyLevel, Feedback
from src.agent.learn.learner import train_policy
from eval.personas import Persona
import random
import uuid

def simulate_episode(persona: Persona, dataset: list[dict], decider_fn):
    """
    Simulates a learning episode for a given persona over a dataset of emails.
    decider_fn: Callable[[Situation, list[ProposedAction], dict], list[Decision]]
    """
    history_log = []
    approved_actions = []
    current_policy = {}
    
    for case in dataset:
        sit_data = case.get("situation", {})
        if not sit_data:
            continue
            
        sit = Situation(**sit_data)
        actions = [ProposedAction(**a) for a in case.get("proposals", [])]
        
        decisions = decider_fn(sit, actions, current_policy)
        for dec in decisions:
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
                    
            elif dec.level == AutonomyLevel.ASK:
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
            
            if feedback_kind in {"approve", "edit"}:
                approved_actions.append({
                    "action_type": dec.action.type,
                    "sender_class": sit.sender_class,
                    "intent": sit.intent,
                    "planner_confidence": dec.action.confidence
                })
                # Re-train
                current_policy = train_policy(approved_actions)
                
            history_log.append({
                "msg_id": sit.msg_id,
                "action": dec.action.type,
                "level": dec.level.name,
                "feedback": feedback_kind
            })
            
    return history_log
