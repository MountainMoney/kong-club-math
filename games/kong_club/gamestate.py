"""Scratch Kong Club spin router — Jul 2 Le Bandit Phase A."""

import random

from src.events.events import freespin_end_event, fs_trigger_event

from game_cluster import GameCluster, spin_trace
from game_events import mode_state_event, progress_fill_event, update_tile_event
from game_override import GameStateOverride


class GameState(GameStateOverride):
    """Route SDK simulations into the scratch state machine."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim, simulation_seed)
        # Coin-game Random() reads this — do not leave it unset (Random(0) never rolls powers
        # on typical boards; first 17 draws of that stream are all coins).
        self.simulation_seed = sim if simulation_seed is None else simulation_seed
        self.repeat = True
        while self.repeat:
            self.reset_book()
            if self.betmode == "feature_spin":
                self.run_feature_spin()
            elif self.betmode == "peak_spin":
                self.run_peak_spin()
            elif self.betmode == "bonus_see":
                self.run_bonus_buy("see")
            elif self.betmode == "bonus_hear":
                self.run_bonus_buy("hear")
            elif self.betmode == "bonus_mystery":
                self.run_mystery_spin()
            elif self.betmode == "bonus_risky":
                self.run_risky_spin()
            else:
                self.run_base_spin()
            self.check_repeat()
        self.imprint_wins()

    def run_base_spin(self):
        self.board_activation_fired_this_spin = False
        self.gametype = self.config.basegame_type
        self.use_reel_family("base")
        if self.reel_set_name == "base_teaser" and (
            self.should_force_initial_scatters() or self.outcome_bucket() == "cap"
        ):
            self.use_reel_family("gamble_dead")
        if self.outcome_bucket() == "cap":
            self.seed_peak_gold_tiles()
        self.draw_prepared_board()
        if self.outcome_bucket() == "cap" and not GameCluster.find_winning_clusters(self.board, self.config):
            self._force_feature_spin_connection()
            self._finalize_initial_board()
        self.resolve_cascade_loop()
        scatter_count = self.count_special_symbols("scatter")
        bonus_hit = (
            scatter_count >= 3
            and not self.wincap_triggered
            and self.outcome_bucket() != "cap"
        )
        if bonus_hit:
            self.triggered_freegame = True
            self.bonus_variant = self.resolve_bonus_variant_from_scatters(scatter_count)
            if self.betmode != "bonus_mystery":
                self.criteria = "freegame"
            # Mode before setWin so the frontend starts See/Hear/Speak on the landed scatters.
            self.speak_direct = self.bonus_variant == "speak"
            mode_name = (
                f"start_bonus_{self.bonus_variant}"
                if self.betmode == "bonus_mystery"
                else f"organic_bonus_{self.bonus_variant}"
            )
            mode_state_event(self, mode_name)
            self.tot_fs = self.config.bonus_spins
        if self.outcome_bucket() == "cap":
            self.apply_cap_topup()
        self.set_end_tumble_event()
        self.log_spin_end("base")
        self.win_manager.update_gametype_wins(self.gametype)

        if bonus_hit:
            if self.betmode != "bonus_mystery":
                fs_trigger_event(self, basegame_trigger=True, freegame_trigger=False)
            self.run_freespin()

        self.evaluate_finalwin()

    def run_feature_spin(self):
        """Full coin bar, one guaranteed cluster, then the coin game. No bonus."""
        self.board_activation_fired_this_spin = False
        self.tumbles_this_spin = 0
        self.triggered_freegame = False
        self.gametype = self.config.basegame_type
        self.use_reel_family("feature")
        self.reset_progress()
        # The bar opens full. A connection (tiny or a wild chain) then runs the coin game.
        self.progress_value = self.progress_threshold
        progress_fill_event(self)
        self.draw_feature_spin_board()
        self.resolve_cascade_loop()
        if (
            not self.board_activation_fired_this_spin
            and not self.wincap_triggered
            and int(getattr(self, "tumbles_this_spin", 0) or 0) > 0
        ):
            self.progress_value = self.progress_threshold
            progress_fill_event(self)
            self.execute_board_activation(refill_after=False)
        self.triggered_freegame = False
        if self.outcome_bucket() == "cap":
            self.apply_cap_topup()
        self.set_end_tumble_event()
        self.log_spin_end("feature_spin")
        self.win_manager.update_gametype_wins(self.gametype)
        self.evaluate_finalwin()

    def run_peak_spin(self):
        """Trifecta: all-gold board. Half the spins miss. A connection runs one coin game."""
        self.board_activation_fired_this_spin = False
        self.tumbles_this_spin = 0
        self.gametype = self.config.basegame_type
        self.use_reel_family("peak")
        self.reset_progress()
        self.seed_peak_gold_tiles()
        mode_state_event(self, "peak_spin")
        if self.outcome_bucket() == "dead_juicy":
            self.draw_dead_juicy_board()
            self.win_data = {"totalWin": 0.0, "wins": []}
        else:
            self.draw_peak_board()
            self.tumbles_this_spin = 1
            self.progress_value = self.progress_threshold
            progress_fill_event(self)
            self.execute_board_activation(refill_after=False)
        self.set_end_tumble_event()
        self.log_spin_end("peak_spin")
        self.win_manager.update_gametype_wins(self.gametype)
        self.evaluate_finalwin()

    def run_mystery_spin(self):
        """Guaranteed bonus: 50% See / 45% Hear / 5% Speak."""
        variant = {"pick_see": "see", "pick_hear": "hear", "pick_speak": "speak"}.get(
            self.criteria, "see"
        )
        self.run_bonus_buy(variant)

    def run_risky_spin(self):
        """50% dead / 40% Hear / 10% Speak."""
        if self.criteria == "risky_hear":
            self.run_bonus_buy("hear")
            return
        if self.criteria == "risky_speak":
            self.run_bonus_buy("speak")
            return
        self.run_gamble_dead_spin()

    def run_gamble_dead_spin(self):
        """Hard miss: board drops, no clusters, no ST, no bar, no coins."""
        self.board_activation_fired_this_spin = False
        self.tumbles_this_spin = 0
        self.gametype = self.config.basegame_type
        self.use_reel_family("gamble_dead")
        self.draw_gamble_dead_board()
        self.win_data = {"totalWin": 0.0, "wins": []}
        self.set_end_tumble_event()
        self.log_spin_end("gamble_dead")
        self.win_manager.update_gametype_wins(self.gametype)
        self.evaluate_finalwin()

    def run_bonus_buy(self, variant: str):
        self.triggered_freegame = True
        self.bonus_variant = variant
        self.speak_direct = variant == "speak"
        self.upgraded_to_speak = False
        if self.betmode in ("bonus_see", "bonus_hear") and self.outcome_bucket() != "cap":
            self.criteria = f"bonus_{variant}"
        self.tot_fs = self.config.bonus_spins
        mode_state_event(self, f"start_bonus_{variant}")
        self.run_freespin()
        if self.outcome_bucket() == "cap":
            self.apply_cap_topup()
        self.evaluate_finalwin()

    def run_freespin(self):
        self.gametype = self.config.freegame_type
        if not getattr(self, "bonus_variant", None):
            self.bonus_variant = "hear"
        if self.bonus_variant in ("speak", "madness"):
            self.progress_threshold = self.config.progress_thresholds.get("bonus_speak", 5)
        elif self.bonus_variant == "see":
            self.progress_threshold = self.config.progress_thresholds.get("bonus_see", 5)
        else:
            self.progress_threshold = self.config.progress_thresholds.get("bonus_hear", 5)
        # See and Hear start empty. Speak No Evil starts full and refills after each coin game.
        if self.bonus_variant in ("speak", "madness"):
            self.progress_value = self.progress_threshold
        else:
            self.progress_value = 0
        self._hear_upgrade_on_fs = None
        if self.bonus_variant == "hear" and random.random() < float(self.config.hear_to_speak_rate):
            self._hear_upgrade_on_fs = random.randint(1, max(int(self.tot_fs), 1))
        # Which third of the 10 spins is allowed to be the big one.
        if self.bonus_variant in ("see", "hear"):
            # Late spins are naturally richer (tiles stick on Hear, the bar
            # fills later on See). Bias the hot window earlier so each third
            # still lands the best spin at least 15% of the time.
            self.arc_window = random.choices((0, 1, 2), weights=(5, 3, 2))[0]
        progress_fill_event(self)
        self.reset_grid_mults()
        update_tile_event(self)
        while self.fs < self.tot_fs and not self.wincap_triggered:
            self.update_freespin()
            self.board_activation_fired_this_spin = False
            self.board_activations_this_spin = 0
            self.tumbles_this_spin = 0
            variant = getattr(self, "bonus_variant", None) or "see"
            family = "speak" if variant in ("speak", "madness") else variant if variant in ("see", "hear") else "see"
            self.use_reel_family(family, self._bonus_reel_name(variant))
            self._plant_scatters_on_reveal = (
                5 if self.is_hear_bonus() and self.fs == getattr(self, "_hear_upgrade_on_fs", None) else 0
            )
            self.draw_prepared_board()
            self.resolve_cascade_loop()
            self._apply_bonus_scatter_followup()
            if self.is_speak_bonus() and getattr(self, "board_activations_this_spin", 0) == 0:
                self.execute_board_activation(refill_after=True)
            self.set_end_tumble_event()
            self.log_spin_end("bonus")
            self.win_manager.update_gametype_wins(self.gametype)
        freespin_end_event(self)

    def _apply_bonus_scatter_followup(self):
        """Retriggers, and See's 4-scatter upgrade to Hear. No end-of-bonus coin game."""
        if self.wincap_triggered:
            return
        count = self.count_special_symbols("scatter")
        if count < 2:
            return
        extra = 0
        if self.is_see_bonus() and count >= 4:
            self.bonus_variant = "hear"
            extra = 4
            mode_state_event(self, "upgrade_bonus_hear")
        elif self.is_hear_bonus() and count >= 5:
            # Upgrade keeps every tile at its rank and does not take the direct-entry
            # 1,000× floor.
            self.upgraded_to_speak = True
            self.speak_direct = False
            self.bonus_variant = "speak"
            extra = 4
            mode_state_event(self, "upgrade_bonus_speak")
        elif count >= 3:
            extra = 4
        else:
            extra = 2
        self.tot_fs += extra
        fs_trigger_event(self, basegame_trigger=False, freegame_trigger=True)

    def assert_bonus_spin_activation_invariant(self):
        """Phase A: Hear no longer guarantees activation every tumble spin."""
        return

    def log_spin_end(self, mode: str):
        spin_trace(
            f"[SPIN END] mode={mode} progress={self.progress_value}/{self.progress_threshold} "
            f"boardActivationFired={str(self.board_activation_fired_this_spin).lower()} "
            f"totalPayout={round(self.win_manager.spin_win, 2)}x"
        )
