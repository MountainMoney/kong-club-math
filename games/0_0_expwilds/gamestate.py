"""Handles the state and output for a single simulation round"""

from src.calculations.statistics import get_random_outcome
from game_override import GameStateOverride


class GameState(GameStateOverride):
    """Handle all game-logic and event updates for a given simulation number."""

    def run_spin(self, sim):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            if self.betmode == "superspin":
                self.run_superspin()
            else:
                self.draw_board(emit_event=True)

                self.win_data = self.get_lines()
                self.win_manager.update_spinwin(self.win_data["totalWin"])
                self.emit_linewin_events()

                self.win_manager.update_gametype_wins(self.gametype)
                if self.check_fs_condition() and self.check_freespin_entry():
                    self.run_freespin_from_base()

                self.evaluate_finalwin()

        self.imprint_wins()

    def run_freespin(self):
        self.reset_fs_spin()
        self.expanding_wilds = [[] for _ in range(self.config.num_reels)]
        self.avaliable_reels = [i for i in range(self.config.num_reels)]

        while self.fs < self.tot_fs:
            self.update_freespin()
            self.draw_board(emit_event=False)
            # Freegame reelstips have no wild naturally
            self.update_with_existing_wilds()

            wild_on_reveal = get_random_outcome(self.get_current_distribution_conditions()["landing_wilds"])
            if wild_on_reveal > 0:
                self.assign_new_wilds(wild_on_reveal)

            self.win_data = self.get_lines()
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            self.emit_linewin_events()
            self.win_manager.update_gametype_wins(self.gametype)

        self.end_freespin()

    def run_superspin(self):
        self.repeat = True
        pass
