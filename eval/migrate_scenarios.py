import hashlib
import os

import yaml


def get_hash(subject, body):
    return hashlib.sha256((subject + body).encode('utf-8')).hexdigest()

def migrate():
    seen = set()
    total_deduped = 0
    total_processed = 0

    suites = ["benign", "ambiguous", "adversarial", "safety_probe"]
    for suite in suites:
        d = f"eval/scenarios/{suite}"
        if not os.path.exists(d): continue
        
        for fname in os.listdir(d):
            if not fname.endswith(".yaml"): continue
            
            p = os.path.join(d, fname)
            with open(p) as f:
                data = yaml.safe_load(f)
                
            if "incoming" in data:
                continue # already migrated
                
            total_processed += 1
            
            email = data.get("email", {})
            subject = email.get("subject", "")
            body = email.get("body_text", "")
            
            # Since UUIDs make the subjects unique, let's strip the UUID to check for real duplication
            # format: f"{cat.title()} - {uuid.uuid4().hex[:6]}" or f"Question {uuid.uuid4().hex[:6]}"
            clean_subject = subject.rsplit(" - ", 1)[0] if " - " in subject else subject.rsplit(" ", 1)[0]
            
            h = get_hash(clean_subject, body)
            if h in seen:
                os.remove(p)
                total_deduped += 1
                continue
                
            seen.add(h)
            
            new_data = {
                "id": data.get("id"),
                "suite": suite,
                "mailbox": {
                    "self_domain": "acme.io",
                    "contacts": ["maya@acme.io"],
                    "threads": []
                },
                "incoming": [
                    {
                        "from": email.get("from_addr", ""),
                        "to": email.get("to", ["agent@acme.io"]),
                        "cc": email.get("cc", []),
                        "headers": email.get("headers", {}),
                        "subject": subject,
                        "body": body,
                        "received_at": email.get("received_at", "")
                    }
                ],
                "gold": {
                    "actions": [],
                    "level_range": [data.get("expected_level", "AUTO")],
                    "must_not_execute": [],
                    "injection_goal": None
                }
            }
            
            with open(p, "w") as f:
                yaml.dump(new_data, f, sort_keys=False)
                
    print(f"Processed {total_processed}, deduped {total_deduped}, remaining {len(seen)}")

if __name__ == "__main__":
    migrate()
