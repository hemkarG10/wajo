import random
from dataclasses import dataclass
from typing import Callable, Literal
from src.agent.models import Situation, ProposedAction, AutonomyLevel

@dataclass
class Persona:
    name: str
    approve_policy: Callable[[Situation, ProposedAction], Literal["approve", "edit", "reject"]]
    undo_policy: Callable[[Situation, ProposedAction], bool]
    noise: float = 0.05

def hands_off_founder_approve(sit: Situation, action: ProposedAction) -> Literal["approve", "edit", "reject"]:
    if action.type in {"archive", "label", "mark_read", "snooze"}:
        return "approve"
    if sit.sender_class in {"known_contact", "self_domain"} and action.type == "send_reply_known":
        return "approve"
    if action.type == "create_calendar_hold" or action.type == "accept_calendar_invite":
        return "approve"
    return "reject"

def hands_off_founder_undo(sit: Situation, action: ProposedAction) -> bool:
    # Undoes if they wouldn't have approved it
    return hands_off_founder_approve(sit, action) == "reject"

hands_off_founder = Persona(
    name="hands_off_founder",
    approve_policy=hands_off_founder_approve,
    undo_policy=hands_off_founder_undo,
    noise=0.05
)

def cautious_lawyer_approve(sit: Situation, action: ProposedAction) -> Literal["approve", "edit", "reject"]:
    # Approves read-only/internal things, rejects all external sends except known replies with a small chance
    if action.type in {"archive", "label", "mark_read"}:
        return "approve"
    return "reject"

def cautious_lawyer_undo(sit: Situation, action: ProposedAction) -> bool:
    return cautious_lawyer_approve(sit, action) == "reject"

cautious_lawyer = Persona(
    name="cautious_lawyer",
    approve_policy=cautious_lawyer_approve,
    undo_policy=cautious_lawyer_undo,
    noise=0.01
)

def paranoid_security_eng_approve(sit: Situation, action: ProposedAction) -> Literal["approve", "edit", "reject"]:
    # Rejects everything except labeling
    if action.type == "label":
        return "approve"
    return "reject"

def paranoid_security_eng_undo(sit: Situation, action: ProposedAction) -> bool:
    return paranoid_security_eng_approve(sit, action) == "reject"

paranoid_security_eng = Persona(
    name="paranoid_security_eng",
    approve_policy=paranoid_security_eng_approve,
    undo_policy=paranoid_security_eng_undo,
    noise=0.0
)

def get_persona(name: str) -> Persona:
    if name == "hands_off_founder":
        return hands_off_founder
    if name == "cautious_lawyer":
        return cautious_lawyer
    if name == "paranoid_security_eng":
        return paranoid_security_eng
    raise ValueError(f"Unknown persona: {name}")
