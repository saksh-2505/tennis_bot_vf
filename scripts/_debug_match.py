from database import SessionLocal
from models.tracked_match import TrackedMatch
from models.bettingsite import BettingsiteFoundMatch
from matcher.engine import match_all

session = SessionLocal()
unmatched = session.query(TrackedMatch).filter(
    TrackedMatch.betting_market_id.is_(None),
    TrackedMatch.status != 'LIVE'
).limit(5).all()
bt = session.query(BettingsiteFoundMatch).all()

bt_events = [
    {
        'name': f"{b.player_a} v {b.player_b}",
        'market_id': b.market_id,
        'runner_a': b.player_a,
        'runner_b': b.player_b,
        'date': b.event_date or '',
        'comp_name': b.comp_name or '',
    }
    for b in bt
]

print(f"Unmatched: {len(unmatched)}, BT events: {len(bt_events)}")

results = match_all(unmatched, bt_events, session=session)
for r in results:
    print(f"found={r.match_found} mkt={r.selected_market_id} conf={r.selected_confidence:.3f} {r.flashscore_match_id}")

matched = sum(1 for r in results if r.match_found)
print(f"Matched: {matched}/{len(unmatched)}")
session.close()
