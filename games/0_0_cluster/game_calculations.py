from src.executables.executables import Executables


class GameCalculations(Executables):
    """
    This function will override the evaluate_clusters() function in cluster.py
    This is to account for the grid multiplier in winning positions.
    """

    def evaluate_clusters(
        self,
        clusters: dict,
        multiplier_key: str = "multiplier",
        return_data: dict = {"totalWin": 0, "wins": []},
    ) -> type:
        """Find all clusters on the active board - modified from the function in calculations/clusters by
        considering the current multiplier in the position_multipliers array."""
        exploding_symbols = []
        total_win = 0
        for sym in clusters:
            for cluster in clusters[sym]:
                syms_in_cluster = len(cluster)
                if (syms_in_cluster, sym) in self.config.paytable:
                    # For this specific game there are no multipliers on the symbols
                    # though we extract the multiplier from the board grid-positions
                    cluster_mult = 0
                    for positions in cluster:
                        if self.position_multipliers[positions[0]][positions[1]] > 1:
                            cluster_mult += self.position_multipliers[positions[0]][positions[1]]
                    cluster_mult = max(cluster_mult, 1)

                    json_positions = [{"reel": p[0], "row": p[1]} for p in cluster]
                    sym_win = self.config.paytable[(syms_in_cluster, sym)]
                    symwin_mult = sym_win * cluster_mult
                    symwin_mult, global_mult = self.apply_mult(self.board, "global", symwin_mult, json_positions)
                    total_win += symwin_mult

                    overlay_position = self.get_central_cluster_position(json_positions)
                    return_data["wins"] += [
                        {
                            "symbol": sym,
                            "clusterSize": syms_in_cluster,
                            "win": symwin_mult,
                            "positions": json_positions,
                            "meta": {
                                "globalMult": global_mult,
                                "clusterMult": cluster_mult,
                                "winWithoutMult": sym_win,
                                "overlay": {"reel": overlay_position[0], "row": overlay_position[1]},
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
