"""Record cache entries for all scenarios. Resumable, rate-limited.

Usage: AGENT_LLM_PROVIDER=gemini python eval/record.py [--rpm 10] [--limit 50]
"""
import argparse
import copy
import os
import sys
import time
from datetime import datetime
from pathlib import Path

import yaml

from src.agent.injection import scan
from src.agent.llm import LlmAdapter
from src.agent.models import EmailMessage
from src.agent.planner import propose_actions
from src.agent.triage import extract_situation


def main():
    parser = argparse.ArgumentParser(description="Record LLM cache for eval scenarios")
    parser.add_argument("--rpm", type=int, default=15, help="Max requests per minute")
    parser.add_argument("--limit", type=int, default=0, help="Max scenarios to process (0=all)")
    args = parser.parse_args()

    provider = os.environ.get("AGENT_LLM_PROVIDER", "")
    if not provider or provider == "heuristic":
        print("ERROR: set AGENT_LLM_PROVIDER to gemini/anthropic/openai to record")
        sys.exit(1)

    llm = LlmAdapter(mode="record", provider=provider)

    scenarios_dir = Path("eval/scenarios")
    if not scenarios_dir.exists():
        print("ERROR: eval/scenarios/ not found")
        sys.exit(1)

    files = sorted(scenarios_dir.rglob("*.yaml"))
    total = len(files)
    if args.limit > 0:
        files = files[: args.limit]

    delay = 60.0 / args.rpm if args.rpm > 0 else 0

    with open("config/actions.yaml") as f:
        registry = yaml.safe_load(f)

    done = 0
    skipped = 0
    errors = 0
    trusted_contacts = {"maya@acme.io"}

    for i, file in enumerate(files):
        with open(file) as f:
            case = yaml.safe_load(f)

        raw_email = copy.deepcopy(case["email"])
        raw_email["received_at"] = datetime.fromisoformat(raw_email["received_at"])
        email = EmailMessage(**raw_email)

        # Each scenario needs 3 calls: scan, triage, planner
        # If all 3 are cached, skip
        try:
            # scan (judge)
            inj = scan(email, llm)
            # triage
            situation = extract_situation(email, llm)
            # planner
            propose_actions(
                situation,
                email,
                llm,
                trusted_contacts=trusted_contacts,
                action_registry_keys=list(registry.keys()),
            )
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
                        inj = scan(email, llm)
                        situation = extract_situation(email, llm)
                        propose_actions(
                            situation,
                            email,
                            llm,
                            trusted_contacts=trusted_contacts,
                            action_registry_keys=list(registry.keys()),
                        )
                        done += 1
                        break
                    except Exception:
                        continue
                else:
                    errors += 1
                    print(f"  FAILED after retries: {file.name}")
            else:
                errors += 1
                print(f"  ERROR: {file.name}: {e}")

        remaining = len(files) - (i + 1)
        print(f"[{i + 1}/{len(files)}] {file.name} | remaining={remaining} done={done} errors={errors}")

        if delay > 0 and i < len(files) - 1:
            time.sleep(delay)

    print(f"\nDone. {done} recorded, {skipped} skipped, {errors} errors out of {total} total scenarios.")


if __name__ == "__main__":
    main()
