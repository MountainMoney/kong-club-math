# Kong Club PAR Smoke Report

This is a pre-optimizer smoke report. Final PAR requires 100k+ simulations per mode after Python 3.12 dependency setup is complete.

Target RTP: 96.50%
Max win cap: 25000x
Payout units: book/LUT payouts are hundredths of stake, so 9600 means 96.00x.

## Mode Summary

### base
- Spins: 50
- Mean payout / EV: 2.3640x
- Hit rate: 62.00%
- Std dev: 14.3249
- Max observed: 102.60x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 1.50x / 102.60x
- CVaR95 / CVaR99: 35.23x / 102.60x

### base_ante
- Spins: 50
- Mean payout / EV: 2.3640x
- Hit rate: 62.00%
- Std dev: 14.3249
- Max observed: 102.60x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 1.50x / 102.60x
- CVaR95 / CVaR99: 35.23x / 102.60x

### feature_spin
- Spins: 25
- Mean payout / EV: 42.6800x
- Hit rate: 100.00%
- Std dev: 52.1050
- Max observed: 219.60x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 161.00x / 219.60x
- CVaR95 / CVaR99: 190.30x / 219.60x

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
- Mean payout / EV: 87.3560x
- Hit rate: 96.00%
- Std dev: 139.4581
- Max observed: 629.40x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 304.90x / 629.40x
- CVaR95 / CVaR99: 467.15x / 629.40x

### bonus_hear
- Spins: 25
- Mean payout / EV: 495.3040x
- Hit rate: 100.00%
- Std dev: 795.8379
- Max observed: 3591.60x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 2289.70x / 3591.60x
- CVaR95 / CVaR99: 2940.65x / 3591.60x

### bonus_gamble
- Spins: 25
- Mean payout / EV: 243.4280x
- Hit rate: 100.00%
- Std dev: 263.7248
- Max observed: 992.40x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 925.70x / 992.40x
- CVaR95 / CVaR99: 959.05x / 992.40x

## Event Coverage

Missing required smoke events: none

Observed events:
- boardActivation: 118
- finalWin: 225
- freeSpinEnd: 75
- kongClubMode: 100
- progressFill: 838
- reveal: 925
- setTotalWin: 925
- setWin: 414
- tumbleBoard: 513
- updateFreeSpin: 750
- updateLevelUpTiles: 626
- updateTumbleWin: 631
- winInfo: 513
