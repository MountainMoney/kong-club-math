"""Cluster payout calculations for Jul 2 Le Bandit Phase A."""

from __future__ import annotations

from src.calculations.cluster import Cluster
from src.executables.executables import Executables

from game_cluster import GameCluster


class GameCalculations(Executables):
    """Pay each cluster the plain paytable. Tiles do not multiply the win."""

    def cluster_base_payout(self, cluster) -> float:
        size = GameCluster.paytable_size(cluster.size)
        return self.config.paytable[(size, cluster.symbol)]

    def cluster_monkey_multiplier(self, cluster) -> int:
        return 1

    def evaluate_clusters(self, winning_clusters) -> dict:
        return_data = {"totalWin": 0.0, "wins": []}
        for cluster in winning_clusters:
            base_payout = self.cluster_base_payout(cluster)
            monkey_mult = self.cluster_monkey_multiplier(cluster)
            payout = base_payout * monkey_mult
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
                        "clusterMult": 1,
                        "monkeyMult": monkey_mult,
                        "winWithoutMult": base_payout,
                        "overlay": {"reel": overlay[0], "row": overlay[1]},
                    },
                }
            )
        return return_data
