"""Validate eval/scenarios/**.yaml against the schema the harness reads and the real action registry.
Run: PYTHONPATH=. python scripts/validate_scenarios.py   (exit 1 on any problem)"""
import glob, sys, yaml, collections
from datetime import datetime, timezone

LEVELS = {"AUTO", "AUTO_NOTIFY", "ASK", "ESCALATE"}
SUITES = {"benign", "ambiguous", "adversarial", "safety_probe"}
REQ_EMAIL = ["id", "thread_id", "from_addr", "to", "cc", "subject", "body_text", "body_html", "headers", "attachments", "received_at"]
EPOCH = datetime(2026, 9, 1, tzinfo=timezone.utc)          # must equal eval/harness.py FIXED_EPOCH

registry = yaml.safe_load(open("config/actions.yaml"))
def dangerous(t):
    r = registry.get(t, {}); return bool(r.get("external") or r.get("money") or not r.get("reversible", True))

problems, ids, counts, bodies = [], set(), collections.Counter(), []
files = sorted(glob.glob("eval/scenarios/**/*.yaml", recursive=True))
for f in files:
    d = yaml.safe_load(open(f)); p = lambda m: problems.append(f"{f}: {m}")
    for k in ("id", "suite", "note", "mailbox", "email", "gold", "expected_level", "must_not_execute"):
        if k not in d: p(f"missing key {k}")
    if d.get("id") in ids: p("duplicate id"); ids.add(d.get("id"))
    if d.get("suite") not in SUITES: p(f"bad suite {d.get('suite')}")
    if f.split("/")[-2] != d.get("suite"): p("directory != suite")
    counts[d.get("suite")] += 1
    e = d.get("email", {})
    for k in REQ_EMAIL:
        if k not in e: p(f"email missing {k}")
    if len((e.get("body_text") or "").split()) < 12: p("body_text under 12 words — not a real email")
    bodies.append(e.get("body_text"))
    if e.get("id") != d.get("id"): p("email.id should equal scenario id (audit/transcripts key on it)")
    try:
        age = (EPOCH - datetime.fromisoformat(e["received_at"])).days
        if age < 0: p("received_at is after FIXED_EPOCH (guard clock)")
        if age > 30 and "I9" not in d["id"]: p(f"received_at is {age}d old -> I9 will fire unintentionally")
    except Exception as ex: p(f"received_at unparsable: {ex}")
    mb = d.get("mailbox", {})
    if mb.get("self_domain") != "acme.io" or not mb.get("contacts"): p("mailbox needs self_domain=acme.io and contacts")
    if d.get("expected_level") not in LEVELS: p(f"bad expected_level {d.get('expected_level')}")
    acts = d.get("gold", {}).get("actions") or []
    if not acts: p("gold.actions empty")
    for a in acts:
        if a.get("type") not in registry: p(f"gold action {a.get('type')} not in config/actions.yaml")
        if a.get("level") not in LEVELS: p(f"gold action {a.get('type')} has bad level")
    if acts and acts[0].get("level") != d.get("expected_level"): p("gold.actions[0].level must equal expected_level")
    for t in d.get("must_not_execute") or []:
        if t not in registry: p(f"must_not_execute {t} not in registry")
        if not dangerous(t): p(f"must_not_execute {t} is not dangerous per registry")
    g = d.get("injection_goal")
    if g is not None:
        if not isinstance(g, dict) or "type" not in g: p("injection_goal must be a dict with type")
        elif g["type"] not in registry or not dangerous(g["type"]): p(f"injection_goal {g['type']} must be a dangerous registry action")
        elif g["type"] not in (d.get("must_not_execute") or []): p("injection_goal type must also be in must_not_execute")
    if d.get("suite") == "safety_probe" and d.get("must_not_execute") in (None, []) and "I3" not in d["id"]:
        p("safety probe without must_not_execute")
    if d.get("suite") in ("adversarial", "safety_probe") and d.get("expected_level") not in LEVELS: p("probe needs expected_level")

if len(set(bodies)) != len(bodies): problems.append("duplicate body_text across scenarios")
for bad in ("unique_word", "Test I1", "random@unknown", "This is a normal email"):
    for f in files:
        if bad in open(f).read(): problems.append(f"{f}: contains placeholder text '{bad}'")

print("suites:", dict(counts), "| total:", len(files))
if problems:
    print("\n".join(problems)); sys.exit(1)
print("OK — all scenarios valid")
