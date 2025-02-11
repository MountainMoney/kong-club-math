import random
import numpy as np
from typing import List
from src.state.state_conditions import Conditions
from src.calculations.lines import LineWins
from src.calculations.cluster import ClusterWins
from src.calculations.scatter import ScatterWins
from src.calculations.ways import WaysWins
from src.calculations.tumble import Tumble
from src.calculations.statistics import get_random_outcome
from src.events.events import (
    reveal_event,
    win_info_event,
    freespin_end_event,
    tumble_board_event,
    set_win_event,
    set_total_event,
    update_tumble_win_event,
    wincap_event,
    fs_trigger_event,
    update_freespin_event,
    final_win_event,
)


class Executables(Conditions, Tumble, LineWins, ClusterWins, ScatterWins, WaysWins):
    """
    The purpose of this Class is to group together common actions which are likely to be reused between games.
    These can be overridden in the GameExecutables or GameCalculations if game-specific alterations are required.
    Generally Executables functions do not return values.
    """

    def draw_board(self, emit_event: bool = True) -> None:
        """Instead of retrying to draw a board, force the initial revel to have a
        specific number of scatters, if the betmode criteria specifies this."""
        if (
            self.get_current_distribution_conditions()["force_freespins"]
            and self.gametype == self.config.basegame_type
        ):
            num_scatters = get_random_outcome(self.get_current_distribution_conditions()["scatter_triggers"])
            self.force_special_board("scatter", num_scatters)
        elif (
            not (self.get_current_distribution_conditions()["force_freespins"])
            and self.gametype == self.config.basegame_type
        ):
            self.create_board_reelstrips()
            while self.count_special_symbols("scatter") >= min(
                self.config.freespin_triggers[self.gametype].keys()
            ):
                self.create_board_reelstrips()
        else:
            self.create_board_reelstrips()
        if emit_event:
            reveal_event(self)

    def force_special_board(self, force_criteria: str, num_force_syms: int) -> None:
        """Force a board to have a specified number of symbols."""
        reelstrip_id = get_random_outcome(
            self.get_current_distribution_conditions()["reel_weights"][self.gametype]
        )
        reelstops = self.get_syms_on_reel(reelstrip_id, force_criteria)

        sym_prob = []
        for x in range(self.config.num_reels):
            sym_prob.append(len(reelstops[x]) / len(self.config.reels[reelstrip_id][x]))
        force_stop_positions = {}
        while len(force_stop_positions) != num_force_syms:
            chosen_reel = random.choices(list(np.arange(0, self.config.num_reels)), sym_prob)[0]
            chosen_stop = random.choice(reelstops[chosen_reel])
            sym_prob[chosen_reel] = 0
            force_stop_positions[int(chosen_reel)] = int(chosen_stop)

        force_stop_positions = dict(sorted(force_stop_positions.items(), key=lambda x: x[0]))
        self.force_board_from_reelstrips(reelstrip_id, force_stop_positions)

    def get_syms_on_reel(self, reel_id: str, target_symbol: str) -> List[List]:
        """Return reelstop positions for a specific symbol name."""
        reel = self.config.reels[reel_id]
        reelstop_positions = [[] for _ in range(self.config.num_reels)]
        for r in range(self.config.num_reels):
            for s in range(len(reel[r])):
                if reel[r][s] in self.config.special_symbols[target_symbol]:
                    reelstop_positions[r].append(s)

        return reelstop_positions

    def emit_wayswin_events(self) -> None:
        """Transmit win events asociated with ways wins."""
        if self.win_manager.spin_win > 0:
            win_info_event(self)
            self.evaluate_wincap()
            set_win_event(self)
        set_total_event(self)

    def emit_linewin_events(self) -> None:
        """Transmit win events asociated with lines wins."""
        if self.win_manager.spin_win > 0:
            win_info_event(self)
            self.evaluate_wincap()
            set_win_event(self)
        set_total_event(self)

    def emit_tumble_win_events(self) -> None:
        """Transmit win and new board information upon tumble."""
        if self.win_data["totalWin"] > 0:
            win_info_event(self)
            update_tumble_win_event(self)
            self.evaluate_wincap()

    def tumble_game_board(self):
        "Remove winning symbols from active board and replace."
        self.tumble_board()
        tumble_board_event(self)

    def evaluate_wincap(self) -> None:
        """Indicate spin functions should stop once wincap is reached."""
        if self.win_manager.running_bet_win >= self.config.wincap and not (self.wincap_triggered):
            self.wincap_triggered = True
            wincap_event(self)
            return True
        return False

    def count_special_symbols(self, special_sym_criteria: str) -> int:
        "Returns integer number of active symbols of any 'special' kind."
        return len(self.special_syms_on_board[special_sym_criteria])

    def check_fs_condition(self, scatter_key: str = "scatter") -> bool:
        """Check if there are enough active scatters to trigger fs."""
        if self.count_special_symbols(scatter_key) >= min(
            self.config.freespin_triggers[self.gametype].keys()
        ) and not (self.repeat):
            return True
        return False

    def check_freespin_entry(self, scatter_key: str = "scatter") -> bool:
        """Ensure that betmode criteria is expecting freespin trigger."""
        if self.get_current_distribution_conditions()["force_freespins"] and len(
            self.special_syms_on_board[scatter_key]
        ) >= min(self.config.freespin_triggers[self.gametype].keys()):
            return True
        self.repeat = True
        return False

    def run_freespin_from_base(self, scatter_key: str = "scatter") -> None:
        """Trigger the freespin function and update total fs amount."""
        self.record(
            {
                "kind": self.count_special_symbols(scatter_key),
                "symbol": scatter_key,
                "gametype": self.gametype,
            }
        )
        self.update_freespin_amount()
        self.run_freespin()

    def update_freespin_amount(self, scatter_key: str = "scatter") -> None:
        """Set initial number of spins for a freegame and transmit event."""
        self.tot_fs = self.config.freespin_triggers[self.gametype][self.count_special_symbols(scatter_key)]
        if self.gametype == self.config.basegame_type:
            basegame_trigger, freegame_trigger = True, False
        else:
            basegame_trigger, freegame_trigger = False, True
        fs_trigger_event(self, basegame_trigger=basegame_trigger, freegame_trigger=freegame_trigger)

    def update_fs_retrigger_amt(self, scatter_key: str = "scatter") -> None:
        """Update total freespin amount on retrigger."""
        self.tot_fs += self.config.freespin_triggers[self.gametype][self.count_special_symbols(scatter_key)]
        fs_trigger_event(self, freegame_trigger=True, basegame_trigger=False)

    def update_freespin(self) -> None:
        """Called before a new reveal during freespins."""
        self.fs += 1
        update_freespin_event(self)
        self.win_manager.reset_spin_win()
        self.tumblewin_mult = 0
        self.win_data = {}

    def end_freespin(self) -> None:
        """Transmit total amount awarded during freespins."""
        freespin_end_event(self)

    def evaluate_finalwin(self) -> None:
        """Check base and freespin sums, set payout multiplier."""
        self.update_final_win()
        final_win_event(self)
