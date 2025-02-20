from copy import copy, deepcopy
from src.events.events import *

APPLY_TUMBLE_MULTIPLIER = "applyMultiplierToTumble"
UPDATE_GRID = "updateGrid"


def applyMutToTumbleWinEvent(gamestate):
    event = {
        "index": len(gamestate.book["events"]),
        "type": APPLY_TUMBLE_MULTIPLIER,
        "amount": int(round(min(gamestate.running_bet_win, gamestate.config.wincap) * 100, 0)),
        "meta": {"baseAmount": gamestate.tumble_win, "tumbleMultiplier": gamestate.globalMult},
    }
    gamestate.book["events"] += [deepcopy(event)]


def updateGridMultiplierEvent(gamestate):
    event = {
        "index": len(gamestate.book["events"]),
        "type": UPDATE_GRID,
        "gridMultipliers": deepcopy(gamestate.position_multipliers),
    }
    gamestate.book["events"] += [deepcopy(event)]
