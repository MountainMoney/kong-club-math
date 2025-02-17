"""Defines reusable events"""

from copy import deepcopy
from src.events.event_constants import *


def json_ready_sym(symbol: object, special_attributes: list = None):
    """Converts a symbol to dictionary/JSON format."""
    assert special_attributes is not None
    print_sym = {"name": symbol.name}
    attrs = vars(symbol)
    for key, val in attrs.items():
        if key in special_attributes and symbol.get_attribute(key) != False:
            print_sym[key] = val
    return print_sym


def reveal_event(gamestate):
    """Display the initial board drawn from reelstrips."""
    board_client = []
    special_attributes = list(gamestate.config.special_symbols.keys())
    for reel, _ in enumerate(gamestate.board):
        board_client.append([])
        for row in range(len(gamestate.board[reel])):
            board_client[reel].append(json_ready_sym(gamestate.board[reel][row], special_attributes))

    if gamestate.config.include_padding:
        for reel, _ in enumerate(board_client):
            board_client[reel] = [json_ready_sym(gamestate.top_symbols[reel], special_attributes)] + board_client[
                reel
            ]
            board_client[reel].append(json_ready_sym(gamestate.bottom_symbols[reel], special_attributes))

    event = {
        "index": len(gamestate.book["events"]),
        "type": REVEAL,
        "board": board_client,
        "paddingPositions": gamestate.reel_positions,
        "gameType": gamestate.gametype,
        "anticipation": gamestate.anticipation,
    }

    gamestate.book["events"] += [deepcopy(event)]


def fs_trigger_event(
    gamestate,
    include_padding_index=True,
    basegame_trigger: bool = None,
    freegame_trigger: bool = None,
):
    """Triggers feature game from the basegame."""
    assert basegame_trigger != freegame_trigger, "must set either basegame_trigger or freeSpinTrigger to = True"
    event = {}
    scatter_positions = []
    for reel, _ in enumerate(gamestate.special_syms_on_board["scatter"]):
        scatter_positions.append(gamestate.special_syms_on_board["scatter"][reel])
    if include_padding_index:
        for pos in scatter_positions:
            pos["row"] += 1

    if basegame_trigger:
        event = {
            "index": len(gamestate.book["events"]),
            "type": FREESPINTRIGGER,
            "totalFs": gamestate.tot_fs,
            "positions": scatter_positions,
        }
    elif freegame_trigger:
        event = {
            "index": len(gamestate.book["events"]),
            "type": FREESPINRETRIGGER,
            "totalFs": gamestate.tot_fs,
            "positions": scatter_positions,
        }

    assert gamestate.tot_fs > 0, "total freespins (gamestate.tot_fs) must be >0"
    gamestate.book["events"] += [deepcopy(event)]


def set_win_event(gamestate, winlevel_key: str = "standard"):
    """Used for updating cumulative win ticker (for a single outcome)."""
    if not gamestate.wincap_triggered:
        event = {
            "index": len(gamestate.book["events"]),
            "type": SET_WIN,
            "amount": int(
                min(
                    round(gamestate.win_manager.spin_win * 100, 0),
                    gamestate.config.wincap * 100,
                )
            ),
            "winLevel": gamestate.config.get_win_level(gamestate.win_manager.spin_win, winlevel_key),
        }
        gamestate.book["events"] += [event]


def set_total_event(gamestate):
    """Updates win amount for a betting round (including cumulative wins across multiple freespin wins)."""
    event = {
        "index": len(gamestate.book["events"]),
        "type": SET_TOTAL_WIN,
        "amount": int(
            round(
                min(gamestate.win_manager.running_bet_win, gamestate.config.wincap) * 100,
                0,
            )
        ),
    }
    gamestate.book["events"] += [event]


def set_tumble_event(gamestate):
    """Update banner indicating wins from successive tumbles."""
    event = {
        "index": len(gamestate.book["events"]),
        "type": SET_TUMBLE_WIN,
        "amount": int(round(min(gamestate.tumble_win, gamestate.config.wincap) * 100)),
    }
    gamestate.book["events"] += [event]


def wincap_event(gamestate):
    """Emit to indicate spin actions should stop due to maximum win amount achieved."""
    event = {
        "index": len(gamestate.book["events"]),
        "type": WINCAP,
        "amount": int(
            round(
                min(gamestate.win_manager.running_bet_win, gamestate.config.wincap) * 100,
                0,
            )
        ),
    }
    gamestate.book["events"] += [event]


def win_info_event(gamestate, include_padding_index=True):
    """
    include_padding_index: starts winning-symbol positions at row=1, to account for top/bottom symbol inclusion in board
    """
    win_data_copy = {}
    a = id(gamestate.win_data["wins"])
    win_data_copy["wins"] = deepcopy(gamestate.win_data["wins"])
    b = id(win_data_copy["wins"])
    if a == b:
        print("copy error")
    for idx, w in enumerate(win_data_copy["wins"]):
        if include_padding_index:
            new_positions = []
            for p in w["positions"]:
                new_positions.append({"reel": p["reel"], "row": p["row"] + 1})
        else:
            new_positions = w["positions"]

        win_data_copy["wins"][idx]["win"] = int(
            round(min(win_data_copy["wins"][idx]["win"], gamestate.config.wincap) * 100, 0)
        )
        win_data_copy["wins"][idx]["positions"] = new_positions
        if "meta" in win_data_copy["wins"][idx]["positions"]:
            win_data_copy["wins"][idx]["meta"] = win_data_copy["wins"][idx]["meta"]
            win_data_copy["wins"][idx]["meta"]["winWithoutMult"] = int(
                round(
                    min(
                        win_data_copy["wins"][idx]["meta"]["winWithoutMult"],
                        gamestate.config.wincap,
                    )
                    * 100,
                    0,
                )
            )
            if "overlay" in win_data_copy["wins"][idx]["meta"] and include_padding_index:
                win_data_copy["wins"][idx]["meta"]["overlay"]["row"] += 1

    dict_data = {
        "index": len(gamestate.book["events"]),
        "type": WIN_DATA,
        "totalWin": int(round(min(gamestate.win_data["totalWin"], gamestate.config.wincap) * 100, 0)),
        "wins": win_data_copy["wins"],
    }
    gamestate.book["events"] += [deepcopy(dict_data)]


def update_tumble_win_event(gamestate):
    """Update a banner to record successive tumble wins."""
    event = {
        "index": len(gamestate.book["events"]),
        "type": UPDATE_TUMBLE_WIN,
        "amount": int(round(min(gamestate.win_manager.spin_win, gamestate.config.wincap) * 100, 0)),
    }
    gamestate.book["events"] += [event]


def update_freespin_event(gamestate):
    """Update the current spin number and total freespins"""
    event = {
        "index": len(gamestate.book["events"]),
        "type": UPDATE_FS,
        "amount": int(gamestate.fs),
        "total": int(gamestate.tot_fs),
    }
    gamestate.book["events"] += [event]


def freespin_end_event(gamestate, winlevel_key="endFeature"):
    """End of feature trigger."""
    event = {
        "index": len(gamestate.book["events"]),
        "type": FREE_SPIN_END,
        "amount": int(min(gamestate.win_manager.freegame_wins, gamestate.config.wincap) * 100),
        "winLevel": gamestate.config.get_win_level(gamestate.win_manager.freegame_wins, winlevel_key),
    }
    gamestate.book["events"] += [event]


def final_win_event(gamestate):
    """Assigns final payout multiplier for a simulation."""
    event = {
        "index": len(gamestate.book["events"]),
        "type": FINAL_WIN,
        "amount": int(round(min(gamestate.final_win, gamestate.config.wincap) * 100, 0)),
    }
    gamestate.book["events"] += [event]


def update_global_mult_event(gamestate):
    """Increment global multiplier value."""
    event = {
        "index": len(gamestate.book["events"]),
        "type": UPDATE_GLOBAL_MULT,
        "globalMult": int(gamestate.global_multiplier),
    }

    gamestate.book["events"] += [deepcopy(event)]


def tumble_board_event(gamestate):
    """States the symbol positions removed from a board during tumeble, and which new symbols should take their place."""
    special_attributes = list(gamestate.config.special_symbols.keys())

    if gamestate.config.include_padding:
        exploding = []
        for sym in gamestate.exploding_symbols:
            exploding.append({"reel": sym["reel"], "row": sym["row"] + 1})
    else:
        exploding = gamestate.exploding_symbols

    exploding = sorted(exploding, key=lambda x: x["reel"])

    new_symbols = [[] for _ in range(gamestate.config.num_reels)]
    count = 0
    for r, _ in enumerate(gamestate.new_symbols_from_tumble):
        if len(gamestate.new_symbols_from_tumble[r]) > 0:
            new_symbols[r] = [json_ready_sym(s, special_attributes) for s in gamestate.new_symbols_from_tumble[r]]

    gamestate.book["events"] += deepcopy(
        [
            {
                "index": len(gamestate.book["events"]),
                "type": TUMBLE_BOARD,
                "newSymbols": new_symbols,
                "explodingSymbols": exploding,
            }
        ]
    )
