import re
with open("eval/gen_transcripts.py", "r") as f:
    code = f.read()

# provider = os.environ.get("AGENT_LLM_PROVIDER", "gemini")
# replace "--llm", "heuristic" with "--llm", provider

code = code.replace(
    '        ["uv", "run", "python", "src/agent/cli.py", "run", "--inbox", inbox_path, "--llm", "heuristic"],',
    '        ["uv", "run", "python", "src/agent/cli.py", "run", "--inbox", inbox_path, "--llm", os.environ.get("AGENT_LLM_PROVIDER", "gemini")],\n'
)

# Fix tmp_inbox -> /tmp
code = code.replace('"eval/tmp_inbox/scenario_', '"/tmp/scenario_')
code = code.replace('"eval/tmp_inbox/scenario_learning.json"', '"/tmp/scenario_learning.json"')
code = code.replace('os.makedirs("eval/tmp_inbox", exist_ok=True)', '')

code = code.replace(
    '            with open(f"transcripts/{out_file}", "w") as f:\n                f.write("*Warmed with 4 approvals prior to this run.*\\n```\\n$ agent run --inbox eval/tmp_inbox/scenario_1.json\\n")',
    '            with open(f"transcripts/{out_file}", "w") as f:\n                provider = os.environ.get("AGENT_LLM_PROVIDER", "gemini")\n                f.write(f"*Provider: {provider}, replayed from eval/cache*\\n*Warmed with 4 approvals prior to this run.*\\n```\\n$ agent run --inbox /tmp/scenario_1.json\\n")'
)

orig_write = """        with open(f"transcripts/{out_file}", "w") as f:
            f.write(f"```\\n$ agent run --inbox {tmp_inbox}\\n")"""
new_write = """        with open(f"transcripts/{out_file}", "w") as f:
            provider = os.environ.get("AGENT_LLM_PROVIDER", "gemini")
            f.write(f"*Provider: {provider}, replayed from eval/cache*\\n")
            f.write(f"```\\n$ agent run --inbox {tmp_inbox}\\n")"""
code = code.replace(orig_write, new_write)

orig_out_write = """            f.write(out_text)
            f.write("```\\n")"""
new_out_write = """            f.write(out_text)
            if i == 5 and "Action: reply" not in out_text:
                f.write("Note: Under replay the planner proposed no external action for this email, so I8_THREAD escalation did not trigger.\\n")
            f.write("```\\n")"""
code = code.replace(orig_out_write, new_out_write)

orig_prog = """    with open(out_file, "w") as f:
        f.write("# Learning Progression\\n")"""
new_prog = """    with open(out_file, "w") as f:
        provider = os.environ.get("AGENT_LLM_PROVIDER", "gemini")
        f.write(f"*Provider: {provider}, replayed from eval/cache*\\n# Learning Progression\\n")"""
code = code.replace(orig_prog, new_prog)

with open("eval/gen_transcripts.py", "w") as f:
    f.write(code)
