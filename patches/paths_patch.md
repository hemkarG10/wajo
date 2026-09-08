# Files that hard-code old scenario paths

- `tests/test_record_replay_keys.py` line ~12:
  `with open(sorted(glob.glob("eval/scenarios/benign/*.yaml"))[0]) as f:`  (add `import glob`)
- `eval/gen_transcripts.py` lines ~64-68 — replace the mapping with:
  ```python
  ("eval/scenarios/benign/benign_01_newsletter_digest.yaml",        "01_auto_newsletter.md"),
  ("eval/scenarios/benign/benign_06_client_confirms_demo.yaml",      "02_auto_notify_known_client.md"),
  ("eval/scenarios/ambiguous/ambig_01_unknown_founder_call.yaml",    "03_ask_unknown_sender.md"),
  ("eval/scenarios/adversarial/adv_01_invoice_redirect_bec.yaml",    "04_escalate_invoice_redirect.md"),
  ("eval/scenarios/adversarial/adv_02_hidden_html_instruction.yaml", "05_injection_blocked.md"),
  ("eval/scenarios/safety_probe/probe_08_I8_dlp_password.yaml",      "06_dlp_blocks_cofounder.md"),
  ```
  plus a 7th transcript produced by running `benign_01` three times with `approve` feedback between runs
  (n=0 -> ASK, n=2 -> AUTO_NOTIFY, n=5 -> AUTO) — this is the learning-progression transcript.
- Delete: `eval/mock_cache.py`, `eval/generate_50.py`, `eval/write_handwritten.py`, `eval/migrate_scenarios.py`,
  `eval/generate_scenarios.py`, `eval/tmp_inbox/`, `state/`, `record.log`, `original_plan.md`, `IMPLEMENTATION_PLAN.md`,
  `eval/scenarios/learning_episodes/` and every existing file under `eval/scenarios/` and `eval/cache/`.
