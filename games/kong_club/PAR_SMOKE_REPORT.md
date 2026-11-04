# Kong Club PAR Smoke Report

This is a pre-optimizer smoke report. Final PAR requires 100k+ simulations per mode after Python 3.12 dependency setup is complete.

Target RTP: 96.30%
Max win cap: 25000x
Payout units: book/LUT payouts are hundredths of stake, so 9600 means 96.00x.

## Mode Summary

### base
- Spins: 4
- Mean payout / EV: 0.0000x
- Hit rate: 0.00%
- Std dev: 0.0000
- Max observed: 0.00x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 0.00x / 0.00x
- CVaR95 / CVaR99: 0.00x / 0.00x

### base_ante
- Spins: 4
- Mean payout / EV: 0.0000x
- Hit rate: 0.00%
- Std dev: 0.0000
- Max observed: 0.00x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 0.00x / 0.00x
- CVaR95 / CVaR99: 0.00x / 0.00x

### hunt_2
- Spins: 4
- Mean payout / EV: 0.0000x
- Hit rate: 0.00%
- Std dev: 0.0000
- Max observed: 0.00x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 0.00x / 0.00x
- CVaR95 / CVaR99: 0.00x / 0.00x

### feature_spin
- Spins: 4
- Mean payout / EV: 10.1500x
- Hit rate: 100.00%
- Std dev: 6.5583
- Max observed: 20.21x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 20.21x / 20.21x
- CVaR95 / CVaR99: 20.21x / 20.21x

### peak_spin
- Spins: 4
- Mean payout / EV: 10062.5000x
- Hit rate: 100.00%
- Std dev: 8689.8738
- Max observed: 25000.00x
- Near max rate (>=90% cap): 25.00%
- P95 / P99: 25000.00x / 25000.00x
- CVaR95 / CVaR99: 25000.00x / 25000.00x

### bonus_see
- Spins: 4
- Mean payout / EV: 25.2000x
- Hit rate: 100.00%
- Std dev: 19.8161
- Max observed: 58.82x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 58.82x / 58.82x
- CVaR95 / CVaR99: 58.82x / 58.82x

### bonus_hear
- Spins: 4
- Mean payout / EV: 507.5825x
- Hit rate: 100.00%
- Std dev: 719.6244
- Max observed: 1748.05x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 1748.05x / 1748.05x
- CVaR95 / CVaR99: 1748.05x / 1748.05x

### bonus_pick
- Spins: 4
- Mean payout / EV: 25.2000x
- Hit rate: 100.00%
- Std dev: 19.8161
- Max observed: 58.82x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 58.82x / 58.82x
- CVaR95 / CVaR99: 58.82x / 58.82x

### bonus_risky
- Spins: 4
- Mean payout / EV: 0.0000x
- Hit rate: 0.00%
- Std dev: 0.0000
- Max observed: 0.00x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 0.00x / 0.00x
- CVaR95 / CVaR99: 0.00x / 0.00x

## Event Coverage

Missing required smoke events: none

Observed events:
- boardActivation: 6
- finalWin: 36
- freeSpinEnd: 12
- freeSpinRetrigger: 5
- kongClubMode: 16
- progressFill: 81
- reveal: 154
- setTotalWin: 154
- setWin: 37
- tumbleBoard: 43
- updateFreeSpin: 130
- updateLevelUpTiles: 59
- updateTumbleWin: 49
- winInfo: 43
- wincap: 1
