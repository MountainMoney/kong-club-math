"""Evaluates and records winds for lines games."""

from typing import List, Dict
from src.calculations.board import Board
from src.wins.multiplier_strategy import MultiplierStrategy


class LineWins(MultiplierStrategy):
    """Primary win evaluation and recording."""

    def record_line_win(self, kind: int, symbol: str, mult: int, gametype: str) -> None:
        """Force file description for line-win."""
        self.record({"kind": kind, "symbol": symbol, "mult": mult, "gametype": gametype})

    def line_win_info(self, symbol: str, kind: int, win: float, positions: list, meta_data: dict) -> dict:
        """Construct line-win event key."""
        return {
            "symbol": symbol,
            "kind": kind,
            "win": win,
            "positions": positions,
            "meta": meta_data,
        }

    def get_lines(self, wild_key: str = "wild", wild_sym: str = "W", multiplier_method: str = "symbol"):
        """More efficient lines calculation"""
        return_data = {
            "totalWin": 0,
            "wins": [],
        }

        for line_index in self.config.pay_lines.keys():
            line = self.config.pay_lines[line_index]
            first_sym = self.board[0][line[0]]
            finished_wild_win = False if first_sym.check_attribute(wild_key) else True
            first_non_wild = first_sym if finished_wild_win else None
            potential_line = [first_sym]

            wild_matches = 0 * (finished_wild_win) + 1 * (not (finished_wild_win))
            matches = 1 * (finished_wild_win) + 0 * (not (finished_wild_win))
            base_win, wild_win = 0, 0

            for reel in range(1, len(line)):
                sym = self.board[reel][line[reel]]
                if finished_wild_win:
                    if sym.name == first_non_wild.name or sym.check_attribute(wild_key):
                        matches += 1
                    else:
                        break
                else:
                    if sym.check_attribute(wild_key) and first_non_wild is None:
                        wild_matches += 1
                    elif first_non_wild is None:
                        first_non_wild = sym
                        matches += 1
                        finished_wild_win = True
                    else:
                        break
                potential_line.append(sym)

            if (wild_matches, wild_sym) in self.config.paytable:
                wild_win = self.config.paytable[(wild_matches, wild_sym)]
            if first_non_wild is not None:
                if (wild_matches + matches, first_non_wild.name) in self.config.paytable:
                    base_win = self.config.paytable[(wild_matches + matches, first_non_wild.name)]

            if base_win > 0 or wild_win > 0:
                if wild_win > base_win:
                    positions = [{"reel": idx, "row": line[idx]} for idx in range(0, wild_matches)]
                    line_win, applied_mult = self.apply_mult(multiplier_method, wild_win, positions)
                    win_dict = self.line_win_info(
                        potential_line[0].name,
                        wild_matches,
                        line_win,
                        positions,
                        {
                            "lineIndex": line_index,
                            "multiplier": applied_mult,
                            "winWithoutMult": wild_win,
                            "globalMult": self.global_multiplier,
                            "lineMultiplier": applied_mult / self.global_multiplier,
                        },
                    )
                else:
                    positions = [{"reel": idx, "row": line[idx]} for idx in range(0, matches + wild_matches)]
                    line_win, applied_mult = self.apply_mult(multiplier_method, base_win, positions)
                    win_dict = self.line_win_info(
                        first_non_wild.name,
                        matches + wild_matches,
                        line_win,
                        positions,
                        {
                            "lineIndex": line_index,
                            "multiplier": applied_mult,
                            "winWithoutMult": base_win,
                            "globalMult": self.global_multiplier,
                            "lineMultiplier": applied_mult / self.global_multiplier,
                        },
                    )

                self.record_line_win(
                    wild_matches + matches,
                    first_non_wild.name,
                    applied_mult,
                    self.gametype,
                )

                return_data["totalWin"] += line_win
                return_data["wins"].append(win_dict)

        return return_data
