"""Handles the state and output for a single simulation round"""

from game_override import GameStateOverride
from game_events import win_info_event, new_sticky_event
from src.events.events import update_freespin_event, reveal_event, set_total_event, set_win_event
from src.calculations.statistics import get_random_outcome


class GameState(GameStateOverride):
    """Handle all game-logic and event updates for a given simulation number."""

    def run_spin(self, sim):
        """Entry point for all game-modes."""
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

            self.update_with_existing_wilds()  # Override board with expanding wilds, update mults on each

            wild_on_reveal = get_random_outcome(self.get_current_distribution_conditions()["landing_wilds"])
            if wild_on_reveal > 0:  # Assign new expanding wilds - send event with positions
                self.assign_new_wilds(wild_on_reveal)

            self.win_data = self.get_lines()
            self.win_manager.update_spinwin(self.win_data["totalWin"])
            self.emit_linewin_events()
            self.win_manager.update_gametype_wins(self.gametype)

        self.end_freespin()

    def run_superspin(self):
        """Re-spin style mode."""
        self.repeat = False
        self.reset_superspin()
        while self.fs < self.tot_fs:
            self.update_freespin()
            self.create_board_reelstrips()
            if self.criteria == "0":
                while len(self.special_syms_on_board["prize"]):
                    self.create_board_reelstrips()
            self.replace_board_with_stickys()
            reveal_event(self)

            new_sticky_symbols = self.check_for_new_prize()
            if len(new_sticky_symbols) > 0:
                new_sticky_event(self, new_sticky_symbols)
                self.fs = 0
                update_freespin_event(self)

        prize_win = self.get_final_board_prize()
        self.win_data = prize_win
        if prize_win["totalWin"] > 0:
            self.win_manager.update_spinwin(prize_win["totalWin"])
            self.win_manager.update_gametype_wins(self.gametype)

        if self.win_manager.spin_win > 0:
            win_info_event(self)
            self.evaluate_wincap()
            set_win_event(self)
        set_total_event(self)

        self.evaluate_finalwin()
