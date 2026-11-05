"""Scratch Kong Club SDK overrides."""

from game_executables import GameExecutables


class GameStateOverride(GameExecutables):
    """Keep only SDK-required hooks; all game behavior lives in GameExecutables/GameState."""

    def reset_book(self):
        super().reset_book()
        self.bonus_variant = None
        self.speak_direct = False
        self.upgraded_to_speak = False
        self.coin_game_cap_hit = False
        self.sticky_wild_positions = []
        self.reset_spin_state(keep_tiles=False)
        if int(getattr(self, "repeat_count", 0) or 0) == 0:
            self._locked_base_kind = None
            self.want_near_miss = False

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
        elif self.betmode == "peak_spin" and bucket == "live" and pay <= 1e-9:
            self.repeat = True
        elif bucket == "cap" and abs(pay - float(self.config.wincap)) > 1e-6:
            self.repeat = True
        elif getattr(self, "coin_game_cap_hit", False):
            # The 10-rerun cap is a reject. Shipped books never record it.
            self.repeat = True
        elif getattr(self, "want_near_miss", False) and int(getattr(self, "repeat_count", 0) or 0) < 6:
            if int(getattr(self, "progress_value", 0) or 0) < 8 and not getattr(self, "board_activation_fired_this_spin", False):
                self.repeat = True
        elif getattr(self, "force_tiny_hit", False) and int(getattr(self, "repeat_count", 0) or 0) < 18:
            pay_cents = int(round(pay * 100))
            if not 19 <= pay_cents <= 55:
                self.repeat = True
        elif getattr(self, "speak_direct", False) and not getattr(self, "upgraded_to_speak", False):
            floor = float(getattr(self.config, "speak_direct_min_win", 1000.0) or 0.0)
            # Direct Speak only. An upgrade out of Hear does not take the floor.
            if pay + 1e-9 < floor and abs(pay - float(self.config.wincap)) > 1e-6:
                self.repeat = True
        if not self.repeat:
            self._locked_base_kind = None
            self.want_near_miss = False
