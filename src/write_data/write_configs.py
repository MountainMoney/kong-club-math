"""Handle generation configuration files after simulations and optimisation process have concluded."""

import json


def generate_configs(gamestate: object, json_padding: bool = True, assign_properties: bool = True):
    """Construct frontend, backend and optimisation-required configuration files."""
    make_fe_config(
        gamestate=gamestate,
        json_padding=json_padding,
        assign_properties=assign_properties,
    )


def pass_fe_betmode(betmode):
    """Generate frontend configuration json file."""
    modeInfo = {}
    modeInfo["cost"] = betmode.get_cost()
    modeInfo["feature"] = betmode.get_feature()
    modeInfo["buyBonus"] = betmode.getBuyBonus()
    modeInfo["rtp"] = betmode.get_rtp()
    modeInfo["max_win"] = betmode.get_wincap()

    return {betmode.get_name(): modeInfo}


def make_fe_config(gamestate, json_padding=True, assign_properties=True, **kwargs):
    """
    json_padding formats symbols the same as the board {'name': symbol} (default), alternatively an array of strings ['H1',...] is passed
    assign_properties will invode
    """
    if assign_properties:
        assert json_padding is True, "json_padding must be `True` to invoke symbol properties in padding"

    jsonInfo = {}
    jsonInfo["providerName"] = str(gamestate.config.provider_name)
    jsonInfo["gameName"] = str(gamestate.config.game_name)
    jsonInfo["gameID"] = gamestate.config.game_id
    jsonInfo["rtp"] = gamestate.config.rtp
    jsonInfo["numReels"] = gamestate.config.num_reels
    jsonInfo["numRows"] = gamestate.config.num_rows

    jsonInfo["betModes"] = {}
    for betmode in gamestate.config.bet_modes:
        bmInfo = pass_fe_betmode(betmode)
        modeName = next(iter(bmInfo))
        jsonInfo["betModes"][modeName] = bmInfo[modeName]

    # Optionally include any custom information
    for key, val in kwargs:
        jsonInfo[key] = val

    try:
        jsonInfo["paylines"] = gamestate.config.pay_lines
    except:
        pass

    symbols = {}
    for sym in gamestate.symbol_storage.symbols.values():
        symbols[sym.name] = {}
        special_properties = []
        for prop in gamestate.config.special_symbols:
            if sym.name in gamestate.config.special_symbols[prop]:
                special_properties.append(prop)

        if sym.paytable is not None:
            symbols[sym.name]["paytable"] = sym.paytable

        if len(special_properties) > 0:
            symbols[sym.name]["special_properties"] = special_properties

    jsonInfo["symbols"] = symbols
    reelStripDictionaryJSON = {}
    if json_padding:
        for idx, reels in gamestate.config.padding_reels.items():
            reelStripDictionaryJSON[idx] = [[] for _ in range(gamestate.config.num_reels)]
            for c, _ in enumerate(reels):
                column = reels[c]
                for i, _ in enumerate(column):
                    reelStripDictionaryJSON[idx][c].append({"name": column[i]})
                    if len(gamestate.symbol_storage.symbols[column[i]].special_functions) > 0:
                        pass
                        # s = Symbol(gamestate.config, column[i])
                        # s.apply_special_function()
                        pass
        # TODO: implement special function
        jsonInfo["paddingReels"] = reelStripDictionaryJSON
    elif not json_padding:
        jsonInfo["paddingReels"] = gamestate.config.paddingReels

    fe_json = open(
        str.join(
            "/",
            [
                gamestate.config.config_path,
                "config_fe_" + str(gamestate.config.game_id) + ".json",
            ],
        ),
        "w",
    )
    fe_json.write(json.dumps(jsonInfo, indent=4))
    fe_json.close()
