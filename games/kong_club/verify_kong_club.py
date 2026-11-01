"""Kong Club lightweight math verification.

This script is intentionally separate from the SDK optimizer. It gives fast
feedback on mechanic invariants before expensive book generation.
"""

from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, pstdev
import sys

SDK_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SDK_ROOT))

from game_config import GameConfig
from gamestate import GameState


REQUIRED_EVENTS = {
    "reveal",
    "winInfo",
    "updateTumbleWin",
    "setWin",
    "setTotalWin",
    "finalWin",
    "updateLevelUpTiles",
    "progressFill",
    "boardActivation",
}


def percentile(values, pct):
    if not values:
        return 0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, int(round((pct / 100) * (len(ordered) - 1))))
    return ordered[idx]


def cvar(values, pct):
    threshold = percentile(values, pct)
    tail = [v for v in values if v >= threshold]
    return mean(tail) if tail else 0


def get_smoke_distribution(config, mode):
    preferred = {
        "base": "basegame",
        "base_ante": "basegame",
        "feature_spin": "nibble",
        "peak_spin": "nibble",
        "bonus_see": "bonus_see",
        "bonus_hear": "bonus_hear",
        "bonus_gamble": "gamble_hear",
    }[mode]
    for bet_mode in config.bet_modes:
        if bet_mode.get_name() == mode:
            for dist in bet_mode.get_distributions():
                if dist.get_criteria() == preferred:
                    return dist
    raise RuntimeError(f"Could not find smoke distribution for {mode}: {preferred}")


def run_mode(config, mode, sims):
    payouts = []
    event_counts = Counter()
    max_seen = 0
    near_max = 0
    board_activations = 0
    criteria_counts = Counter()

    dist = get_smoke_distribution(config, mode)
    for sim in range(sims):
        state = GameState(config)
        state.betmode = mode
        state.criteria = dist.get_criteria()
        state.run_spin(sim)
        payout = state.final_win
        payouts.append(payout)
        max_seen = max(max_seen, payout)
        if payout >= config.wincap * 0.9:
            near_max += 1
        criteria_counts[state.criteria] += 1
        spin_events = Counter()
        for event in state.book.events:
            spin_events[event["type"]] += 1
        for event_type, count in spin_events.items():
            event_counts[event_type] += count
        board_activations += spin_events.get("boardActivation", 0)

    return {
        "mode": mode,
        "sims": sims,
        "mean": mean(payouts),
        "std": pstdev(payouts) if len(payouts) > 1 else 0,
        "hit_rate": sum(1 for p in payouts if p > 0) / len(payouts),
        "max_seen": max_seen,
        "near_max_rate": near_max / len(payouts),
        "p95": percentile(payouts, 95),
        "p99": percentile(payouts, 99),
        "cvar95": cvar(payouts, 95),
        "cvar99": cvar(payouts, 99),
        "event_counts": dict(event_counts),
        "criteria_counts": dict(criteria_counts),
    }


def write_report(results, config):
    lines = [
        "# Kong Club PAR Smoke Report",
        "",
        "This is a pre-optimizer smoke report. Final PAR requires 100k+ simulations per mode after Python 3.12 dependency setup is complete.",
        "",
        f"Target RTP: {config.rtp:.2%}",
        f"Max win cap: {config.wincap:.0f}x",
        "Payout units: book/LUT payouts are hundredths of stake, so 9600 means 96.00x.",
        "",
        "## Mode Summary",
        "",
    ]
    for result in results:
        lines.extend(
            [
                f"### {result['mode']}",
                f"- Spins: {result['sims']}",
                f"- Mean payout / EV: {result['mean']:.4f}x",
                f"- Hit rate: {result['hit_rate']:.2%}",
                f"- Std dev: {result['std']:.4f}",
                f"- Max observed: {result['max_seen']:.2f}x",
                f"- Near max rate (>=90% cap): {result['near_max_rate']:.2%}",
                f"- P95 / P99: {result['p95']:.2f}x / {result['p99']:.2f}x",
                f"- CVaR95 / CVaR99: {result['cvar95']:.2f}x / {result['cvar99']:.2f}x",
                "",
            ]
        )

    lines.extend(
        [
            "## Event Coverage",
            "",
        ]
    )
    all_events = defaultdict(int)
    for result in results:
        for event_type, count in result["event_counts"].items():
            all_events[event_type] += count
    missing = sorted(REQUIRED_EVENTS - set(all_events))
    lines.append(f"Missing required smoke events: {', '.join(missing) if missing else 'none'}")
    lines.append("")
    lines.append("Observed events:")
    for event_type in sorted(all_events):
        lines.append(f"- {event_type}: {all_events[event_type]}")

    with open(Path(__file__).with_name("PAR_SMOKE_REPORT.md"), "w", encoding="utf-8") as report:
        report.write("\n".join(lines) + "\n")


def main():
    config = GameConfig()
    modes = [
        "base",
        "base_ante",
        "feature_spin",
        "peak_spin",
        "bonus_see",
        "bonus_hear",
        "bonus_gamble",
    ]
    sims_by_mode = {
        "base": 50,
        "base_ante": 50,
        "feature_spin": 25,
        "peak_spin": 25,
        "bonus_see": 25,
        "bonus_hear": 25,
        "bonus_gamble": 25,
    }
    results = [run_mode(config, mode, sims_by_mode[mode]) for mode in modes]
    assert abs(config.rtp - 0.965) < 1e-9, config.rtp
    assert config.coin_game_max_reruns == 10
    assert config.max_board_activations_hear == 1
    for result in results:
        assert result["max_seen"] <= config.wincap, f"{result['mode']} exceeded max win cap"
        for event_type in result["event_counts"]:
            assert "monkeyMayhem" not in event_type
    write_report(results, config)
    print(f"Wrote {Path(__file__).with_name('PAR_SMOKE_REPORT.md')}")


if __name__ == "__main__":
    main()
