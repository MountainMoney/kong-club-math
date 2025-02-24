import random
from src.state.books import Book


class SpinState:
    def __init__(self, sim: int, criteria: str, win_manager: object):
        self.sim = sim
        self.criteria = criteria
        self.win_manager = win_manager
        self.book = Book(sim)
        self.reset_book()

    def reset_book(self) -> None:
        """Reset global simulation variables."""
        self.board = [[[] for _ in range(self.config.num_rows[x])] for x in range(self.config.num_reels)]
        self.top_symbols = None
        self.bottom_symbols = None
        self.book_id = self.sim + 1
        self.book = Book(self.book_id)
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

    def reset_fs_spin(self) -> None:
        """Use if using repeat during freespin games."""
        self.triggered_freespins = True
        self.fs = 0
        self.gametype = self.config.freegame_type
        self.win_manager.reset_spin_win()

    def reset_seed(self, sim: int = 0) -> None:
        """Reset rng seed to simulation number for reproducibility."""
        random.seed(sim + 1)
        self.sim = sim

    def get_wincap_triggered(self) -> bool:
        """Break out of spin progress if max-win is triggered."""
        if self.wincap_triggered:
            return True
        return False

    def update_final_win(self) -> None:
        """Separate base and freegame wins, verify the sum of there are equal to the final simulation payout."""
        final = round(min(self.win_manager.running_bet_win, self.config.wincap), 2)
        basewin = round(min(self.win_manager.basegame_wins, self.config.wincap), 2)
        freewin = round(min(self.win_manager.freegame_wins, self.config.wincap), 2)

        self.final_win = final
        self.book.payout_multiplier = self.final_win
        self.book.basegame_wins = basewin
        self.book.freegame_wins = freewin

        assert min(
            round(self.win_manager.basegame_wins + self.win_manager.freegame_wins, 2),
            self.config.wincap,
        ) == round(
            min(self.win_manager.running_bet_win, self.config.wincap), 2
        ), "Base + Free game payout mismatch!"
        assert min(
            round(self.book.basegame_wins + self.book.freegame_wins, 2),
            self.config.wincap,
        ) == min(
            round(self.book.payout_multiplier, 2), round(self.config.wincap, 2)
        ), "Base + Free game payout mismatch!"

    def check_repeat(self) -> None:
        """Checks if the spin failed a criteria constraint at any point."""
        if self.repeat is False:
            win_criteria = self.get_current_betmode_distributions().get_win_criteria()
            if win_criteria is not None and self.final_win != win_criteria:
                self.repeat = True

            if self.get_current_distribution_conditions()["force_freespins"] and not (self.triggered_freespins):
                self.repeat = True
