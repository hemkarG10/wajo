*Provider: gemini, replayed from eval/cache*
# Learning Progression

## Run 1 (Level: ASK)
```
$ agent run --inbox /tmp/scenario_learning.json

Processing Email: Devtools Weekly #218: type checkers, a new build cache, and 3 
launches (From: digest@devtoolsweekly.email)
╭─────────────── Decision & Outcome ───────────────╮
│ ID: dec-archive-benign_01_newsletter_digest      │
│ Action: archive                                  │
│ Level: ASK (Policy: ASK, Floor: AUTO)            │
│ Outcome: queued_ask - Drafted archive for review │
╰──────────────────────────────────────────────────╯
╭────────────── Decision & Outcome ──────────────╮
│ ID: dec-label-benign_01_newsletter_digest      │
│ Action: label                                  │
│ Level: ASK (Policy: ASK, Floor: AUTO)          │
│ Outcome: queued_ask - Drafted label for review │
╰────────────────────────────────────────────────╯
Saved policy to state/policy.json

```

*(runs 2–4: approved, level unchanged)*

## Run 5 (Level: AUTO_NOTIFY)
```
$ agent run --inbox /tmp/scenario_learning.json

Processing Email: Devtools Weekly #218: type checkers, a new build cache, and 3 
launches (From: digest@devtoolsweekly.email)
╭───────────────── Decision & Outcome ──────────────────╮
│ ID: dec-archive-benign_01_newsletter_digest           │
│ Action: archive                                       │
│ Level: AUTO_NOTIFY (Policy: AUTO_NOTIFY, Floor: AUTO) │
│ Outcome: dry_run - Would execute archive              │
╰───────────────────────────────────────────────────────╯
╭───────────────── Decision & Outcome ──────────────────╮
│ ID: dec-label-benign_01_newsletter_digest             │
│ Action: label                                         │
│ Level: AUTO_NOTIFY (Policy: AUTO_NOTIFY, Floor: AUTO) │
│ Outcome: dry_run - Would execute label                │
╰───────────────────────────────────────────────────────╯
Saved policy to state/policy.json

```

*(runs 6–9: approved, level unchanged)*

## Run 10 (Level: AUTO)
```
$ agent run --inbox /tmp/scenario_learning.json

Processing Email: Devtools Weekly #218: type checkers, a new build cache, and 3 
launches (From: digest@devtoolsweekly.email)
╭──────────── Decision & Outcome ─────────────╮
│ ID: dec-archive-benign_01_newsletter_digest │
│ Action: archive                             │
│ Level: AUTO (Policy: AUTO, Floor: AUTO)     │
│ Outcome: dry_run - Would execute archive    │
╰─────────────────────────────────────────────╯
╭─────────── Decision & Outcome ────────────╮
│ ID: dec-label-benign_01_newsletter_digest │
│ Action: label                             │
│ Level: AUTO (Policy: AUTO, Floor: AUTO)   │
│ Outcome: dry_run - Would execute label    │
╰───────────────────────────────────────────╯
Saved policy to state/policy.json

```
