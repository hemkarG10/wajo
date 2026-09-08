"""Guards against relabelled or hand-written cache entries (see history: eval/mock_cache.py)."""
import glob, json, pytest

@pytest.mark.parametrize("path", sorted(glob.glob("eval/cache/*.json")))
def test_cache_entry_is_a_real_recorded_call(path):
    d = json.load(open(path))
    assert d["mode"] == "record", "cache entries may only be written by eval/record.py"
    assert d["provider"] != "heuristic"
    assert d["input_tokens"] > 0 and d["output_tokens"] > 0, "real provider calls report token usage"
    assert d["latency_ms"] > 0

def test_no_cache_writer_outside_llm_adapter():
    import pathlib, re
    offenders = [p for p in pathlib.Path(".").rglob("*.py")
                 if ".venv" not in p.parts and p.name != "llm.py" and re.search(r"_write_cache\(", p.read_text())]
    assert not offenders, f"only LlmAdapter may write cache files: {offenders}"
