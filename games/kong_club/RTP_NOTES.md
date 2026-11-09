# Kong Club math — 96.3% lock (pay table + Feature Spin)

Target RTP is **96.3%** on every mode. Each mode has **500 books** until ship. Max win stays 25,000x.

Cluster pay = locked face × the sum of lit tile multipliers (bronze 2× / silver 5× / gold 10×). Faces are multiples of total bet. Size is uncapped; **13+ shares one face**.

| Symbols | 5 | 6 | 7 | 8 | 9–10 | 11–12 | 13+ |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 10 / J / Q / K / A | 0.1 | 0.2 | 0.3 | 0.5 | 1.5 | 5 | 15 |
| Lemon, Coconut | 0.3 | 0.4 | 0.5 | 0.7 | 2.5 | 7.5 | 25 |
| Orange, Grape | 0.5 | 0.7 | 1 | 1.5 | 5 | 15 | 50 |
| Banana | 1 | 1.5 | 2 | 3 | 10 | 30 | 100 |

Base, Ante, and Hunt pay the plain face on the first connection, then face × the lit sum after tiles rank up. Feature Spin and bonuses light the tiles first, then pay face × the new sum.

## Feature Spin

Every Feature Spin opens with the coin bar full (`progressFill` value = threshold = 10 before the reveal). The spin always lands at least one cluster (short low clusters are common; wild chains and a size-14 cluster show up in this library). When the tumble chain goes idle, the coin game runs on every lit tile. Feature Spin and Trifecta Spin do not open a bonus.

This 500-book file:

- 500/500 have a cluster, a tumble, and a `boardActivation` coin game with at least one flipped tile
- 0/500 open a bonus
- 0 coin-game rerun caps
- unweighted mean win **77.01x** (min 6x, max 3,025x)
- published price **75x** (top of the 50–75x band). Lookup weights pull the weighted mean to 72.225x so RTP is 96.3%

Trifecta stays 1,000x, 50% dead / 50% live, no cluster pay, no bonus. Hunt prices stay 5 / 6 / 10 / 25 and the locked scatter rates stay 9% / 13% / 18% / 45%. Buy prices stay 100 / 300 / 330 / 500. The pay-table change still fit those prices, so they were not re-solved.

## Published RTP (weighted)

| Mode | Cost | RTP | Books |
| --- | --- | --- | --- |
| base | 1 | 96.300% | 500 |
| base_ante | 1.4 | 96.300% | 500 |
| hunt_2 | 5 | 96.300% | 500 |
| hunt_3 | 6 | 96.300% | 500 |
| hunt_4 | 10 | 96.300% | 500 |
| hunt_5 | 25 | 96.300% | 500 |
| feature_spin | 75 | 96.300% | 500 |
| peak_spin | 1000 | 96.300% | 500 |
| bonus_see | 100 | 96.300% | 500 |
| bonus_hear | 300 | 96.300% | 500 |
| bonus_pick (renamed `bonus_mystery`, see below) | 330 | 96.300% | 500 |
| bonus_risky | 500 | 96.300% | 500 |

### Mode rename: `bonus_pick` -> `bonus_mystery` (Nov 8, 2026)

Ryan asked for the Mystery Bonus key to be `bonus_mystery` in math and web. The
code, `mode_prices.json`, and scripts now use `bonus_mystery` (`GameConfig` still
reads a legacy `bonus_pick` price if present). The table above and the files in
`library/publish_files/` and `reports/` describe the pr7-963 run and still say
`bonus_pick`; they were **not** regenerated. The next authorized math run emits
`index.json` mode `bonus_mystery`, `books_bonus_mystery.jsonl.zst`, and
`lookUpTable_bonus_mystery.csv` / `lookUpTable_bonus_mystery_0.csv`. The RGS/Stake
mode name is whatever `index.json` says, so the uploaded name changes too. Book
criteria names (`pick_see` / `pick_hear` / `pick_speak`) are unchanged.

`reports/locked_spec_963.json` and `reports/lock_rtp.json` are the machine-readable copies. `mode_prices.json` is what `GameConfig` loads.

## Regenerate

From the repo root. `MM_SIMS` defaults to 500. Leave it there until ship.

```bash
python3 games/kong_club/run.py
python3 games/kong_club/scripts/fit_published_rtp.py
python3 games/kong_club/scripts/mode_report.py
```

`run.py` writes `library/publish_files/books_<mode>.jsonl.zst` and the raw lookup tables. `fit_published_rtp.py` reweights those tables onto 96.3%, writes `mode_prices.json`, and copies costs into `index.json`. Feature Spin price is solved into 50–75x from the book mean (half-step, clamped to that band). Hunt costs and scatter rates are held. Trifecta stays 1,000x with a 50% dead rate. Buys keep their prices and their See / Hear / Speak mix.

One mode only:

```bash
MM_MODES=feature_spin python3 games/kong_club/run.py
python3 games/kong_club/scripts/fit_published_rtp.py
```

The fitter reads every mode, so the other book files must already be present.

## Verify

```bash
python3 games/kong_club/scripts/test_scratch_rebuild.py
python3 games/kong_club/scripts/test_game_loop_smoke.py
python3 games/kong_club/scripts/mode_report.py
```

The pay-table test checks every locked face, including 9 = 10, 11 = 12, and 13 = 30. The Feature Spin tests require a full opening bar, a winning cluster, a coin-game `boardActivation` with flipped tiles, and no bonus. Smoke does the same for Trifecta (no bonus, dead spins do not run the coin game).

`mode_report.py` must print 96.300% and 500 books on every mode, and `coin_cap_hits` must stay 0.
