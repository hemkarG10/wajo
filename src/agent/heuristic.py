"""Heuristic provider: rule-based classification with no LLM calls.

Used as the default provider for eval and as a fallback.
Exposes heuristic_generate(system, prompt, response_model) -> BaseModel
so llm.py can delegate to it.
"""
import re
from typing import TypeVar

from pydantic import BaseModel

from src.agent.models import (
    EmailMessage,
    Intent,
    ProposedAction,
    Provenance,
    SenderClass,
    Sensitivity,
    Situation,
)

T = TypeVar("T", bound=BaseModel)

# ---- Injection heuristic patterns ----
INJECTION_PATTERNS = [
    r"(?i)ignore\s+previous\s+instructions",
    r"(?i)system\s+prompt",
    r"(?i)override\s+instructions",
    r"(?i)forget\s+all",
    r"(?i)disregard\s+previous",
    r"(?i)bypass\s+security",
    r"(?i)you\s+are\s+now",
    r"(?i)new\s+instructions",
    r"(?i)ignore\s+above",
    r"(?i)pretend\s+you",
]

# ---- Intent keywords ----
INTENT_KEYWORDS: dict[str, list[str]] = {
    "newsletter": ["unsubscribe", "newsletter", "weekly digest", "mailing list", "email preferences"],
    "scheduling": ["calendar", "meeting", "schedule", "appointment", "rsvp", "availability", "call at", "call for"],
    "receipt": ["receipt", "order confirmation", "your order", "purchase confirmation", "payment received", "transaction"],
    "notification": ["notification", "alert:", "system maintenance", "update:", "status change", "reminder:"],
    "financial": ["invoice", "payment due", "wire transfer", "bank account", "billing", "pay ", "amount due"],
    "security_alert": ["password", "verify your", "suspicious activity", "security alert", "unauthorized", "login attempt", "two-factor", "2fa"],
    "legal_hr": ["legal notice", "compliance", "subpoena", "human resources", "employment", "termination", "nda", "contract review"],
    "request_for_action": ["please review", "can you", "could you", "action required", "request:", "need you to", "sign the", "approve the"],
    "sales_cold": ["demo", "free trial", "limited offer", "exclusive deal", "pricing", "enterprise plan", "scale your"],
    "social": ["happy birthday", "congratulations", "invitation", "party", "dinner", "drinks", "catch up"],
    "spam": ["buy now", "click here", "act now", "limited time", "winner", "congratulations you", "miracle", "weight loss", "viagra"],
}

# ---- Urgency markers ----
URGENCY_HIGH_MARKERS = [
    r"(?i)\burgent\b",
    r"(?i)\basap\b",
    r"(?i)\bimmediate(ly)?\b",
    r"(?i)\bcritical\b",
    r"(?i)\bemergency\b",
    r"(?i)\btime.sensitive\b",
]

# ---- DLP patterns for sensitivity ----
DLP_PATTERNS = [
    (r"(?i)\bssn\b|\b\d{3}-\d{2}-\d{4}\b", Sensitivity.REGULATED),
    (r"\b(?:\d[ -]*?){13,16}\b", Sensitivity.REGULATED),  # credit card
    (r"(?i)\bconfidential\b", Sensitivity.CONFIDENTIAL),
    (r"(?i)\bprivate\b|\bsensitive\b", Sensitivity.PERSONAL),
]

# ---- (intent, sender_class) → proposals table ----
PROPOSAL_TABLE: dict[tuple[str, str], list[dict]] = {
    ("newsletter", "newsletter"): [
        {"type": "archive", "params": {}, "prov": {}, "rationale": "Archive newsletter", "confidence": 0.85},
        {"type": "label", "params": {"label": "Newsletters"}, "prov": {"label": "system"}, "rationale": "Label newsletter", "confidence": 0.85},
    ],
    ("newsletter", "unknown"): [
        {"type": "archive", "params": {}, "prov": {}, "rationale": "Archive likely newsletter", "confidence": 0.75},
    ],
    ("scheduling", "known_contact"): [
        {"type": "create_calendar_hold", "params": {}, "prov": {}, "rationale": "Create calendar hold for scheduling request", "confidence": 0.70},
        {"type": "send_reply_known", "params": {"body": "Checking my calendar, will confirm shortly."}, "prov": {"body": "system"}, "rationale": "Acknowledge scheduling request", "confidence": 0.65},
    ],
    ("scheduling", "self_domain"): [
        {"type": "create_calendar_hold", "params": {}, "prov": {}, "rationale": "Hold calendar for internal scheduling", "confidence": 0.75},
    ],
    ("scheduling", "unknown"): [
        {"type": "save_draft_reply", "params": {"body": "Thank you for reaching out. Let me check my availability."}, "prov": {"body": "system"}, "rationale": "Draft reply for unknown scheduling", "confidence": 0.50},
    ],
    ("receipt", "known_contact"): [
        {"type": "label", "params": {"label": "Receipts"}, "prov": {"label": "system"}, "rationale": "Label receipt", "confidence": 0.80},
        {"type": "archive", "params": {}, "prov": {}, "rationale": "Archive receipt", "confidence": 0.80},
    ],
    ("receipt", "unknown"): [
        {"type": "label", "params": {"label": "Receipts"}, "prov": {"label": "system"}, "rationale": "Label receipt from unknown", "confidence": 0.60},
    ],
    ("notification", "self_domain"): [
        {"type": "mark_read", "params": {}, "prov": {}, "rationale": "Mark internal notification read", "confidence": 0.80},
    ],
    ("notification", "known_contact"): [
        {"type": "mark_read", "params": {}, "prov": {}, "rationale": "Mark notification read", "confidence": 0.75},
    ],
    ("notification", "unknown"): [
        {"type": "mark_read", "params": {}, "prov": {}, "rationale": "Mark notification from unknown as read", "confidence": 0.55},
    ],
    ("financial", "known_contact"): [
        {"type": "label", "params": {"label": "Finance"}, "prov": {"label": "system"}, "rationale": "Label financial email", "confidence": 0.70},
    ],
    ("financial", "unknown"): [
        {"type": "label", "params": {"label": "Finance"}, "prov": {"label": "system"}, "rationale": "Label financial email from unknown sender", "confidence": 0.45},
    ],
    ("security_alert", "self_domain"): [
        {"type": "label", "params": {"label": "Security"}, "prov": {"label": "system"}, "rationale": "Label security alert", "confidence": 0.70},
    ],
    ("security_alert", "unknown"): [
        {"type": "label", "params": {"label": "Security"}, "prov": {"label": "system"}, "rationale": "Label security alert from unknown", "confidence": 0.40},
    ],
    ("request_for_action", "known_contact"): [
        {"type": "send_reply_known", "params": {"body": "Got it, will take a look."}, "prov": {"body": "system"}, "rationale": "Acknowledge known contact request", "confidence": 0.65},
    ],
    ("request_for_action", "self_domain"): [
        {"type": "send_reply_known", "params": {"body": "On it."}, "prov": {"body": "system"}, "rationale": "Acknowledge internal request", "confidence": 0.70},
    ],
    ("request_for_action", "unknown"): [
        {"type": "save_draft_reply", "params": {"body": "Thank you for your message."}, "prov": {"body": "system"}, "rationale": "Draft reply for unknown request", "confidence": 0.40},
    ],
    ("sales_cold", "unknown"): [
        {"type": "archive", "params": {}, "prov": {}, "rationale": "Archive cold sales email", "confidence": 0.80},
    ],
    ("social", "known_contact"): [
        {"type": "send_reply_known", "params": {"body": "Thanks!"}, "prov": {"body": "system"}, "rationale": "Acknowledge social message", "confidence": 0.60},
    ],
    ("social", "unknown"): [
        {"type": "archive", "params": {}, "prov": {}, "rationale": "Archive social from unknown", "confidence": 0.55},
    ],
    ("spam", "unknown"): [
        {"type": "move_to_trash", "params": {}, "prov": {}, "rationale": "Trash spam", "confidence": 0.90},
        {"type": "block_sender", "params": {}, "prov": {}, "rationale": "Block spam sender", "confidence": 0.85},
    ],
}


def classify_sender(email: EmailMessage, self_domain: str = "acme.io", contacts: set[str] | None = None) -> SenderClass:
    """Classify sender using domain, contacts, and headers."""
    contacts = contacts or set()
    sender = email.from_addr.lower()

    if sender.endswith(f"@{self_domain}"):
        return SenderClass.SELF_DOMAIN

    # Check List-Unsubscribe header
    if email.headers.get("List-Unsubscribe") or email.headers.get("list-unsubscribe"):
        return SenderClass.NEWSLETTER

    if sender in {c.lower() for c in contacts}:
        return SenderClass.KNOWN_CONTACT

    # Check if domain is known org
    sender_domain = sender.split("@")[-1] if "@" in sender else ""
    if any(c.lower().endswith(f"@{sender_domain}") for c in contacts if "@" in c):
        return SenderClass.KNOWN_ORG

    return SenderClass.UNKNOWN


def classify_intent(email: EmailMessage) -> Intent:
    """Classify intent using keyword matching on subject + body."""
    text = (email.subject + " " + email.body_text).lower()

    # Check List-Unsubscribe first
    if email.headers.get("List-Unsubscribe") or email.headers.get("list-unsubscribe"):
        return Intent.NEWSLETTER
    if "unsubscribe" in text and ("newsletter" in text or "digest" in text or "mailing" in text):
        return Intent.NEWSLETTER

    # Score each intent by keyword hits
    scores: dict[str, int] = {}
    for intent_name, keywords in INTENT_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > 0:
            scores[intent_name] = score

    if not scores:
        return Intent.OTHER

    best = max(scores, key=lambda k: scores[k])
    return Intent(best)


def classify_sensitivity(email: EmailMessage) -> Sensitivity:
    """Classify sensitivity using DLP regex patterns."""
    text = email.subject + " " + email.body_text
    for pattern, level in DLP_PATTERNS:
        if re.search(pattern, text):
            return level
    return Sensitivity.NONE


def classify_urgency(email: EmailMessage) -> str:
    """Classify urgency from subject markers."""
    text = email.subject + " " + email.body_text
    for pattern in URGENCY_HIGH_MARKERS:
        if re.search(pattern, text):
            return "high"
    return "normal"


def heuristic_scan(email: EmailMessage) -> dict:
    """Run injection heuristic scan. Returns dict matching InjectionLLMOutput schema."""
    text = email.body_text or ""
    hits = []
    for pat in INJECTION_PATTERNS:
        matches = re.findall(pat, text)
        hits.extend(matches)

    judgement = "likely" if hits else "none"
    return {
        "llm_judgement": judgement,
        "suspicious_spans": hits[:5],
    }


def heuristic_triage(email: EmailMessage, self_domain: str = "acme.io", contacts: set[str] | None = None) -> dict:
    """Run heuristic triage. Returns dict matching TriageOut schema."""
    sender_class = classify_sender(email, self_domain, contacts)
    intent = classify_intent(email)
    sensitivity = classify_sensitivity(email)
    urgency = classify_urgency(email)

    return {
        "sender_class": sender_class.value,
        "intent": intent.value,
        "sensitivity": sensitivity.value,
        "urgency": urgency,
        "requested_actions": [],
        "deadline": None,
        "thread_participants": list({email.from_addr} | set(email.to)),
        "summary": email.subject[:100],
        "llm_confidence": 0.80,
        "llm_judgement": "none",
        "suspicious_spans": [],
    }


def heuristic_plan(situation_dict: dict, body_text: str = "") -> dict:
    """Generate proposals from (intent, sender_class) table, plus extracted actions."""
    intent = situation_dict.get("intent", "other")
    sender_class = situation_dict.get("sender_class", "unknown")

    key = (intent, sender_class)
    proposals = PROPOSAL_TABLE.get(key)

    if proposals is None:
        proposals = PROPOSAL_TABLE.get((intent, "unknown"))
    if proposals is None:
        proposals = [{"type": "archive", "params": {}, "prov": {}, "rationale": "Default archive", "confidence": 0.50}]

    actions = []
    
    # Extract requested actions from body text
    import re
    # forward|send|share .* to <email>
    m_fwd = re.search(r"(?i)(?:forward|send|share).*?to\s+([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", body_text)
    if m_fwd:
        email_addr = m_fwd.group(1)
        actions.append({
            "type": "forward_other",
            "to": [email_addr],
            "cc": None,
            "body": None,
            "label": None,
            "amount": None,
            "currency": None,
            "url": None,
            "subject": None,
            "rationale": f"Requested forward to {email_addr}",
            "confidence": 0.9,
            "flag_untrusted_request": True,
            "prov": {"to": "untrusted_request"}
        })
        
    # pay|wire|transfer .* ($|€)?<amount>
    m_pay = re.search(r"(?i)(?:pay|wire|transfer).*?(?:\$|€)?(\d+(?:\.\d{2})?)", body_text)
    if m_pay:
        amount_val = float(m_pay.group(1))
        actions.append({
            "type": "pay",
            "to": None,
            "cc": None,
            "body": None,
            "label": None,
            "amount": amount_val,
            "currency": "USD",
            "url": None,
            "subject": None,
            "rationale": f"Requested payment of {amount_val}",
            "confidence": 0.9,
            "flag_untrusted_request": True,
            "prov": {"amount": "untrusted_request"}
        })
        
    # reply with|send (password|credentials|code)
    m_reply = re.search(r"(?i)(?:reply with|send)\s+(password|credentials|code)", body_text)
    if m_reply:
        actions.append({
            "type": "send_reply_other",
            "to": None,
            "cc": None,
            "body": f"Requested {m_reply.group(1)}",
            "label": None,
            "amount": None,
            "currency": None,
            "url": None,
            "subject": None,
            "rationale": "Requested sensitive info",
            "confidence": 0.9,
            "flag_untrusted_request": True,
            "prov": {"body": "untrusted_request"}
        })

    for p in proposals:
        actions.append({
            "type": p["type"],
            "to": None,
            "cc": None,
            "body": p["params"].get("body"),
            "label": p["params"].get("label"),
            "amount": p["params"].get("amount"),
            "currency": None,
            "url": None,
            "subject": None,
            "rationale": p["rationale"],
            "confidence": p["confidence"],
            "flag_untrusted_request": None,
            "prov": p.get("prov", {})
        })

    return {"actions": actions}


def _parse_email_from_prompt(prompt: str) -> EmailMessage | None:
    """Best-effort parse an EmailMessage from a prompt string for heuristic use."""
    import json as _json
    from datetime import datetime

    # Try to find email fields in the prompt
    lines = prompt.strip().split("\n")
    from_addr = ""
    to_list: list[str] = []
    subject = ""
    body_lines: list[str] = []
    in_body = False
    msg_id = "heuristic"

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("From:"):
            from_addr = stripped[5:].strip()
        elif stripped.startswith("To:"):
            raw = stripped[3:].strip()
            to_list = [r.strip().strip("'\"[]") for r in raw.split(",")]
        elif stripped.startswith("Subject:"):
            subject = stripped[8:].strip()
        elif stripped.startswith("Body:") or stripped.startswith("Email Body:"):
            in_body = True
            rest = stripped.split(":", 1)[1].strip() if ":" in stripped else ""
            if rest:
                body_lines.append(rest)
        elif in_body:
            body_lines.append(line)

    if not from_addr and not body_lines:
        # Fall back: the whole prompt is the body
        body_lines = lines

    body_text = "\n".join(body_lines).strip()

    return EmailMessage(
        id=msg_id,
        thread_id="t_heuristic",
        from_addr=from_addr or "unknown@unknown.com",
        to=to_list or ["agent@acme.io"],
        cc=[],
        subject=subject,
        body_text=body_text,
        body_html=None,
        headers={},
        attachments=[],
        received_at=datetime.now(),
    )


def heuristic_generate(system: str, prompt: str, response_model: type[T]) -> T:
    """Main entry point: dispatch to the appropriate heuristic based on schema name."""
    model_name = response_model.__name__

    email = _parse_email_from_prompt(prompt)

    if model_name == "TriageOut":
        if email:
            result = heuristic_triage(email)
        else:
            result = {
                "sender_class": "unknown",
                "intent": "other",
                "sensitivity": "none",
                "urgency": "normal",
                "requested_actions": [],
                "deadline": None,
                "thread_participants": [],
                "summary": "Unknown",
                "llm_confidence": 0.50,
                "llm_judgement": "none",
                "suspicious_spans": [],
            }
        return response_model.model_validate(result)

    elif model_name == "PlannerOut":
        # Extract situation from the prompt (it's JSON-embedded)
        import json as _json
        sit_dict = {}
        try:
            # Find the JSON block in the prompt
            if "Situation:" in prompt:
                after_sit = prompt.split("Situation:", 1)[1]
                # Find the JSON object
                brace_start = after_sit.index("{")
                depth = 0
                for i, c in enumerate(after_sit[brace_start:]):
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                    if depth == 0:
                        json_str = after_sit[brace_start : brace_start + i + 1]
                        sit_dict = _json.loads(json_str)
                        break
        except (ValueError, _json.JSONDecodeError):
            pass

        result = heuristic_plan(sit_dict, email.body_text if email else "")
        return response_model.model_validate(result)

    else:
        raise ValueError(f"Heuristic provider does not support schema: {model_name}")
