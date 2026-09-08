def scenario_ctx(case: dict) -> dict:
    mailbox = case.get("mailbox", {})
    self_domain = mailbox.get("self_domain", "")
    contacts = set(mailbox.get("contacts", []))
    threads = set(mailbox.get("threads", []))
    
    participants = set(threads)
    for msg in case.get("incoming", []):
        if "from" in msg:
            participants.add(msg["from"])
        elif "from_addr" in msg:
            participants.add(msg["from_addr"])
        for to in msg.get("to", []):
            participants.add(to)
        for cc in msg.get("cc", []):
            participants.add(cc)
            
    return {
        "self_domain": self_domain,
        "contacts": contacts,
        "thread_participants": list(participants),
        "dry_run": False
    }
