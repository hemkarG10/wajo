import re
with open("eval/gen_transcripts.py", "r") as f:
    code = f.read()

orig = """        dec_id = get_latest_decision()
        run_cli_feedback(dec_id, "approve")"""

new = """        for p in Path("state/decisions").glob("*.json"):
            run_cli_feedback(p.stem, "approve")
            p.unlink()"""
code = code.replace(orig, new)

orig2 = """                dec = get_latest_decision()
                run_cli_feedback(dec, "approve")"""
new2 = """                for p in Path("state/decisions").glob("*.json"):
                    run_cli_feedback(p.stem, "approve")
                    p.unlink()"""
code = code.replace(orig2, new2)

with open("eval/gen_transcripts.py", "w") as f:
    f.write(code)
