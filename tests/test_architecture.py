import ast
from pathlib import Path


def test_guard_does_not_import_learn():
    """
    Ensure src/agent/guard.py does not import anything from src/agent/learn/.
    This enforces the strict separation where Guard is a pure floor uninfluenced by learning.
    """
    guard_path = Path(__file__).parent.parent / "src" / "agent" / "guard.py"
    assert guard_path.exists(), "guard.py not found"
    
    with open(guard_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename=str(guard_path))
        
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "learn" not in alias.name, f"guard.py must not import {alias.name}"
                
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                assert "learn" not in node.module, f"guard.py must not import from {node.module}"
