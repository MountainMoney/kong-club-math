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
        elif variant in ("speak", "madness"):
            key = "bonus_speak"
        elif variant == "see":
            key = "bonus_see"
        else:
            key = mode
        default_bar = 10 if mode in getattr(self.config, "base_like_modes", set()) or mode == "feature_spin" else 5
        self.progress_threshold = self.config.progress_thresholds.get(key, default_bar)
        # Speak No Evil refills the bar at the start of every spin.
        self.progress_value = self.progress_threshold if variant in ("speak", "madness") else 0
        self.progress_activation_count = 0

    def reset_spin_state(self, keep_tiles=False):
        if not keep_tiles:
            self.reset_grid_mults()
        self.reset_progress()
        self.board_activation_fired_this_spin = False
        self.board_activations_this_spin = 0
        self.progress_cap_override = None
        self.force_bar_fill = False
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
            "bonus_speak",
        )

    def is_hear_bonus(self) -> bool:
        return self.is_bonus_mode() and getattr(self, "bonus_variant", None) == "hear"

    def is_speak_bonus(self) -> bool:
        return self.is_bonus_mode() and getattr(self, "bonus_variant", None) in ("speak", "madness")

    def is_madness_bonus(self) -> bool:
        return self.is_speak_bonus()

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
        floor = 3
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
            # Wilds are uncapped. More than four can land; the strip weights keep that rare.
            self.board = board
            self.top_symbols = top_symbols
            self.bottom_symbols = bottom_symbols
            if attempts >= 12 or not self._columns_artifact():
                break

    def _strip_bonus_triggers(self) -> None:
        """Feature Spin and Trifecta never land a scatter, so they cannot open a bonus."""
        if getattr(self, "betmode", None) not in ("feature_spin", "peak_spin"):
            return
        scatter = self.config.scatter_symbol
        for reel in range(self.config.num_reels):
            for row in range(self.config.num_rows[reel]):
                if self.board[reel][row].name != scatter:
                    continue
                neighbor_names = set()
                for step_reel, step_row in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    next_reel, next_row = reel + step_reel, row + step_row
                    if 0 <= next_reel < self.config.num_reels and 0 <= next_row < self.config.num_rows[next_reel]:
                        neighbor_names.add(self.board[next_reel][next_row].name)
                replacement = next(
                    (symbol for symbol in self.config.paying_symbols if symbol not in neighbor_names),
                    self.config.low_symbols[0],
                )
                self.board[reel][row] = self.create_symbol(replacement)

    def _finalize_initial_board(self):
        self._strip_bonus_triggers()
        if self.should_force_initial_scatters():
            self.force_initial_scatters(self.resolve_forced_scatter_count())
            self.apply_scatter_anticipation()
        self.apply_gamble_two_bait()

        # Phase A: sticky HEAR disabled — never apply / refresh / level stickies.
        self.sticky_wild_positions = []

        need = int(getattr(self, "_plant_scatters_on_reveal", 0) or 0)
        if need and self.betmode not in ("feature_spin", "peak_spin"):
            self._ensure_min_scatters(need)
        self.get_special_symbols_on_board()
        self.prepare_landed_specials(initial_fill=True)
        reveal_event(self)
        if self.book.events:
            self.book.events[-1]["reelSet"] = getattr(self, "reel_set_name", self.reelstrip_id)

    def use_reel_family(self, family: str, name: str | None = None) -> None:
        """Pick one weighted strip set for this spin and point the refill at its pair."""
        if name is None:
            name = self.config.pick_reel_set(family)
        self.reel_set_name = name
        self.reelstrip_id = name
        self.reelstrip = self.config.reels[name]
        refill_id = self.config.tumble_refill_reel_ids.get(name, f"{name}_REFILL")
        self.refill_strip = self.config.reels[refill_id]

    def _bonus_reel_name(self, variant: str) -> str | None:
        """Put the hot spin in a random third so See / Hear arcs are not all late."""
        if variant not in ("see", "hear"):
            return None
        window = getattr(self, "arc_window", None)
        if window is None:
            return None
        span = max(int(self.config.bonus_spins), 1)
        third = min(2, (int(self.fs) - 1) * 3 // span)
        if third == window:
            hot = f"{variant}_burst"
            mid = f"{variant}_steady"
            hot_p = 0.12 if variant == "hear" else 0.03
            return hot if random.random() < hot_p else mid
        return f"{variant}_slow" if random.random() < 0.88 else f"{variant}_steady"

    def _uses_base_mix(self) -> bool:
        mode = getattr(self, "betmode", "")
        if mode not in getattr(self.config, "base_like_modes", set()):
            return False
        if getattr(self, "gametype", None) == self.config.freegame_type:
            return False
        if self.outcome_bucket() == "cap":
            return False
        return True

    def _column_names(self) -> list[tuple[str, ...]]:
        return [
            tuple(self.board[reel][row].name for row in range(self.config.num_rows[reel]))
            for reel in range(self.config.num_reels)
        ]

    def _columns_artifact(self) -> bool:
        """Solid paying column, or two columns showing the same five symbols."""
        cols = self._column_names()
        if any(len(set(col)) == 1 and col[0] not in {self.config.standard_wild, self.config.scatter_symbol} for col in cols):
            return True
        return any(cols[i] == cols[j] for i in range(len(cols)) for j in range(i + 1, len(cols)))

    def _repair_live_columns(self) -> None:
        pool = list(self.config.paying_symbols)
        for _ in range(16):
            if not self._columns_artifact():
                return
            cols = self._column_names()
            for reel, col in enumerate(cols):
                if len(set(col)) == 1 and col[0] not in {self.config.standard_wild, self.config.scatter_symbol}:
                    row = random.randrange(len(col))
                    self.board[reel][row] = self.create_symbol(next(symbol for symbol in pool if symbol != col[0]))
            cols = self._column_names()
            for left in range(len(cols)):
                for right in range(left + 1, len(cols)):
                    if cols[left] == cols[right]:
                        row = random.randrange(len(cols[right]))
                        current = cols[right][row]
                        self.board[right][row] = self.create_symbol(next(symbol for symbol in pool if symbol != current))

    def _random_blob(self, blocked: set[tuple[int, int]], size: int) -> list[tuple[int, int]]:
        """Connected orthogonal shape. Never a full column."""
        free = [
            (reel, row)
            for reel in range(self.config.num_reels)
            for row in range(self.config.num_rows[reel])
            if (reel, row) not in blocked
        ]
        if len(free) < 5:
            return []
        start = random.choice(free)
        blob = [start]
        per_reel: dict[int, int] = {start[0]: 1}
        guard = 0
        while len(blob) < size and guard < 50:
            guard += 1
            random.shuffle(blob)
            placed = False
            for reel, row in blob:
                neighbors = []
                for step_reel, step_row in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nxt = (reel + step_reel, row + step_row)
                    if nxt in blocked or nxt in blob:
                        continue
                    if not (0 <= nxt[0] < self.config.num_reels and 0 <= nxt[1] < self.config.num_rows[nxt[0]]):
                        continue
                    if per_reel.get(nxt[0], 0) >= 4:
                        continue
                    neighbors.append(nxt)
                if neighbors:
                    pick = random.choice(neighbors)
                    blob.append(pick)
                    per_reel[pick[0]] = per_reel.get(pick[0], 0) + 1
                    placed = True
                    break
            if not placed:
                break
        return blob if len(blob) >= 5 else []

    def _overlay_irregular_wins(self, count: int) -> None:
        """Stamp a few low-symbol blobs onto a real strip stop. The rest of the board stays."""
        lows = list(self.config.low_symbols)
        random.shuffle(lows)
        blocked: set[tuple[int, int]] = set()
        for index in range(count):
            blob = self._random_blob(blocked, random.choice((5, 5, 6, 6, 7)))
            if not blob:
                break
            symbol = lows[index % len(lows)]
            for reel, row in blob:
                self.board[reel][row] = self.create_symbol(symbol)
                blocked.add((reel, row))
        self._repair_live_columns()

    def _arm_followup_refill(self, explode: set[tuple[int, int]]) -> None:
        """Second wave: irregular lows in the cells that just exploded, then a quiet strip."""
        gaps = {
            reel: sum(1 for row in range(self.config.num_rows[reel]) if (reel, row) in explode)
            for reel in range(self.config.num_reels)
        }
        post = [[None for _ in range(self.config.num_rows[reel])] for reel in range(self.config.num_reels)]
        for reel in range(self.config.num_reels):
            survivors = [
                self.board[reel][row].name
                for row in range(self.config.num_rows[reel])
                if (reel, row) not in explode
            ]
            for offset, name in enumerate(survivors):
                post[reel][gaps[reel] + offset] = name
        gap_cells = [(reel, row) for reel in range(self.config.num_reels) for row in range(gaps[reel])]
        used: set[tuple[int, int]] = set()
        lows = list(self.config.low_symbols)
        random.shuffle(lows)
        for index, symbol in enumerate(lows):
            if index >= 3:
                break
            cells = []
            # Walk only through gap cells so the new symbols are the ones that fall in.
            pool = [cell for cell in gap_cells if cell not in used]
            if len(pool) < 5:
                break
            start = random.choice(pool)
            cells = [start]
            per_reel = {start[0]: 1}
            guard = 0
            while len(cells) < 5 and guard < 40:
                guard += 1
                extended = False
                for reel, row in list(cells):
                    neighbors = []
                    for step_reel, step_row in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nxt = (reel + step_reel, row + step_row)
                        if nxt not in pool or nxt in cells:
                            continue
                        if per_reel.get(nxt[0], 0) >= 3:
                            continue
                        neighbors.append(nxt)
                    if neighbors:
                        pick = random.choice(neighbors)
                        cells.append(pick)
                        per_reel[pick[0]] = per_reel.get(pick[0], 0) + 1
                        extended = True
                        break
                if not extended:
                    break
            if len(cells) < 5:
                continue
            for reel, row in cells:
                post[reel][row] = symbol
                used.add((reel, row))
        quiet = list(self.config.paying_symbols)
        for reel, row in gap_cells:
            if post[reel][row] is None:
                post[reel][row] = quiet[(reel * 2 + row) % len(quiet)]
        # Break a solid column in the landed board by editing a gap cell.
        for reel in range(self.config.num_reels):
            names = [post[reel][row] for row in range(self.config.num_rows[reel])]
            if len(set(names)) == 1 and gaps[reel]:
                post[reel][0] = quiet[(reel + 3) % len(quiet)]
        self.refill_strip = []
        tail_pool = list(self.config.paying_symbols)
        for reel in range(self.config.num_reels):
            wave = [post[reel][row] for row in range(gaps[reel])]
            tail = tail_pool[:]
            random.shuffle(tail)
            while len(tail) < 24:
                extra = tail_pool[:]
                random.shuffle(extra)
                tail.extend(extra)
            self.refill_strip.append((wave + tail)[:40])
            self.reel_positions[reel] = 0

    def _draw_base_mix_board(self) -> None:
        """Strip stops only. Hits, misses, and near-misses are windows of those strips."""
        bucket = self.outcome_bucket()
        self.progress_cap_override = None
        self.force_bar_fill = False
        if getattr(self, "force_tiny_hit", False) and bucket == "basegame":
            self.use_reel_family("base", "base_small")
            self.progress_cap_override = 2
            self._fill_initial_board()
            return
        if self.should_force_initial_scatters() or bucket == "freegame":
            self.use_reel_family("base", "base_quiet")
            self._fill_initial_board()
            return
        if bucket == "bar_pay":
            # Busy connecting strips. The bar must reach 10 through real cluster
            # wins (+1 each); check_repeat redraws the spin until it does.
            self.use_reel_family("base", "base_link")
            self._fill_initial_board()
            return
        near_p = float(getattr(self.config, "base_near_miss_share", 0.05))
        small_p = float(getattr(self.config, "base_small_rate", 0.46))
        kind = getattr(self, "_locked_base_kind", None)
        if kind not in {"near", "small", "quiet"}:
            roll = random.random()
            if roll < near_p:
                kind = "near"
            elif roll < near_p + small_p:
                kind = "small"
            else:
                kind = "quiet"
            self._locked_base_kind = kind
        if kind == "near":
            # A real stop, plus a few irregular low blobs, then one short follow-up.
            # Progress stops at 8/10 so the coin game does not start.
            self.use_reel_family("base", "base_quiet")
            self.progress_cap_override = 8
            self.want_near_miss = True
            self._fill_initial_board()
            self._overlay_irregular_wins(5)
            clusters = GameCluster.find_winning_clusters(self.board, self.config)
            explode = {pos for cluster in clusters for pos in cluster.positions}
            if explode:
                self._arm_followup_refill(explode)
            return
        if kind == "small":
            self.use_reel_family("base", "base_small")
            self.progress_cap_override = max(1, self.progress_threshold - 1)
            self._fill_initial_board()
            return
        self.use_reel_family("base", "base_quiet")
        self._fill_initial_board()

    def draw_prepared_board(self):
        """Initial fill: a random stop per column, read straight off that reel strip."""
        if self._uses_base_mix():
            self._draw_base_mix_board()
            self._finalize_initial_board()
            return
        self._fill_initial_board()
        self._finalize_initial_board()

    def _plant_quiet_miss(self) -> None:
        """No 5-cluster and no scatter. Symbol layout still changes every spin."""
        pays = list(self.config.paying_symbols)
        random.shuffle(pays)
        grid = [
            [pays[(reel * 3 + row + (reel * row)) % len(pays)] for row in range(5)]
            for reel in range(6)
        ]
        self._install_planted_grid(grid, pays[0], pays[1])

    def _plant_two_step(self) -> None:
        """Two single-column tumbles with varying sizes. Bar stops at 2."""
        self._plant_short_chain(steps=2, vary_size=True)

    def _plant_pair(self) -> None:
        """Two separated clusters, sizes 5–7. One tumble, bar stops at 2."""
        pays = list(self.config.paying_symbols)
        random.shuffle(pays)
        left, right = pays[0], pays[1]
        reels = list(range(self.config.num_reels))
        random.shuffle(reels)
        pair = None
        for a, b in ((reels[i], reels[j]) for i in range(6) for j in range(i + 1, 6)):
            if abs(a - b) >= 2:
                pair = (a, b)
                break
        reel_a, reel_b = pair or (0, 3)
        fillers = [symbol for symbol in pays[2:] if symbol not in (left, right)]
        if len(fillers) < 2:
            fillers = [symbol for symbol in pays if symbol not in (left, right)]
        grid = [[fillers[(reel + row) % len(fillers)] for row in range(5)] for reel in range(6)]

        def paint(reel: int, other: int, symbol: str) -> None:
            size = random.choice((5, 5, 6, 6, 7))
            for row in range(5):
                grid[reel][row] = symbol
            extra = size - 5
            if extra <= 0:
                return
            side = reel - 1 if reel < other and reel > 0 else reel + 1
            if not 0 <= side < 6 or side == other:
                side = reel + 1 if reel < 5 else reel - 1
            if side == other or not 0 <= side < 6:
                return
            rows = list(range(5))
            random.shuffle(rows)
            for row in rows[:extra]:
                grid[side][row] = symbol

        paint(reel_a, reel_b, left)
        paint(reel_b, reel_a, right)
        self._install_planted_grid(grid, fillers[0], fillers[-1])

    def _plant_two_fresh_columns(self, pool: list[str]) -> None:
        """Two separated size-5 clusters. One tumble, two bronze ranks, no chain."""
        symbols = list(pool)
        random.shuffle(symbols)
        left, right = symbols[0], symbols[1 % len(symbols)]
        fillers = [symbol for symbol in symbols if symbol not in (left, right)]
        if len(fillers) < 2:
            fillers = [symbol for symbol in self.config.paying_symbols if symbol not in (left, right)]
        reels = list(range(self.config.num_reels))
        random.shuffle(reels)
        reel_a, reel_b = 0, 3
        for a, b in ((reels[i], reels[j]) for i in range(6) for j in range(i + 1, 6)):
            if abs(a - b) >= 2:
                reel_a, reel_b = a, b
                break
        grid = [[fillers[(reel + row) % len(fillers)] for row in range(5)] for reel in range(6)]
        for row in range(5):
            grid[reel_a][row] = left
            grid[reel_b][row] = right
        self._install_planted_grid(grid, fillers[0], fillers[-1])
        self.refill_strip = [list(column) for column in self.config.reels["base_quiet_REFILL"]]

    def _plant_bar_near_miss(self) -> None:
        """Six fresh columns, then two of them win once more. Bar stops at 8/10.

        The first pass pays the plain face. The second pass pays bronze on two
        columns and then the refill goes quiet, so the coin game does not start.
        """
        self.progress_cap_override = 8
        lows = list(self.config.low_symbols)
        random.shuffle(lows)
        assignment = {
            0: lows[0],
            3: lows[0],
            1: lows[1],
            2: lows[2],
            4: lows[3],
            5: lows[4],
        }
        grid = [[assignment[reel] for _ in range(5)] for reel in range(6)]
        self._install_planted_grid(grid, "LE", "CO")
        follow = [1, 5] if random.random() < 0.5 else [2, 4]
        follow_syms = [lows[1], lows[2]]
        random.shuffle(follow_syms)
        banned = set(follow_syms)
        quiet_pool = [symbol for symbol in ["LE", "CO", "OR", "GR", "BA", *lows] if symbol not in banned]
        self.refill_strip = []
        for reel in range(6):
            if reel in follow:
                sym = follow_syms[follow.index(reel) % len(follow_syms)]
                tail = [quiet_pool[(index + reel) % len(quiet_pool)] for index in range(40)]
                self.refill_strip.append(([sym] * 5 + tail)[:50])
            else:
                self.refill_strip.append(
                    [quiet_pool[(index + reel * 2) % len(quiet_pool)] for index in range(50)]
                )

    def _plant_tiny_hit(self) -> None:
        """One cluster worth about 0.2x–0.5x. Used to break a long dead run."""
        self.progress_cap_override = 1
        kind = random.choice(("le", "prem", "low7", "low8"))
        if kind == "le":
            symbol, extra = random.choice(("LE", "CO")), 0
        elif kind == "prem":
            symbol, extra = random.choice(("OR", "GR")), 0
        elif kind == "low7":
            symbol, extra = random.choice(self.config.low_symbols), 2
        else:
            symbol, extra = random.choice(self.config.low_symbols), 3
        win_reel = random.randrange(self.config.num_reels)
        others = [name for name in self.config.paying_symbols if name != symbol]
        random.shuffle(others)
        grid = [[others[(reel + row) % len(others)] for row in range(5)] for reel in range(6)]
        for row in range(5):
            grid[win_reel][row] = symbol
        if extra:
            side = win_reel + 1 if win_reel < 5 else win_reel - 1
            for row in range(extra):
                grid[side][row] = symbol
        self._install_planted_grid(grid, others[0], others[1])
        self.refill_strip = []
        for reel in range(6):
            self.refill_strip.append(
                [others[(index + reel) % len(others)] for index in range(50)]
            )

    def _plant_single_column(self, pool: list[str], vary_size: bool = False) -> None:
        """One winning column, then a quiet refill so the cascade does not continue."""
        self._plant_short_chain(steps=2, vary_size=vary_size, pool=pool)
        quiet = self.config.reels["base_quiet_REFILL"]
        self.refill_strip = [list(column) for column in quiet]

    def _plant_short_chain(self, steps: int = 3, vary_size: bool = False, pool: list[str] | None = None) -> None:
        """One column wins, then refills into more single-column wins, then stops.

        Symbol, reel, and (optionally) cluster size vary so books do not share a signature.
        """
        win_reel = random.randrange(self.config.num_reels)
        chain = list(pool or self.config.paying_symbols)
        random.shuffle(chain)
        winner = chain[0]
        others = [symbol for symbol in self.config.paying_symbols if symbol not in chain] or chain[1:]
        if len(others) < 2:
            others = [symbol for symbol in self.config.paying_symbols if symbol != winner]
        grid = [["" for _ in range(5)] for _ in range(6)]
        for row in range(5):
            grid[win_reel][row] = winner
        for reel in range(6):
            if reel == win_reel:
                continue
            for row in range(5):
                grid[reel][row] = others[(reel + row) % len(others)]
                if grid[reel][row] == winner:
                    grid[reel][row] = others[(reel + row + 1) % len(others)]
        if vary_size:
            self._extend_cluster(grid, win_reel, winner, forbid=set())
        self._install_planted_grid(grid, others[0], others[1])
        self.refill_strip = [list(column) for column in self.refill_strip]
        follow = [symbol for symbol in chain[1:]] or [winner]
        random.shuffle(follow)
        symbols: list[str] = []
        while len(symbols) < max(1, steps - 1):
            random.shuffle(follow)
            symbols.extend(follow)
        symbols = symbols[: max(1, steps - 1)]
        strip: list[str] = []
        # Exactly five of each symbol. A longer run mixes the next symbol into the window and the chain stops.
        for symbol in symbols:
            strip.extend([symbol] * 5)
        pad = [symbol for symbol in others if symbol != symbols[0]]
        while len(strip) < 50:
            strip.extend(pad)
        self.refill_strip[win_reel] = strip[:50]

    def _extend_cluster(self, grid, reel: int, symbol: str, forbid: set[int]) -> None:
        """Grow a size-5 column into a size-6 or size-7 so the pay band changes."""
        extra = random.choice((0, 1, 1, 2))
        if extra <= 0:
            return
        sides = [side for side in (reel - 1, reel + 1) if 0 <= side < 6 and side not in forbid]
        if not sides:
            return
        side = random.choice(sides)
        rows = list(range(5))
        random.shuffle(rows)
        for row in rows[:extra]:
            grid[side][row] = symbol

    def _install_planted_grid(self, grid, top: str, bottom: str) -> None:
        self.board = [
            [self.create_symbol(grid[reel][row]) for row in range(5)] for reel in range(6)
        ]
        self.top_symbols = [self.create_symbol(top) for _ in range(6)]
        self.bottom_symbols = [self.create_symbol(bottom) for _ in range(6)]
        self.reel_positions = [0] * 6
        self.anticipation = [0] * 6

    def _plant_dead_teaser(self) -> None:
        """Exactly 2 scatters, one size-4 near-miss, and 3 or 4 paying clusters.

        Each paying cluster is one full column. Columns do not share a symbol,
        so they cannot merge. Positions and symbols change every spin.
        """
        cluster_count = 4 if random.random() < 0.5 else 3
        # Lows only. A bronze column pays 1× once tiles multiply, so the teaser stays a small win.
        symbols = list(self.config.low_symbols)
        random.shuffle(symbols)
        order = list(range(self.config.num_reels))
        random.shuffle(order)
        cluster_reels = order[:cluster_count]
        near_reel = order[cluster_count]
        filler_reels = order[cluster_count + 1 :]
        grid = [["" for _ in range(5)] for _ in range(6)]
        for index, reel in enumerate(cluster_reels):
            for row in range(5):
                grid[reel][row] = symbols[index]
        near_symbol = symbols[cluster_count]
        near_rows = list(range(5))
        random.shuffle(near_rows)
        for row in near_rows[:4]:
            grid[near_reel][row] = near_symbol
        scatter = self.config.scatter_symbol
        grid[near_reel][near_rows[4]] = scatter
        filler_pool = [symbol for symbol in symbols if symbol != near_symbol]
        second_scatter_reel = filler_reels[0]
        for reel in filler_reels:
            for row in range(5):
                grid[reel][row] = filler_pool[(reel + row) % len(filler_pool)]
        scatter_row = random.randrange(5)
        grid[second_scatter_reel][scatter_row] = scatter
        self.board = [
            [self.create_symbol(grid[reel][row]) for row in range(5)] for reel in range(6)
        ]
        self.top_symbols = [self.create_symbol(filler_pool[0]) for _ in range(6)]
        self.bottom_symbols = [self.create_symbol(filler_pool[-1]) for _ in range(6)]
        self.reel_positions = [0] * 6
        self.anticipation = [0] * 6

    def outcome_bucket(self) -> str:
        return normalize_bucket(getattr(self, "betmode", ""), getattr(self, "criteria", ""))

    def draw_feature_spin_board(self):
        """A real stop that already connects. Mild strips are short; rich strips bring wilds."""
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
        # Reel stops alone repeat at 250k. Nudge two cells so dead books stay unique.
        self._jitter_nonwinning_cells()
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

    def _jitter_nonwinning_cells(self) -> None:
        """Swap a few cells without creating a 5-cluster. Breaks exact board repeats."""
        pays = list(self.config.paying_symbols)
        for _ in range(6):
            reel = random.randrange(self.config.num_reels)
            row = random.randrange(self.config.num_rows[reel])
            current = self.board[reel][row].name
            if current == self.config.scatter_symbol:
                continue
            alt = random.choice([symbol for symbol in pays if symbol != current])
            self.board[reel][row] = self.create_symbol(alt)
            if GameCluster.find_winning_clusters(self.board, self.config):
                self.board[reel][row] = self.create_symbol(current)

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
        if getattr(self, "betmode", None) != "bonus_risky":
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
        """Last resort: one irregular 5-cluster, not a painted column or a straight rank."""
        self._overlay_irregular_wins(1)
        if not GameCluster.find_winning_clusters(self.board, self.config):
            symbol = self.config.low_symbols[0]
            for reel, row in ((0, 0), (1, 0), (1, 1), (2, 1), (2, 2)):
                self.board[reel][row] = self.create_symbol(symbol)
            self._repair_live_columns()

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
        """3 ST = See. 4 ST = Hear. 5+ ST = Speak No Evil."""
        variant_map = getattr(self.config, "bonus_variant_map", {3: "see", 4: "hear", 5: "speak", 6: "speak"})
        if scatter_count in variant_map:
            return variant_map[scatter_count]
        if scatter_count >= 5:
            return "speak"
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
                pool = self.config.coin_values[sym.name]
                weights = self.config.coin_value_weights[sym.name]
                value = float(random.choices(pool, weights=weights, k=1)[0])
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
        # plain -> bronze -> silver -> gold. Gold does not upgrade further.
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
            if getattr(self, "betmode", None) in {
                "bonus_see",
                "bonus_hear",
                "bonus_mystery",
                "bonus_risky",
            }:
                variant = getattr(self, "bonus_variant", None)
                if variant == "hear" or self.betmode == "bonus_hear":
                    bonus_scale *= float(getattr(self.config, "hear_cluster_pay_scale", None) or getattr(self.config, "buy_cluster_pay_scale", 1.0) or 1.0)
                elif variant == "see" or self.betmode == "bonus_see":
                    bonus_scale *= float(getattr(self.config, "see_cluster_pay_scale", None) or getattr(self.config, "buy_cluster_pay_scale", 1.0) or 1.0)
                else:
                    bonus_scale *= float(getattr(self.config, "buy_cluster_pay_scale", 1.0) or 1.0)
                if variant == "speak" and self.betmode == "bonus_mystery":
                    bonus_scale *= float(getattr(self.config, "mystery_speak_cluster_scale", 1.0) or 1.0)
                elif variant == "speak" and self.betmode == "bonus_risky":
                    bonus_scale *= float(getattr(self.config, "risky_speak_cluster_scale", 1.0) or 1.0)
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

    def _maybe_tumble_special(self, sym):
        """Wilds can land in a tumble. Scatters that tumble in count."""
        name = getattr(sym, "name", None)
        if name in {self.config.standard_wild, self.config.scatter_symbol, *self.config.coin_symbols}:
            return sym
        if self.betmode in ("feature_spin", "peak_spin"):
            scatter_p = 0.0
        elif self.is_bonus_mode():
            scatter_p = float(getattr(self.config, "tumble_scatter_chance_bonus", 0.0))
        else:
            scatter_p = float(getattr(self.config, "tumble_scatter_chance_base", 0.0))
        wild_p = float(getattr(self.config, "tumble_wild_chance", 0.0))
        roll = random.random()
        if roll < wild_p:
            return self.create_symbol(self.config.standard_wild)
        if roll < wild_p + scatter_p:
            return self.create_symbol(self.config.scatter_symbol)
        return sym

    def _ensure_min_scatters(self, count: int) -> None:
        """Place scatters until the board shows at least `count` of them."""
        scatter = self.config.scatter_symbol
        have = self.count_special_symbols("scatter")
        guard = 0
        while have < count and guard < 40:
            guard += 1
            reel = random.randrange(self.config.num_reels)
            row = random.randrange(self.config.num_rows[reel])
            if self.board[reel][row].name == scatter:
                continue
            self.board[reel][row] = self.create_symbol(scatter)
            have += 1

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
                sym = self._maybe_tumble_special(sym)
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
        """One coin game per spin in every mode. The old Hear 3-cap is gone."""
        return False

    def advance_progress(self, tumble_steps: int = 1, *, activate: bool = True):
        if tumble_steps <= 0:
            return
        cap = getattr(self, "progress_cap_override", None)
        if cap is not None and self.progress_value >= cap:
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
        if getattr(self, "progress_cap_override", None) is not None:
            return
        if self.progress_value >= self.progress_threshold and not self.board_activation_fired_this_spin:
            self.execute_board_activation(refill_after=True)

    def execute_board_activation(self, refill_after: bool = False):
        # One coin game per spin in every mode.
        if self.board_activation_fired_this_spin:
            return
        self.board_activation_fired_this_spin = True
        self.board_activations_this_spin = getattr(self, "board_activations_this_spin", 0) + 1
        trigger_progress = self.progress_value
        total, items, rounds = resolve_coin_game(self)
        if getattr(self, "coin_game_cap_hit", False):
            total = float(self.config.wincap)
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
        # See clears ranks after a coin game. Hear and Speak keep them.
        # One coin game per spin — the bar does not arm a second one.
        if self.is_see_bonus():
            self.reset_grid_mults()
            update_tile_event(self)
        self.progress_value = 0
        progress_fill_event(self)
        if self.is_speak_bonus():
            self.progress_value = self.progress_threshold
            progress_fill_event(self)
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
                # Base, Ante, and Hunt pay the plain face first, then rank the tiles up,
                # so a small cluster is often under 1x and still leaves bronze or silver.
                # Bonuses light first and pay face × the new multiplier sum.
                rank_after_pay = (
                    getattr(self, "betmode", "") in getattr(self.config, "base_like_modes", set())
                    and getattr(self, "gametype", None) != self.config.freegame_type
                )
                if rank_after_pay:
                    self.award_clusters(clusters)
                    self.mark_level_up_tiles(clusters)
                else:
                    self.mark_level_up_tiles(clusters)
                    self.award_clusters(clusters)
                self.mark_removed_symbols(winning_types, clusters)
                win_info_event(self)
                update_tumble_win_event(self)
                if self.wincap_triggered:
                    break
                # +1 per winning cluster. Overflow past 5 is ignored. Coin game waits until idle.
                for _ in clusters:
                    if self.progress_value >= self.progress_threshold:
                        break
                    self.advance_progress(1, activate=False)
                self.gravity_and_refill(emit_event=True)
            if self.wincap_triggered or step > self.config.max_tumbles_per_spin:
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
