"""Scratch Kong Club spin router — Jul 2 Le Bandit Phase A."""

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
            elif self.betmode == "bonus_gamble":
                self.run_gamble_spin()
            else:
                self.run_base_spin()
            self.check_repeat()
        self.imprint_wins()

    def run_base_spin(self):
        self.board_activation_fired_this_spin = False
        self.gametype = self.config.basegame_type
        self.reelstrip_id = self.config.initial_reelstrip_id(self.betmode, self.gametype)
        self.reelstrip = self.config.reels[self.reelstrip_id]
        self.refill_strip = self.config.reels[
            self.config.tumble_refill_reel_ids.get(self.reelstrip_id, "REFILL_BASE")
        ]
        if self.outcome_bucket() == "cap":
            self.seed_peak_gold_tiles()
        self.draw_prepared_board()
        if self.outcome_bucket() == "cap" and not GameCluster.find_winning_clusters(self.board, self.config):
            self._force_feature_spin_connection()
            self._finalize_initial_board()
        scatter_count = self.count_special_symbols("scatter")
        self.resolve_cascade_loop()
        bonus_hit = (
            scatter_count >= 3
            and not self.wincap_triggered
            and self.outcome_bucket() != "cap"
        )
        if bonus_hit:
            self.triggered_freegame = True
            self.bonus_variant = self.resolve_bonus_variant_from_scatters(scatter_count)
            if self.betmode != "bonus_gamble":
                self.criteria = "freegame"
            # Mode before setWin so FE starts See/Hear/Madness on the landed ST board.
            mode_name = (
                f"start_bonus_{self.bonus_variant}"
                if self.betmode == "bonus_gamble"
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
            if self.betmode != "bonus_gamble":
                fs_trigger_event(self, basegame_trigger=True, freegame_trigger=False)
            self.run_freespin()

        self.evaluate_finalwin()

    def run_feature_spin(self):
        self.board_activation_fired_this_spin = False
        self.gametype = self.config.basegame_type
        self.reelstrip_id = self.config.initial_reelstrip_id(self.betmode, self.gametype)
        self.reelstrip = self.config.reels[self.reelstrip_id]
        self.refill_strip = self.config.reels[
            self.config.tumble_refill_reel_ids.get(self.reelstrip_id, "FEATURE_SPIN_REFILL")
        ]
        self.reset_progress()
        # Bar starts full; every spin connects, then coin game waits for cascade idle.
        progress_fill_event(self)
        self.draw_feature_spin_board()
        self.resolve_cascade_loop()
        if self.outcome_bucket() == "cap":
            self.apply_cap_topup()
        self.set_end_tumble_event()
        self.log_spin_end("feature_spin")
        self.win_manager.update_gametype_wins(self.gametype)
        self.evaluate_finalwin()

    def run_peak_spin(self):
        """1000× PEAK: gold chrome/coins, Feature strips; dead land, silent cluster trigger."""
        self.board_activation_fired_this_spin = False
        self.gametype = self.config.basegame_type
        self.reelstrip_id = self.config.initial_reelstrip_id(self.betmode, self.gametype)
        self.reelstrip = self.config.reels[self.reelstrip_id]
        self.refill_strip = self.config.reels[
            self.config.tumble_refill_reel_ids.get(self.reelstrip_id, "REFILL_BASE")
        ]
        self.reset_progress()
        mode_state_event(self, "peak_spin")
        self.seed_peak_gold_tiles()
        progress_fill_event(self)
        self.draw_peak_board()
        self.resolve_cascade_loop()
        if self.outcome_bucket() == "cap":
            self.apply_cap_topup()
        self.set_end_tumble_event()
        self.log_spin_end("peak_spin")
        self.win_manager.update_gametype_wins(self.gametype)
        self.evaluate_finalwin()

    def run_gamble_spin(self):
        if self.should_force_initial_scatters():
            self.run_base_spin()
            return
        self.run_gamble_dead_spin()

    def run_gamble_dead_spin(self):
        """Hard miss: board drops, no clusters, no ST, no bar, no coins."""
        self.board_activation_fired_this_spin = False
        self.tumbles_this_spin = 0
        self.gametype = self.config.basegame_type
        self.reelstrip_id = self.config.initial_reelstrip_id(self.betmode, self.gametype)
        self.reelstrip = self.config.reels[self.reelstrip_id]
        self.refill_strip = self.config.reels[
            self.config.tumble_refill_reel_ids.get(self.reelstrip_id, "REFILL_BASE")
        ]
        self.draw_gamble_dead_board()
        self.win_data = {"totalWin": 0.0, "wins": []}
        self.set_end_tumble_event()
        self.log_spin_end("gamble_dead")
        self.win_manager.update_gametype_wins(self.gametype)
        self.evaluate_finalwin()

    def run_bonus_buy(self, variant: str):
        self.triggered_freegame = True
        self.bonus_variant = variant
        self.criteria = f"bonus_{variant}"
        self.tot_fs = self.config.bonus_spins
        mode_state_event(self, f"start_bonus_{variant}")
        self.run_freespin()
        self.evaluate_finalwin()

    def run_freespin(self):
        self.gametype = self.config.freegame_type
        if not getattr(self, "bonus_variant", None):
            self.bonus_variant = "hear"
        if self.bonus_variant == "madness":
            self.progress_threshold = self.config.progress_thresholds.get("bonus_madness", 5)
        elif self.bonus_variant == "see":
            self.progress_threshold = self.config.progress_thresholds.get("bonus_see", 5)
        else:
            self.progress_threshold = self.config.progress_thresholds.get("bonus_hear", 5)
        # See / Hear start at 0. Madness starts full (Feature-like) for the whole bonus.
        if self.bonus_variant == "madness":
            self.progress_value = self.progress_threshold
        else:
            self.progress_value = 0
        progress_fill_event(self)
        self.reset_grid_mults()
        update_tile_event(self)
        while self.fs < self.tot_fs and not self.wincap_triggered:
            self.update_freespin()
            self.board_activation_fired_this_spin = False
            self.board_activations_this_spin = 0
            self.tumbles_this_spin = 0
            self.reelstrip_id = self.config.initial_reelstrip_id(
                self.betmode,
                self.gametype,
                getattr(self, "bonus_variant", None),
            )
            self.reelstrip = self.config.reels[self.reelstrip_id]
            self.refill_strip = self.config.reels[self.config.tumble_refill_reel_ids[self.reelstrip_id]]
            self.draw_prepared_board()
            self.resolve_cascade_loop()
            if self.is_madness_bonus() and getattr(self, "board_activations_this_spin", 0) == 0:
                self.execute_board_activation(refill_after=True)
            self.set_end_tumble_event()
            self.log_spin_end("bonus")
            self.win_manager.update_gametype_wins(self.gametype)
        freespin_end_event(self)

    def assert_bonus_spin_activation_invariant(self):
        """Phase A: Hear no longer guarantees activation every tumble spin."""
        return

    def log_spin_end(self, mode: str):
        spin_trace(
            f"[SPIN END] mode={mode} progress={self.progress_value}/{self.progress_threshold} "
            f"boardActivationFired={str(self.board_activation_fired_this_spin).lower()} "
            f"totalPayout={round(self.win_manager.spin_win, 2)}x"
        )
