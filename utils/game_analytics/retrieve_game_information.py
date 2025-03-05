import json
from get_pay_splits import *
from get_symbol_hits import *
import importlib
import os, sys


def get_config_class(gameID):
    sys.path.append("./")
    module_path = f"Games.{gameID}.GameConfig"
    module = importlib.import_module(module_path)
    class_name = "GameConfig"
    config_class = getattr(module, class_name)

    return config_class()


class GameInformation:
    def __init__(self, gameID, analysis_ranges=None, modes_to_analyse=None, custom_keys=None):
        self.gameID = gameID
        self.modes_to_analyse = modes_to_analyse
        self.configPath = str.join("/", ["games", self.gameID, "library", "lonfigs", "config.json"])
        self.mathConfigPath = str.join("/", ["Games", self.gameID, "Library", "Configs", "math_config.json"])
        self.libraryPath = str.join("/", ["Games", self.gameID, "Library"])
        self.lutPath = str.join("/", ["Games", self.gameID, "Library", "lookUpTables"])

        if custom_keys == None:
            self.custom_keys = [{}]
        else:
            self.custom_keys = custom_keys

        if analysis_ranges != None:
            self.win_ranges = analysis_ranges
        else:
            self.win_ranges = [
                (0, 1),
                (1, 5),
                (5, 10),
                (10, 20),
                (20, 50),
                (50, 100),
                (100, 200),
                (200, 300),
                (300, 500),
                (500, 1000),
                (1000, 2000),
                (2000, 3000),
                (3000, 5000),
                (5000, 10000),
                (10000, 15000),
                (15000, 20000),
                (20000, 20001),
            ]
        self.load_config()

        if modes_to_analyse != None:
            self.modes_to_analyse = self.all_modes

        self.get_fence_information()

        # Change to optional inputs
        self.get_mode_split_hit_rates()
        self.get_symbol_hit_rates(self.modes_to_analyse)
        self.get_custom_hit_rates(modes_to_analyse=self.all_modes, custom_search_keys=self.custom_keys)
        self.get_range_hit_counts()
        print("Info Load Successful.")

    def load_config(self):
        config_class = get_config_class(self.gameID)
        with open(self.configPath, "r") as f:
            config_object = json.load(f)

        all_modes = []
        cost_mapping = {}
        for mode in config_object["bookShelfConfig"]:
            all_modes.append(mode["name"])
            cost_mapping[mode["name"]] = mode["cost"]

        self.config = config_class
        self.all_modes = all_modes
        self.cost_mapping = cost_mapping

    def get_fence_information(self):
        game_type_mapping = {}
        mode_fence_info = {}
        math_config = open(self.mathConfigPath, "r")
        math_config_object = json.load(math_config)
        for mode in self.all_modes:
            game_type_mapping[mode] = []
            mode_fence_info[mode] = {}
            for fence in math_config_object["fences"]:
                if fence["bet_mode"] == mode:
                    for fences in fence["fences"]:
                        if fences["name"] not in ["0", "wincap"]:
                            game_type_mapping[mode].append(fences["name"])
                            if fences["hr"] != "x":
                                mode_fence_info[mode][fences["name"]] = {
                                    "hr": float(fences["hr"]),
                                    "rtp": float(fences["rtp"]),
                                    "av_win": round(
                                        float(fences["hr"])
                                        * float(fences["rtp"])
                                        * self.cost_mapping[fence["bet_mode"]],
                                        2,
                                    ),
                                }
                            else:
                                mode_fence_info[mode][fences["name"]] = {}
        self.game_type_fences = game_type_mapping
        self.mode_fence_info = mode_fence_info

    def get_mode_split_hit_rates(self, modes_to_analyse=None):
        if modes_to_analyse == None:
            modes_to_analyse = self.all_modes
        mode_hit_rate_info = {}
        for mode in modes_to_analyse:
            mode_hit_rate_info[mode] = {}
            lut_path, split_path, fences_path = return_all_filepaths(self.gameID, mode)
            sub_modes = list(self.mode_fence_info[mode].keys())
            mode_sorted_distributions, total_mode_weight = make_split_win_distribution(
                lut_path, split_path, fences_path, sub_modes, "baseGame"
            )
            sub_mode_hits, sub_mode_probs, sub_mode_rtp_allocation = return_hit_rates(
                mode_sorted_distributions, total_mode_weight, self.win_ranges
            )

            mode_hit_rate_info[mode]["all_gameType_hits"] = sub_mode_hits
            mode_hit_rate_info[mode]["all_gameType_probs"] = sub_mode_probs
            mode_hit_rate_info[mode]["all_gameType_rtp"] = sub_mode_rtp_allocation

        self.mode_hit_rate_info = mode_hit_rate_info

    def get_range_hit_counts(self, modes_to_analyse=None):
        if modes_to_analyse == None:
            modes_to_analyse = self.all_modes
        self.mode_hit_rates, self.mode_hit_counts = get_unoptimised_hits(
            self.lutPath, self.all_modes, self.win_ranges
        )

    def get_symbol_hit_rates(self, modes_to_analyse: list) -> None:
        self.hr_summary, self.av_win_summary, self.sim_count_summary = construct_symbol_probabilities(
            self.config, self.all_modes
        )

    def get_custom_hit_rates(self, modes_to_analyse: list, custom_search_keys: list[dict]) -> None:
        assert modes_to_analyse != None, "specify which mode/s to assess"
        assert custom_search_keys != None
        self.custum_hr_summary, self.custom_av_win_summary, self.custom_sim_count_summary = (
            construct_custom_key_probabilities(
                self.config, modes_to_analyse, cumstom_serach_keys=custom_search_keys
            )
        )
