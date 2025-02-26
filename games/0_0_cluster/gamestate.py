from game_override import GameStateOverride
from src.calculations.cluster import get_cluster_data
from game_events import updateGridMultiplierEvent


class GameState(GameStateOverride):

    def run_spin(self, sim):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            # Reset simulation variables and draw a new board based on the betmode criteria.
            self.reset_book()
            self.draw_board()

            self.win_data, self.board, self.exploding_symbols = get_cluster_data(
                config=self.config, board=self.board, global_multiplier=self.global_multiplier
            )
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            self.emit_tumble_win_events()

            while self.win_data["totalWin"] > 0 and not (self.wincap_triggered):
                self.tumble_game_board()
                self.win_data, self.board, self.exploding_symbols = get_cluster_data(
                    config=self.config, board=self.board, global_multiplier=self.global_multiplier
                )
                self.win_manager.update_spinwin(self.win_data["totalWin"])
                self.emit_tumble_win_events()

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition() and self.check_freespin_entry():
                self.run_freespin_from_base()

            self.evaluate_finalwin()

        self.imprint_wins()

    def run_freespin(self):
        self.reset_fs_spin()
        while self.fs < self.tot_fs:
            self.update_freespin()
            self.draw_board()
            updateGridMultiplierEvent(self)
            # Apply game-specific actions (i.e special symbol attributes before or after evaluation)

            self.win_data, self.board, self.exploding_symbols = get_cluster_data(
                config=self.config, board=self.board, global_multiplier=self.global_multiplier
            )
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            self.emit_tumble_win_events()
            self.update_grid_mults()
            while self.win_data["totalWin"] > 0 and not (self.wincap_triggered):
                self.tumble_game_board()
                self.win_data, self.board, self.exploding_symbols = get_cluster_data(
                    config=self.config, board=self.board, global_multiplier=self.global_multiplier
                )
                self.win_manager.update_spinwin(self.win_data["totalWin"])
                self.emit_tumble_win_events()
                self.update_grid_mults()

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition():
                self.update_fs_retrigger_amt()

        self.end_freespin()
