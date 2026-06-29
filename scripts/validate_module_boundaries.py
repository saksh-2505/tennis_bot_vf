"""Validate module boundaries: warn on forbidden cross-module imports."""
import ast
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent

# Forbidden imports: key=module, value=list of modules it must NOT import
FORBIDDEN = {
    "finalizer": ["incidents", "orchestrator", "live_collector", "registry", "collector"],
    "live_collector": ["incidents", "orchestrator", "finalizer", "registry"],
    "collector": ["incidents", "orchestrator", "finalizer", "live_collector", "registry"],
    "registry": ["incidents", "orchestrator", "finalizer", "live_collector"],
    "orchestrator": ["incidents"],
    "incidents": ["orchestrator", "finalizer", "live_collector", "registry", "collector"],
}

SKIP = {"tests", ".venv", "__pycache__"}


def main():
    errors = []
    for pyfile in sorted(BASE.rglob("*.py")):
        if any(p in pyfile.parts for p in SKIP):
            continue
        rel = str(pyfile.relative_to(BASE))
        module_name = rel.split("/")[0]
        if module_name not in FORBIDDEN:
            continue
        try:
            tree = ast.parse(pyfile.read_text())
            for node in ast.walk(tree):
                mod = None
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        mod = alias.name.split(".")[0]
                elif isinstance(node, ast.ImportFrom):
                    mod = (node.module or "").split(".")[0]
                if mod and mod in FORBIDDEN.get(module_name, []):
                    errors.append(f"  {rel} imports forbidden module: {mod}")
        except Exception as e:
            errors.append(f"  {rel}: {e}")

    if errors:
        print("Module boundary violations:")
        for e in errors:
            print(e)
    else:
        print("All module boundaries valid.")


if __name__ == "__main__":
    main()
