from datetime import UTC, datetime
from enum import Enum, IntEnum
from typing import Any, Literal, Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...

class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)

class SimClock:
    def __init__(self, current_time: datetime):
        self._now = current_time
    def now(self) -> datetime:
        return self._now
    def advance(self, seconds: float = 0, hours: float = 0):
        from datetime import timedelta
        self._now += timedelta(seconds=seconds, hours=hours)

from pydantic import BaseModel


class AutonomyLevel(IntEnum):
    AUTO = 0          # proceed silently (audit log only)
    AUTO_NOTIFY = 1   # proceed, then tell the user (digest) with undo where possible
    ASK = 2           # prepare, do nothing until the user approves/edits/rejects
    ESCALATE = 3      # do nothing; surface to the user with a recommendation and why


class SenderClass(str, Enum):
    SELF_DOMAIN = "self_domain"      # same org
    KNOWN_CONTACT = "known_contact"  # in contacts or ≥3 prior threads
    KNOWN_ORG = "known_org"          # domain seen before, person not
    NEWSLETTER = "newsletter"        # List-Unsubscribe / bulk headers
    UNKNOWN = "unknown"


class Intent(str, Enum):
    SCHEDULING = "scheduling"
    INFO_REQUEST = "info_request"
    REQUEST_FOR_ACTION = "request_for_action"
    NEWSLETTER = "newsletter"
    RECEIPT = "receipt"
    NOTIFICATION = "notification"
    SOCIAL = "social"
    SALES_COLD = "sales_cold"
    SPAM = "spam"
    LEGAL_HR = "legal_hr"
    FINANCIAL = "financial"
    SECURITY_ALERT = "security_alert"
    OTHER = "other"


class Sensitivity(str, Enum):
    NONE = "none"
    PERSONAL = "personal"
    CONFIDENTIAL = "confidential"
    REGULATED = "regulated"


class AttachmentMeta(BaseModel):
    filename: str
    mime: str
    size: int





class EmailMessage(BaseModel):
    id: str
    thread_id: str
    from_addr: str
    to: list[str]
    cc: list[str]
    subject: str
    body_text: str
    body_html: str | None
    headers: dict[str, str]
    attachments: list[AttachmentMeta]
    received_at: datetime


class InjectionSignals(BaseModel):
    heuristic_hits: list[str]           # e.g. "ignore_previous", "hidden_text", "zero_width_chars"
    llm_judgement: Literal["none", "suspicious", "likely", "skipped", "error"]
    score: float                        # 0..1 combined
    suspicious_spans: list[str]


class Situation(BaseModel):
    msg_id: str
    sender_class: SenderClass
    intent: Intent
    sensitivity: Sensitivity
    urgency: Literal["low", "normal", "high"]
    requested_actions: list[str]        # what the *sender* asks for, verbatim-ish (untrusted)
    deadline: datetime | None
    thread_participants: list[str]
    summary: str                        # ≤ 2 sentences, model-written
    llm_confidence: float               # model's self-reported confidence in the extraction (0..1)


class Provenance(str, Enum):
    USER = "user"                       # from the user's own instructions/rules/contacts
    SYSTEM = "system"                   # constants, templates, thread metadata
    THREAD = "thread"                   # existing thread participants / prior messages from known contacts
    UNTRUSTED = "untrusted"             # appeared in the incoming email body/subject/attachment


class ProposedAction(BaseModel):
    type: str                           # key into the action registry (Section 5.1)
    params: dict[str, Any]              # e.g. {"to": [...], "body": "..."} / {"label": "Receipts"}
    provenance: dict[str, Provenance]   # per-param provenance, set by the planner's post-processor
    rationale: str
    confidence: float                   # planner's confidence this is what the user wants (0..1)
    flag_untrusted_request: str | None = None


class Decision(BaseModel):
    id: str
    msg_id: str
    situation: Situation | None = None
    action: ProposedAction
    level: AutonomyLevel                # final = max(policy_level, floor)
    policy_level: AutonomyLevel         # what the learned policy wanted
    floor: AutonomyLevel                # what the guard required
    floor_reasons: list[str]            # which invariants fired (I1..In)
    policy_reason: dict                 # bucket key, alpha, beta, n, lcb, llm_conf, rule_id
    guard_config_hash: str
    created_at: datetime


class ExecutionOutcome(BaseModel):
    decision_id: str
    executed: bool
    blocked_reason: str | None                # "untrusted_destination" | "kill_switch" | "rate_cap" | "dry_run" | None
    effects: list[str]                        # human-readable: "labeled msg_123 'Receipts'"
    undo_token: str | None                    # reversible actions and grace-window sends
    notified: bool
    at: datetime


class Feedback(BaseModel):
    decision_id: str
    kind: Literal[
        "approve", "edit", "reject", "undo", "stop_asking", "always_ask",
        "escalate_was_right", "escalate_was_overkill"
    ]
    edited_params: dict | None = None
    note: str | None = None
    at: datetime
