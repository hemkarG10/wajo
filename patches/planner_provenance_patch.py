# REPLACE _derive_provenance in src/agent/planner.py and the provenance loop in propose_actions.
# Recipients (to/cc) use an ALLOW-LIST: a recipient is USER (in contacts) or THREAD (in the thread, which
# includes the email's own sender via eval/context.py) — anything else is UNTRUSTED, whether or not the literal
# string appears in the body. This closes the base64 / paraphrase gap in I5. Other params keep substring logic.
from typing import Any
from src.agent.models import EmailMessage, Provenance

_RANK = {Provenance.USER: 0, Provenance.SYSTEM: 0, Provenance.THREAD: 1, Provenance.UNTRUSTED: 2}


def _derive_provenance(val: Any, email: EmailMessage, trusted_contacts: set[str],
                       thread_participants: set[str], param_name: str | None = None) -> Provenance:
    if not isinstance(val, str):
        return Provenance.SYSTEM
    v = val.lower().strip()
    contacts = {c.lower() for c in trusted_contacts}
    thread = {p.lower() for p in thread_participants}
    if param_name in ("to", "cc"):
        if v in contacts:
            return Provenance.USER
        if v in thread:
            return Provenance.THREAD
        return Provenance.UNTRUSTED
    if v in contacts:
        return Provenance.USER
    if v in thread:
        return Provenance.THREAD
    body = (email.body_text or "").lower() + " " + (email.body_html or "").lower() + " " + (email.subject or "").lower()
    if len(v) >= 4 and v in body:
        return Provenance.UNTRUSTED
    return Provenance.SYSTEM


def derive_params_provenance(params: dict, email: EmailMessage, trusted_contacts: set[str],
                             thread_participants: set[str]) -> dict[str, Provenance]:
    """Worst provenance across every element of list-valued params (was: first element only)."""
    prov: dict[str, Provenance] = {}
    for k, v in params.items():
        vals = v if isinstance(v, list) else [v]
        worst = Provenance.SYSTEM
        for item in vals:
            p = _derive_provenance(item, email, trusted_contacts, thread_participants, param_name=k)
            if _RANK[p] > _RANK[worst]:
                worst = p
        prov[k] = worst
    return prov

# In propose_actions(), replace the `prov = {}` ... loop with:
#     prov = derive_params_provenance(params, email, trusted_contacts, set(situation.thread_participants))
# and ensure the sender is part of thread_participants (eval/context.py patch does this for scenarios;
# cli.py should add email.from_addr to ctx["thread_participants"] the same way).
