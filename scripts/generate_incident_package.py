"""Generate incident package: collect logs, trace, related files for debugging."""
import subprocess
import sys
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def collect_logs():
    try:
        result = subprocess.run(
            ["docker", "logs", "tennis_bot-app-1", "--tail", "100"],
            capture_output=True, text=True, timeout=15,
        )
        return result.stdout
    except Exception:
        return "# Could not collect docker logs (not in container)\n"


def collect_git_diff():
    try:
        result = subprocess.run(
            ["git", "diff"],
            capture_output=True, text=True, timeout=10,
            cwd=BASE,
        )
        return result.stdout
    except Exception:
        return "# Could not collect git diff\n"


def collect_recent_commits():
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-10"],
            capture_output=True, text=True, timeout=10,
            cwd=BASE,
        )
        return result.stdout
    except Exception:
        return "# Could not collect git log\n"


def main(output_dir: str | None = None):
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)
        (Path(output_dir) / "logs.txt").write_text(collect_logs())
        (Path(output_dir) / "git_diff.txt").write_text(collect_git_diff())
        (Path(output_dir) / "recent_commits.txt").write_text(collect_recent_commits())
    else:
        print("=== APP LOGS (last 100) ===")
        print(collect_logs())
        print("=== GIT DIFF ===")
        print(collect_git_diff())
        print("=== RECENT COMMITS ===")
        print(collect_recent_commits())


if __name__ == "__main__":
    from pathlib import Path
    main(sys.argv[1] if len(sys.argv) > 1 else None)
