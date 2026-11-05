"""BFS flood-fill cluster detection for Jul 2 Le Bandit Phase A."""

from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass


ORTHOGONAL_DELTAS = ((1, 0), (-1, 0), (0, 1), (0, -1))
MIN_WINNING_CLUSTER_SIZE = 5


@dataclass(frozen=True)
class ClusterConnection:
    symbol: str
    positions: tuple[tuple[int, int], ...]
    wild_positions: tuple[tuple[int, int], ...] = ()

    @property
    def size(self) -> int:
        return len(self.positions)


class GameCluster:
    """Find all orthogonal 5+ clusters. Diagonals never connect."""

    @staticmethod
    def _in_bounds(board, reel: int, row: int) -> bool:
        return 0 <= reel < len(board) and 0 <= row < len(board[reel])

    @staticmethod
    def _is_wild_for_cluster(sym, config) -> bool:
        if sym.name in {config.scatter_symbol, *config.coin_symbols}:
            return False
        # Phase A: MW only (SEE/HEAR parked as non-wilds).
        return sym.name == config.standard_wild

    @staticmethod
    def _matches_symbol(sym, target_symbol: str, config) -> bool:
        if sym.name == target_symbol:
            return True
        return GameCluster._is_wild_for_cluster(sym, config)

    @staticmethod
    def find_symbol_clusters(board, config, target_symbol: str) -> list[ClusterConnection]:
        visited: set[tuple[int, int]] = set()
        clusters: list[ClusterConnection] = []

        for reel in range(len(board)):
            for row in range(len(board[reel])):
                start = board[reel][row]
                if start.name != target_symbol or (reel, row) in visited:
                    continue

                queue: deque[tuple[int, int]] = deque([(reel, row)])
                component: set[tuple[int, int]] = set()
                wilds: set[tuple[int, int]] = set()
                has_natural = False

                while queue:
                    r, c = queue.popleft()
                    if (r, c) in component:
                        continue
                    if not GameCluster._in_bounds(board, r, c):
                        continue
                    sym = board[r][c]
                    if not GameCluster._matches_symbol(sym, target_symbol, config):
                        continue

                    component.add((r, c))
                    if sym.name == target_symbol:
                        has_natural = True
                    else:
                        wilds.add((r, c))

                    for dr, dc in ORTHOGONAL_DELTAS:
                        queue.append((r + dr, c + dc))

                natural_positions = {
                    pos for pos in component if board[pos[0]][pos[1]].name == target_symbol
                }
                visited.update(natural_positions)
                if has_natural:
                    clusters.append(
                        ClusterConnection(
                            target_symbol,
                            tuple(sorted(component)),
                            tuple(sorted(wilds)),
                        )
                    )

        return clusters

    @staticmethod
    def find_winning_clusters(board, config) -> list[ClusterConnection]:
        winning: list[ClusterConnection] = []
        seen: set[tuple[str, tuple[tuple[int, int], ...]]] = set()
        for symbol in config.paying_symbols:
            for cluster in GameCluster.find_symbol_clusters(board, config, symbol):
                if cluster.size < MIN_WINNING_CLUSTER_SIZE:
                    continue
                key = (cluster.symbol, cluster.positions)
                if key in seen:
                    continue
                seen.add(key)
                winning.append(cluster)
        return winning

    @staticmethod
    def paytable_size(size: int) -> int:
        """Cluster pays are per size, minimum 5, with no top band."""
        return max(5, int(size))

    @staticmethod
    def format_cluster_log(cluster: ClusterConnection) -> str:
        positions = ", ".join(f"[{reel},{row}]" for reel, row in cluster.positions)
        return f"Cluster found: {cluster.symbol} size {cluster.size} at positions {positions}"

    @staticmethod
    def log_winning_clusters(clusters: list[ClusterConnection]) -> None:
        for cluster in clusters:
            spin_trace(GameCluster.format_cluster_log(cluster))


def spin_trace(message: str) -> None:
    """Per-spin debug. Off during bulk sims; set MM_SPIN_TRACE=1 to print."""
    if os.environ.get("MM_SPIN_TRACE") == "1":
        print(message)
