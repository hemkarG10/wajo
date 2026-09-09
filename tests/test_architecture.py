import ast
from pathlib import Path


def test_guard_imports():
    """
    Dependency rule: guard.py may import models, actions, yaml/stdlib only.
    Nothing under learn/ is importable from guard.py.
    """
    guard_path = Path("src/agent/guard.py")
    assert guard_path.exists(), "src/agent/guard.py must exist"

    with open(guard_path, "r", encoding="utf-8") as f:
        tree = ast.parse(f.read(), filename="guard.py")

    disallowed_imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("agent.learn") or "learn" in alias.name:
                    disallowed_imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module and (node.module.startswith("agent.learn") or "learn" in node.module):
                disallowed_imports.append(node.module)

    assert not disallowed_imports, f"guard.py has disallowed imports: {disallowed_imports}"

def test_no_disable_guard():
    src_dir = Path("src")
    violating_files = []
    for file in src_dir.rglob("*.py"):
        text = file.read_text()
        if "disable_guard" in text:
            violating_files.append(str(file))
    assert not violating_files, f"disable_guard found in {violating_files}"


def test_production_package_does_not_import_src_namespace():
    violating_files = []
    for file in Path("src/agent").rglob("*.py"):
        if "src.agent" in file.read_text():
            violating_files.append(str(file))
    assert not violating_files, f"installed package imports src namespace: {violating_files}"
