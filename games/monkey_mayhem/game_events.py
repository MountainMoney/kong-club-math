"""Scratch Monkey Mayhem book events."""

from __future__ import annotations

from copy import deepcopy

from src.events.event_constants import EventConstants
from src.events.events import json_ready_sym


UPDATE_TILES = "updateLevelUpTiles"
PROGRESS_FILL = "progressFill"
BOARD_ACTIVATION = "boardActivation"
COIN_SEED = "coinSeed"
SCATTER_PAYOUT = "scatterPayout"
STICKY_WILDS = "stickyWilds"
MODE_STATE = "monkeyMayhemMode"


def update_tile_event(gamestate):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": UPDATE_TILES,
            "tileLevels": deepcopy(gamestate.tile_levels),
            "tileMultipliers": deepcopy(gamestate.position_multipliers),
            "gameType": gamestate.gametype,
            "mode": gamestate.betmode,
        }
    )


def progress_fill_event(gamestate):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": PROGRESS_FILL,
            "value": gamestate.progress_value,
            "threshold": gamestate.progress_threshold,
            "mode": gamestate.betmode,
            "activationCount": gamestate.progress_activation_count,
        }
    )


def board_activation_event(gamestate, payout, items, rounds=1):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": BOARD_ACTIVATION,
            "activationWin": int(round(min(payout, gamestate.config.wincap) * 100, 0)),
            "tileMultipliers": deepcopy(gamestate.position_multipliers),
            "tileLevels": deepcopy(gamestate.tile_levels),
            "coinFeature": {
                "totalPayout": round(payout, 2),
                "rounds": int(rounds),
                "items": deepcopy(items),
            },
        }
    )


def coin_seed_event(gamestate, seeds):
    if not seeds:
        return
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": COIN_SEED,
            "seeds": deepcopy(seeds),
            "tileLevels": deepcopy(gamestate.tile_levels),
            "tileMultipliers": deepcopy(gamestate.position_multipliers),
        }
    )


def scatter_payout_event(gamestate, count, payout):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": SCATTER_PAYOUT,
            "count": int(count),
            "amount": int(round(payout * 100, 0)),
            "positions": deepcopy(gamestate.special_syms_on_board.get("scatter", [])),
        }
    )


def sticky_wilds_event(gamestate):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": STICKY_WILDS,
            "positions": deepcopy(gamestate.sticky_wild_positions),
        }
    )


def mode_state_event(gamestate, state):
    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": MODE_STATE,
            "state": state,
            "mode": gamestate.betmode,
            "gameType": gamestate.gametype,
        }
    )


def tumble_board_event(gamestate):
    special_attributes = list(gamestate.config.special_symbols.keys())
    exploding = []
    for pos in getattr(gamestate, "removed_symbols", []):
        row = pos["row"] + 1 if gamestate.config.include_padding else pos["row"]
        exploding.append({"reel": pos["reel"], "row": row})
    exploding.sort(key=lambda pos: (pos["reel"], pos["row"]))

    new_symbols = [[] for _ in range(gamestate.config.num_reels)]
    for reel, symbols in enumerate(gamestate.new_symbols_from_tumble):
        new_symbols[reel] = [json_ready_sym(sym, special_attributes) for sym in symbols]

    result_board = []
    for reel, _ in enumerate(gamestate.board):
        column = [
            json_ready_sym(gamestate.board[reel][row], special_attributes)
            for row in range(len(gamestate.board[reel]))
        ]
        if gamestate.config.include_padding:
            column = [json_ready_sym(gamestate.top_symbols[reel], special_attributes)] + column
            column.append(json_ready_sym(gamestate.bottom_symbols[reel], special_attributes))
        result_board.append(column)

    gamestate.book.add_event(
        {
            "index": len(gamestate.book.events),
            "type": EventConstants.TUMBLE_BOARD.value,
            "newSymbols": new_symbols,
            "explodingSymbols": exploding,
            "resultBoard": result_board,
        }
    )
