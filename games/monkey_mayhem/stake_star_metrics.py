"""Estimate Stake star-rating tail metrics from publish LUTs."""

from __future__ import annotations

import json
from pathlib import Path

from reweight_lut import MODE_COSTS, MAX_WIN_PAYOUT, PAYOUT_5K, PUBLISH, read_lut, rtp_from_rows, tail_rtp_share

GAME_DIR = Path(__file__).resolve().parent


def unweighted_tail_share(rows, threshold: int) -> float:
    payouts = [p for _, _, p in rows]
    total = sum(payouts)
    tail = sum(p for p in payouts if p >= threshold)
    return tail / total if total else 0.0


def main() -> None:
    report = []
    for mode, cost in MODE_COSTS.items():
        rows = read_lut(PUBLISH / f"lookUpTable_{mode}_0.csv")
        n = len(rows)
        max_rows = sum(1 for _, _, p in rows if p >= MAX_WIN_PAYOUT)
        payouts = [p for _, _, p in rows]
        row_prob_53x = sum(1 for p in payouts if p >= 5_300) / n
        tw = sum(w for _, w, _ in rows)
        mean_w = sum(w * p for _, w, p in rows) / tw / 100.0 / cost
        var_w = sum(w * ((p / 100.0 / cost - mean_w) ** 2) for _, w, p in rows) / tw
        row_prob_40x = sum(1 for p in payouts if p >= 4_000) / n
        item = {
            "mode": mode,
            "rows": n,
            "weighted_rtp": rtp_from_rows(rows, cost),
            "weighted_std": var_w**0.5,
            "max_win_rows": max_rows,
            "max_win_row_pct": max_rows / n,
            "row_prob_40x": row_prob_40x,
            "row_prob_53x": row_prob_53x,
            "weighted_10k_rtp_share": tail_rtp_share(rows, cost, MAX_WIN_PAYOUT),
            "weighted_5kplus_rtp_share": tail_rtp_share(rows, cost, PAYOUT_5K),
            "unweighted_10k_rtp_share": unweighted_tail_share(rows, MAX_WIN_PAYOUT),
            "unweighted_100x_rtp_share": unweighted_tail_share(rows, 10_000),
        }
        report.append(item)
        print(
            f"{mode}: rtp={item['weighted_rtp']:.4f} std={item['weighted_std']:.2f} "
            f"40x+_rows={100*row_prob_40x:.2f}% "
            f"53x+_rows={100*row_prob_53x:.2f}% "
            f"w10k={item['weighted_10k_rtp_share']:.4f} uw100x={item['unweighted_100x_rtp_share']:.4f}"
        )

    out = GAME_DIR / "library" / "stake_star_metrics.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
