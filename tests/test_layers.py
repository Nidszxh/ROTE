import ast
from pathlib import Path


def test_no_evaluation_import_in_src_packages():
    src = Path("src")
    violations = []
    for pkg in src.iterdir():
        if not pkg.is_dir() or pkg.name == "evaluation":
            continue
        for py in pkg.rglob("*.py"):
            try:
                tree = ast.parse(py.read_text())
            except Exception:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for a in node.names:
                        if a.name.split(".")[0] == "evaluation":
                            violations.append(str(py))
                elif (
                    isinstance(node, ast.ImportFrom)
                    and node.module
                    and node.module.split(".")[0] == "evaluation"
                ):
                    violations.append(str(py))
    assert not violations, f"evaluation imported in non-eval packages: {violations}"
