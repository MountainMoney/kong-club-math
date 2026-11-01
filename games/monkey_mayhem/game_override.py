"""Scratch Monkey Mayhem SDK overrides."""

from game_executables import GameExecutables


class GameStateOverride(GameExecutables):
    """Keep only SDK-required hooks; all game behavior lives in GameExecutables/GameState."""

    def reset_book(self):
        super().reset_book()
        self.bonus_variant = None
        self.sticky_wild_positions = []
        self.reset_spin_state(keep_tiles=False)

    def reset_fs_spin(self):
        super().reset_fs_spin()
        self.reset_spin_state(keep_tiles=True)

    def assign_special_sym_function(self):
        pass

    def update_final_win(self) -> None:
        self.final_win = min(round(self.win_manager.running_bet_win, 2), self.config.wincap)
        self.book.payout_multiplier = self.final_win
        self.book.basegame_wins = round(self.win_manager.basegame_wins, 2)
        self.book.freegame_wins = round(self.win_manager.freegame_wins, 2)

    def check_repeat(self) -> None:
        """Use SDK repeat logic so forced freegame books retry until bonus triggers."""
        super().check_repeat()
        if self.repeat:
            return
        from game_criteria import feature_bucket_ok, normalize_bucket, peak_bucket_ok

        bucket = normalize_bucket(self.betmode, self.criteria)
        pay = float(getattr(self, "final_win", 0) or 0)
        tumbles = int(getattr(self, "tumbles_this_spin", 0) or 0)
        if self.betmode == "feature_spin" and not feature_bucket_ok(bucket, pay, tumbles):
            self.repeat = True
        elif self.betmode == "peak_spin" and not peak_bucket_ok(
            bucket, pay, tumbles, float(self.config.wincap)
        ):
            self.repeat = True
        elif bucket == "cap" and abs(pay - float(self.config.wincap)) > 1e-6:
            self.repeat = True
