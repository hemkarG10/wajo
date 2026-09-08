from src.agent.models import EmailMessage, Provenance
from src.agent.planner import _derive_provenance


def test_planner_provenance():
    email = EmailMessage(
        id="msg",
        thread_id="thread",
        from_addr="sender@example.com",
        to=["recipient@example.com"],
        cc=[],
        subject="Hello",
        body_text="Some text that does not contain the target email.",
        body_html=None,
        headers={},
        attachments=[],
        received_at="2026-09-01T00:00:00Z"
    )
    trusted = {"trusted@example.com"}
    thread = {"sender@example.com", "other@example.com"}

    # Sender's own address is THREAD
    assert _derive_provenance("sender@example.com", email, trusted, thread, param_name="to") == Provenance.THREAD

    # A "to" address not in contacts or thread is UNTRUSTED even if not in body
    assert _derive_provenance("unknown@example.com", email, trusted, thread, param_name="to") == Provenance.UNTRUSTED
    
    # A trusted address is USER
    assert _derive_provenance("trusted@example.com", email, trusted, thread, param_name="to") == Provenance.USER
