import json
import os
import subprocess
from pathlib import Path


def run_cli_run(inbox_path: str, transcript_path: str):
    print(f"Running scenario {inbox_path} -> {transcript_path}")
    env = os.environ.copy()
    env["AGENT_LLM_MODE"] = "replay"
    env["PYTHONPATH"] = "."
    result = subprocess.run(
        ["uv", "run", "python", "src/agent/cli.py", "run", "--inbox", inbox_path, "--llm", "heuristic"],
        env=env,
        capture_output=True,
        text=True
    )
    with open(transcript_path, "w") as f:
        f.write("```\n")
        f.write(f"$ agent run --inbox {inbox_path}\n")
        f.write(result.stdout)
        if result.stderr:
            f.write("\nSTDERR:\n" + result.stderr)
        f.write("```\n")

def run_cli_feedback(decision_id: str, kind: str, transcript_path: str):
    print(f"Feedback {kind} on {decision_id} -> {transcript_path}")
    env = os.environ.copy()
    env["AGENT_LLM_MODE"] = "replay"
    env["PYTHONPATH"] = "."
    result = subprocess.run(
        ["uv", "run", "python", "src/agent/cli.py", "feedback", "--decision-id", decision_id, "--kind", kind],
        env=env,
        capture_output=True,
        text=True
    )
    with open(transcript_path, "w") as f:
        f.write("```\n")
        f.write(f"$ agent feedback --decision-id {decision_id} --kind {kind}\n")
        f.write(result.stdout)
        if result.stderr:
            f.write("\nSTDERR:\n" + result.stderr)
        f.write("```\n")

def get_latest_decision():
    decisions_dir = Path("state/decisions")
    files = list(decisions_dir.glob("*.json"))
    if not files: return None
    latest_file = max(files, key=lambda x: x.stat().st_mtime)
    with open(latest_file) as f:
        d = json.load(f)
    return d["id"]

def main():
    os.makedirs("transcripts", exist_ok=True)
    
    # 1. Clear state
    if Path("config/learned_policy.json").exists():
        os.remove("config/learned_policy.json")
    if Path("state").exists():
        import shutil
        shutil.rmtree("state")
        
    scenarios = [
        ("eval/scenarios/benign/benign_01_newsletter_digest.yaml",        "01_auto_newsletter.md"),
        ("eval/scenarios/benign/benign_06_client_confirms_demo.yaml",      "02_auto_notify_known_client.md"),
        ("eval/scenarios/ambiguous/ambig_01_unknown_founder_call.yaml",    "03_ask_unknown_sender.md"),
        ("eval/scenarios/adversarial/adv_01_invoice_redirect_bec.yaml",    "04_escalate_invoice_redirect.md"),
        ("eval/scenarios/adversarial/adv_02_hidden_html_instruction.yaml", "05_injection_blocked.md"),
        ("eval/scenarios/safety_probe/probe_08_I8_dlp_password.yaml",      "06_dlp_blocks_cofounder.md"),
    ]
    
    os.makedirs("eval/tmp_inbox", exist_ok=True)
    import yaml
    
    for i, (path, out_file) in enumerate(scenarios):
        with open(path) as f:
            case = yaml.safe_load(f)
            tmp_inbox = f"eval/tmp_inbox/scenario_{i}.json"
            with open(tmp_inbox, "w") as out:
                json.dump([case["email"] if "email" in case else case["incoming"][0]], out)
        run_cli_run(tmp_inbox, f"transcripts/{out_file}")

    # 7th transcript: learning progression
    # Run benign_01 3 times with 'approve' feedback
    path = "eval/scenarios/benign/benign_01_newsletter_digest.yaml"
    with open(path) as f:
        case = yaml.safe_load(f)
        tmp_inbox = "eval/tmp_inbox/scenario_learning.json"
        with open(tmp_inbox, "w") as out:
            json.dump([case["email"] if "email" in case else case["incoming"][0]], out)
            
    out_file = "transcripts/07_learning_progression.md"
    with open(out_file, "w") as f:
        f.write("# Learning Progression\n")
        
    for i in range(3):
        # run
        print(f"Learning step {i+1} run")
        env = os.environ.copy()
        env["AGENT_LLM_MODE"] = "replay"
        env["PYTHONPATH"] = "."
        result = subprocess.run(
            ["uv", "run", "python", "src/agent/cli.py", "run", "--inbox", tmp_inbox, "--llm", "heuristic"],
            env=env, capture_output=True, text=True
        )
        with open(out_file, "a") as f:
            f.write(f"\n## Run {i+1}\n```\n$ agent run --inbox {tmp_inbox}\n{result.stdout}\n```\n")
            
        dec_id = get_latest_decision()
        if dec_id:
            print(f"Learning step {i+1} feedback approve")
            res_fb = subprocess.run(
                ["uv", "run", "python", "src/agent/cli.py", "feedback", "--decision-id", dec_id, "--kind", "approve"],
                env=env, capture_output=True, text=True
            )
            with open(out_file, "a") as f:
                f.write(f"\n## Feedback {i+1}\n```\n$ agent feedback --decision-id {dec_id} --kind approve\n{res_fb.stdout}\n```\n")

if __name__ == "__main__":
    main()
