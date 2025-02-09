from copy import copy
from abc import ABC, abstractmethod
import random

from src.config.config import *
from src.write_data.write_data import *
from src.calculations.symbol import Symbol
from src.wins.win_manager import WinManager
from src.calculations.symbol import SymbolStorage


class GeneralGameState(ABC):
    """Master gamestate which other classes inherit from."""

    def __init__(self, config):
        self.config = config
        self.library = {}
        self.recorded_events = {}
        self.special_symbol_functions = {}
        self.temp_wins = []
        self.win_manager = WinManager(self.config.basegame_type, self.config.freegame_type)
        self.sim = 0
        self.criteria = ""
        self.reset_seed()
        self.create_symbol_map()
        self.reset_book()
        self.assign_special_sym_function()
        self.reset_fs_spin()

    def create_symbol_map(self) -> None:
        """Construct all valid symbols from config file (from pay-table and special symbols)."""
        all_symbols_list = set()
        for key, _ in self.config.paytable.items():
            all_symbols_list.add(key[1])

        for key in self.config.special_symbols:
            for sym in self.config.special_symbols[key]:
                all_symbols_list.add(sym)

        all_symbols_list = list(all_symbols_list)
        self.symbol_storage = SymbolStorage(self.config, all_symbols_list)

    @abstractmethod
    def assign_special_sym_function(self):
        """ "Define custom symbol functions in game_override."""
        warn("No special symbol functions are defined")

    def reset_book(self) -> None:
        """Reset global simulation variables."""
        self.board = [[[] for _ in range(self.config.num_rows[x])] for x in range(self.config.num_reels)]
        self.top_symbols = None
        self.bottom_symbols = None
        self.book_id = self.sim + 1
        self.book = {
            "id": self.book_id,
            "payoutMultiplier": 0.0,
            "events": [],
            "criteria": self.criteria,
        }
        self.win_data = {
            "totalWin": 0,
            "wins": [],
        }
        self.win_manager.reset_end_round_wins()
        self.global_multiplier = 1
        self.final_win = 0
        self.tot_fs = 0
        self.fs = 0
        self.wincap_triggered = False
        self.triggered_freespins = False
        self.gametype = self.config.basegame_type
        self.repeat = False
        self.anticipation = [0] * self.config.num_reels

    def reset_seed(self, sim: int = 0) -> None:
        """Reset rng seed to simulation number for reproducibility."""
        random.seed(sim + 1)
        self.sim = sim

    def reset_fs_spin(self) -> None:
        """Use if using repeat during freespin games."""
        self.triggered_freespins = True
        self.fs = 0
        self.gametype = self.config.freegame_type
        self.win_manager.reset_spin_win()

    def get_betmode(self, mode_name) -> BetMode:
        """Return all current betmode information."""
        for betmode in self.config.bet_modes:
            if betmode.get_name() == mode_name:
                return betmode
        print("\nWarning: betmode couldn't be retrieved\n")

    def get_current_betmode(self) -> object:
        """Get current betmode information."""
        for betmode in self.config.bet_modes:
            if betmode.get_name() == self.betmode:
                return betmode

    def get_current_betmode_distributions(self) -> object:
        """Return current betmode criteria information."""
        dist = self.get_current_betmode().get_distributions()
        for c in dist:
            if c._criteria == self.criteria:
                return c
        raise RuntimeError("could not locate criteria distribtuion")

    def get_current_distribution_conditions(self) -> dict:
        """Return requirements for criteria setup/acceptance."""
        for d in self.get_betmode(self.betmode).get_distributions():
            if d._criteria == self.criteria:
                return d._conditions
        return RuntimeError("could not locate betmode conditions")

    # State verifications/checks
    def get_wincap_triggered(self) -> bool:
        """Break out of spin progress if max-win is triggered."""
        if self.wincap_triggered:
            return True
        return False

    def in_criteria(self, *args) -> bool:
        """Checks if the current win criteria matches a given list."""
        for arg in args:
            if self.criteria == arg:
                return True
        return False

    def record(self, description: dict) -> None:
        """
        Record functions must be used for distribution conditions.
        Freespin triggers are most commonly used, i.e {"kind": X, "symbol": "S", "gametype": "basegame"}
        It is recommended to otherwise record rare events with several keys in order to reduce the overall file-size containing many duplicate ids
        """
        self.temp_wins.append(description)
        self.temp_wins.append(self.book_id)

    def check_force_keys(self, description) -> None:
        """Check and append unique force-key paramaters."""
        current_mode_force_keys = self.get_current_betmode().get_force_keys()  # type:ignore
        for keyValue in description:
            if keyValue[0] not in current_mode_force_keys:
                self.get_current_betmode().add_force_key(keyValue[0])  # type:ignore

    def combine(self, modes, betmode_name) -> None:
        for modeConfig in modes:
            for betmode in modeConfig:
                if betmode.get_name() == betmode_name:
                    break
            force_keys = betmode.get_force_keys()  # type:ignore
            for key in force_keys:
                if key not in self.get_betmode(betmode_name).get_force_keys():  # type:ignore
                    self.get_betmode(betmode_name).add_force_key(key)  # type:ignore

    def imprint_wins(self) -> None:
        """Record all events to library if criteria conditions are satisfied."""
        for temp_win_index in range(int(len(self.temp_wins) / 2)):
            description = tuple(sorted(self.temp_wins[2 * temp_win_index].items()))
            book_id = self.temp_wins[2 * temp_win_index + 1]
            if description in self.recorded_events and (
                book_id not in self.recorded_events[description]["bookIds"]
            ):
                self.recorded_events[description]["timesTriggered"] += 1
                self.recorded_events[description]["bookIds"] += [book_id]
            else:
                self.check_force_keys(description)
                self.recorded_events[description] = {
                    "timesTriggered": 1,
                    "bookIds": [book_id],
                }
        self.temp_wins = []
        self.library[self.sim + 1] = copy(self.book)
        self.win_manager.update_end_round_wins()

    def update_final_win(self) -> None:
        """Separate base and freegame wins, verify the sum of there are equal to the final simulation payout."""
        final = round(min(self.win_manager.running_bet_win, self.config.wincap), 2)
        basewin = round(min(self.win_manager.basegame_wins, self.config.wincap), 2)
        freewin = round(min(self.win_manager.freegame_wins, self.config.wincap), 2)

        self.final_win = final
        self.book["payoutMultiplier"] = self.final_win
        self.book["baseGameWins"] = basewin
        self.book["freeGameWins"] = freewin

        assert min(
            round(self.win_manager.basegame_wins + self.win_manager.freegame_wins, 2),
            self.config.wincap,
        ) == round(self.win_manager.running_bet_win, 2), "Base + Free game payout mismatch!"
        assert min(
            round(self.book["baseGameWins"] + self.book["freeGameWins"], 2),
            self.config.wincap,
        ) == round(self.book["payoutMultiplier"], 2), "Base + Free game payout mismatch!"

    def check_repeat(self) -> None:
        """Checks if the spin failed a criteria constraint at any point."""
        if self.repeat is False:
            win_criteria = self.get_current_betmode_distributions().get_win_criteria()
            if win_criteria is not None and self.final_win != win_criteria:
                self.repeat = True

            if self.get_current_distribution_conditions()["force_freespins"] and not (self.triggered_freespins):
                self.repeat = True

        if self.in_criteria("baseGame") and self.final_win == 0:
            print("here")

    @abstractmethod
    def run_spin(self, sim):
        """run_spin should be defined in gamestate."""
        print("Base Game is not implemented in this game. Currently passing when calling runSpin.")

    @abstractmethod
    def run_freespin(self):
        """run_freespin trigger function should be defined in gamestate."""
        print("gamestate requires def run_freespin(), currently passing when calling runFreeSpin")

    def run_sims(
        self,
        betmode_copy_list,
        betmode,
        sim_to_criteria,
        total_threads,
        total_repeats,
        num_sims,
        thread_index,
        repeat_count,
        compress=True,
        write_event_list=True,
    ) -> None:
        """Assigns criteria and runs individual simulations. Results are stored in tempory file to be combined when all threads are finished."""
        self.betmode = betmode
        self.num_sims = num_sims
        for sim in range(
            thread_index * num_sims + (total_threads * num_sims) * repeat_count,
            (thread_index + 1) * num_sims + (total_threads * num_sims) * repeat_count,
        ):
            self.criteria = sim_to_criteria[sim]
            self.run_spin(sim)
        mode_cost = self.get_current_betmode().get_cost()
        print(
            "Thread " + str(thread_index),
            "finished with",
            round(self.win_manager.total_cumulative_wins / (num_sims * mode_cost), 3),
            "RTP.",
            f"[baseGame: {round(self.win_manager.cumulative_base_wins/(num_sims*mode_cost), 3)}, freeGame: {round(self.win_manager.cumulative_free_wins/(num_sims*mode_cost), 3)}]",
            flush=True,
        )
        last_file_write = thread_index == total_threads - 1 and repeat_count == total_repeats - 1
        frist_file_write = thread_index == 0 and repeat_count == 0

        write_json(
            self,
            list(self.library.values()),
            "temp_multi_threaded_files/books_"
            + betmode
            + "_"
            + str(thread_index)
            + "_"
            + str(repeat_count)
            + ".json",
            frist_file_write,
            last_file_write,
            compress,
        )
        print_recorded_wins(self, betmode + "_" + str(thread_index) + "_" + str(repeat_count))
        make_lookup_tables(
            self,
            "lookUpTable_" + betmode + "_" + str(thread_index) + "_" + str(repeat_count),
        )
        make_lookup_to_criteria(
            self,
            "lookUpTableIdToCriteria_" + betmode + "_" + str(thread_index) + "_" + str(repeat_count),
        )
        make_lookup_pay_split(
            self,
            "lookUpTableSegmented" + "_" + str(betmode) + "_" + str(thread_index) + "_" + str(repeat_count),
        )
        if write_event_list:
            write_library_events(self, list(self.library.values()), betmode)
        betmode_copy_list.append(self.config.bet_modes)
