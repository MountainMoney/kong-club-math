"""Game logic and event emission for standard 'ways' game with a fixed board size."""

from game_override import GameStateOverride
from src.calculations.ways import get_ways_data


class GameState(GameStateOverride):

    def run_spin(self, sim):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.draw_board(emit_event=True)

            # Evaluate base-game board
            self.win_data = get_ways_data(self.config, self.board)
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            self.emit_wayswin_events()

            self.win_manager.update_gametype_wins(self.gametype)
            # Check Scatter condition and trigger freegame
            if self.check_fs_condition() and self.check_freespin_entry():
                self.run_freespin_from_base()

            self.evaluate_finalwin()
            self.check_repeat()

        self.imprint_wins()

    def run_freespin(self):
        self.reset_fs_spin()
        while self.fs < self.tot_fs:
            self.update_freespin()
            self.draw_board(emit_event=True)

            self.win_data = get_ways_data(self.config, self.board)
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            self.emit_wayswin_events()

            if self.check_fs_condition():
                self.update_fs_retrigger_amt()

            self.win_manager.update_gametype_wins(self.gametype)
        self.end_freespin()
