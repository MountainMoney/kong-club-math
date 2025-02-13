"""Handle win calculation for pay-anywhere games"""

from typing import List, Dict
from collections import defaultdict
from src.wins.multiplier_strategy import MultiplierStrategy


class ScatterWins(MultiplierStrategy):
    """
    Scatter (pay-anywhere) class for handling wins win calculations and recording.
    """

    def get_central_scatter_position(self, rows_for_overlay: List, winning_positions: List[Dict]) -> tuple:
        """Return position on screen to display win amount."""
        closest_to_middle = 100
        reel_to_overlay = 0
        row_to_overlay = 0
        for pos in winning_positions:
            reel, row = pos["reel"], pos["row"]
            dist_from_middle = (reel - self.config.num_reels / 2) ** 2 + (
                row - self.config.num_rows[reel] / 2
            ) ** 2
            if (
                dist_from_middle < closest_to_middle
                and row not in rows_for_overlay
                and len(rows_for_overlay) < len(self.board[reel])
            ):
                closest_to_middle = dist_from_middle
                reel_to_overlay = reel
                row_to_overlay = row

        # assert all([row_to_overlay >= 0, reel_to_overlay >= 0])
        return (reel_to_overlay, row_to_overlay)

    def record_scatter_wins(
        self, num_winning_syms: int, symbol: int, total_multiplier: int, gametype: str
    ) -> None:
        """Force-file description key generator."""
        self.record(
            {
                "win_size": num_winning_syms,
                "symbol": symbol,
                "totalMult": total_multiplier,
                "gametype": gametype,
            }
        )

    def get_scatterpay_wins(
        self,
        record_wins: bool = True,
        wild_key: str = "wild",
        multiplier_key: str = "multiplier",
    ) -> dict:
        """Return win data for all paying symbols"""
        return_data = {
            "totalWin": 0,
            "wins": [],
        }
        exploding_symbols = []
        rows_for_overlay = []
        symbols_on_board = defaultdict(list)
        wild_positions = []
        total_win = 0.0
        for reel_idx, reel in enumerate(self.board):
            for row_idx, symbol in enumerate(reel):
                if symbol.name not in self.config.special_symbols[wild_key]:
                    symbols_on_board[symbol.name].append({"reel": reel_idx, "row": row_idx})
                else:
                    wild_positions.append({"reel": reel_idx, "row": row_idx})

        # Update all symbol positions with wilds, as this symbol is shared
        for sym in symbols_on_board:
            if len(wild_positions) > 0:
                symbols_on_board[sym].append(wild_positions)
            win_size = len(symbols_on_board[sym])
            if (win_size, sym) in self.config.paytable:
                symbol_mult = 0
                for p in symbols_on_board[sym]:
                    if self.board[p["reel"]][p["row"]].check_attribute(multiplier_key):
                        symbol_mult += self.board[p["reel"]][p["row"]].get_attribute(multiplier_key)
                    symbol_mult = max(symbol_mult, 1)

                    self.board[p["reel"]][p["row"]].assign_attribute({"explode": True})
                    # Account for special symbols, such as wilds which can apply to multiple groups
                    if p not in exploding_symbols:
                        exploding_symbols.append(p)

                if record_wins:
                    self.record_scatter_wins(
                        win_size,
                        sym,
                        symbol_mult * self.global_multiplier,
                        self.gametype,
                    )
                overlay_position = self.get_central_scatter_position(rows_for_overlay, symbols_on_board[sym])
                rows_for_overlay.append(overlay_position[1])
                symbol_win_data = {
                    "symbol": sym,
                    "win": self.config.paytable[(win_size, sym)] * self.global_multiplier * symbol_mult,
                    "positions": symbols_on_board[sym],
                    "meta": {
                        "globalMult": self.global_multiplier,
                        "clusterMult": symbol_mult,
                        "winWithoutMult": self.config.paytable[(win_size, sym)],
                        "overlay": {
                            "reel": overlay_position[0],
                            "row": overlay_position[1],
                        },
                    },
                }
                total_win += symbol_win_data["win"]
                return_data["wins"].append(symbol_win_data)

        return_data["totalWin"] = total_win
        self.win_manager.tumble_win = total_win
        self.exploding_symbols = exploding_symbols

        return return_data
