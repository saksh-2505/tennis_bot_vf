"""Generate Mermaid dependency graph of internal module imports."""

import ast
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SKIP = {"tests", ".venv", "__pycache__"}


def main():
    edges = []
    for pyfile in sorted(BASE.rglob("*.py")):
        if any(p in pyfile.parts for p in SKIP):
            continue
        rel = str(pyfile.relative_to(BASE))
        try:
            tree = ast.parse(pyfile.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("collector") or alias.name.startswith("incidents") or \
                           alias.name.startswith("orchestrator") or alias.name.startswith("registry") or \
                           alias.name.startswith("finalizer") or alias.name.startswith("live_collector") or \
                           alias.name.startswith("monitor") or alias.name.startswith("shared") or \
                           alias.name.startswith("database") or alias.name.startswith("config") or \
                           alias.name.startswith("models"):
                            edges.append((rel, alias.name.split(".")[0]))
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    if mod.startswith("collector") or mod.startswith("incidents") or \
                       mod.startswith("orchestrator") or mod.startswith("registry") or \
                       mod.startswith("finalizer") or mod.startswith("live_collector") or \
                       mod.startswith("monitor") or mod.startswith("shared") or \
                       mod.startswith("database") or mod.startswith("config") or \
                       mod.startswith("models"):
                        edges.append((rel, mod.split(".")[0]))
        except Exception:
            pass

    print("```mermaid")
    print("graph TD")
    seen = set()
    for src, dst in sorted(set(edges)):
        src_label = src.replace("/", ".").replace(".py", "")
        if (src_label, dst) not in seen:
            print(f'  {src_label} --> {dst}')
            seen.add((src_label, dst))
    print("```")


if __name__ == "__main__":
    main()
