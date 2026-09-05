import json
import re
from datetime import datetime, timezone
from typing import Iterator, Protocol

from src.agent.models import AttachmentMeta, EmailMessage


class MailProvider(Protocol):
    def new_messages(self) -> Iterator[EmailMessage]: ...


def html_to_text(html: str | None) -> str:
    """Strips HTML tags to extract plaintext."""
    if not html:
        return ""
    # Very basic strip; in a real app, use beautifulsoup4
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def normalize_email(raw_email: dict) -> EmailMessage:
    """Converts a raw email dict into an EmailMessage model."""
    body_text = raw_email.get("body_text")
    body_html = raw_email.get("body_html")
    
    if not body_text and body_html:
        body_text = html_to_text(body_html)
        
    attachments = [
        AttachmentMeta(**att) for att in raw_email.get("attachments", [])
    ]
    
    received_at = raw_email.get("received_at")
    if isinstance(received_at, str):
        received_at = datetime.fromisoformat(received_at)
    if not received_at:
        received_at = datetime.now(timezone.utc)
        
    return EmailMessage(
        id=raw_email.get("id", "missing-id"),
        thread_id=raw_email.get("thread_id", "missing-thread"),
        from_addr=raw_email.get("from_addr", ""),
        to=raw_email.get("to", []),
        cc=raw_email.get("cc", []),
        subject=raw_email.get("subject", ""),
        body_text=body_text or "",
        body_html=body_html,
        headers=raw_email.get("headers", {}),
        attachments=attachments,
        received_at=received_at,
    )


class FakeMailbox:
    """A JSON-backed fake mailbox."""
    def __init__(self, file_path: str):
        self.file_path = file_path
        
    def new_messages(self) -> Iterator[EmailMessage]:
        with open(self.file_path, "r") as f:
            data = json.load(f)
            
        for msg_data in data:
            yield normalize_email(msg_data)
