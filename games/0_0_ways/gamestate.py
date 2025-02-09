from game_override import GameStateOverride


class GameState(GameStateOverride):

    def run_spin(self, sim):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            self.draw_board(emit_event=True)

            self.win_data = self.get_ways_data(recor)
            self.win_manager.update_spinwin(self.win_data["totalWin"])

            self.evaluate_final_win()

        self.imprint_wins()

    def run_freespin(self):
        self.reset_fs_spin()
