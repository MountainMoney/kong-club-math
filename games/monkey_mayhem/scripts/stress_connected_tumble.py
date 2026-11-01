"""Stress super-cascade tumble — cells cleared, chain length, and RTP metrics."""

from collections import Counter
from pathlib import Path
import sys

GAME_ROOT = Path(__file__).resolve().parents[1]
SDK_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SDK_ROOT))
sys.path.insert(0, str(GAME_ROOT))

from game_config import GameConfig
from gamestate import GameState
from src.calculations.cluster import Cluster


def count_exploded_cells(state):
    return sum(
        1
        for reel in range(state.config.num_reels)
        for row in range(state.config.num_rows[reel])
        if getattr(state.board[reel][row], "explode", False)
    )


def run_super_cascade_stress(sims=500):
    config = GameConfig()
    stats = {
        "tumbles": 0,
        "cells_cleared": [],
        "orphan_clears": 0,
        "next_cluster_wins": 0,
        "chain_lengths": [],
    }

    for sim in range(sims):
        state = GameState(config)
        state.betmode = "base"
        state.criteria = "board_activation"
        state.setup_forced_medium_win()
        state.get_clusters_update_wins()
        if state.win_data.get("totalWin", 0) <= 0:
            continue

        chain = 0
        while state.win_data.get("totalWin", 0) > 0 and chain < 50:
            chain += 1
            win_positions = {
                (pos["reel"], pos["row"])
                for win in state.win_data.get("wins", [])
                for pos in win.get("positions", [])
            }
            cleared = count_exploded_cells(state)
            stats["cells_cleared"].append(cleared)
            stats["orphan_clears"] += max(0, cleared - len(win_positions))

            state.tumble_board()
            state.prepare_landed_specials()

            clusters = Cluster.get_clusters(state.board, "wild")
            has_pay_cluster = False
            for sym, cluster_list in clusters.items():
                if sym not in config.paying_symbols:
                    continue
                for cluster in cluster_list:
                    if len(cluster) >= 5 and (len(cluster), sym) in config.paytable:
                        has_pay_cluster = True
                        break
                if has_pay_cluster:
                    break
            if has_pay_cluster:
                stats["next_cluster_wins"] += 1

            stats["tumbles"] += 1
            state.get_clusters_update_wins()

        stats["chain_lengths"].append(chain)

    return stats


def run_mode_rtp_spot(mode="base", sims=1000):
    config = GameConfig()
    payouts = []
    chains = []

    for sim in range(sims):
        state = GameState(config)
        state.betmode = mode
        state.criteria = "basegame" if mode in ("base", "base_ante") else "freegame"
        state.run_spin(sim)
        payouts.append(state.final_win)
        tumbles = sum(1 for event in state.book.events if event.get("type") == "tumbleBoard")
        chains.append(tumbles)

    rtp = sum(payouts) / sims if sims else 0
    avg_chain = sum(chains) / len(chains) if chains else 0
    return rtp, avg_chain, max(chains) if chains else 0


def pct(num, den):
    return 0 if den == 0 else round(100 * num / den, 1)


def avg(values):
    return 0 if not values else round(sum(values) / len(values), 2)


def main():
    print("stress_super_cascade: forced medium-win clear metrics")
    stats = run_super_cascade_stress(500)
    print(f"  tumbles measured: {stats['tumbles']}")
    print(f"  avg cells cleared per tumble: {avg(stats['cells_cleared'])}")
    print(f"  orphan super-clears (beyond win positions): {stats['orphan_clears']}")
    print(f"  post-tumble paying clusters (5+): {pct(stats['next_cluster_wins'], stats['tumbles'])}%")
    if stats["chain_lengths"]:
        print(f"  avg tumble chain length: {avg(stats['chain_lengths'])}")
        print(f"  chain length histogram: {dict(Counter(stats['chain_lengths']))}")

    print("stress_super_cascade: RTP spot-check (1000 sims per mode)")
    for mode in ("base", "base_ante", "bonus_see", "bonus_hear"):
        rtp, avg_chain, max_chain = run_mode_rtp_spot(mode, 1000)
        print(f"  {mode}: RTP proxy={rtp:.4f}, avg tumbles={avg_chain:.2f}, max={max_chain}")
    print("stress_super_cascade: done")


if __name__ == "__main__":
    main()
