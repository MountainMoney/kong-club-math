# Kong Club PAR Smoke Report

This is a pre-optimizer smoke report. Final PAR requires 100k+ simulations per mode after Python 3.12 dependency setup is complete.

Target RTP: 96.50%
Max win cap: 25000x
Payout units: book/LUT payouts are hundredths of stake, so 9600 means 96.00x.

## Mode Summary

### base
- Spins: 50
- Mean payout / EV: 3.1220x
- Hit rate: 54.00%
- Std dev: 19.5248
- Max observed: 139.70x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 1.50x / 139.70x
- CVaR95 / CVaR99: 29.74x / 139.70x

### base_ante
- Spins: 50
- Mean payout / EV: 3.1220x
- Hit rate: 54.00%
- Std dev: 19.5248
- Max observed: 139.70x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 1.50x / 139.70x
- CVaR95 / CVaR99: 29.74x / 139.70x

### feature_spin
- Spins: 25
- Mean payout / EV: 37.2240x
- Hit rate: 100.00%
- Std dev: 26.4451
- Max observed: 101.30x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 95.60x / 101.30x
- CVaR95 / CVaR99: 98.45x / 101.30x

### peak_spin
- Spins: 25
- Mean payout / EV: 2776.0000x
- Hit rate: 100.00%
- Std dev: 1482.5903
- Max observed: 7500.00x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 5225.00x / 7500.00x
- CVaR95 / CVaR99: 6362.50x / 7500.00x

### bonus_see
- Spins: 25
- Mean payout / EV: 206.5800x
- Hit rate: 100.00%
- Std dev: 228.7481
- Max observed: 775.10x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 695.70x / 775.10x
- CVaR95 / CVaR99: 735.40x / 775.10x

### bonus_hear
- Spins: 25
- Mean payout / EV: 206.5800x
- Hit rate: 100.00%
- Std dev: 228.7481
- Max observed: 775.10x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 695.70x / 775.10x
- CVaR95 / CVaR99: 735.40x / 775.10x

### bonus_gamble
- Spins: 25
- Mean payout / EV: 106.3480x
- Hit rate: 100.00%
- Std dev: 178.1616
- Max observed: 692.00x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 474.50x / 692.00x
- CVaR95 / CVaR99: 583.25x / 692.00x

## Event Coverage

Missing required smoke events: none

Observed events:
- boardActivation: 92
- coinSeed: 492
- finalWin: 225
- freeSpinEnd: 75
- kongClubMode: 100
- progressFill: 675
- reveal: 925
- setTotalWin: 925
- setWin: 395
- tumbleBoard: 511
- updateFreeSpin: 750
- updateLevelUpTiles: 1070
- updateTumbleWin: 555
- winInfo: 463
