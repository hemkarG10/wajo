```
$ agent feedback --decision-id dec-archive-b2 --kind stop_asking

STDERR:
╭───────────────────── Traceback (most recent call last) ──────────────────────╮
│ /Users/hemkar/Documents/wajo/src/agent/cli.py:110 in feedback                │
│                                                                              │
│   107 │   try:                                                               │
│   108 │   │   with open(f"state/decisions/{decision_id}.json", "r") as f:    │
│   109 │   │   │   d_dict = json.load(f)                                      │
│ ❱ 110 │   │   │   decision = Decision.model_validate(d_dict)                 │
│   111 │   except FileNotFoundError:                                          │
│   112 │   │   console.print(f"[bold red]Decision {decision_id} not found in  │
│       state/decisions/[/bold red]")                                          │
│   113 │   │   raise typer.Exit(1)                                            │
╰──────────────────────────────────────────────────────────────────────────────╯
NameError: name 'Decision' is not defined
```
