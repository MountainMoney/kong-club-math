"""

"""

from copy import copy

from game_calculations import GameCalculations
from game_events import send_mult_info_event
from src.events.events import (
    update_global_mult_event,
    set_win_event,
    set_total_event,
    fs_trigger_event,
    update_tumble_win_event,
)


class GameExecutables(GameCalculations):
    """Game specific executable functions. Used for grouping commonly used/repeated applications."""

    def set_end_tumble_event(self):
        """After all tumbling events have finished, multiply tumble-win by sum of mult symbols."""
        if self.gametype == self.config.freegame_type:  # Only multipliers in freeSpins
            board_mult, mult_info = self.get_board_multipliers()
            base_tumble_win = copy(self.win_manager.spin_win)
            self.win_manager.set_spin_win(base_tumble_win * board_mult)
            if self.win_manager.spin_win > 0 and len(mult_info) > 0:
                send_mult_info_event(
                    self,
                    board_mult,
                    mult_info,
                    base_tumble_win,
                    self.win_manager.spin_win,
                )
                update_tumble_win_event(self)

        if self.win_manager.spin_win > 0:
            set_win_event(self)
        set_total_event(self)

    def update_global_mult(self):
        """Increment multiplier value and emit corresponding event."""
        self.global_multiplier += 1
        update_global_mult_event(self)

    def update_freespin_amount(self, scatter_key: str = "scatter"):
        """Update current and total freespin number and emit event."""
        self.tot_fs = self.count_special_symbols(scatter_key) * 2
        if self.gametype == self.config.basegame_type:
            basegame_trigger, freegame_trigger = True, False
        else:
            basegame_trigger, freegame_trigger = False, True
        fs_trigger_event(self, basegame_trigger=basegame_trigger, freegame_trigger=freegame_trigger)
