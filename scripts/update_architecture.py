"""Auto-update architecture.md with current file stats and structure."""
import subprocess
from datetime import datetime, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ARCH_PATH = BASE / "architecture.md"


def get_python_file_stats() -> dict[str, int]:
    files: dict[str, int] = {}
    for pyfile in sorted(BASE.rglob("*.py")):
        if ".venv" in pyfile.parts or "tests" in pyfile.parts:
            continue
        rel = str(pyfile.relative_to(BASE))
        lines = len(pyfile.read_text().splitlines())
        files[rel] = lines
    return files


def get_folder_stats(files: dict[str, int]) -> dict[str, dict]:
    folders: dict[str, dict] = {}
    for path, lines in files.items():
        parts = path.split("/")
        folder = parts[0] if len(parts) >= 2 else "root"
        if folder not in folders:
            folders[folder] = {"files": 0, "lines": 0}
        folders[folder]["files"] += 1
        folders[folder]["lines"] += lines
    return folders


def update_architecture():
    files = get_python_file_stats()
    folders = get_folder_stats(files)
    total_files = len(files)
    total_lines = sum(files.values())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    arch_text = ARCH_PATH.read_text()

    # Build summary block
    lines = []
    lines.append(f"**Auto-generated file stats:** {total_files} Python files, {total_lines:,} lines (excl. tests/). Updated {now}.\n")
    for folder in sorted(folders, key=lambda f: -folders[f]["lines"]):
        info = folders[folder]
        lines.append(f"- **{folder}/**: {info['files']} files, {info['lines']:,} lines")
    summary = "\n".join(lines)

    # Replace the "Current Status:" line with updated version
    old_marker = "**Current Status:**"
    idx = arch_text.find(old_marker)
    if idx < 0:
        print("Could not find Current Status marker")
        return

    # Find the "---\n\n## " that ends the status block
    next_marker = "---\n\n## "
    end_idx = arch_text.find(next_marker, idx)
    if end_idx < 0:
        print("Could not find section end marker")
        return

    replacement = (
        "**Current Status:** "
        f"{total_files} Python files, {total_lines:,} lines (excl. tests/). "
        f"Updated {now}.\n\n"
        f"{summary}\n"
    )

    new_text = arch_text[:idx] + replacement + arch_text[end_idx:]
    ARCH_PATH.write_text(new_text)
    print(f"Updated {ARCH_PATH.name}")


if __name__ == "__main__":
    update_architecture()
