# Learning Progression

## Run 1
```
$ agent run --inbox eval/tmp_inbox/scenario_learning.json

Processing Email: Devtools Weekly #218: type checkers, a new build cache, and 3 
launches (From: digest@devtoolsweekly.email)
╭─────────────── Decision & Outcome ───────────────╮
│ ID: dec-archive-benign_01_newsletter_digest      │
│ Action: archive                                  │
│ Level: ASK (Policy: ASK, Floor: AUTO)            │
│ Outcome: queued_ask - Drafted archive for review │
╰──────────────────────────────────────────────────╯
Saved policy to state/policy.json

```

## Feedback 1
```
$ agent feedback --decision-id dec-archive-benign_01_newsletter_digest --kind approve
Applied feedback approve to decision dec-archive-benign_01_newsletter_digest

```

## Run 2
```
$ agent run --inbox eval/tmp_inbox/scenario_learning.json

Processing Email: Devtools Weekly #218: type checkers, a new build cache, and 3 
launches (From: digest@devtoolsweekly.email)
╭─────────────── Decision & Outcome ───────────────╮
│ ID: dec-archive-benign_01_newsletter_digest      │
│ Action: archive                                  │
│ Level: ASK (Policy: ASK, Floor: AUTO)            │
│ Outcome: queued_ask - Drafted archive for review │
╰──────────────────────────────────────────────────╯
Saved policy to state/policy.json

```

## Feedback 2
```
$ agent feedback --decision-id dec-archive-benign_01_newsletter_digest --kind approve
Applied feedback approve to decision dec-archive-benign_01_newsletter_digest

```

## Run 3
```
$ agent run --inbox eval/tmp_inbox/scenario_learning.json

Processing Email: Devtools Weekly #218: type checkers, a new build cache, and 3 
launches (From: digest@devtoolsweekly.email)
╭─────────────── Decision & Outcome ───────────────╮
│ ID: dec-archive-benign_01_newsletter_digest      │
│ Action: archive                                  │
│ Level: ASK (Policy: ASK, Floor: AUTO)            │
│ Outcome: queued_ask - Drafted archive for review │
╰──────────────────────────────────────────────────╯
Saved policy to state/policy.json

```

## Feedback 3
```
$ agent feedback --decision-id dec-archive-benign_01_newsletter_digest --kind approve
Applied feedback approve to decision dec-archive-benign_01_newsletter_digest

```
