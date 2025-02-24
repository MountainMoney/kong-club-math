"""Handle generation configuration files after simulations and optimization process have concluded."""

import json
import os
import shutil
from utils.get_file_hash import get_hash
from utils.analysis.distribution_functions import get_distribution_std, get_lookup_length


def copy_and_rename_csv(filepath: str) -> None:
    """If no optimization has been run, initialise the lookup table."""
    file_location = str.join("/", filepath.split("/")[:-1])
    new_filepath = str.join("/", [file_location, filepath.split("/")[-1].split(".csv")[0] + "_0.csv"])
    shutil.copy(filepath, new_filepath)


def generate_configs(gamestate: object, json_padding: bool = True, assign_properties: bool = True):
    """Construct frontend, backend and optimization-required configuration files."""
    make_fe_config(
        gamestate=gamestate,
        json_padding=json_padding,
        assign_properties=assign_properties,
    )
    make_be_config(gamestate)


def pass_fe_betmode(betmode):
    """Generate frontend configuration json file."""
    mode_info = {}
    mode_info["cost"] = betmode.get_cost()
    mode_info["feature"] = betmode.get_feature()
    mode_info["buyBonus"] = betmode.get_buybonus()
    mode_info["rtp"] = betmode.get_rtp()
    mode_info["max_win"] = betmode.get_wincap()

    return {betmode.get_name(): mode_info}


def make_fe_config(gamestate, json_padding=True, assign_properties=True, **kwargs):
    """
    json_padding formats symbols the same as the board {'name': symbol} (default), alternatively an array of strings ['H1',...] is passed
    assign_properties will invoke a symbol attribute
    """
    if assign_properties:
        assert json_padding is True, "json_padding must be `True` to invoke symbol properties in padding"

    json_info = {}
    json_info["providerName"] = str(gamestate.config.provider_name)
    json_info["gameName"] = str(gamestate.config.game_name)
    json_info["gameID"] = gamestate.config.game_id
    json_info["rtp"] = gamestate.config.rtp
    json_info["numReels"] = gamestate.config.num_reels
    json_info["numRows"] = gamestate.config.num_rows

    json_info["betModes"] = {}
    for betmode in gamestate.config.bet_modes:
        bm_info = pass_fe_betmode(betmode)
        m_name = next(iter(bm_info))
        json_info["betModes"][m_name] = bm_info[m_name]

    # Optionally include any custom information
    for key, val in kwargs:
        json_info[key] = val

    if hasattr(gamestate.config, "pay_lines"):
        json_info["paylines"] = gamestate.config.paylines

    symbols = {}
    for sym in gamestate.symbol_storage.symbols.values():
        symbols[sym.name] = {}
        special_properties = []
        for prop in gamestate.config.special_symbols:
            if sym.name in gamestate.config.special_symbols[prop]:
                special_properties.append(prop)

        if hasattr(sym, "paytable"):
            symbols[sym.name]["paytable"] = sym.paytable

        if len(special_properties) > 0:
            symbols[sym.name]["special_properties"] = special_properties

    json_info["symbols"] = symbols
    reelstrip_json = {}
    if json_padding:
        for idx, reels in gamestate.config.padding_reels.items():
            reelstrip_json[idx] = [[] for _ in range(gamestate.config.num_reels)]
            for c, _ in enumerate(reels):
                column = reels[c]
                for i, _ in enumerate(column):
                    reelstrip_json[idx][c].append({"name": column[i]})

        json_info["paddingReels"] = reelstrip_json
    elif not json_padding:
        json_info["paddingReels"] = gamestate.config.paddingReels

    f_name = str.join("/", [gamestate.config.config_path, "config_fe_" + str(gamestate.config.game_id) + ".json"])
    fe_json = open(f_name, "w", encoding="UTF-8")
    fe_json.write(json.dumps(json_info, indent=4))
    fe_json.close()


def make_be_config(gamestate):
    """ "Generate config.json for RGS to retrieve game details and hash-values."""
    config = gamestate.config

    fe_config_name = "config_fe_" + str(config.game_id) + ".json"
    fe_config_sha = get_hash(config.config_path + "/" + fe_config_name)
    available_bm = gamestate.config.bet_modes

    # General game data
    be_info = {}
    be_info["frontendConfig"] = {"file": fe_config_name, "sha256": fe_config_sha}
    be_info["workingName"] = config.working_name
    be_info["frontendConfig"] = {"file": fe_config_name, "sha256": fe_config_sha}
    be_info["workingName"] = str(config.working_name)
    be_info["gameID"] = config.game_id
    if config.rtp < 1:
        be_info["rtp"] = config.rtp * 100  # RGS expects RTP as a %
    else:
        be_info["rtp"] = config.rtp
    be_info["betDenomination"] = int(config.min_denomination * 100 * 100)
    be_info["minDenomination"] = int(config.min_denomination * 100)
    be_info["providerNumber"] = int(config.provider_number)
    be_info["standardForceFile"] = {
        "file": "force.json",
        "sha256": get_hash(str.join("/", [config.force_path, "force.json"])),
    }

    # Betmode specific data
    be_info["bookShelfConfig"] = []
    for bet in available_bm:
        lut_table = str.join("_", ["lookUpTable", bet.get_name(), "0.csv"])
        std_table = str.join("/", [config.lookup_path, "lookUpTable_" + bet.get_name() + "_0.csv"])
        if not (os.path.exists(std_table)):
            print(f"File does not exist: {std_table}, \n Generating lut_0 file.")
            base_table = str.join("/", [config.lookup_path, "lookUpTable_" + bet.get_name() + ".csv"])
            copy_and_rename_csv(base_table)

        lut_sha_value = get_hash(std_table)
        std_val = round(get_distribution_std(std_table) / bet.get_cost(), 2)
        booklength = get_lookup_length(std_table)
        dic = {
            "name": bet.get_name(),
            "tables": {"file": lut_table, "condition": "totalSpin > -1", "sha256": lut_sha_value, "name": "0"},
            "cost": bet.get_cost(),
            "rtp": bet.get_rtp(),
            "std": std_val,
            "bookLength": booklength,
            "feature": bet.get_feature(),
            "autoEndRoundDisabled": bet.get_auto_close_disabled(),
            "buyBonus": bet.get_buybonus(),
            "maxWin": bet.get_wincap(),
        }
        data_file = str.join("_", ["books", bet.get_name() + ".json.zst"])
        data_loc = str.join("/", [config.compressed_path, data_file])
        data_sha = get_hash(data_loc)

        force_file = str.join("_", ["force_for_rob", bet.get_name() + ".json"])
        force_loc = str.join("/", [config.force_path, force_file])
        force_sha = get_hash(force_loc)

        dic["booksFile"] = {"file": data_file, "sha256": data_sha}
        dic["forceFile"] = {"file": force_file, "sha256": force_sha}
        be_info["bookShelfConfig"].append(dic)

    file = open(config.config_path + "/config.json", "w", encoding="UTF-8")
    file.write(json.dumps(be_info, indent=4))
    file.close()
