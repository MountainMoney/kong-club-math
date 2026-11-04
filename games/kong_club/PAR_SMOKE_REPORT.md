# Kong Club PAR Smoke Report

This is a pre-optimizer smoke report. Final PAR requires 100k+ simulations per mode after Python 3.12 dependency setup is complete.

Target RTP: 96.30%
Max win cap: 25000x
Payout units: book/LUT payouts are hundredths of stake, so 9600 means 96.00x.

## Mode Summary

### base
- Spins: 4
- Mean payout / EV: 0.0400x
- Hit rate: 25.00%
- Std dev: 0.0693
- Max observed: 0.16x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 0.16x / 0.16x
- CVaR95 / CVaR99: 0.16x / 0.16x

### base_ante
- Spins: 4
- Mean payout / EV: 0.0400x
- Hit rate: 25.00%
- Std dev: 0.0693
- Max observed: 0.16x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 0.16x / 0.16x
- CVaR95 / CVaR99: 0.16x / 0.16x

### hunt_2
- Spins: 4
- Mean payout / EV: 0.0400x
- Hit rate: 25.00%
- Std dev: 0.0693
- Max observed: 0.16x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 0.16x / 0.16x
- CVaR95 / CVaR99: 0.16x / 0.16x

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
- Mean payout / EV: 2243.7500x
- Hit rate: 100.00%
- Std dev: 598.7944
- Max observed: 3275.00x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 3275.00x / 3275.00x
- CVaR95 / CVaR99: 3275.00x / 3275.00x

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
- Mean payout / EV: 157.0825x
- Hit rate: 100.00%
- Std dev: 132.0130
- Max observed: 354.05x
- Near max rate (>=90% cap): 0.00%
- P95 / P99: 354.05x / 354.05x
- CVaR95 / CVaR99: 354.05x / 354.05x

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
- progressFill: 84
- reveal: 154
- setTotalWin: 154
- setWin: 41
- tumbleBoard: 46
- updateFreeSpin: 130
- updateLevelUpTiles: 62
- updateTumbleWin: 52
- winInfo: 46
