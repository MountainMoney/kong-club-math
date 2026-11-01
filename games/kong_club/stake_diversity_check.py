"""Stake Engine payout diversity gates (portal feedback).

Requirements (combined across all bet modes in the upload):
  1. >= 1,200 unique payout values in the book pool (unweighted LUT rows).
  2. The most common payout value must appear in > 1,000 books (row count).
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from reweight_lut import MODE_COSTS, PUBLISH, read_lut

GAME_DIR = Path(__file__).resolve().parent
MIN_UNIQUE_PAYOUTS = 1_200
MIN_TOP_PAYOUT_COUNT = 1_000


def analyze_modes(modes: list[str] | None = None) -> dict:
    modes = modes or list(MODE_COSTS.keys())
    combined = Counter()
    per_mode = {}

    for mode in modes:
        path = PUBLISH / f"lookUpTable_{mode}_0.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        rows = read_lut(path)
        payouts = [p for _, _, p in rows]
        counts = Counter(payouts)
        top_pay, top_cnt = counts.most_common(1)[0]
        per_mode[mode] = {
            "rows": len(rows),
            "unique_payouts": len(counts),
            "top_payout": top_pay,
            "top_count": top_cnt,
        }
        combined.update(counts)

    top_pay, top_cnt = combined.most_common(1)[0]
    return {
        "modes": per_mode,
        "combined_unique_payouts": len(combined),
        "combined_top_payout": top_pay,
        "combined_top_count": top_cnt,
        "pass_unique": len(combined) >= MIN_UNIQUE_PAYOUTS,
        "pass_top_count": top_cnt > MIN_TOP_PAYOUT_COUNT,
    }


def main() -> None:
    report = analyze_modes()
    print(
        f"combined unique={report['combined_unique_payouts']} "
        f"(need >={MIN_UNIQUE_PAYOUTS}) "
        f"top={report['combined_top_payout']} count={report['combined_top_count']} "
        f"(need >{MIN_TOP_PAYOUT_COUNT})"
    )
    for mode, item in report["modes"].items():
        print(
            f"  {mode}: unique={item['unique_payouts']} "
            f"top={item['top_payout']} x{item['top_count']}"
        )

    out = GAME_DIR / "library" / "stake_diversity_report.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if not report["pass_unique"] or not report["pass_top_count"]:
        print("FAIL: Stake payout diversity gates not met.", file=sys.stderr)
        sys.exit(1)
    print("PASS: Stake payout diversity gates met.")


if __name__ == "__main__":
    main()
