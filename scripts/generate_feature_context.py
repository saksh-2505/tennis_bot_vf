"""Generate feature context: collect relevant files for a feature."""
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FEATURE_MAP = {
    "collector.flashscore": [
        "collector/flashscore/__init__.py", "collector/flashscore/client.py",
        "collector/flashscore/parser.py", "models/flashscore.py",
        "tests/test_flashscore_collector.py",
    ],
    "collector.betting_site": [
        "collector/betting_site/__init__.py", "collector/betting_site/client.py",
        "collector/betting_site/parser.py", "models/bettingsite.py",
        "tests/test_bettingsite_collector.py",
    ],
    "live_collector": [
        "live_collector/service.py", "live_collector/flashscore_live.py",
        "live_collector/betting_live.py",
        "tests/test_live_collector.py",
    ],
    "finalizer": [
        "finalizer/service.py", "finalizer/stats.py", "finalizer/validation.py",
        "models/completed_match.py",
        "tests/test_match_finalizer.py",
    ],
    "incidents": [
        "incidents/monitor.py", "incidents/service.py", "incidents/models.py",
        "incidents/config.py", "incidents/recovery.py",
        "incidents/notifier.py", "incidents/package_generator.py",
        "tests/test_incident_manager.py",
    ],
    "orchestrator": [
        "orchestrator/service.py", "tests/test_orchestrator.py",
    ],
    "registry": [
        "registry/service.py", "models/tracked_match.py",
        "tests/test_match_registry.py",
    ],
}


def main(feature: str):
    files = FEATURE_MAP.get(feature, [])
    if not files:
        print(f"Unknown feature: {feature}")
        print(f"Available: {', '.join(FEATURE_MAP.keys())}")
        sys.exit(1)

    for f in files:
        path = os.path.join(BASE, f)
        if os.path.exists(path):
            print(f)
        else:
            print(f"# MISSING: {f}", file=sys.stderr)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/generate_feature_context.py <feature>")
        print(f"Features: {', '.join(FEATURE_MAP.keys())}")
        sys.exit(1)
    main(sys.argv[1])
