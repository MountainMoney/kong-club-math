"""Ways wins executables/calculations."""

from src.calculations.board import Board
from src.config.config import Config
from src.wins.multiplier_strategy import apply_mult
from collections import defaultdict


def get_ways_data(config: Config, board: Board, wild_key: str = "wild"):
    """Ways calculation with possibility for global multiplier application."""
    return_data = {
        "totalWin": 0,
        "wins": [],
    }
    potential_wins = defaultdict()
    wilds = [[] for _ in range(len(board))]
    for reel, _ in enumerate(board):
        for row, _ in enumerate(board[reel]):
            sym = board[reel][row]
            if reel == 0 and sym.name not in potential_wins:
                potential_wins[sym.name] = [[] for _ in range(len(board))]
                potential_wins[sym.name][0] = [{"reel": reel, "row": row}]
            elif sym.name in potential_wins:
                potential_wins[sym.name][reel].append({"reel": reel, "row": row})

            if sym.name in config.special_symbols[wild_key]:
                wilds[reel].append({"reel": reel, "row": row})

    for symbol in potential_wins:
        kind, ways, cumulative_sym_mult = 0, 1, 0
        for reel, _ in enumerate(potential_wins[symbol]):
            if len(potential_wins[symbol][reel]) > 0 or len(wilds[reel]) > 0:
                kind += 1
                mult_enhance = 0
                # Note that here multipliers on subsequent reels multiplier (not add, like in lines games)
                for s in potential_wins[symbol][reel]:
                    if (
                        board[s["reel"]][s["row"]].check_attribute("multiplier")
                        and board[s["reel"]][s["row"]].get_attribute("multiplier") > 1
                    ):
                        mult_enhance += board[s["reel"]][s["row"]].get_attribute("multiplier")
                for s in wilds[reel]:
                    if (
                        board[s["reel"]][s["row"]].check_attribute("multiplier")
                        and board[s["reel"]][s["row"]].get_attribute("multiplier") > 1
                    ):
                        mult_enhance += board[s["reel"]][s["row"]].get_attribute("multiplier")

                ways *= len(potential_wins[symbol][reel]) + len(wilds[reel]) + mult_enhance
                cumulative_sym_mult += mult_enhance
            else:
                break

        if (kind, symbol) in config.paytable:
            positions = []
            for reel in range(kind):
                for pos in potential_wins[symbol][reel]:
                    positions += [pos]
                for pos in wilds[reel]:
                    positions += [pos]

            win = config.paytable[kind, symbol] * ways
            win_amt, multiplier = apply_mult(board=board, strategy="global", win_amount=win)
            return_data["wins"] += [
                {
                    "symbol": symbol,
                    "kind": kind,
                    "win": win_amt,
                    "positions": positions,
                    "meta": {
                        "ways": ways,
                        "globalMult": multiplier,
                        "winWithoutMult": win,
                        "symbolMult": cumulative_sym_mult,
                    },
                }
            ]
            return_data["totalWin"] += win
            # if record_wins:
            #     self.record(
            #         {
            #             "kind": kind,
            #             "symbol": symbol,
            #             "ways": ways,
            #             "gametype": self.gametype,
            #         }
            #     )

    return return_data
