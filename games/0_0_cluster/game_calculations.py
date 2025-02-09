import sys

sys.path.append("./")
from src.executables.executables import Executables


class GameCalculations(Executables):
    """
    This fuction will override the evaluate_clusters() function in cluster.py
    This is to account for the grid multiplier in winning positions.
    """

    def evaluate_clusters(
        self,
        clusters: dict,
        multiplier_key: str = "multiplier",
        return_data: dict = {"totalWin": 0, "wins": []},
    ) -> type:
        exploding_symbols = []
        total_win = 0
        for sym in clusters:
            for cluster in clusters[sym]:
                numSymsInCluster = len(cluster)
                if (numSymsInCluster, sym) in self.config.paytable:
                    # For this specific game there are no multipliers on the symbols
                    # though we extract the multiplier from the board grid-positions
                    cluster_mult = 0
                    for positions in cluster:
                        if self.position_multipliers[positions[0]][positions[1]] > 1:
                            cluster_mult += self.position_multipliers[positions[0]][positions[1]]

                    cluster_mult = max(cluster_mult, 1)
                    symwin = self.config.paytable[(numSymsInCluster, sym)]
                    symwin_mult = symwin * cluster_mult * self.global_multiplier
                    total_win += symwin_mult
                    jsonPositions = [{"reel": p[0], "row": p[1]} for p in cluster]
                    return_data["wins"] += [
                        {
                            "symbol": sym,
                            "clusterSize": numSymsInCluster,
                            "win": symwin_mult,
                            "positions": jsonPositions,
                            "meta": {
                                "multiplier": cluster_mult,
                                "winWithoutMult": symwin,
                                "globalMult": self.global_multiplier,
                                "clusterMultiplier": cluster_mult,
                            },
                        }
                    ]

                    for positions in cluster:
                        self.board[positions[0]][positions[1]].explode = True
                        if {
                            "reel": positions[0],
                            "row": positions[1],
                        } not in exploding_symbols:
                            exploding_symbols.append({"reel": positions[0], "row": positions[1]})

        return return_data, exploding_symbols, total_win
