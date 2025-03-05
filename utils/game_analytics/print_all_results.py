import json
import xlsxwriter


class PrintJSON:
    def __init__(self, gameInfo):
        self.gameInfo = gameInfo
        self.setup_json()
        self.print_info()
        self.close_json()

    def setup_json(self):
        json_path = "/".join([self.gameInfo.libraryPath, "statistics_summary.json"])
        self.json_object = open(json_path, "w")

    def print_info(self):
        """Parse game information in JSON format."""
        data = {
            "cost_mapping": self.gameInfo.cost_mapping,
            "mode_fence_info": self.gameInfo.mode_fence_info,
            "hr_summary": self.gameInfo.hr_summary,
            "av_win_summary": self.gameInfo.av_win_summary,
            "sim_count_summary": self.gameInfo.sim_count_summary,
            "custom_hr_summary": self.gameInfo.custum_hr_summary,
            "custom_av_win_summary": self.gameInfo.custom_av_win_summary,
            "custom_sim_count_summary": self.gameInfo.custom_sim_count_summary,
        }
        json.dump(data, self.json_object, indent=4)  # Add indent for pretty-printing

    def close_json(self):
        self.json_object.close()


class PrintXLSX:
    def __init__(self, gameInfo):
        self.gameInfo = gameInfo
        self.global_ranges = list(self.gameInfo.win_ranges)
        self.setup_xlsx()
        for mode in self.gameInfo.all_modes:
            self.write_mode_probs(str(mode), 0, 0)
            self.write_range_hit_counts(str(mode), 0, self.top_row_col_end)
            self.write_custom_key_info(str(mode), self.last_row_end + 2)
        self.workbook.close()

    def setup_xlsx(self):
        self.stat_file_name = str.join(
            "_",
            ["Games/" + str(self.gameInfo.gameID) + "/Library/" + self.gameInfo.gameID, "full_statistics.xlsx"],
        )
        self.workbook = xlsxwriter.Workbook(self.stat_file_name)

    def write_mode_probs(self, mode, x0, y0):
        # Main info: rtp-allocation and hit-rates
        self.hit_rate_sheet = self.workbook.add_worksheet(str(mode))
        headers = ["Win Ranges", "Hit Rates", "RTP Allocation"]
        self.hit_rate_sheet.write_row(0, 0, headers)
        hr_dict = self.gameInfo.mode_hit_rate_info[mode]["all_gameType_hits"]["cumulative"]
        rtp_dict = self.gameInfo.mode_hit_rate_info[mode]["all_gameType_rtp"]["cumulative"]
        for idx, win_range in enumerate(self.global_ranges):
            self.hit_rate_sheet.write(x0 + idx + 1, y0, str(win_range))
            self.hit_rate_sheet.write(x0 + idx + 1, y0 + 1, hr_dict[win_range])
            self.hit_rate_sheet.write(x0 + idx + 1, y0 + 2, list(rtp_dict.values())[idx])

        # Hit-rate table by game-mode
        game_headers = list(self.gameInfo.mode_hit_rate_info[mode]["all_gameType_rtp"].keys())
        game_headers_reduced = game_headers[:-1]
        game_col_start = y0 + 5
        self.hit_rate_sheet.write_row(x0, game_col_start + 1, game_headers_reduced)

        hr_dict = self.gameInfo.mode_hit_rate_info[mode]["all_gameType_hits"]
        rtp_dict = self.gameInfo.mode_hit_rate_info[mode]["all_gameType_rtp"]

        for idx, win_range in enumerate(self.global_ranges):
            self.hit_rate_sheet.write(x0 + idx + 1, game_col_start, str(win_range))
            for idy, game_type in enumerate(game_headers_reduced):
                print(hr_dict[game_type][list(self.global_ranges)[idx]])
                self.hit_rate_sheet.write(
                    x0 + idx + 1, game_col_start + 1 + idy, str(hr_dict[game_type][list(self.global_ranges)[idx]])
                )

        # Write symbol hit-rate table
        symRow = len(self.global_ranges) + 5
        symCol = 0
        self.top_row_col_end = game_col_start + 4 + idy
        sym_mode_hit_rate = self.gameInfo.hr_summary[mode]
        sym_count_hit_rate = self.gameInfo.sim_count_summary[mode]
        sym_avg_win = self.gameInfo.av_win_summary[mode]

        symbols, kinds = [], []
        for key in list(sym_mode_hit_rate.keys()):
            temp_kind = eval(key)["kind"]
            temp_symbol = eval(key)["symbol"]
            if temp_symbol not in symbols:
                symbols.append(temp_symbol)
            if temp_kind not in kinds:
                kinds.append(temp_kind)

        freq_dict = {}
        count_dict = {}
        av_dict = {}
        for sym in symbols:
            freq_dict[sym] = {}
            count_dict[sym] = {}
            av_dict[sym] = {}
            for kind in kinds:
                freq_dict[sym][kind] = 0
                count_dict[sym][kind] = 0
                av_dict[sym][kind] = 0

        for key in list(sym_mode_hit_rate.keys()):
            temp_sym = eval(key)["symbol"]
            temp_kind = eval(key)["kind"]
            freq_dict[temp_sym][temp_kind] = round(sym_mode_hit_rate[key], 2)
            count_dict[temp_sym][temp_kind] = int(sym_count_hit_rate[key])
            av_dict[temp_sym][temp_kind] = round(sym_avg_win[key], 1)

        # Symbol combination hit-rates
        self.hit_rate_sheet.write(symRow - 1, symCol, str("HIT RATES"))
        for idSym, sym in enumerate(symbols):
            self.hit_rate_sheet.write(symRow + idSym + 1, symCol, str(sym))
        for idKind, kind in enumerate(kinds):
            self.hit_rate_sheet.write(symRow, symCol + 1 + idKind, kind)
            for idSym, sym in enumerate(symbols):
                self.hit_rate_sheet.write(symRow + idSym + 1, symCol + idKind + 1, freq_dict[sym][kind])

        self.last_row_end = symRow + idSym + 1
        self.last_col_end = symCol + idKind + 4

        # Write number valid sim counts
        self.hit_rate_sheet.write(symRow - 1, symCol + self.last_col_end, str("SIM COUNTS"))
        for idSym, sym in enumerate(symbols):
            self.hit_rate_sheet.write(symRow + idSym + 1, symCol + self.last_col_end, str(sym))
        for idKind, kind in enumerate(kinds):
            self.hit_rate_sheet.write(symRow, symCol + 1 + idKind + self.last_col_end, kind)
            for idSym, sym in enumerate(symbols):
                self.hit_rate_sheet.write(
                    symRow + idSym + 1, symCol + idKind + 1 + self.last_col_end, count_dict[sym][kind]
                )

        self.last_col_end += symCol + idKind + 4
        # Write Avg Win for valid symbol combination
        self.hit_rate_sheet.write(symRow - 1, symCol + self.last_col_end, str("AVG WINS"))
        for idSym, sym in enumerate(symbols):
            self.hit_rate_sheet.write(symRow + idSym + 1, symCol + self.last_col_end, str(sym))
        for idKind, kind in enumerate(kinds):
            self.hit_rate_sheet.write(symRow, symCol + 1 + idKind + self.last_col_end, kind)
            for idSym, sym in enumerate(symbols):
                self.hit_rate_sheet.write(
                    symRow + idSym + 1, symCol + idKind + 1 + self.last_col_end, av_dict[sym][kind]
                )

        self.last_row_end = symRow + idSym + 4
        print("done.")

    def write_range_hit_counts(self, mode, x0, y0):
        range_hit_counts = self.gameInfo.mode_hit_counts
        self.hit_rate_sheet.write(x0, y0, "Win Ranges")
        self.hit_rate_sheet.write(x0, y0 + 1, "SIM COUNTS")
        for idx, key in enumerate(list(range_hit_counts[mode].keys())):
            self.hit_rate_sheet.write(x0 + idx + 1, y0, str(key))
            self.hit_rate_sheet.write(x0 + 1 + idx, y0 + 1, range_hit_counts[mode][key])

    def write_custom_key_info(self, mode, row_start):
        custom_hr = self.gameInfo.custum_hr_summary[mode]
        custom_count = self.gameInfo.custom_sim_count_summary[mode]
        custom_avg = self.gameInfo.custom_av_win_summary[mode]
        custom_keys = list(custom_hr.keys())
        # write hr, sim_count, av_win
        self.hit_rate_sheet.write(row_start, 0, str("CUSTOM"))
        self.hit_rate_sheet.write_row(row_start + 1, 1, ["HR", "COUNT", "AVG"])
        for idx, key in enumerate(custom_keys):
            self.hit_rate_sheet.write(row_start + 2 + idx, 0, str(key))
            self.hit_rate_sheet.write(row_start + 2 + idx, 1, str(custom_hr[key]))
            self.hit_rate_sheet.write(row_start + 2 + idx, 2, str(custom_count[key]))
            self.hit_rate_sheet.write(row_start + 2 + idx, 3, str(custom_avg[key]))
        print("done")

    def write_key_mode_info(self, mode, row_start):
        pass
