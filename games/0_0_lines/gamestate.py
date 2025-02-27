from game_override import GameStateOverride
from src.calculations.lines import get_lines


class GameState(GameStateOverride):
    """Handles game logic and events for a single simulation number/game-round."""

    def run_spin(self, sim):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.draw_board()

            self.win_data = get_lines(self.board, self.config, global_multiplier=self.global_multiplier)
            self.record_lines_wins()
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            self.emit_linewin_events()

            self.win_manager.update_gametype_wins(self.gametype)
            if self.check_fs_condition():
                self.run_freespin_from_base()

            self.evaluate_finalwin()
            self.check_repeat()

        self.imprint_wins()

    def run_freespin(self):
        self.reset_fs_spin()
        while self.fs < self.tot_fs:
            self.update_freespin()
            self.draw_board()

            self.win_data = get_lines(self.board, self.config, global_multiplier=self.global_multiplier)
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            self.emit_linewin_events()

            if self.check_fs_condition():
                self.update_fs_retrigger_amt()

            self.win_manager.update_gametype_wins(self.gametype)

        self.end_freespin()
