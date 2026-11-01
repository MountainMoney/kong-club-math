"""Export Stake review event IDs from publish LUTs."""

from __future__ import annotations

import json
from pathlib import Path
from statistics import median

from reweight_lut import MODE_COSTS, PUBLISH, read_lut

GAME_DIR = Path(__file__).resolve().parent
MODES = list(MODE_COSTS.keys())
GAME_SLUG = "monkey-mayhem"
VERSION = "v0_4_0_250k"
MAX_WIN_PAYOUT = 1_000_000


def pick_event_ids(mode: str) -> dict[str, int]:
    rows = read_lut(PUBLISH / f"lookUpTable_{mode}_0.csv")
    if not rows:
        raise RuntimeError(f"No LUT rows for {mode}")

    by_payout: dict[int, list[int]] = {}
    for sim_id, _, payout in rows:
        by_payout.setdefault(payout, []).append(sim_id)

    max_payout = max(by_payout)
    max_event = by_payout[max_payout][0]

    payouts = sorted(by_payout)
    median_payout = int(median(payouts))
    closest_median = min(payouts, key=lambda p: abs(p - median_payout))
    avg_event = by_payout[closest_median][0]

    high_threshold = max(MAX_WIN_PAYOUT // 10, 10_000)
    high_payout = next((p for p in reversed(payouts) if p >= high_threshold), max_payout)
    high_event = by_payout[high_payout][0]

    return {
        "max_win": max_event,
        "high_win": high_event,
        "average": avg_event,
        "max_payout_hundredths": max_payout,
        "high_payout_hundredths": high_payout,
        "average_payout_hundredths": closest_median,
    }


def replay_url(mode: str, event: int, amount_api: int = 1_000_000) -> str:
    return (
        f"https://YOUR_FRONTEND_URL/?replay=true"
        f"&game={GAME_SLUG}"
        f"&version={VERSION}"
        f"&mode={mode}"
        f"&event={event}"
        f"&amount={amount_api}"
        f"&currency=USD"
        f"&lang=en"
        f"&rgs_url=YOUR_RGS_URL"
    )


def main() -> None:
    report = {mode: pick_event_ids(mode) for mode in MODES}
    out = GAME_DIR / "STAKE_REVIEW_EVENT_IDS.md"
    lines = [
        "# Monkey Mayhem — Stake Review Event IDs",
        "",
        f"Game slug: `{GAME_SLUG}`",
        f"Math version: `{VERSION}`",
        "",
        "Replace `YOUR_FRONTEND_URL` and `YOUR_RGS_URL` with staging values.",
        "",
    ]
    for mode, data in report.items():
        cost = MODE_COSTS[mode]
        lines.extend(
            [
                f"## {mode} (cost {cost}×)",
                "",
                f"- **Max win:** event `{data['max_win']}` (payout {data['max_payout_hundredths'] / 100:.2f}× cost)",
                f"- **High win:** event `{data['high_win']}` (payout {data['high_payout_hundredths'] / 100:.2f}× cost)",
                f"- **Average:** event `{data['average']}` (payout {data['average_payout_hundredths'] / 100:.2f}× cost)",
                "",
                "Replay URL template:",
                "",
                "```",
                replay_url(mode, data["max_win"]),
                "```",
                "",
            ]
        )

    out.write_text("\n".join(lines), encoding="utf-8")
    json_path = GAME_DIR / "library" / "stake_review_event_ids.json"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote {out}")
    print(f"Wrote {json_path}")


if __name__ == "__main__":
    main()
