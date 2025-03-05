"""Handle generation configuration files after simulations and optimization process have concluded."""

import json
import os
import shutil
import warnings
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
    make_temp_math_config(gamestate)
    # make_math_config(gamestate)


def pass_fe_betmode(betmode):
    """Generate frontend configuration json file."""
    mode_info = {}
    mode_info["cost"] = betmode.get_cost()
    mode_info["feature"] = betmode.get_feature()
    mode_info["buyBonus"] = betmode.get_buybonus()
    mode_info["rtp"] = betmode.get_rtp()
    mode_info["max_win"] = betmode.get_wincap()

    return {betmode.get_name(): mode_info}


def make_temp_math_config(gamestate):
    """
    This is a temporary function who's only purpose is to generate a math_config.json file
    which is directly compatible with with existing optimization script. Will be reformatted
    when the new algorithm is implemented.
    """
    jsonInfo = {}
    jsonInfo["gameID"] = gamestate.config.game_id
    file = open(gamestate.config.config_path + "/math_config.json", "w")
    rust_dict = {}
    rust_dict["game_id"] = jsonInfo["gameID"]
    rust_dict["bet_modes"] = []

    # Separated betmode information
    opt_mode = None
    for bet_mode in gamestate.config.bet_modes:
        for mode, mode_obj in gamestate.config.optimization_params.items():
            if mode == bet_mode._name:
                opt_mode = mode
                break

        if opt_mode is not None:
            bet_mode_rust = {
                "bet_mode": bet_mode._name,
                "cost": bet_mode._cost,
                "rtp": bet_mode._rtp,
                "max_win": bet_mode._wincap,
            }
            rust_dict["bet_modes"] += [bet_mode_rust]

            rust_dict["fences"] = []
            rust_fence = {"bet_mode": bet_mode._name, "fences": []}
            fence_info = {}
            for fence, fence_obj in mode_obj["conditions"].items():
                fence_info = {}
                fence_info["name"] = fence
                fence_info["avg_win"] = fence_obj.av_win
                fence_info["hr"] = fence_obj.hr
                fence_info["rtp"] = fence_obj.rtp

                fence_info["identity_condition"] = {}
                fence_info["identity_condition"]["search"] = []
                if fence_obj.params["force_search"] != {}:
                    fence_info["identity_condition"]["search"].append(
                        {
                            "name": str(list(fence_obj.force_search.keys())[0]),
                            "value": str(list(fence_obj.force_search.values())[0]),
                        }
                    )
                fence_info["identity_condition"]["win_range_start"] = fence_obj.params["search_range"][0]
                fence_info["identity_condition"]["win_range_end"] = fence_obj.params["search_range"][1]
                fence_info["opposite"] = False

                rust_fence["fences"] += [fence_info]
            rust_dict["fences"] += [rust_fence]

        rust_dict["dresses"] = []
        rust_dress = {"bet_mode": bet_mode._name, "dresses": []}
        for dress_obj in mode_obj["scaling"]:
            dress_info = {}
            dress_info["fence"] = dress_obj["criteria"]
            dress_info["scale_factor"] = dress_obj["scale_factor"]
            dress_info["identity_condition_win_range"] = [dress_obj["win_range"][0], dress_obj["win_range"][1]]
            dress_info["prob"] = dress_obj["probability"]

            rust_dress["dresses"].append(dress_info)

        rust_dict["dresses"] += [rust_dress]

    file.write(json.dumps(rust_dict, indent=4))
    file.close()


def make_math_config(gamestate):
    jsonInfo = {}
    jsonInfo["gameID"] = gamestate.config.game_id

    rust_dict = {}
    rust_dict["game_name"] = jsonInfo["gameID"]
    rust_dict["bet_modes"] = []
    for bet_mode in gamestate.config.bet_modes:
        bet_mode_rust = {
            "bet_mode": bet_mode._name,
            "cost": bet_mode._cost,
            "rtp": bet_mode._rtp,
            "max_win": bet_mode._wincap,
        }
        opt_mode = None
        for mode, mode_obj in gamestate.config.optimization_params.items():
            if mode == bet_mode._name:
                opt_mode = mode
                break
        if opt_mode is not None:

            data = []
            search_data = []
            for cond, opt_obj in mode_obj["conditions"].items():
                opt_dict = opt_obj.to_dict()
                if opt_dict["force_search"] != {}:
                    search_data.append({})
                    search_data[-1]["name"] = str(list(opt_dict["force_search"].keys())[0])
                    search_data[-1]["value"] = str(list(opt_dict["force_search"].values())[0])
                else:
                    search_data = []
                data.append(
                    {
                        "criteria": cond,
                        "rtp": opt_dict["rtp"],
                        "avg_win": opt_dict["av_win"],
                        "hr": opt_dict["hr"],
                        "identity_condition": {
                            "search": search_data,
                            "opposite": False,
                            "win_range_start": opt_dict["search_range"][0],
                            "win_range_end": opt_dict["search_range"][1],
                        },
                    }
                )
            bet_mode_rust["opt_conditions"] = data

            bet_mode_rust["scaling"] = []
            for scale in mode_obj["scaling"]:
                bet_mode_rust["scaling"].append(
                    {
                        "criteria": scale["criteria"],
                        "scale_factor": scale["scale_factor"],
                        "identity_condition_win_range": [scale["win_range"][0], scale["win_range"][1]],
                        "prob": scale["probability"],
                    }
                )

            bet_mode_rust["opt_params"] = mode_obj["parameters"]

            rust_dict["bet_modes"].append(bet_mode_rust)

            file = open(gamestate.config.config_path + "/math_config.json", "w")
            file.write(json.dumps(rust_dict, indent=4))
            file.close()


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
        try:
            data_sha = get_hash(data_loc)
        except FileNotFoundError:
            data_sha = ""
            warnings.warn("Compressed books file not found. Hash is empty.")

        force_file = str.join("_", ["force_record", bet.get_name() + ".json"])
        force_loc = str.join("/", [config.force_path, force_file])
        force_sha = get_hash(force_loc)

        dic["booksFile"] = {"file": data_file, "sha256": data_sha}
        dic["forceFile"] = {"file": force_file, "sha256": force_sha}
        be_info["bookShelfConfig"].append(dic)

    file = open(config.config_path + "/config.json", "w", encoding="UTF-8")
    file.write(json.dumps(be_info, indent=4))
    file.close()
