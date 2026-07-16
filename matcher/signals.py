"""Signal extraction for confidence-based market matching.

Each signal function takes a tracked match and a betting event candidate
and returns a score 0.0–1.0 and an explanation string.
"""
from __future__ import annotations

import logging
import re
import unicodedata
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_COMPOUND_LAST_NAMES = {
    "de minaur", "van de zandschulp", "van assche", "de jong",
    "van rijthoven", "di mino", "da silva", "del bonis",
    "de almeida", "de schepper", "de loore", "de bakker",
    "de graaf", "van der goes", "van lottum", "van de kerkhof",
    "de la torre", "di pasquale", "dos santos", "el aynaoui",
    "al ghareeb", "da costa", "dos reis", "del olmo",
    "de la fuente", "del castillo", "da silveira", "van duijvenbode",
    "van campenhout", "van beek", "van hoorn", "de vries",
    "van der plas", "van den heuvel", "de groot", "de wit",
    "de bruijn", "de vries", "van dijk", "van der meer",
    "van den berg", "de lange", "de boer", "de jager",
    "van der linden", "de ruiter", "van dam", "de vos",
    "de haan", "van der velde",
}

_SHORT_NAMES = {"wu", "ma", "li", "lu", "na", "xu", "yu", "bo", "he", "ji", "qi", "ye", "ko", "ho", "z", "n", "m", "p", "c", "k"}


def signal_player_names(
    fs_name_a: str,
    fs_name_b: str,
    bt_name_a: str,
    bt_name_b: str,
) -> tuple[float, str]:
    a1, r1 = _player_match_score(fs_name_a, bt_name_a)
    b1, r2 = _player_match_score(fs_name_b, bt_name_b)
    forward = a1 * b1

    a2, r3 = _player_match_score(fs_name_a, bt_name_b)
    b2, r4 = _player_match_score(fs_name_b, bt_name_a)
    swapped = a2 * b2

    if forward >= swapped:
        return forward, f"A:[{a1:.2f}]{r1} B:[{b1:.2f}]{r2}"
    return swapped, f"A↔B:[{a2:.2f}]{r3} B↔A:[{b2:.2f}]{r4}"


def _pair_score(
    fs_a: str, fs_b: str, bt_a: str, bt_b: str,
) -> tuple[float, str]:
    a_score, a_reason = _player_match_score(fs_a, bt_a)
    b_score, b_reason = _player_match_score(fs_b, bt_b)

    combined = a_score * b_score
    reason = f"A:{a_reason}[{a_score:.2f}] B:{b_reason}[{b_score:.2f}]"
    return combined, reason


def _normalize_name_for_match(name: str) -> str:
    n = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = n.replace(",", " ").replace(";", " ")
    n = " ".join(n.split())
    return n.lower()


def _player_match_score(fs_name: str, bt_name: str) -> tuple[float, str]:
    fs = _normalize_name_for_match(fs_name.strip())
    bt = _normalize_name_for_match(bt_name.strip())

    if fs == bt:
        return 1.0, "exact"

    if _is_reversed(fs, bt):
        return 1.0, "reversed"

    fs_parts = fs.split()
    bt_parts = bt.split()

    if len(fs_parts) <= 1 or len(bt_parts) <= 1:
        return 0.0, "single_word"

    fs_last = _extract_last(fs_parts)
    bt_last = _extract_last(bt_parts)

    if fs_last == bt_last:
        score = _first_name_score(
            _extract_first(fs_parts), _extract_first(bt_parts),
        )
        if score >= 0.8:
            return score, "last+first_match"
        return 0.7, "last_match_only"

    if fs_last in bt_last or bt_last in fs_last:
        first_match = (
            _extract_first(fs_parts) and _extract_first(bt_parts)
            and _first_name_score(
                _extract_first(fs_parts), _extract_first(bt_parts),
            ) >= 0.5
        )
        if first_match:
            return 0.6, "last_substring_with_first"
        return 0.5, "last_substring"

    initial_match = _check_initials(fs_parts, bt_parts) or _check_initials(
        bt_parts, fs_parts,
    )
    if initial_match:
        last_from_fs = _extract_last(fs_parts)
        last_from_bt = _extract_last(bt_parts)
        if len(last_from_fs) >= 5 and len(last_from_bt) >= 5 and last_from_fs[:5] == last_from_bt[:5]:
            return 0.4, "initial+last_prefix"
        first_from_fs = _extract_first(fs_parts)
        first_from_bt = _extract_first(bt_parts)
        if first_from_fs and first_from_bt and first_from_fs[0] == first_from_bt[0]:
            return 0.25, "initial+first_initial"
        if last_from_fs in last_from_bt or last_from_bt in last_from_fs:
            return 0.2, "initial+last_substring"
        return 0.15, "initial_only"

    fs_last_clean = _extract_last([p for p in fs_parts if p not in _SHORT_NAMES])
    bt_last_clean = _extract_last([p for p in bt_parts if p not in _SHORT_NAMES])
    if fs_last_clean and bt_last_clean and fs_last_clean in bt_last_clean:
        return 0.3, "last_skip_initials"

    all_fs_in_bt = all(p in bt_parts for p in fs_parts)
    if all_fs_in_bt:
        return 0.2, "all_fs_parts_in_bt"

    if fs_last[:5] == bt_last[:5] and len(fs_last) >= 5:
        first_match = (
            _extract_first(fs_parts) and _extract_first(bt_parts)
            and _first_name_score(
                _extract_first(fs_parts), _extract_first(bt_parts),
            ) >= 0.5
        )
        if first_match:
            return 0.25, "last_prefix_with_first"
        return 0.15, "last_prefix_weak"

    return 0.0, "no_match"


def _is_reversed(name1: str, name2: str) -> bool:
    p1 = name1.split()
    p2 = name2.split()
    if len(p1) < 2 or len(p2) < 2:
        return False
    if len(p1) == 2 and len(p2) == 2:
        return p1[0] == p2[1] and p1[1] == p2[0]
    if len(p1) == len(p2):
        return all(a == b for a, b in zip(p1, reversed(p2)))
    if len(p1) == 2 and len(p2) > 2:
        check1 = any(p1[0] == p for p in p2[1:]) and any(p1[1] == p for p in p2[:-1])
        check2 = all(p in p2 for p in p1)
        return check1 and check2
    if len(p2) == 2 and len(p1) > 2:
        check1 = any(p2[0] == p for p in p1[1:]) and any(p2[1] == p for p in p1[:-1])
        check2 = all(p in p1 for p in p2)
        return check1 and check2
    return False


def _first_name_score(fn1: str, fn2: str) -> float:
    if not fn1 or not fn2:
        return 0.5
    if fn1 == fn2:
        return 1.0
    if fn1[0] == fn2[0] and (len(fn1) <= 2 or len(fn2) <= 2):
        return 0.8
    return 0.3


def _extract_last(parts: list[str]) -> str:
    if len(parts) == 1:
        return parts[0]
    name = " ".join(parts)

    for compound in _COMPOUND_LAST_NAMES:
        if name.endswith(compound):
            return compound
        if name.startswith(compound) and len(parts) > len(compound.split()):
            return compound

    if len(parts[-1].rstrip(".")) <= 1:
        return parts[0] if len(parts) <= 2 else " ".join(parts[:-1])
    if len(parts) >= 3:
        return f"{parts[-2]} {parts[-1]}"
    return parts[-1]


def _extract_first(parts: list[str]) -> str:
    last = _extract_last(parts)
    last_parts = last.split()
    first_count = len(parts) - len(last_parts)
    if first_count <= 0:
        return ""
    return " ".join(parts[:first_count])


def _check_initials(fs_parts: list[str], bt_parts: list[str]) -> bool:
    if len(fs_parts) < 2 or len(bt_parts) < 2:
        return False
    if len(fs_parts[-1].rstrip(".")) <= 1:
        return True
    return False


def signal_tournament(fs_tournament: str, bt_event_name: str) -> tuple[float, str]:
    if not fs_tournament:
        return 0.5, "no_tournament"

    fs_lower = fs_tournament.lower()

    city = _extract_tournament_city(fs_lower)
    if city and city in bt_event_name.lower():
        return 1.0, f"city:{city}"

    words = fs_lower.replace(",", " ").replace(":", " ").split()
    matches = sum(1 for w in words if len(w) >= 4 and w in bt_event_name.lower())
    if matches >= 2:
        return 0.8, f"word_match:{matches}"
    if matches >= 1:
        return 0.6, f"single_word_match"

    return 0.3, "no_tournament_match"


def _extract_tournament_city(tournament: str) -> str | None:
    m = re.search(r":\s*([^(]+?)\s*(?:\(|$)", tournament)
    if m:
        city = m.group(1).strip().lower()
        return city
    m = re.search(r"-\s*SINGLES:\s*([^(]+?)\s*(?:\(|$)", tournament)
    if m:
        city = m.group(1).strip().lower()
        return city
    return None


def signal_scheduled_time(
    fs_time: datetime | None, bt_event: dict,
) -> tuple[float, str]:
    if fs_time is None:
        return 0.5, "no_fs_time"

    bt_time_str = bt_event.get("date", "") or bt_event.get("start", "")
    if not bt_time_str:
        return 0.5, "no_bt_time"

    try:
        if isinstance(bt_time_str, str):
            if "T" in bt_time_str:
                bt_dt = datetime.fromisoformat(
                    bt_time_str.replace("Z", "+00:00"),
                )
            else:
                bt_dt = datetime.fromisoformat(bt_time_str)
        else:
            bt_dt = datetime.fromtimestamp(float(bt_time_str), tz=timezone.utc)
    except (ValueError, TypeError):
        return 0.5, "parse_error"

    diff_seconds = abs((fs_time - bt_dt).total_seconds())
    if diff_seconds < 3600:
        return 1.0, "exact"
    if diff_seconds < 7200:
        return 0.9, "within_2h"
    if diff_seconds < 14400:
        return 0.6, "within_4h"
    if diff_seconds < 43200:
        return 0.3, "same_day"
    return 0.1, "different_day"


def signal_gender(fs_tournament: str, bt_event: dict) -> tuple[float, str]:
    if not fs_tournament:
        return 0.5, "no_tournament"

    fs_upper = fs_tournament.upper()
    bt_name = str(bt_event.get("name", "")).upper()

    fs_wta = "WTA" in fs_upper
    bt_wta = "WTA" in bt_name or "WOMEN" in bt_name
    fs_atp = "ATP" in fs_upper or "CHALLENGER MEN" in fs_upper
    bt_atp = "ATP" in bt_name or "CHALLENGER" in bt_name or "MEN" in bt_name

    if fs_wta and bt_wta:
        return 1.0, "wta"
    if fs_atp and bt_atp:
        return 1.0, "atp"
    if fs_wta and bt_atp:
        return 0.0, "mismatch:wta_vs_atp"
    if fs_atp and bt_wta:
        return 0.0, "mismatch:atp_vs_wta"

    return 0.5, "unknown"


def signal_competition_type(
    fs_tournament: str, bt_event: dict,
) -> tuple[float, str]:
    if not fs_tournament:
        return 0.5, "no_tournament"

    fs_upper = fs_tournament.upper()
    bt_name = str(bt_event.get("comp_name", "") or bt_event.get("name", "")).upper()

    fs_qual = "QUALIFICATION" in fs_upper
    bt_qual = "QUALIFICATION" in bt_name or "QUAL" in bt_name

    if fs_qual and bt_qual:
        return 1.0, "both_qual"
    if not fs_qual and not bt_qual:
        return 1.0, "both_main"
    if fs_qual != bt_qual:
        return 0.3, "qual_mismatch"

    return 0.5, "unknown"


def extract_signals_from_tracked(
    player1_name: str,
    player2_name: str,
    tournament: str,
    scheduled_start: datetime | None,
    bt_event: dict,
) -> dict:
    return {
        "player_names": signal_player_names(
            player1_name, player2_name,
            str(bt_event.get("name", "").split(" v ")[0] if " v " in bt_event.get("name", "") else bt_event.get("runner_a", "")),
            str(bt_event.get("name", "").split(" v ")[1] if " v " in bt_event.get("name", "") else bt_event.get("runner_b", "")),
        ),
        "tournament": signal_tournament(tournament, str(bt_event.get("name", ""))),
        "scheduled_time": signal_scheduled_time(scheduled_start, bt_event),
        "gender": signal_gender(tournament, bt_event),
        "competition_type": signal_competition_type(tournament, bt_event),
    }
