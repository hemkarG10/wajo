with open("eval/report.py", "r") as f:
    code = f.read()

def fmt(var):
    return f"{var}:.3f"

code = code.replace("{brier:.3f}", "{brier:.3f}" if "{brier}" not in code else "{brier}")
# Actually better to just do this:
code = code.replace("{brier:.3f}", "{brier if isinstance(brier, str) else f'{brier:.3f}'}")
code = code.replace("{brier_cold:.3f}", "{brier_cold if isinstance(brier_cold, str) else f'{brier_cold:.3f}'}")
code = code.replace("{ece:.3f}", "{ece if isinstance(ece, str) else f'{ece:.3f}'}")
code = code.replace("{ece_cold:.3f}", "{ece_cold if isinstance(ece_cold, str) else f'{ece_cold:.3f}'}")
code = code.replace("{tokens:.1f}", "{tokens if isinstance(tokens, str) else f'{tokens:.1f}'}")
code = code.replace("{calls:.1f}", "{calls if isinstance(calls, str) else f'{calls:.1f}'}")
code = code.replace("{latency:.1f}", "{latency if isinstance(latency, str) else f'{latency:.1f}'}")

with open("eval/report.py", "w") as f:
    f.write(code)
