# ADR 8: Prediction — Why Replay-Based

## Problem
Need to evaluate prediction models against historical match data.

## Decision
Replay-based evaluation: replay live data from completed_matches through prediction pipeline.

## Alternatives
- **Live prediction**: Risk financial capital; slow iteration
- **Paper trading (simulated)**: Requires market simulation layer
- **Historical replay**: Use collected scores + odds as ground truth

## Tradeoffs
- + Safe (no financial risk during development)
- + Can replay any completed match with score + odds data
- + Deterministic evaluation (same input = same result)
- - Requires sufficient completed_matches with full tick data
- - Currently 59 matches finalized (many have sparse score data)
- - Replay module is still a stub (Phase 4)

## Consequences
- `replay/` module currently empty
- `completed_matches` stores all data needed for replay
- Future prediction pipeline will read from completed_matches
