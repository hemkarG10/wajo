# DROP-IN replacement for eval/context.py (adds participants from the `email:` schema; keeps `incoming:` support)
def scenario_ctx(case: dict) -> dict:
    mailbox = case.get("mailbox", {})
    self_domain = mailbox.get("self_domain", "")
    contacts = set(mailbox.get("contacts", []))
    participants = set(mailbox.get("threads", []))
    msgs = case.get("incoming") or ([case["email"]] if "email" in case else [])
    for msg in msgs:
        for addr in [msg.get("from") or msg.get("from_addr")] + list(msg.get("to", [])) + list(msg.get("cc", [])):
            if addr:
                participants.add(addr)
    return {
        "self_domain": self_domain,
        "contacts": contacts,
        "thread_participants": list(participants),
        "dry_run": False,
    }
