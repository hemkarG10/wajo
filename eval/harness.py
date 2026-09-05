import json
import uuid
import yaml
from datetime import datetime, timezone
from eval.personas import get_persona
from eval.simulate import simulate_episode
from src.agent.models import Situation, ProposedAction, Decision, AutonomyLevel
from src.agent.decide import make_decision
from src.agent.injection import InjectionSignals

def generate_mock_learning_dataset(n=60):
    ds = []
    # Mix of newsletters (archive) and known_contact replies
    for i in range(n):
        is_newsletter = (i % 2 == 0)
        
        if is_newsletter:
            sit = Situation(
                msg_id=f"msg_n_{i}", sender_class="newsletter", intent="newsletter",
                sensitivity="none", urgency="normal", requested_actions=[],
                deadline=None, thread_participants=[], summary="news", llm_confidence=1.0
            )
            prop = ProposedAction(
                type="archive", params={}, provenance={}, rationale="cleanup", confidence=1.0
            )
        else:
            sit = Situation(
                msg_id=f"msg_r_{i}", sender_class="known_contact", intent="request_for_action",
                sensitivity="none", urgency="normal", requested_actions=[],
                deadline=None, thread_participants=["maya@acme.io"], summary="request", llm_confidence=1.0
            )
            prop = ProposedAction(
                type="send_reply_known", params={"body": "ok"}, provenance={}, rationale="reply", confidence=1.0
            )
            
        ds.append({
            "situation": sit.model_dump(),
            "proposals": [prop.model_dump()]
        })
    return ds

def run_ablation(name, persona_name, dataset, disable_guard=False, poison_trust=False):
    persona = get_persona(persona_name)
    
    with open("config/actions.yaml", "r") as f:
        registry = yaml.safe_load(f)
    with open("config/guard.yaml", "r") as f:
        guard_cfg = yaml.safe_load(f)
    with open("config/policy.yaml", "r") as f:
        policy_cfg = yaml.safe_load(f)

    def decider_fn(sit: Situation, actions: list[ProposedAction], policy: dict, rules: "RulesEngine") -> list[Decision]:
        if poison_trust:
            # Inject a poisoned policy dict
            policy["send_reply_known_known_contact_request_for_action"] = {"n": 10000, "lcb": 1.0, "alpha": 10000, "beta": 1.0}
            policy["archive_newsletter_newsletter"] = {"n": 10000, "lcb": 1.0, "alpha": 10000, "beta": 1.0}
            
        decs = []
        inj = InjectionSignals(heuristic_hits=[], llm_judgement="none", score=0.0, suspicious_spans=[])
        from src.agent.models import EmailMessage, SimClock
        dummy_email = EmailMessage(
            id=sit.msg_id, thread_id="t1", from_addr="x@x.com", to=["y@y.com"], cc=[], 
            subject="mock", body_text="mock", body_html=None, headers={}, 
            attachments=[], received_at=datetime.now(timezone.utc)
        )
        clock = SimClock(dummy_email.received_at)
        for a in actions:
            dec = make_decision(sit, dummy_email, a, inj, registry, guard_cfg, clock=clock, learned_policy=policy, rules=rules, policy_cfg=policy_cfg)
            if disable_guard:
                # Force level to policy_level
                dec.level = dec.policy_level
            decs.append(dec)
        return decs

    history, policy = simulate_episode(persona, dataset, decider_fn)
    
    # Calculate rolling ask rate
    rolling_ask_rate = []
    window = 10
    asks = 0
    for i, h in enumerate(history):
        if h["level"] in {"ASK", "ESCALATE"}:
            asks += 1
        if i >= window:
            if history[i-window]["level"] in {"ASK", "ESCALATE"}:
                asks -= 1
            rolling_ask_rate.append(asks / window)
        else:
            rolling_ask_rate.append(asks / (i + 1))
            
    # Calculate accuracy vs gold (assuming gold is AUTO/AUTO_NOTIFY for this hands_off_founder)
    # For hands_off, they want AUTO for archive, AUTO_NOTIFY for known replies (bounded by floor).
    
    print(f"\n--- {name} Policy ---")
    for k, v in policy.items():
        print(f"{k}: n={v.get('n')}, lcb={v.get('lcb', 0):.3f}")
        
    return {
        "ablation": name,
        "history": history,
        "rolling_ask_rate": rolling_ask_rate
    }

def main():
    ds = generate_mock_learning_dataset(60)
    
    results = {}
    
    # Baseline
    res = run_ablation("baseline", "hands_off_founder", ds)
    results["baseline"] = res
    
    # Ablation 2: No learning
    # Ablation 3: No guard clamp
    res_no_guard = run_ablation("no_guard", "hands_off_founder", ds, disable_guard=True)
    results["no_guard"] = res_no_guard
    
    # Ablation 4: Poisoned trust
    res_poison = run_ablation("poisoned_trust", "hands_off_founder", ds, poison_trust=True)
    results["poisoned_trust"] = res_poison
    
    import os
    os.makedirs("eval/results", exist_ok=True)
    with open("eval/results/metrics.json", "w") as f:
        json.dump(results, f, indent=2)
        
    report = ["# Evaluation Report\n"]
    for name, res in results.items():
        report.append(f"## {name}")
        ask_rates = [f"{rate:.2f}" for rate in res["rolling_ask_rate"]]
        report.append(f"**Rolling Ask Rate:** {', '.join(ask_rates)}\n")
        
    with open("REPORT.md", "w") as f:
        f.write("\n".join(report))

if __name__ == "__main__":
    main()
