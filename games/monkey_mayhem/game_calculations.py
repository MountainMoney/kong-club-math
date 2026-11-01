"""Cluster payout calculations for Jul 2 Le Bandit Phase A."""

from __future__ import annotations

from src.calculations.cluster import Cluster
from src.executables.executables import Executables

from game_cluster import GameCluster


class GameCalculations(Executables):
    """Pay each BFS cluster independently using sum of tile multipliers."""

    def cluster_base_payout(self, cluster) -> float:
        size = GameCluster.paytable_size(cluster.size)
        return self.config.paytable[(size, cluster.symbol)]

    def cluster_monkey_multiplier(self, cluster) -> int:
        return 1

    def cluster_tile_multiplier_sum(self, cluster) -> float:
        """Jul 2: naked cluster pays table ×1; each active tile adds (mult - 1).

        Spec: payout = paytable[size] × bet, then for each active Level-Up tile
        on the cluster: payout += base × (tileMultiplier - 1).
        Equivalent factor: 1 + Σ(mult - 1) over lit cells.

        PEAK gold is chrome + coin faces only.
        Cluster pay uses connection ranks (start 0, +1 per connected tumble).
        Feature Spin pays tile levels like base (no bronze seed).
        """
        levels = self.tile_levels
        if getattr(self, "betmode", None) == "peak_spin":
            levels = getattr(self, "peak_connection_levels", self.tile_levels)
        factor = 1.0
        for reel, row in cluster.positions:
            level = levels[reel][row]
            if level > 0:
                mult = self.level_to_multiplier(level)
                factor += max(0, mult - 1)
        return factor

    def evaluate_clusters(self, winning_clusters) -> dict:
        return_data = {"totalWin": 0.0, "wins": []}
        for cluster in winning_clusters:
            base_payout = self.cluster_base_payout(cluster)
            monkey_mult = self.cluster_monkey_multiplier(cluster)
            tile_sum = self.cluster_tile_multiplier_sum(cluster)
            payout = base_payout * tile_sum * monkey_mult
            return_data["totalWin"] += payout

            positions = [{"reel": reel, "row": row} for reel, row in cluster.positions]
            overlay = Cluster.get_central_cluster_position(positions)
            return_data["wins"].append(
                {
                    "symbol": cluster.symbol,
                    "clusterSize": cluster.size,
                    "win": payout,
                    "positions": positions,
                    "meta": {
                        "globalMult": 1,
                        "clusterMult": tile_sum,
                        "monkeyMult": monkey_mult,
                        "winWithoutMult": base_payout,
                        "overlay": {"reel": overlay[0], "row": overlay[1]},
                    },
                }
            )
        return return_data
