# Kong Club PAR Smoke Report

This is a pre-optimizer smoke report. Final PAR requires 100k+ simulations per mode after Python 3.12 dependency setup is complete.

Target RTP: 96.50%
Max win cap: 25000x
Payout units: book/LUT payouts are hundredths of stake, so 9600 means 96.00x.

## Mode Summary

### base
- Spins: 50
- Mean payout / EV: 0.4680x
- Hit rate: 40.00%
- Std dev: 0.6970
- Max observed: 3.30x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 1.60x / 3.30x
- CVaR95 / CVaR99: 2.10x / 3.30x

### base_ante
- Spins: 50
- Mean payout / EV: 0.4680x
- Hit rate: 40.00%
- Std dev: 0.6970
- Max observed: 3.30x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 1.60x / 3.30x
- CVaR95 / CVaR99: 2.10x / 3.30x

### feature_spin
- Spins: 25
- Mean payout / EV: 57.0800x
- Hit rate: 100.00%
- Std dev: 61.1882
- Max observed: 263.30x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 201.30x / 263.30x
- CVaR95 / CVaR99: 232.30x / 263.30x

### peak_spin
- Spins: 25
- Mean payout / EV: 1890.8000x
- Hit rate: 100.00%
- Std dev: 1045.9805
- Max observed: 5218.00x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 4120.00x / 5218.00x
- CVaR95 / CVaR99: 4669.00x / 5218.00x

### bonus_see
- Spins: 25
- Mean payout / EV: 119.5960x
- Hit rate: 100.00%
- Std dev: 134.8321
- Max observed: 414.80x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 382.90x / 414.80x
- CVaR95 / CVaR99: 398.85x / 414.80x

### bonus_hear
- Spins: 25
- Mean payout / EV: 142.8200x
- Hit rate: 100.00%
- Std dev: 303.8771
- Max observed: 1554.10x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 450.60x / 1554.10x
- CVaR95 / CVaR99: 1002.35x / 1554.10x

### bonus_pick
- Spins: 25
- Mean payout / EV: 241.8720x
- Hit rate: 100.00%
- Std dev: 411.7209
- Max observed: 2105.20x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 762.40x / 2105.20x
- CVaR95 / CVaR99: 1433.80x / 2105.20x

## Event Coverage

Missing required smoke events: none

Observed events:
- boardActivation: 104
- finalWin: 225
- freeSpinEnd: 75
- kongClubMode: 100
- progressFill: 746
- reveal: 925
- setTotalWin: 925
- setWin: 360
- tumbleBoard: 503
- updateFreeSpin: 750
- updateLevelUpTiles: 620
- updateTumbleWin: 607
- winInfo: 503
