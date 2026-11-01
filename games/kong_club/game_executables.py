"""Scratch Kong Club state-machine mechanics — Jul 2 Le Bandit Phase A."""

from __future__ import annotations

import random
from copy import copy

from src.events.events import (
    reveal_event,
    update_freespin_event,
    win_info_event,
    update_tumble_win_event,
    wincap_event,
)

from game_calculations import GameCalculations
from game_cluster import GameCluster, spin_trace
from game_coin_feature import remove_coins_from_board, resolve_coin_game
from game_criteria import normalize_bucket
from src.calculations.statistics import get_random_outcome
from game_events import (
    board_activation_event,
    coin_seed_event,
    mode_state_event,
    progress_fill_event,
    scatter_payout_event,
    tumble_board_event,
    update_tile_event,
)


class GameExecutables(GameCalculations):
    """One authoritative state machine for Jul 2 Le Bandit Phase A."""

    def reset_grid_mults(self):
        self.tile_levels = [
            [0 for _ in range(self.config.num_rows[reel])]
            for reel in range(self.config.num_reels)
        ]
        # Feature / PEAK cluster-pay ranks — seeds must not multiply the first connection.
        self.peak_connection_levels = [
            [0 for _ in range(self.config.num_rows[reel])]
            for reel in range(self.config.num_reels)
        ]
        self.sync_position_multipliers()

    def sync_position_multipliers(self):
        self.position_multipliers = [
            [self.level_to_multiplier(level) for level in reel]
            for reel in self.tile_levels
        ]

    def level_to_multiplier(self, level: int) -> int:
        if level <= 0:
            return 0
        idx = min(level, self.config.max_tile_level) - 1
        return self.config.multiplier_table[idx]

    def reset_progress(self):
        mode = getattr(self, "betmode", "base")
        variant = getattr(self, "bonus_variant", None)
        if variant == "hear":
            key = "bonus_hear"
        elif variant == "madness":
            key = "bonus_madness"
        else:
            key = mode
        self.progress_threshold = self.config.progress_thresholds.get(key, 5)
        self.progress_value = (
            self.progress_threshold if mode == "feature_spin" or variant == "madness" else 0
        )
        self.progress_activation_count = 0

    def reset_spin_state(self, keep_tiles=False):
        if not keep_tiles:
            self.reset_grid_mults()
        self.reset_progress()
        self.board_activation_fired_this_spin = False
        self.board_activations_this_spin = 0
        self.board_coin_values: dict[tuple[int, int], float] = {}
        self.sticky_wild_positions = []
        betmode = getattr(self, "betmode", "base")
        gametype = getattr(self, "gametype", self.config.basegame_type)
        self.reelstrip_id = self.config.initial_reelstrip_id(betmode, gametype)
        self.reelstrip = self.config.reels[self.reelstrip_id]
        self.refill_strip = self.config.reels[self.config.tumble_refill_reel_ids[self.reelstrip_id]]
        self.reel_positions = [0] * self.config.num_reels
        self.padding_position = [0] * self.config.num_reels
        self.top_symbols = [self.create_symbol("T") for _ in range(self.config.num_reels)]
        self.bottom_symbols = [self.create_symbol("T") for _ in range(self.config.num_reels)]
        self.new_symbols_from_tumble = [[] for _ in range(self.config.num_reels)]
        self.removed_symbols = []
        self.win_data = {"totalWin": 0.0, "wins": []}

    def create_symbol(self, name: str):
        return self.symbol_storage.create_symbol(name)

    def _draw_from_strip(self, reel: int, strip: list[str], advance=True):
        if strip and isinstance(strip[0], list):
            strip = strip[reel]
        pos = self.reel_positions[reel] % len(strip)
        name = strip[pos]
        if advance:
            self.reel_positions[reel] = (pos + 1) % len(strip)
        return self.create_symbol(name)

    def is_bonus_mode(self) -> bool:
        return self.gametype == self.config.freegame_type or self.betmode in (
            "bonus_see",
            "bonus_hear",
            "bonus_madness",
        )

    def is_hear_bonus(self) -> bool:
        return self.is_bonus_mode() and getattr(self, "bonus_variant", None) == "hear"

    def is_madness_bonus(self) -> bool:
        return self.is_bonus_mode() and getattr(self, "bonus_variant", None) == "madness"

    def is_see_bonus(self) -> bool:
        return self.is_bonus_mode() and getattr(self, "bonus_variant", None) == "see"

    def should_force_initial_scatters(self) -> bool:
        if self.is_bonus_mode():
            return False
        conditions = self.get_current_distribution_conditions()
        if not isinstance(conditions, dict):
            return False
        return bool(conditions.get("force_freegame"))

    def resolve_forced_scatter_count(self) -> int:
        """Pick scatter count from distribution conditions (Football Fiesta pattern)."""
        conditions = self.get_current_distribution_conditions()
        if not isinstance(conditions, dict):
            count = 4
        else:
            triggers = conditions.get("scatter_triggers")
            if not triggers:
                count = 4
            else:
                count = int(get_random_outcome(triggers))
        floor = 4 if getattr(self, "betmode", None) == "bonus_gamble" else 3
        return min(max(count, floor), self.config.num_reels)

    def _fill_initial_board(self):
        """Random stop per reel. No book events — callers reveal once."""
        attempts = 0
        while True:
            attempts += 1
            wild_count = 0
            board = []
            top_symbols = []
            bottom_symbols = []
            for reel in range(self.config.num_reels):
                strip = self.reelstrip[reel]
                start = random.randrange(0, len(strip))
                self.reel_positions[reel] = (start + self.config.num_rows[reel]) % len(strip)
                top_symbols.append(self.create_symbol(strip[(start - 1) % len(strip)]))
                column = []
                for row in range(self.config.num_rows[reel]):
                    sym = self.create_symbol(strip[(start + row) % len(strip)])
                    wild_count += int(sym.name == self.config.standard_wild)
                    column.append(sym)
                bottom_symbols.append(
                    self.create_symbol(strip[(start + self.config.num_rows[reel]) % len(strip)])
                )
                board.append(column)
            if wild_count <= self.config.max_initial_wilds or attempts >= 20:
                self.board = board
                self.top_symbols = top_symbols
                self.bottom_symbols = bottom_symbols
                break

    def _finalize_initial_board(self):
        if self.should_force_initial_scatters():
            self.force_initial_scatters(self.resolve_forced_scatter_count())
            self.apply_scatter_anticipation()
        self.apply_gamble_two_bait()

        # Phase A: sticky HEAR disabled — never apply / refresh / level stickies.
        self.sticky_wild_positions = []

        self.get_special_symbols_on_board()
        self.prepare_landed_specials(initial_fill=True)
        reveal_event(self)

    def draw_prepared_board(self):
        """Initial fill: choose a random start per column and read 5 symbols downward."""
        self._fill_initial_board()
        self._finalize_initial_board()

    def outcome_bucket(self) -> str:
        return normalize_bucket(getattr(self, "betmode", ""), getattr(self, "criteria", ""))

    def draw_feature_spin_board(self):
        """Plant the Feature toy (full bar), then a board that matches the bucket."""
        if self.outcome_bucket() == "dead_juicy":
            self.draw_dead_juicy_board()
            return
        for _ in range(80):
            self._fill_initial_board()
            if GameCluster.find_winning_clusters(self.board, self.config):
                self._finalize_initial_board()
                return
        self._force_feature_spin_connection()
        self._finalize_initial_board()

    def draw_dead_juicy_board(self):
        """Toy stays visible (bar / gold). No 5-cluster, no ST. No pity connect."""
        filled = False
        for _ in range(80):
            self._fill_initial_board()
            if not GameCluster.find_winning_clusters(self.board, self.config) and not self._board_has_scatter():
                filled = True
                break
        if not filled:
            self._strip_board_scatters()
            for _ in range(12):
                if not GameCluster.find_winning_clusters(self.board, self.config):
                    break
                self._break_winning_clusters()
        self._finalize_initial_board()

    def draw_peak_board(self):
        """Gold chrome already seeded. Dead bucket must not connect."""
        if self.outcome_bucket() == "dead_juicy":
            self.draw_dead_juicy_board()
            return
        for _ in range(80):
            self._fill_initial_board()
            if GameCluster.find_winning_clusters(self.board, self.config):
                self._finalize_initial_board()
                return
        self._force_feature_spin_connection()
        self._finalize_initial_board()

    def apply_cap_topup(self):
        """Cap books: after a real toy reveal, land exactly on wincap."""
        if self.outcome_bucket() != "cap":
            return
        remaining = max(0.0, self.config.wincap - self.win_manager.running_bet_win)
        if remaining <= 1e-9:
            return
        self.win_manager.update_spinwin(remaining)
        self.wincap_triggered = True
        wincap_event(self)

    def _board_has_scatter(self) -> bool:
        scatter = self.config.scatter_symbol
        return any(symbol.name == scatter for reel in self.board for symbol in reel)

    def _strip_board_scatters(self) -> None:
        filler = self.config.low_symbols[0]
        scatter = self.config.scatter_symbol
        for reel in range(self.config.num_reels):
            for row in range(self.config.num_rows[reel]):
                if self.board[reel][row].name == scatter:
                    self.board[reel][row] = self.create_symbol(filler)

    def _break_winning_clusters(self) -> None:
        clusters = GameCluster.find_winning_clusters(self.board, self.config)
        for cluster in clusters:
            reel, row = cluster.positions[0]
            current = self.board[reel][row].name
            alt = next(
                (symbol for symbol in self.config.low_symbols if symbol != current),
                self.config.high_symbols[0],
            )
            self.board[reel][row] = self.create_symbol(alt)

    def draw_gamble_dead_board(self):
        """Gamble miss: no 5-connect. Always 2 ST on reels 0–1 as tease bait."""
        filled = False
        for _ in range(80):
            self._fill_initial_board()
            if not GameCluster.find_winning_clusters(self.board, self.config) and not self._board_has_scatter():
                filled = True
                break
        if not filled:
            self._strip_board_scatters()
            for _ in range(12):
                if not GameCluster.find_winning_clusters(self.board, self.config):
                    break
                self._break_winning_clusters()
        self.apply_gamble_two_bait()
        self._finalize_initial_board()

    def apply_gamble_two_bait(self):
        """Every gamble trigger land: ST on reels 0 and 1, then tease. No rate."""
        if getattr(self, "betmode", None) != "bonus_gamble":
            return
        if getattr(self, "gametype", None) == self.config.freegame_type:
            return
        scatter = self.config.scatter_symbol
        for reel in (0, 1):
            if any(getattr(symbol, "name", None) == scatter for symbol in self.board[reel]):
                continue
            row = random.randrange(0, self.config.num_rows[reel])
            self.board[reel][row] = self.create_symbol(scatter)
        self.apply_scatter_anticipation()

    def _force_feature_spin_connection(self):
        """Guarantee a 5-wide orthogonal cluster on the top row."""
        symbol = self.config.low_symbols[0]
        for reel in range(5):
            self.board[reel][0] = self.create_symbol(symbol)

    def force_initial_scatters(self, count: int):
        """Place exactly `count` scatters on distinct reels (max one per reel)."""
        reels = list(range(min(count, self.config.num_reels)))
        for reel in reels:
            row = random.randrange(0, self.config.num_rows[reel])
            self.board[reel][row] = self.create_symbol(self.config.scatter_symbol)

    def apply_scatter_anticipation(self):
        """Tease after the 2nd ST through the 5th ST reel, or through the last reel."""
        scatter_reels = []
        for reel in range(self.config.num_reels):
            if any(getattr(symbol, "name", None) == self.config.scatter_symbol for symbol in self.board[reel]):
                scatter_reels.append(reel)
        anticipation = [0] * self.config.num_reels
        if len(scatter_reels) >= 2:
            last_tease = scatter_reels[4] if len(scatter_reels) >= 5 else self.config.num_reels - 1
            tease = 1
            for reel in range(scatter_reels[1] + 1, last_tease + 1):
                anticipation[reel] = tease
                tease += 1
        self.anticipation = anticipation

    def resolve_bonus_variant_from_scatters(self, scatter_count: int) -> str:
        """3 ST = See. 4 ST = Hear. 5+ ST = Monkey Madness."""
        variant_map = getattr(self.config, "bonus_variant_map", {3: "see", 4: "hear", 5: "madness", 6: "madness"})
        if scatter_count in variant_map:
            return variant_map[scatter_count]
        if scatter_count >= 5:
            return "madness"
        if scatter_count >= 4:
            return "hear"
        if scatter_count >= 3:
            return "see"
        return "hear"

    def seed_peak_gold_tiles(self):
        """PEAK: every cell starts gold (level 3). Clusters still have to connect."""
        if not getattr(self.config, "peak_spin_seed_gold", True):
            return
        gold = int(self.config.max_tile_level)
        for reel in range(self.config.num_reels):
            for row in range(self.config.num_rows[reel]):
                self.seed_tile_to_level(reel, row, gold)
        update_tile_event(self)

    def prepare_landed_specials(self, initial_fill=False):
        """Seed tiles + assign coin values when CB/CS/CG land."""
        self.get_special_symbols_on_board()
        if not hasattr(self, "board_coin_values") or self.board_coin_values is None:
            self.board_coin_values = {}

        seeds = []
        for reel in range(self.config.num_reels):
            for row in range(self.config.num_rows[reel]):
                sym = self.board[reel][row]
                if sym.name not in self.config.coin_symbols:
                    continue
                if (reel, row) in self.board_coin_values:
                    continue
                seed_level = self.config.coin_seed_levels[sym.name]
                self.seed_tile_to_level(reel, row, seed_level)
                value = float(random.choice(self.config.coin_values[sym.name]))
                self.board_coin_values[(reel, row)] = value
                seeds.append(self._seed_payload(reel, row, sym.name, value))

        if seeds:
            coin_seed_event(self, seeds)
            update_tile_event(self)

    def multiplier_to_level(self, multiplier: int) -> int:
        level = 1
        for idx, value in enumerate(self.config.multiplier_table, start=1):
            if value <= multiplier:
                level = idx
        return level

    def seed_tile_to_level(self, reel: int, row: int, level: int):
        self.tile_levels[reel][row] = min(
            max(self.tile_levels[reel][row], int(level)),
            self.config.max_tile_level,
        )
        self.position_multipliers[reel][row] = self.level_to_multiplier(self.tile_levels[reel][row])

    def increment_tile(self, reel: int, row: int):
        current = max(self.tile_levels[reel][row], 0)
        # 5ST / Monkey Madness: no bronze — first connection is silver, then gold.
        if self.is_madness_bonus() and current < 2:
            next_level = 2
        else:
            next_level = current + 1
        self.tile_levels[reel][row] = min(next_level, self.config.max_tile_level)
        self.position_multipliers[reel][row] = self.level_to_multiplier(self.tile_levels[reel][row])

    def _seed_payload(self, reel, row, symbol, value=None):
        payload = {
            "reel": reel,
            "row": row,
            "symbol": symbol,
            "seedLevel": self.tile_levels[reel][row],
            "multiplier": self.position_multipliers[reel][row],
        }
        if value is not None:
            payload["coinValue"] = value
        return payload

    def sticky_position_set(self) -> set[tuple[int, int]]:
        """Phase A: sticky HEAR disabled."""
        return set()

    def detect_clusters(self):
        clusters = GameCluster.find_winning_clusters(self.board, self.config)
        GameCluster.log_winning_clusters(clusters)
        return clusters

    def activate_tiles_from_clusters(self, clusters):
        """Increment tile level only on connected cluster cells (incl. wilds in those clusters).

        Super Cascade still deletes every cell of each winning type — but non-connected
        same-type cells that get deleted do NOT receive a Level-Up Tile rank.
        """
        if not clusters:
            return
        positions: set[tuple[int, int]] = set()
        for cluster in clusters:
            positions.update(cluster.positions)
            positions.update(cluster.wild_positions)

        changed = False
        seeded_buy = getattr(self, "betmode", None) == "peak_spin"
        if seeded_buy and not hasattr(self, "peak_connection_levels"):
            self.peak_connection_levels = [
                [0 for _ in range(self.config.num_rows[reel])]
                for reel in range(self.config.num_reels)
            ]
        for reel, row in positions:
            if 0 <= reel < self.config.num_reels and 0 <= row < self.config.num_rows[reel]:
                self.increment_tile(reel, row)
                if seeded_buy:
                    current = self.peak_connection_levels[reel][row]
                    self.peak_connection_levels[reel][row] = min(
                        current + 1, self.config.max_tile_level
                    )
                changed = True
        if changed:
            update_tile_event(self)

    def mark_level_up_tiles(self, clusters):
        self.activate_tiles_from_clusters(clusters)

    def mark_removed_symbols(self, winning_types: set[str], clusters=None):
        cluster_wild_positions = set()
        for cluster in clusters or []:
            cluster_wild_positions.update(cluster.wild_positions)
        coin_symbols = set(self.config.coin_symbols)
        self.removed_symbols = []
        for reel in range(self.config.num_reels):
            for row in range(self.config.num_rows[reel]):
                sym = self.board[reel][row]
                sym.explode = False
                # Coins never explode/remove via cascade.
                if sym.name in coin_symbols:
                    continue
                if sym.name in winning_types or (reel, row) in cluster_wild_positions:
                    sym.explode = True
                    self.removed_symbols.append({"reel": reel, "row": row, "symbol": sym.name})
        if self.removed_symbols:
            spin_trace(f"Removed symbols: {self.removed_symbols}")

    def award_clusters(self, clusters):
        self.win_data = self.evaluate_clusters(clusters)
        amount = self.win_data["totalWin"]
        if amount <= 0:
            return
        # Sticky FS boards light most cells — downscale cluster pays in bonus only.
        if self.is_bonus_mode():
            bonus_scale = float(getattr(self.config, "bonus_cluster_pay_scale", 1.0))
            if bonus_scale != 1.0:
                amount = round(amount * bonus_scale, 6)
                for win in self.win_data["wins"]:
                    win["win"] = round(float(win["win"]) * bonus_scale, 6)
                self.win_data["totalWin"] = amount
        remaining = max(0.0, self.config.wincap - self.win_manager.running_bet_win)
        paid = min(amount, remaining)
        if paid < amount:
            scale = paid / amount if amount else 0
            for win in self.win_data["wins"]:
                win["win"] *= scale
            self.win_data["totalWin"] = paid
        self.win_manager.update_spinwin(paid)
        self.win_manager.tumble_win = paid
        if self.win_manager.running_bet_win >= self.config.wincap:
            self.wincap_triggered = True
            wincap_event(self)

    def gravity_and_refill(self, emit_event=True):
        self.board_before_tumble = copy(self.board)
        old_coin_values = dict(getattr(self, "board_coin_values", {}) or {})
        new_coin_values: dict[tuple[int, int], float] = {}
        self.new_symbols_from_tumble = [[] for _ in range(self.config.num_reels)]
        for reel in range(self.config.num_reels):
            column = self.board[reel]
            survivors = []
            survivor_values = []
            for row, sym in enumerate(column):
                if getattr(sym, "explode", False):
                    continue
                survivors.append(sym)
                survivor_values.append(old_coin_values.get((reel, row)))
            gap_count = self.config.num_rows[reel] - len(survivors)
            new_column = [None] * gap_count + survivors
            for slot in range(gap_count):
                sym = self._draw_from_strip(reel, self.refill_strip)
                sym.explode = False
                new_column[slot] = sym
                self.new_symbols_from_tumble[reel].append(sym)
            for idx, value in enumerate(survivor_values):
                if value is not None:
                    new_coin_values[(reel, gap_count + idx)] = value
            if any(sym is None for sym in new_column):
                raise RuntimeError(f"column {reel} still has empty cells after refill")
            for sym in new_column:
                sym.explode = False
            self.board[reel] = new_column
            if gap_count:
                spin_trace(
                    f"Refill column {reel}: "
                    f"{[sym.name for sym in self.new_symbols_from_tumble[reel]]}"
                )
        self.board_coin_values = new_coin_values
        self.sticky_wild_positions = []
        self.get_special_symbols_on_board()
        self.prepare_landed_specials(initial_fill=False)
        if emit_event:
            tumble_board_event(self)

    def _hear_activation_cap_reached(self) -> bool:
        cap = getattr(self.config, "max_board_activations_hear", 3)
        return self.is_hear_bonus() and getattr(self, "board_activations_this_spin", 0) >= cap

    def advance_progress(self, tumble_steps: int = 1, *, activate: bool = True):
        if tumble_steps <= 0:
            return
        if self.board_activation_fired_this_spin and self.gametype == self.config.basegame_type:
            return
        if self._hear_activation_cap_reached():
            return
        self.progress_value = min(self.progress_value + tumble_steps, self.progress_threshold)
        spin_trace(
            f"Progress: {self.progress_value}/{self.progress_threshold} "
            f"(+{tumble_steps} tumble{'s' if tumble_steps != 1 else ''})"
        )
        progress_fill_event(self)
        if (
            activate
            and self.progress_value >= self.progress_threshold
            and not self.board_activation_fired_this_spin
        ):
            # Tests / forced fills may activate here. Live spins wait for cascade idle.
            self.execute_board_activation(refill_after=True)

    def check_progress_bar(self):
        """Activate only when the bar is full and the cascade is idle."""
        if self._hear_activation_cap_reached():
            return
        # Dead Feature / PEAK spins must not fire empty boardActivation after reveal.
        if self.betmode in ("feature_spin", "peak_spin") and getattr(self, "tumbles_this_spin", 0) <= 0:
            return
        if self.progress_value >= self.progress_threshold and not self.board_activation_fired_this_spin:
            self.execute_board_activation(refill_after=True)

    def execute_board_activation(self, refill_after: bool = False):
        # Base + Feature + Madness: one board activation per spin.
        if self.board_activation_fired_this_spin and (
            self.gametype == self.config.basegame_type or self.is_madness_bonus()
        ):
            return
        if self._hear_activation_cap_reached():
            return
        self.board_activation_fired_this_spin = True
        self.board_activations_this_spin = getattr(self, "board_activations_this_spin", 0) + 1
        trigger_progress = self.progress_value
        total, items, rounds = resolve_coin_game(self)
        self.progress_activation_count += 1
        spin_trace(
            f"[BOARD ACTIVATION TRIGGERED] progress={trigger_progress} "
            f"reveals={len(items)} rounds={rounds} totalPayout={round(total, 2)}x"
        )
        if total > 0:
            remaining = max(0.0, self.config.wincap - self.win_manager.running_bet_win)
            total = min(total, remaining)
            self.win_manager.update_spinwin(total)
        board_activation_event(self, total, items, rounds)
        if total > 0:
            update_tumble_win_event(self)

        removed = remove_coins_from_board(self)
        self.progress_value = 0
        progress_fill_event(self)
        if self.is_madness_bonus():
            # Stay full (Feature-like). Do not unlock a second coin game on later tumbles.
            self.progress_value = self.progress_threshold
            progress_fill_event(self)
        elif self.is_bonus_mode():
            # Hear / See may chain multiple activations in one spin; base stays capped at one.
            self.board_activation_fired_this_spin = False
        if refill_after and removed:
            self.gravity_and_refill(emit_event=True)
        elif removed:
            # Coins already marked explode; upcoming gravity clears them.
            for reel, row in removed:
                if 0 <= reel < self.config.num_reels and 0 <= row < self.config.num_rows[reel]:
                    self.board[reel][row].explode = True
        if self.win_manager.running_bet_win >= self.config.wincap:
            self.wincap_triggered = True
            wincap_event(self)

    def resolve_cascade_loop(self):
        if self.betmode == "peak_spin":
            # SUMMIT: dead land. A silent 5+ cluster still fills the bar / coin game.
            # No cluster pay, no winInfo, no cascade.
            self.tumbles_this_spin = 0
            self.win_data = {"totalWin": 0.0, "wins": []}
            if self.detect_clusters():
                self.tumbles_this_spin = 1
                self.advance_progress(1, activate=False)
            self.check_progress_bar()
            return
        step = 0
        self.tumbles_this_spin = 0
        while not self.wincap_triggered:
            while not self.wincap_triggered:
                clusters = self.detect_clusters()
                if not clusters:
                    self.win_data = {"totalWin": 0.0, "wins": []}
                    break
                step += 1
                self.tumbles_this_spin = step
                if step > self.config.max_tumbles_per_spin:
                    mode_state_event(self, "max_tumble_safety_stop")
                    break
                winning_types = {cluster.symbol for cluster in clusters}
                # Light connected cells first, then pay base × sum of those 2/5/10 multipliers.
                self.mark_level_up_tiles(clusters)
                self.award_clusters(clusters)
                self.mark_removed_symbols(winning_types, clusters)
                win_info_event(self)
                update_tumble_win_event(self)
                if self.wincap_triggered:
                    break
                # Base: +1 per tumble. See/Hear: +1 per cluster connection.
                if self.is_bonus_mode():
                    for _ in clusters:
                        if self.progress_value >= self.progress_threshold:
                            break
                        self.advance_progress(1, activate=False)
                else:
                    self.advance_progress(1, activate=False)
                self.gravity_and_refill(emit_event=True)
            if self.wincap_triggered:
                break
            # Bar full (or Feature prefilled) — coin game only after all cluster tumbles stop.
            self.check_progress_bar()
            if step > self.config.max_tumbles_per_spin:
                break
            # Coin-removal refill can create leftover clusters; pay those next (no mid-tumble coin game).
            if self.detect_clusters() and not self.wincap_triggered:
                continue
            break

    def award_scatter_payout(self):
        if not self.config.scatter_pays:
            return
        count = min(self.count_special_symbols("scatter"), max(self.config.scatter_pays))
        payout = self.config.scatter_pays.get(count, 0)
        if payout <= 0:
            return
        scatter_payout_event(self, count, payout)
        remaining = max(0.0, self.config.wincap - self.win_manager.running_bet_win)
        self.win_manager.update_spinwin(min(payout, remaining))

    def set_end_tumble_event(self):
        from src.events.events import set_win_event, set_total_event

        if self.win_manager.spin_win > 0:
            set_win_event(self)
        set_total_event(self)

    def update_freespin(self) -> None:
        self.fs += 1
        update_freespin_event(self)
        self.win_manager.reset_spin_win()
        self.win_data = {"totalWin": 0.0, "wins": []}

    def ensure_feature_spin_coin_game(self):
        """Feature Spin activates after the cascade is idle — no force."""
        return

    def run_activation_if_prefilled(self):
        """Feature Spin waits for a winning tumble, then idle, before activating."""
        return
