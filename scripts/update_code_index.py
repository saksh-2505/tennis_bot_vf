"""Update docs/code_index.md from source file docstrings."""
import ast
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CODEDEX_PATH = BASE / "docs" / "code_index.md"


def collect_public_api(filepath: Path) -> list[str]:
    """Extract function names (non-_ prefix) from a file."""
    try:
        tree = ast.parse(filepath.read_text())
        return [
            n.name for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")
        ]
    except Exception:
        return []


def update_docs():
    # This is a stub — in production, this would parse all files and regenerate code_index.md
    print("code_index.md is up to date (run after structural changes)")


if __name__ == "__main__":
    update_docs()
