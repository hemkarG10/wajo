import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import yaml

from agent.models import AutonomyLevel


def run_cli_run(inbox_path: str):
    env = os.environ.copy()
    env["AGENT_LLM_MODE"] = "replay"
    env["PYTHONPATH"] = "."
    result = subprocess.run(
        ["uv", "run", "python", "src/agent/cli.py", "run", "--inbox", inbox_path, "--llm", os.environ.get("AGENT_LLM_PROVIDER", "gemini")],

        env=env, capture_output=True, text=True
    )
    return result.stdout

def run_cli_feedback(decision_id: str, kind: str):
    env = os.environ.copy()
    env["AGENT_LLM_MODE"] = "replay"
    env["PYTHONPATH"] = "."
    result = subprocess.run(
        ["uv", "run", "python", "src/agent/cli.py", "feedback", "--decision-id", decision_id, "--kind", kind],
        env=env, capture_output=True, text=True
    )
    return result.stdout

def get_latest_decision():
    decisions_dir = Path("state/decisions")
    files = list(decisions_dir.glob("*.json"))
    if not files: return None
    latest_file = max(files, key=lambda x: x.stat().st_mtime)
    with open(latest_file) as f:
        d = json.load(f)
    return d["id"]
    
def get_latest_level():
    decisions_dir = Path("state/decisions")
    files = list(decisions_dir.glob("*.json"))
    if not files: return None
    latest_file = max(files, key=lambda x: x.stat().st_mtime)
    with open(latest_file) as f:
        d = json.load(f)
    return d["level"]["name"] if isinstance(d["level"], dict) else AutonomyLevel(d["level"]).name # if mapped

def main():
    os.makedirs("transcripts", exist_ok=True)
    if Path("eval/results/transcripts").exists():
        shutil.rmtree("eval/results/transcripts")
        
    for f in ["01_benign.md", "02_feedback_approve.md", "03_benign_learned.md", "04_feedback_stop_asking.md", "05_ambiguous.md", "06_adversarial.md", "07_safety.md"]:
        p = Path(f"transcripts/{f}")
        if p.exists(): p.unlink()

    def reset_state():
        if Path("config/learned_policy.json").exists(): os.remove("config/learned_policy.json")
        if Path("state").exists(): shutil.rmtree("state")

    reset_state()

    scenarios = [
        ("eval/scenarios/benign/benign_01_newsletter_digest.yaml",        "01_ask_newsletter.md"), # We will rename based on output
        ("eval/scenarios/benign/benign_06_client_confirms_demo.yaml",      "02_auto_notify_known_client.md"), # we will do special logic
        ("eval/scenarios/ambiguous/ambig_01_unknown_founder_call.yaml",    "03_ask_unknown_sender.md"),
        ("eval/scenarios/adversarial/adv_01_invoice_redirect_bec.yaml",    "04_escalate_invoice_redirect.md"),
        ("eval/scenarios/adversarial/adv_02_hidden_html_instruction.yaml", "05_injection_blocked.md"),
        ("eval/scenarios/safety_probe/probe_08_I8_dlp_password.yaml",      "06_dlp_blocks_cofounder.md"),
    ]

    

    for i, (path, out_file) in enumerate(scenarios):
        if i == 6: continue # 07 is handled later
        with open(path) as f:
            case = yaml.safe_load(f)
            tmp_inbox = f"/tmp/scenario_{i}.json"
            with open(tmp_inbox, "w") as out:
                json.dump([case["email"] if "email" in case else case["incoming"][0]], out)
        
        if i == 1:
            reset_state()
            for _ in range(4):
                run_cli_run(tmp_inbox)
                for p in Path("state/decisions").glob("*.json"):
                    run_cli_feedback(p.stem, "approve")
                    p.unlink()
            out_text = run_cli_run(tmp_inbox)
            level_match = re.search(r"Level:\s+(\w+)", out_text)
            level = level_match.group(1).lower() if level_match else "unknown"
            out_file = f"02_{level}_known_client.md"
            with open(f"transcripts/{out_file}", "w") as f:
                provider = os.environ.get("AGENT_LLM_PROVIDER", "gemini")
                f.write(f"*Provider: {provider}, replayed from eval/cache*\n*Warmed with 4 approvals prior to this run.*\n```\n$ agent run --inbox /tmp/scenario_1.json\n")
                f.write(out_text)
                f.write("```\n")
            continue
            
        reset_state()
        out_text = run_cli_run(tmp_inbox)
        level_match = re.search(r"Level:\s+(\w+)", out_text)
        level = level_match.group(1).lower() if level_match else "unknown"
        if i == 0: out_file = f"01_{level}_newsletter.md"
        with open(f"transcripts/{out_file}", "w") as f:
            provider = os.environ.get("AGENT_LLM_PROVIDER", "gemini")
            f.write(f"*Provider: {provider}, replayed from eval/cache*\n")
            f.write(f"```\n$ agent run --inbox {tmp_inbox}\n")
            f.write(out_text)
            if i == 5 and "Action: reply" not in out_text:
                f.write("Note: Under replay the planner proposed no external action for this email, so I8_THREAD escalation did not trigger.\n")
            f.write("```\n")

    # 07 Progression
    reset_state()
    path = "eval/scenarios/benign/benign_01_newsletter_digest.yaml"
    with open(path) as f:
        case = yaml.safe_load(f)
        tmp_inbox = "/tmp/scenario_learning.json"
        with open(tmp_inbox, "w") as out:
            json.dump([case["email"] if "email" in case else case["incoming"][0]], out)
            
    out_file = "transcripts/07_learning_progression.md"
    
    runs = []
    for i in range(12):
        out = run_cli_run(tmp_inbox)
        level_match = re.search(r"Level:\s+(\w+)", out)
        level = level_match.group(1) if level_match else "ASK"
        runs.append((i+1, level, out))
        if level == "AUTO":
            break
        for p in Path("state/decisions").glob("*.json"):
            run_cli_feedback(p.stem, "approve")
            p.unlink()
        
    first_auto_notify = next((r for r in runs if r[1] == "AUTO_NOTIFY"), None)
    first_auto = next((r for r in runs if r[1] == "AUTO"), None)
    
    with open(out_file, "w") as f:
        provider = os.environ.get("AGENT_LLM_PROVIDER", "gemini")
        f.write(f"*Provider: {provider}, replayed from eval/cache*\n# Learning Progression\n")
        
        # Run 1
        r1 = runs[0]
        f.write(f"\n## Run {r1[0]} (Level: {r1[1]})\n```\n$ agent run --inbox {tmp_inbox}\n{r1[2]}\n```\n")
        
        if first_auto_notify and first_auto_notify[0] > r1[0] + 1:
            f.write(f"\n*(runs {r1[0]+1}–{first_auto_notify[0]-1}: approved, level unchanged)*\n")
            
        if first_auto_notify and first_auto_notify[0] > r1[0]:
            f.write(f"\n## Run {first_auto_notify[0]} (Level: {first_auto_notify[1]})\n```\n$ agent run --inbox {tmp_inbox}\n{first_auto_notify[2]}\n```\n")
            
        if first_auto and first_auto_notify and first_auto[0] > first_auto_notify[0] + 1:
            f.write(f"\n*(runs {first_auto_notify[0]+1}–{first_auto[0]-1}: approved, level unchanged)*\n")
        elif first_auto and not first_auto_notify and first_auto[0] > r1[0] + 1:
            f.write(f"\n*(runs {r1[0]+1}–{first_auto[0]-1}: approved, level unchanged)*\n")
            
        if first_auto and first_auto[0] > r1[0]:
            f.write(f"\n## Run {first_auto[0]} (Level: {first_auto[1]})\n```\n$ agent run --inbox {tmp_inbox}\n{first_auto[2]}\n```\n")

if __name__ == "__main__":
    main()
