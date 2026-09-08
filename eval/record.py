"""Record cache entries for all scenarios. Resumable, rate-limited.

Usage: AGENT_LLM_PROVIDER=gemini python eval/record.py [--rpm 10] [--limit 50]
"""
import argparse
import copy
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import yaml

from eval.context import scenario_ctx
from src.agent.llm import LlmAdapter
from src.agent.models import EmailMessage, SimClock
from src.agent.pipeline import process_email


def main():
    parser = argparse.ArgumentParser(description="Record LLM cache for eval scenarios")
    parser.add_argument("--rpm", type=int, default=15, help="Max requests per minute")
    parser.add_argument("--limit", type=int, default=0, help="Max scenarios to process (0=all)")
    parser.add_argument("--check", action="store_true", help="Record only sample_inbox.json")
    args = parser.parse_args()
    
    provider = os.environ.get("AGENT_LLM_PROVIDER", "")
    if not provider:
        print("ERROR: set AGENT_LLM_PROVIDER to gemini/anthropic/openai/openai_compat/heuristic to record")
        sys.exit(1)

    llm = LlmAdapter(mode="record", provider=provider)

    scenarios_dir = Path("eval/scenarios")
    files = []
    sample_inbox = []
    
    if args.check:
        with open("sample_inbox.json") as f:
            inbox = json.load(f)
            for m in inbox:
                sample_inbox.append({"email": m, "name": f"sample_inbox.json:{m['id']}"})
        total = len(sample_inbox)
    else:
        if not scenarios_dir.exists():
            print("ERROR: eval/scenarios/ not found")
            sys.exit(1)
        files = sorted(scenarios_dir.rglob("*.yaml"))
        if args.limit > 0:
            files = files[: args.limit]
        total = len(files)

    delay = 60.0 / args.rpm if args.rpm > 0 else 0

    with open("config/actions.yaml") as f:
        registry = yaml.safe_load(f)

    done = 0
    skipped = 0
    errors = 0
    
    with open("config/guard.yaml") as f:
        guard_cfg = yaml.safe_load(f)
    with open("config/policy.yaml") as f:
        policy_cfg = yaml.safe_load(f)
        
    cfg = {"registry": registry, "guard_cfg": guard_cfg, "policy_cfg": policy_cfg}
    clock = SimClock(datetime.now(UTC))

    items = sample_inbox if args.check else files

    for i, item in enumerate(items):
        if args.check:
            case = item
            raw_email = copy.deepcopy(case["email"]) # sample_inbox format
            name = item["name"]
        else:
            with open(item) as f:
                case = yaml.safe_load(f)
            raw_email = copy.deepcopy(case["incoming"][0] if "incoming" in case else case["email"])
            name = item.name

        if "from" in raw_email:
            raw_email["from_addr"] = raw_email.pop("from")
        if "body" in raw_email:
            raw_email["body_text"] = raw_email.pop("body")
        raw_email.setdefault("id", case.get("id", "msg") + "_msg")
        raw_email.setdefault("thread_id", case.get("id", "thread") + "_thread")
        raw_email.setdefault("cc", [])
        raw_email.setdefault("body_html", None)
        raw_email.setdefault("headers", {})
        raw_email.setdefault("attachments", [])
        
        if "received_at" not in raw_email and "timestamp" in raw_email:
            raw_email["received_at"] = raw_email.pop("timestamp")
        else:
            raw_email.setdefault("received_at", datetime.now(UTC))
            
        if "from_addr" not in raw_email and "sender" in raw_email:
            raw_email["from_addr"] = raw_email.pop("sender")
        if "to" not in raw_email and "recipients" in raw_email:
            raw_email["to"] = raw_email.pop("recipients")
            
        email = EmailMessage(**raw_email)

        try:
            ctx = scenario_ctx(case)
            process_email(email, ctx, llm, {}, clock, cfg)
            done += 1
        except Exception as e:
            err_str = str(e)
            if "429" in err_str or "503" in err_str or "Quota" in err_str:
                # Exponential backoff
                for attempt in range(5):
                    wait = 2**attempt * 10
                    print(f"  Rate limited, waiting {wait}s...")
                    time.sleep(wait)
                    try:
                        ctx = scenario_ctx(case)
                        process_email(email, ctx, llm, {}, clock, cfg)
                        done += 1
                        break
                    except Exception:
                        continue
                else:
                    errors += 1
                    print(f"  FAILED after retries: {name}")
            else:
                errors += 1
                print(f"  ERROR: {name}: {e}")

        remaining = total - (i + 1)
        print(f"[{i + 1}/{total}] {name} | remaining={remaining} done={done} errors={errors}")

        if delay > 0 and i < total - 1:
            time.sleep(delay)

    print(f"\nDone. {done} recorded, {skipped} skipped, {errors} errors out of {total} total scenarios.")


if __name__ == "__main__":
    main()
