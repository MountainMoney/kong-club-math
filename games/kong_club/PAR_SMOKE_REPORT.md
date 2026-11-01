# Kong Club PAR Smoke Report

This is a pre-optimizer smoke report. Final PAR requires 100k+ simulations per mode after Python 3.12 dependency setup is complete.

Target RTP: 96.00%
Max win cap: 10000x
Payout units: book/LUT payouts are hundredths of stake, so 9600 means 96.00x.

## Mode Summary

### base
- Spins: 50
- Mean payout / EV: 0.0748x
- Hit rate: 66.00%
- Std dev: 0.0824
- Max observed: 0.35x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 0.25x / 0.35x
- CVaR95 / CVaR99: 0.30x / 0.35x

### base_ante
- Spins: 50
- Mean payout / EV: 0.0748x
- Hit rate: 66.00%
- Std dev: 0.0824
- Max observed: 0.35x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 0.25x / 0.35x
- CVaR95 / CVaR99: 0.30x / 0.35x

### feature_spin
- Spins: 25
- Mean payout / EV: 49.2524x
- Hit rate: 100.00%
- Std dev: 14.3599
- Max observed: 78.25x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 73.45x / 78.25x
- CVaR95 / CVaR99: 75.85x / 78.25x

### bonus_see
- Spins: 25
- Mean payout / EV: 150.3444x
- Hit rate: 100.00%
- Std dev: 44.8709
- Max observed: 253.24x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 240.27x / 253.24x
- CVaR95 / CVaR99: 246.75x / 253.24x

### bonus_hear
- Spins: 25
- Mean payout / EV: 1473.7040x
- Hit rate: 100.00%
- Std dev: 1262.8430
- Max observed: 6877.27x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 2687.24x / 6877.27x
- CVaR95 / CVaR99: 4782.26x / 6877.27x

## Event Coverage

Missing required smoke events: none

Observed events:
- boardActivation: 371
- finalWin: 175
- freeSpinEnd: 50
- kongClubMode: 50
- progressFill: 1074
- reveal: 625
- setTotalWin: 625
- setWin: 451
- tumbleBoard: 714
- updateFreeSpin: 500
- updateLevelUpTiles: 579
- updateTumbleWin: 1085
- winInfo: 714
