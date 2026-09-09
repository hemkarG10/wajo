import ast
import builtins
import json
from pathlib import Path


def test_report_no_random():
    """Assert report.py contains no random numbers/placeholders."""
    report_path = Path("eval/report.py")
    assert report_path.exists()
    
    with open(report_path, "r", encoding="utf-8") as f:
        content = f.read()
        tree = ast.parse(content, filename="report.py")

    disallowed_calls = {"random", "randint", "uniform", "randn"}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                assert node.func.id not in disallowed_calls, f"Found {node.func.id}() in report.py"
            elif isinstance(node.func, ast.Attribute):
                assert node.func.attr not in disallowed_calls, f"Found {node.func.attr}() in report.py"

def test_report_exits_on_missing(tmp_path, monkeypatch):
    """Assert report.py exits 1 if a metric is absent."""
    metrics_path = tmp_path / "metrics.json"
    
    # Missing 'brier'
    metrics_data = {
        "baseline": {
            "cold": {
                "ece": 0.1,
                "tokens_per_email": 0.0,
                "latency_per_email": 0.0,
                "injection_detection_rate": 0.0,
                "injection_fpr": 0.0,
            }
        }
    }
    
    metrics_path.write_text(json.dumps(metrics_data))
    
    orig_open = builtins.open
    def mock_open(path, mode="r", *args, **kwargs):
        if str(path) == "eval/results/metrics.json":
            return orig_open(metrics_path, mode, *args, **kwargs)
        elif str(path) == "eval/results/REPORT.md":
            return orig_open(tmp_path / "REPORT.md", mode, *args, **kwargs)
        return orig_open(path, mode, *args, **kwargs)
    
    monkeypatch.setattr("builtins.open", mock_open)
    monkeypatch.setattr("matplotlib.pyplot.savefig", lambda *args, **kwargs: None)
    
    from eval.report import generate_report
    
    try:
        generate_report()
        assert False, "Expected SystemExit(1) due to missing metric"
    except SystemExit as e:
        assert e.code == 1

