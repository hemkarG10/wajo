import re
with open("eval/report.py", "r") as f:
    code = f.read()

code = code.replace(
    'poisoned = metrics.get("poisoned_trust", {})',
    'poisoned = metrics.get("poisoned_trust", {})\n    no_guard_poisoned = metrics.get("no_guard_poisoned", {})'
)

code = code.replace(
    '| Poisoned | {provider} | {poisoned.get(\'warm\', {}).get(\'safety_violations\', "not computed")} | {poisoned.get(\'warm\', {}).get(\'injection_asr\', "not computed")} | {poisoned.get(\'warm\', {}).get(\'false_autonomy_rate\', "not computed")} | {poisoned.get(\'warm\', {}).get(\'regret\', "not computed")} |',
    '| Poisoned | {provider} | {poisoned.get(\'warm\', {}).get(\'safety_violations\', "not computed")} | {poisoned.get(\'warm\', {}).get(\'injection_asr\', "not computed")} | {poisoned.get(\'warm\', {}).get(\'false_autonomy_rate\', "not computed")} | {poisoned.get(\'warm\', {}).get(\'regret\', "not computed")} |\n| No Guard + Poisoned | {provider} | {no_guard_poisoned.get(\'warm\', {}).get(\'safety_violations\', "not computed")} | {no_guard_poisoned.get(\'warm\', {}).get(\'injection_asr\', "not computed")} | {no_guard_poisoned.get(\'warm\', {}).get(\'false_autonomy_rate\', "not computed")} | {no_guard_poisoned.get(\'warm\', {}).get(\'regret\', "not computed")} |'
)

with open("eval/report.py", "w") as f:
    f.write(code)
