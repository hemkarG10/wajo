"""Every cache entry must come from a real provider call in record mode with real token counts. Exit 1 otherwise."""
import collections
import glob
import json
import sys

bad, models = [], collections.Counter()
for f in glob.glob("eval/cache/*.json"):
    d = json.load(open(f))
    models[(d.get("provider"), d.get("model"))] += 1
    if d.get("mode") != "record": bad.append((f, "mode != record"))
    if d.get("provider") == "heuristic": bad.append((f, "heuristic provider"))
    if not d.get("input_tokens") or not d.get("output_tokens"): bad.append((f, "missing token counts"))
    if (d.get("latency_ms"), d.get("input_tokens"), d.get("output_tokens")) in {(850.0, 100, 20), (1250.0, 300, 80), (2500.0, 500, 150)}:
        bad.append((f, "fabricated signature"))
print("entries:", sum(models.values()), "by provider/model:", dict(models))
if len(models) != 1: bad.append(("cache", "more than one provider/model in cache"))
for f, why in bad: print("BAD", f, why)
sys.exit(1 if bad else 0)
