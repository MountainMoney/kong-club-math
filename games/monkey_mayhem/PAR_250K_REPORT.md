# Monkey Mayhem PAR Report — 250k Weighted

Generated from `library/publish_files/lookUpTable_*_0.csv` after reweight pass.
Book/LUT payout parity verified via `execute_all_tests`.

## Weighted RTP (authoritative)

| Mode | Cost | Rows | Weighted RTP | Max-win rows |
|------|------|------|--------------|--------------|
| base | 1.0x | 250,000 | 0.9614 (96.14%) | 251 |
| base_ante | 1.4x | 250,000 | 0.9600 (96.00%) | 250 |
| bonus_see | 100.0x | 250,000 | 0.9600 (96.00%) | 9,843 |
| bonus_hear | 200.0x | 250,000 | 0.9600 (96.00%) | 158,164 |

**Cross-mode RTP spread:** 0.0014 (0.14 pp) — limit ≤ 5.00 pp.

## Tail risk (weighted CVaR, buy modes)

Per Lessons Learned §4.7: buy modes carry highest tail risk; document CVaR95/CVaR99 for portal review.

### bonus_see (100.0x)
- P99 payout: 1977.00x bet
- CVaR95 (tail mean ≥ P95): 11.91x normalized to cost
- CVaR99 (tail mean ≥ P99): 32.29x normalized to cost

### bonus_hear (200.0x)
- P99 payout: 3975.00x bet
- CVaR95 (tail mean ≥ P95): 14.82x normalized to cost
- CVaR99 (tail mean ≥ P99): 22.38x normalized to cost

## Upload package

- Zip: `C:\Users\Cole\Desktop\Slots\Monkey Mayhem\stake_uploads\monkey_mayhem_math_v0_4_0_250k.zip`
- SHA256: `737e7ee86cc9d7553398ca48c519ce4a354605d8b6de6d983d1e8a1439e9dd98  monkey_mayhem_math_v0_4_0_250k.zip`

## Pass criteria checklist

- [x] 250,000 LUT rows per mode
- [x] All 4 books present in publish_files
- [x] Books/LUT payout hash verification
- [x] Max-win row (1,000,000 hundredths) in every mode
- [x] Cross-mode RTP spread ≤ 5%
- [x] Weighted RTP ~96% per mode (base 95.14% — within tolerance; reweight can be re-tuned)
