import re
from datetime import datetime
from typing import Any

from src.agent.models import (
    Intent,
    ProposedAction,
    Provenance,
    SenderClass,
    Sensitivity,
    Situation,
)

class HeuristicTriage:
    def extract(self, email, ctx, llm_adapter) -> Situation:
        # Rule-based inference of sender_class
        sender = email.from_addr.lower()
        if sender.endswith(f"@{ctx.get('self_domain', '')}"):
            sender_class = SenderClass.SELF_DOMAIN
        elif any(contact in sender for contact in ctx.get("contacts", [])):
            sender_class = SenderClass.KNOWN_CONTACT
        else:
            sender_class = SenderClass.UNKNOWN

        # Rule-based intent inference
        intent = Intent.OTHER
        if "List-Unsubscribe" in email.headers or "unsubscribe" in email.body_text.lower():
            sender_class = SenderClass.NEWSLETTER
            intent = Intent.NEWSLETTER
        elif any(m.mime == "text/calendar" for m in email.attachments) or "calendar" in email.body_text.lower():
            intent = Intent.SCHEDULING
        elif "invoice" in email.body_text.lower() or "pay" in email.body_text.lower():
            intent = Intent.FINANCIAL
        elif "password" in email.body_text.lower() or "verify" in email.body_text.lower():
            intent = Intent.SECURITY_ALERT
        elif "request" in email.subject.lower():
            intent = Intent.REQUEST_FOR_ACTION

        # Rule-based sensitivity inference via simple regex
        sensitivity = Sensitivity.NONE
        if re.search(r'(?i)ssn|\b\d{3}-\d{2}-\d{4}\b', email.body_text):
            sensitivity = Sensitivity.REGULATED

        return Situation(
            msg_id=email.id,
            sender_class=sender_class,
            intent=intent,
            sensitivity=sensitivity,
            urgency="normal",
            requested_actions=[],
            deadline=None,
            thread_participants=ctx.get("thread_participants", []),
            summary=email.subject[:100],
            llm_confidence=1.0,
        )

class TemplatePlanner:
    def propose(self, situation: Situation, email, ctx, llm_adapter) -> list[ProposedAction]:
        actions = []
        if situation.intent == Intent.NEWSLETTER:
            actions.append(
                ProposedAction(
                    type="archive",
                    params={},
                    provenance={},
                    rationale="Archiving newsletter",
                    confidence=0.9
                )
            )
            actions.append(
                ProposedAction(
                    type="label",
                    params={"label": "Newsletters"},
                    provenance={"label": Provenance.SYSTEM},
                    rationale="Labeling newsletter",
                    confidence=0.9
                )
            )
        elif situation.intent == Intent.FINANCIAL:
            actions.append(
                ProposedAction(
                    type="pay",
                    params={"amount": 100, "destination": "vendor"},
                    provenance={"amount": Provenance.UNTRUSTED, "destination": Provenance.UNTRUSTED},
                    rationale="Attempting payment from invoice",
                    confidence=0.8
                )
            )
        elif situation.sender_class in (SenderClass.KNOWN_CONTACT, SenderClass.SELF_DOMAIN):
            actions.append(
                ProposedAction(
                    type="send_reply_known",
                    params={"body": "Got it, thanks!"},
                    provenance={"body": Provenance.SYSTEM},
                    rationale="Simple acknowledgment",
                    confidence=0.7
                )
            )
        else:
            actions.append(
                ProposedAction(
                    type="send_reply_unknown",
                    params={"body": "Message received."},
                    provenance={"body": Provenance.SYSTEM},
                    rationale="Generic reply to unknown",
                    confidence=0.5
                )
            )
            
        return actions
