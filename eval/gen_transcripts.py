import os
import subprocess
from pathlib import Path
import json

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
        ("eval/scenarios/benign/00.yaml", "01_benign.md"),
        ("eval/scenarios/benign/02.yaml", "03_benign_learned.md"),
        ("eval/scenarios/ambiguous/00.yaml", "05_ambiguous.md"),
        ("eval/scenarios/adversarial/00.yaml", "06_adversarial.md"),
        ("eval/scenarios/safety_probe/00.yaml", "07_safety.md")
    ]
    
    # Create temp inboxes
    os.makedirs("eval/tmp_inbox", exist_ok=True)
    
    # 01. First benign
    with open(scenarios[0][0]) as f:
        import yaml
        case = yaml.safe_load(f)
        with open("eval/tmp_inbox/01.json", "w") as out:
            json.dump([case["email"]], out)
            
    run_cli_run("eval/tmp_inbox/01.json", "transcripts/01_benign.md")
    dec_id = get_latest_decision()
    
    # 02. Feedback approve
    run_cli_feedback(dec_id, "approve", "transcripts/02_feedback_approve.md")
    
    # 03. Second benign
    with open(scenarios[1][0]) as f:
        case = yaml.safe_load(f)
        with open("eval/tmp_inbox/02.json", "w") as out:
            json.dump([case["email"]], out)
    run_cli_run("eval/tmp_inbox/02.json", "transcripts/03_benign_learned.md")
    dec_id2 = get_latest_decision()
    
    # 04. Feedback stop_asking
    run_cli_feedback(dec_id2, "stop_asking", "transcripts/04_feedback_stop_asking.md")
    
    # 05. Ambiguous
    with open(scenarios[2][0]) as f:
        case = yaml.safe_load(f)
        with open("eval/tmp_inbox/05.json", "w") as out:
            json.dump([case["email"]], out)
    run_cli_run("eval/tmp_inbox/05.json", "transcripts/05_ambiguous.md")
    
    # 06. Adversarial
    with open(scenarios[3][0]) as f:
        case = yaml.safe_load(f)
        with open("eval/tmp_inbox/06.json", "w") as out:
            json.dump([case["email"]], out)
    run_cli_run("eval/tmp_inbox/06.json", "transcripts/06_adversarial.md")

    # 07. Safety
    with open(scenarios[4][0]) as f:
        case = yaml.safe_load(f)
        with open("eval/tmp_inbox/07.json", "w") as out:
            json.dump([case["email"]], out)
    run_cli_run("eval/tmp_inbox/07.json", "transcripts/07_safety.md")

if __name__ == "__main__":
    main()
