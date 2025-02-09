from collections import defaultdict
from abc import ABC, abstractmethod
from src.wins.multiplier_strategy import MultiplierStrategy


class ClusterWins(MultiplierStrategy):
    """
    BFS cluster finding algorithm and win-evaluation.
    """

    def get_neighbours(self, reel, row, local_checked) -> list:
        """All neighbouring symbols within board range."""
        neighbours = []
        if reel > 0:
            if (reel - 1, row) not in local_checked:
                neighbours += [(reel - 1, row)]
                local_checked += [(reel - 1, row)]
        if reel < len(self.board) - 1:
            if (reel + 1, row) not in local_checked:
                neighbours += [(reel + 1, row)]
                local_checked += [(reel + 1, row)]
        if row > 0:
            if (reel, row - 1) not in local_checked:
                neighbours += [(reel, row - 1)]
                local_checked += [(reel, row - 1)]
        if row < len(self.board[reel]) - 1:
            if (reel, row + 1) not in local_checked:
                neighbours += [(reel, row + 1)]
                local_checked += [(reel, row + 1)]
        return neighbours

    def in_cluster(self, reel: int, row: int, og_symbol: str, wild_key: str = "wild") -> bool:
        """Checks if a symbol (including wilds) match cluster type."""
        if self.board[reel][row].check_attribute(wild_key) or og_symbol == self.board[reel][row].name:
            return True

    def check_all_neighbours(
        self,
        already_checked: list,
        local_checked: list,
        potential_cluster: list,
        reel,
        row,
        og_symbol: str,
        wild_key: str = "wild",
    ):
        """Recursively check neights for like-symbols."""
        neighbours = self.get_neighbours(reel, row, local_checked)
        for reel_, row_ in neighbours:
            if self.in_cluster(reel_, row_, og_symbol, wild_key):
                potential_cluster += [(reel_, row_)]
                already_checked += [(reel_, row_)]
                self.check_all_neighbours(
                    already_checked,
                    local_checked,
                    potential_cluster,
                    reel_,
                    row_,
                    og_symbol,
                    wild_key,
                )

    def get_clusters(self, wild_key: str = "wild") -> dict:
        """Return all symbol clusters of size >= 1."""
        already_checked = []
        clusters = defaultdict(list)
        for reel, _ in enumerate(self.board):
            for row, _ in enumerate(self.board[reel]):
                if not (self.board[reel][row].special) and (reel, row) not in already_checked:
                    potential_cluster = [(reel, row)]
                    already_checked += [(reel, row)]
                    local_checked = [(reel, row)]
                    symbol = self.board[reel][row].name
                    self.check_all_neighbours(
                        already_checked,
                        local_checked,
                        potential_cluster,
                        reel,
                        row,
                        symbol,
                        wild_key,
                    )
                    clusters[symbol].append(potential_cluster)

        return clusters

    def evaluate_clusters(
        self,
        clusters: dict,
        multiplier_key: str = "multiplier",
        return_data: dict = {"totalWin": 0, "wins": []},
    ) -> type:
        """Eetermine payout amount from cluster, including symbol multiplier and global multiplier value."""
        exploding_symbols = []
        total_win = 0
        for sym in clusters:
            for cluster in clusters[sym]:
                numSymsInCluster = len(cluster)
                if (numSymsInCluster, sym) in self.config.paytable:
                    cluster_mult = 0
                    for positions in cluster:
                        if self.board[positions[0]][positions[1]].check_attribute(multiplier_key):
                            if int(self.board[positions[0]][positions[1]].get_attribute(multiplier_key)) > 0:
                                cluster_mult += self.board[positions[0]][positions[1]].get_attribute(
                                    multiplier_key
                                )
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

    def get_cluster_data(self, multiplier_key: str = "multiplier", wild_key: str = "wild") -> None:
        """Event-ready win information."""
        clusters = self.get_clusters(wild_key)
        return_data = {
            "totalWin": 0,
            "wins": [],
        }
        return_data, exploding_symbols, total_win = self.evaluate_clusters(clusters, multiplier_key, return_data)

        return_data["totalWin"] += total_win
        self.clusters = clusters
        self.win_manager.tumble_win = total_win
        self.exploding_symbols = exploding_symbols

        return return_data

    def recordClusterWins(self) -> None:
        """Force_for_rob win description keys."""
        for win in self.win_data["wins"]:
            self.record(
                {
                    "clusterSize": win["clusterSize"],
                    "symbol": win["symbol"],
                    "mult": win["meta"]["multiplier"],
                    "gametype": self.gametype,
                }
            )
