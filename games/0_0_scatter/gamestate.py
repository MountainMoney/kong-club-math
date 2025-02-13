from game_override import GameStateOverride


class GameState(GameStateOverride):
    """Gamestate for a single spin"""

    def run_spin(self, sim: int):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.draw_board()

            self.win_data = self.get_scatterpay_wins(record_wins=True)  # Evaluate wins
            self.win_manager.update_spinwin(self.win_data["totalWin"])  # Update wallet
            self.emit_tumble_win_events()  # Transmit win information

            while self.win_data["totalWin"] > 0 and not (self.wincap_triggered):
                self.tumble_game_board()
                self.win_data = self.get_scatterpay_wins(record_wins=True)
                self.win_manager.update_spinwin(self.win_data["totalWin"])
                self.emit_tumble_win_events()

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition() and self.check_freespin_entry():
                self.run_freespin_from_base()

            self.evaluate_finalwin()
            self.check_repeat()

        self.imprint_wins()

    def run_freespin(self):
        self.reset_fs_spin()
        while self.fs < self.tot_fs:
            # Resets global multiplier at each spin
            self.update_freespin()
            self.draw_board()

            self.win_data = self.get_scatterpay_wins(record_wins=True)
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            self.emit_tumble_win_events()

            while self.win_data["totalWin"] > 0 and not (self.wincap_triggered):
                self.tumble_game_board()
                self.update_global_mult()  # Special mechanic - increase multiplier with every tumble
                self.win_data = self.get_scatterpay_wins()
                self.win_manager.update_spinwin(self.win_data["totalWin"])
                self.emit_tumble_win_events()

            self.set_end_tumble_event()
            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition():
                self.update_fs_retrigger_amt()

        self.end_freespin()
