import json
import os

from fastapi import APIRouter

router = APIRouter()

_SCORE_HISTORY_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "verification", "reports", "archive", "score_history.jsonl",
)


@router.get("/verification/health-score-history")
def health_score_history():
    history = []
    try:
        path = os.path.normpath(_SCORE_HISTORY_PATH)
        if os.path.exists(path):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            history.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
    except Exception:
        pass

    return {"history": history}
