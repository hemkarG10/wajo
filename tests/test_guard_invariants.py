from datetime import datetime, timedelta, timezone

import pytest

from src.agent.guard import floor
from src.agent.models import (
    AutonomyLevel,
    EmailMessage,
    InjectionSignals,
    Intent,
    ProposedAction,
    Provenance,
    SenderClass,
    Sensitivity,
    Situation,
)


@pytest.fixture
def mock_registry():
    return {
        "archive": {"reversible": True, "external": False, "money": False, "floor": "AUTO"},
        "pay": {"reversible": False, "external": True, "money": True, "floor": "ESCALATE"},
        "send_reply_known": {"reversible": False, "external": True, "money": False, "floor": "AUTO_NOTIFY"},
        "send_reply_unknown": {"reversible": False, "external": True, "money": False, "floor": "ASK"},
        "permanent_delete": {"reversible": False, "external": False, "money": False, "floor": "ESCALATE"},
    }


@pytest.fixture
def mock_guard_cfg():
    return {
        "dlp_patterns": [r"(?i)password", r"\b\d{3}-\d{2}-\d{4}\b"],
        "stale_days": 30
    }


def _make_sit(**kwargs):
    defaults = {
        "msg_id": "msg-123",
        "sender_class": SenderClass.KNOWN_CONTACT,
        "intent": Intent.INFO_REQUEST,
        "sensitivity": Sensitivity.NONE,
        "urgency": "normal",
        "requested_actions": [],
        "deadline": None,
        "thread_participants": ["alice@known.com"],
        "summary": "Asking for info.",
        "llm_confidence": 0.9,
    }
    defaults.update(kwargs)
    return Situation(**defaults)


def _make_email(**kwargs):
    defaults = {
        "id": "msg-123",
        "thread_id": "th-123",
        "from_addr": "alice@known.com",
        "to": ["me@acme.io"],
        "cc": [],
        "subject": "Hello",
        "body_text": "Hi",
        "body_html": None,
        "headers": {},
        "attachments": [],
        "received_at": datetime.now(timezone.utc)
    }
    defaults.update(kwargs)
    return EmailMessage(**defaults)


def _make_action(type="archive", params=None, provenance=None):
    return ProposedAction(
        type=type,
        params=params or {},
        provenance=provenance or {},
        rationale="because",
        confidence=0.9
    )


def _make_inj(score=0.0, judgement="none"):
    return InjectionSignals(
        heuristic_hits=[],
        llm_judgement=judgement,
        score=score,
        suspicious_spans=[]
    )


def test_i1_money(mock_registry, mock_guard_cfg):
    sit = _make_sit()
    email = _make_email()
    act = _make_action("pay")
    inj = _make_inj()
    level, reasons = floor(sit, email, act, inj, mock_registry, mock_guard_cfg)
    assert level == AutonomyLevel.ESCALATE
    assert "I1" in reasons


def test_i2_irreversible_destructive(mock_registry, mock_guard_cfg):
    sit = _make_sit()
    email = _make_email()
    act = _make_action("permanent_delete")
    inj = _make_inj()
    level, reasons = floor(sit, email, act, inj, mock_registry, mock_guard_cfg)
    assert level == AutonomyLevel.ESCALATE
    assert "I2" in reasons


def test_i3_external_sends_never_silent(mock_registry, mock_guard_cfg):
    sit = _make_sit()
    email = _make_email()
    act = _make_action("send_reply_known")
    inj = _make_inj()
    level, reasons = floor(sit, email, act, inj, mock_registry, mock_guard_cfg)
    assert level >= AutonomyLevel.AUTO_NOTIFY
    assert "I3" in reasons


def test_i4_new_external_recipient(mock_registry, mock_guard_cfg):
    sit = _make_sit(sender_class=SenderClass.UNKNOWN, intent=Intent.REQUEST_FOR_ACTION)
    email = _make_email()
    act = _make_action("archive")
    inj = _make_inj()
    level, reasons = floor(sit, email, act, inj, mock_registry, mock_guard_cfg)
    assert level >= AutonomyLevel.ASK
    assert "I4" in reasons


def test_i5_untrusted_provenance(mock_registry, mock_guard_cfg):
    sit = _make_sit()
    email = _make_email()
    act = _make_action("send_reply_known", params={"to": "hacker@evil.com"}, provenance={"to": Provenance.UNTRUSTED})
    inj = _make_inj()
    level, reasons = floor(sit, email, act, inj, mock_registry, mock_guard_cfg)
    assert level == AutonomyLevel.ESCALATE
    assert "I5" in reasons


def test_i6_suspected_injection_external(mock_registry, mock_guard_cfg):
    sit = _make_sit()
    email = _make_email()
    act = _make_action("send_reply_known")
    inj = _make_inj(score=0.6)
    level, reasons = floor(sit, email, act, inj, mock_registry, mock_guard_cfg)
    assert level == AutonomyLevel.ESCALATE
    assert "I6" in reasons


def test_i6_suspected_injection_internal(mock_registry, mock_guard_cfg):
    sit = _make_sit()
    email = _make_email()
    act = _make_action("archive")
    inj = _make_inj(judgement="likely")
    level, reasons = floor(sit, email, act, inj, mock_registry, mock_guard_cfg)
    assert level >= AutonomyLevel.ASK
    assert "I6" in reasons


def test_i7_sensitive_categories(mock_registry, mock_guard_cfg):
    sit = _make_sit(intent=Intent.SECURITY_ALERT)
    email = _make_email()
    act = _make_action("send_reply_known")
    inj = _make_inj()
    level, reasons = floor(sit, email, act, inj, mock_registry, mock_guard_cfg)
    assert level == AutonomyLevel.ESCALATE
    assert "I7" in reasons
    
    sit = _make_sit(sensitivity=Sensitivity.REGULATED)
    level, reasons = floor(sit, email, act, inj, mock_registry, mock_guard_cfg)
    assert level == AutonomyLevel.ESCALATE
    assert "I7" in reasons


def test_i8_dlp(mock_registry, mock_guard_cfg):
    sit = _make_sit()
    email = _make_email()
    act = _make_action("send_reply_known", params={"body": "My password is Password123"})
    inj = _make_inj()
    level, reasons = floor(sit, email, act, inj, mock_registry, mock_guard_cfg)
    assert level == AutonomyLevel.ESCALATE
    assert "I8" in reasons


def test_i9_stale_days(mock_registry, mock_guard_cfg):
    now = datetime.now(timezone.utc)
    situation = _make_sit()
    stale_email = _make_email(received_at=now - timedelta(days=35))
    action = _make_action("archive")
    injection = _make_inj()
    lvl, reasons = floor(situation, stale_email, action, injection, mock_registry, mock_guard_cfg, now=now)
    assert lvl == AutonomyLevel.ASK
    assert "I9" in reasons
    
    recent_action_counts = {"AUTO_archives_per_hour": 51}
    guard_cfg_rates = {"rate_caps": {"AUTO_archives_per_hour": 50}}
    lvl, reasons = floor(situation, stale_email, action, injection, mock_registry, guard_cfg_rates, now=now, recent_action_counts=recent_action_counts)
    assert lvl == AutonomyLevel.ASK
    assert "I9" in reasons


def test_i11_kill_switch(mock_registry, mock_guard_cfg):
    sit = _make_sit()
    email = _make_email()
    act = _make_action("archive")
    inj = _make_inj()
    level, reasons = floor(sit, email, act, inj, mock_registry, mock_guard_cfg, is_paused=True)
    assert level >= AutonomyLevel.ASK
    assert "I11" in reasons
