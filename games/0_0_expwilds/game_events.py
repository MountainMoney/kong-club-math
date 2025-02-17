"""Events specific to new and updating expanding wild symbols."""

from copy import deepcopy

NEW_EXP_WILDS = "newExpandingWilds"
UPDATE_EXP_WILDS = "updateExpandingWilds"
NEW_STICKY_SYMS = "newStickySymbols"
WIN_DATA = "winInfo"


def new_expanding_wild_event(gamestate, new_exp_wilds: list) -> None:
    """Passed after reveal event"""
    if gamestate.config.include_padding:
        for ew in new_exp_wilds:
            ew["row"] += 1

    dic = {"index": len(gamestate.book["events"]), "type": NEW_EXP_WILDS, "newWilds": new_exp_wilds}
    gamestate.book["events"] += [dic]


def update_expanding_wild_event(gamestate, existing_wild_details: list) -> None:
    """On each reveal - the multiplier value on the expanding wild is updated (sent before reveal)"""
    if gamestate.config.include_padding:
        for ew in existing_wild_details:
            ew["row"] += 1

    dic = {"index": len(gamestate.book["events"]), "type": UPDATE_EXP_WILDS, "newWilds": existing_wild_details}
    gamestate.book["events"] += [dic]


def new_sticky_event(gamestate, new_sticky_syms: list):
    """Pass details on new prize symbols"""
    if gamestate.config.include_padding:
        for sym in new_sticky_syms:
            sym["row"] += 1

    dic = {"index": len(gamestate.book["events"]), "type": NEW_STICKY_SYMS, "newPrizes": new_sticky_syms}
    gamestate.book["events"] += [dic]


def win_info_event(gamestate, include_padding_index=True):
    """
    include_padding_index: starts winning-symbol positions at row=1, to account for top/bottom symbol inclusion in board
    """
    win_data_copy = {}
    win_data_copy["wins"] = deepcopy(gamestate.win_data["wins"])
    prize_details = []
    for _, w in enumerate(win_data_copy["wins"]):
        if include_padding_index:
            prize_details.append({"reel": w["reel"], "row": w["row"] + 1, "value": w["value"]})
        else:
            prize_details.append({"reel": w["reel"], "row": w["row"], "value": w["value"]})

    dict_data = {
        "index": len(gamestate.book["events"]),
        "type": WIN_DATA,
        "totalWin": int(round(min(gamestate.win_data["totalWin"], gamestate.config.wincap) * 100, 0)),
        "wins": win_data_copy["wins"],
    }
    gamestate.book["events"] += [deepcopy(dict_data)]
