"""Generate deterministic example transcripts from the replay evaluation cache."""

import copy
import os
from datetime import UTC, datetime
from pathlib import Path

import yaml

from agent.learn.feedback import process_feedback
from agent.learn.rules import RulesEngine
from agent.llm import LlmAdapter
from agent.models import EmailMessage, Feedback, SimClock
from agent.pipeline import process_email
from eval.context import scenario_ctx

FIXED_EPOCH = datetime(2026, 9, 1, tzinfo=UTC)


def _load_case(path: str) -> dict:
    with open(path) as handle:
        return yaml.safe_load(handle)


def _email_from_case(case: dict) -> EmailMessage:
    raw = copy.deepcopy(case["email"] if "email" in case else case["incoming"][0])
    if "from" in raw:
        raw["from_addr"] = raw.pop("from")
    if "body" in raw:
        raw["body_text"] = raw.pop("body")
    raw.setdefault("id", f"{case['id']}_msg")
    raw.setdefault("thread_id", f"{case['id']}_thread")
    raw.setdefault("cc", [])
    raw.setdefault("body_html", None)
    raw.setdefault("headers", {})
    raw.setdefault("attachments", [])
    raw.setdefault("received_at", FIXED_EPOCH)
    return EmailMessage(**raw)


def _load_config() -> dict:
    with open("config/actions.yaml") as handle:
        registry = yaml.safe_load(handle)
    with open("config/guard.yaml") as handle:
        guard_cfg = yaml.safe_load(handle)
    with open("config/policy.yaml") as handle:
        policy_cfg = yaml.safe_load(handle)
    return {
        "registry": registry,
        "guard_cfg": guard_cfg,
        "policy_cfg": policy_cfg,
    }


def _run_case(case: dict, policy: dict, llm: LlmAdapter, cfg: dict):
    ctx = scenario_ctx(case)
    ctx["dry_run"] = False
    return process_email(
        _email_from_case(case),
        ctx,
        llm,
        policy,
        SimClock(FIXED_EPOCH),
        cfg,
    )


def _format_run(case: dict, decisions, outcomes) -> str:
    lines = [f"Scenario: {case['id']}"]
    for decision, outcome in zip(decisions, outcomes):
        reasons = ", ".join(decision.floor_reasons) or "none"
        lines.extend(
            [
                f"Decision: {decision.id}",
                f"Action: {decision.action.type}",
                (
                    f"Level: {decision.level.name} "
                    f"(Policy: {decision.policy_level.name}, Floor: {decision.floor.name})"
                ),
                f"Floor reasons: {reasons}",
                f"Policy bucket: {decision.policy_reason.get('bucket', 'none')}",
                (
                    "Outcome: executed"
                    if outcome.executed
                    else f"Outcome: held ({outcome.blocked_reason})"
                ),
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def _approve(decisions, policy: dict, policy_cfg: dict):
    rules = RulesEngine(policy.get("_rules", []))
    for decision in decisions:
        process_feedback(
            Feedback(decision_id=decision.id, kind="approve", at=decision.created_at),
            decision,
            policy,
            rules,
            decision.created_at,
            policy_cfg,
        )


def _write_transcript(path: Path, provider: str, note: str, body: str):
    path.write_text(
        f"*Provider: {provider}; deterministic replay from `eval/cache/`.*\n"
        f"*{note}*\n\n"
        f"```text\n{body}\n```\n"
    )


def main():
    output_dir = Path("transcripts")
    output_dir.mkdir(exist_ok=True)
    for old_file in output_dir.glob("*.md"):
        old_file.unlink()

    provider = os.environ.get("AGENT_LLM_PROVIDER", "gemini")
    llm = LlmAdapter(mode="replay", provider=provider)
    cfg = _load_config()

    examples = [
        (
            "eval/scenarios/benign/benign_01_newsletter_digest.yaml",
            "01_ask_newsletter.md",
            "Cold start: no approval history.",
        ),
        (
            "eval/scenarios/ambiguous/ambig_01_unknown_founder_call.yaml",
            "03_ask_unknown_sender.md",
            "Ambiguous request from an unknown sender.",
        ),
        (
            "eval/scenarios/adversarial/adv_01_invoice_redirect_bec.yaml",
            "04_escalate_invoice_redirect.md",
            "Adversarial money and recipient-redirection request.",
        ),
        (
            "eval/scenarios/adversarial/adv_02_hidden_html_instruction.yaml",
            "05_injection_blocked.md",
            "Hidden-HTML prompt-injection attempt.",
        ),
        (
            "eval/scenarios/safety_probe/probe_08_I8_dlp_password.yaml",
            "06_dlp_blocks_cofounder.md",
            "Credential DLP probe.",
        ),
    ]
    for case_path, filename, note in examples:
        case = _load_case(case_path)
        decisions, outcomes = _run_case(case, {}, llm, cfg)
        _write_transcript(
            output_dir / filename,
            provider,
            note,
            _format_run(case, decisions, outcomes),
        )

    client_case = _load_case(
        "eval/scenarios/benign/benign_06_client_confirms_demo.yaml"
    )
    client_policy: dict = {}
    for _ in range(4):
        decisions, _ = _run_case(client_case, client_policy, llm, cfg)
        _approve(decisions, client_policy, cfg["policy_cfg"])
    decisions, outcomes = _run_case(client_case, client_policy, llm, cfg)
    _write_transcript(
        output_dir / "02_auto_notify_known_client.md",
        provider,
        "Warmed with four approvals before this run.",
        _format_run(client_case, decisions, outcomes),
    )

    learning_case = _load_case(
        "eval/scenarios/benign/benign_01_newsletter_digest.yaml"
    )
    learning_policy: dict = {}
    runs = []
    for run_number in range(1, 13):
        decisions, outcomes = _run_case(learning_case, learning_policy, llm, cfg)
        runs.append((run_number, decisions, outcomes))
        if any(decision.level.name == "AUTO" for decision in decisions):
            break
        _approve(decisions, learning_policy, cfg["policy_cfg"])

    progression = []
    for run_number, decisions, outcomes in runs:
        levels = ", ".join(decision.level.name for decision in decisions)
        progression.append(
            f"Run {run_number} ({levels})\n{_format_run(learning_case, decisions, outcomes)}"
        )
    _write_transcript(
        output_dir / "07_learning_progression.md",
        provider,
        "Repeated approvals move a reversible newsletter action toward autonomy.",
        "\n\n".join(progression),
    )


if __name__ == "__main__":
    main()
