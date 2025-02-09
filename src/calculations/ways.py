from src.wins.multiplier_strategy import MultiplierStrategy
from collections import defaultdict


class WaysWins(MultiplierStrategy):
    """Ways wins execuatables/calculations."""

    def get_ways_data(self, wild_key: str = "wild", record_wins: bool = False):
        """Ways calculation with possibility for global multiplier application."""
        return_data = {
            "totalWin": 0,
            "wins": [],
        }
        potential_wins = defaultdict(str)
        wilds = [[] for _ in range(len(self.board))]
        for reel, _ in enumerate(self.board):
            for row, _ in enumerate(self.board[reel]):
                sym = self.board[reel][row].name
                if reel == 0:
                    potential_wins[sym.name] = [[] for _ in range(len(self.board))]
                    potential_wins[sym.name][0] = [{"reel": reel, "row": row}]
                else:
                    potential_wins[sym.name][reel].append({"reel": reel, "row": row})

                if sym.name in self.config.special_symbols[wild_key]:
                    wilds[reel].append({"reel": reel, "row": row})

        for symbol in potential_wins:
            kind, ways = 0, 1
            for reel, _ in enumerate(potential_wins[symbol]):
                if len(potential_wins[symbol][reel]) > 0 or len(wilds[reel]) > 0:
                    kind += 1
                    ways *= len(potential_wins[symbol][reel]) + len(wilds[reel])
                else:
                    break

            if (kind, symbol) in self.config.paytable:
                positions = []
                for reel in range(kind):
                    for pos in potential_wins[symbol][reel]:
                        positions += [pos]
                    for pos in wilds[reel]:
                        positions += [pos]

                win = self.config.paytable[kind, symbol] * ways
                win_amt, multiplier = self.apply_mult("global", win)
                return_data["wins"] += [
                    {
                        "symbol": symbol,
                        "kind": kind,
                        "win": win_amt,
                        "positions": positions,
                        "meta": {"ways": ways, "multiplier": multiplier},
                    }
                ]
                return_data["totalWin"] += win
                if record_wins:
                    self.record(
                        {
                            "kind": kind,
                            "symbol": symbol,
                            "ways": ways,
                            "gametype": self.gametype,
                        }
                    )

        return return_data
