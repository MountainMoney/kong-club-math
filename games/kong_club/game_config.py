"""Kong Club math configuration — classic 3-tier tiles + Jul 2 cascade.

Symbol IDs align with the art pipeline:
T/J/Q/K/A, LE/CO/OR/GR/BA, MW, ST, CB/CS/CG.
Tile ranks: 0=none, 1=bronze, 2=silver, 3=gold (mults 2/5/10).
Powers: MULTI + COLLECTOR live (rare; pots rarer than clovers). TIER_SHIFT retired.
"""

from __future__ import annotations

import random

from src.config.betmode import BetMode
from src.config.config import Config
from src.config.distributions import Distribution
from game_criteria import (
    ANTE_CAP_QUOTA,
    BASE_CAP_QUOTA,
    FEATURE_CAP_QUOTA,
    FEATURE_DEAD_QUOTA,
    GAMBLE_CAP_QUOTA,
    HEAR_CAP_QUOTA,
    SEE_CAP_QUOTA,
    FEATURE_NIBBLE_QUOTA,
    FEATURE_RUN_QUOTA,
    PEAK_CAP_QUOTA,
    PEAK_CLIP_QUOTA,
    PEAK_DEAD_QUOTA,
    PEAK_NIBBLE_QUOTA,
    PEAK_RUN_QUOTA,
    PEAK_TEASE_QUOTA,
)


STAKE_SLUG = "kong-club"

# Organic bonus entry — same pattern as Football Fiesta:
# quota picks "freegame" criteria → force N scatters from weighted table → no organic land on base strips.
# See / Hear / Madness given a bonus. Madness stays rare so a 3,000× floor
# does not blow base or ante RTP. Ante uses the same mix; only the rate doubles.
SCATTER_TRIGGERS = {3: 989, 4: 10, 5: 1}
SCATTER_TRIGGERS_ANTE = {3: 989, 4: 10, 5: 1}
# Somewhat rarer than the 1/220 · 1/110 pair. Ante stays exactly twice base.
# Scatter faces stay {3: 989, 4: 10, 5: 1} — not a balancing lever.
BASE_FREEGAME_QUOTA = 1 / 260
ANTE_FREEGAME_QUOTA = 1 / 130

# Gamble — 50% dead / 45% Hear / 5% Madness.
# Cost = (0.45·E[Hear] + 0.05·E[Madness] + 25000/4500) / 0.965.
# Raised with the restored coin faces and tile multipliers. Still under the old 1,567×.
GAMBLE_BUY_COST = 380.0
SEE_BUY_COST = 115.0
HEAR_BUY_COST = 250.0
FEATURE_BUY_COST = 65.0
GAMBLE_DEAD_QUOTA = 0.50
GAMBLE_HEAR_QUOTA = 0.45
GAMBLE_MADNESS_QUOTA = 0.05
# Dead spins: always plant 2 ST on reels 0–1 and tease the rest (no bonus).
GAMBLE_DEAD_BAIT_RATE = 1.0


class GameConfig(Config):
    """Source-of-truth configuration for Kong Club (3-tier tiles)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "kong_club"
        self.provider_name = "Trifecta"
        self.provider_number = 0
        self.working_name = "Kong Club"
        self.rtp = 0.965
        self.wincap = 25000.0
        self.win_type = "cluster"
        self.construct_paths()

        self.num_reels = 6
        self.num_rows = [5] * self.num_reels
        self.include_padding = True

        self.low_symbols = ["T", "J", "Q", "K", "A"]
        self.high_symbols = ["LE", "CO", "OR", "GR", "BA"]
        self.paying_symbols = self.low_symbols + self.high_symbols
        self.standard_wild = "MW"
        self.scatter_symbol = "ST"
        self.coin_symbols = ["CB", "CS", "CG"]

        # Phase A: only MW is a cluster wild.
        self.special_symbols = {
            "wild": [self.standard_wild],
            "scatter": [self.scatter_symbol],
            "coin": self.coin_symbols,
        }

        # Classic MM ranks: 0=none, 1=bronze, 2=silver, 3=gold.
        self.multiplier_table = [2, 5, 10]
        self.tile_level_multipliers = self.multiplier_table
        self.max_tile_level = 3
        self.coin_seed_levels = {"CB": 1, "CS": 2, "CG": 3}
        # Frontend hard faces. Books may only reveal these values.
        # Weights lean low so a gold board does not print the 250 / 500 faces.
        self.coin_values = {
            "CB": [1, 2, 3, 4],
            "CS": [5, 7, 10, 15, 20],
            "CG": [25, 50, 100, 250, 500],
        }
        self.coin_value_weights = {
            "CB": [70, 20, 7, 3],
            "CS": [60, 24, 10, 4, 2],
            "CG": [82, 12, 4, 1, 1],
        }
        # Face pools keyed by tile level (1→CB, 2→CS, 3→CG).
        self.activation_coin_value_pools = self._build_activation_coin_pools()
        self.activation_coin_value_weights = self._build_activation_coin_weights()

        # See / Hear / Madness fill in 5 cluster connections (Cole 2026-09-02).
        self.progress_thresholds = {
            "base": 5,
            "base_ante": 5,
            "feature_spin": 5,
            "peak_spin": 1,
            "bonus_see": 5,
            "bonus_hear": 5,
            "bonus_madness": 5,
            "bonus_mystery": 5,
        }
        # One coin game per spin. The old Hear cap of 3 is not used.
        self.max_board_activations_hear = 1
        self.coin_game_max_reruns = 10
        # MULTI faces — LOCKED Cole 2026-07-18 (COIN_POWERS_LOCKED.md).
        self.coin_game_multi_values = [2, 3, 4, 5, 10, 20]
        self.coin_game_multi_weights = [35, 28, 18, 12, 5, 2]
        # Baseline vs power weights when rolling each lit cell's prize kind.
        self.coin_game_coin_weight = 100
        # Per-tile-tier powers (same table in every priced mode). Coin 100 vs:
        # bronze 3/0 (~2.9% clover · 0% pot), silver 6/2, gold 8/3.
        # TIER_SHIFT stays retired.
        self.coin_game_power_by_tile_level = {
            1: {"multiplier": 3, "collector": 0, "tier_shift": 0},
            2: {"multiplier": 6, "collector": 2, "tier_shift": 0},
            3: {"multiplier": 8, "collector": 3, "tier_shift": 0},
        }
        # PEAK uses the gold table. Regen cannot spawn pots, so 8/3 stays finite.
        self.coin_game_power_peak_gold = {"multiplier": 8, "collector": 3, "tier_shift": 0}
        # Reruns use the same opening rates: coin 100 vs bronze 3/0, silver 6/2, gold 8/3.
        self.coin_game_rerun_power_by_tile_level = {
            1: {"coin": 100, "multiplier": 3, "collector": 0, "tier_shift": 0},
            2: {"coin": 100, "multiplier": 6, "collector": 2, "tier_shift": 0},
            3: {"coin": 100, "multiplier": 8, "collector": 3, "tier_shift": 0},
        }
        # Mode fallback matches bronze so Extra Chance / unknown modes do not invent pots.
        self.coin_game_power_weights = {
            "base": {"multiplier": 3, "collector": 0, "tier_shift": 0},
            "base_ante": {"multiplier": 3, "collector": 0, "tier_shift": 0},
            "feature_spin": {"multiplier": 3, "collector": 0, "tier_shift": 0},
            "peak_spin": {"multiplier": 3, "collector": 0, "tier_shift": 0},
            "bonus_see": {"multiplier": 3, "collector": 0, "tier_shift": 0},
            "bonus_hear": {"multiplier": 3, "collector": 0, "tier_shift": 0},
            "bonus_madness": {"multiplier": 3, "collector": 0, "tier_shift": 0},
            "bonus_mystery": {"multiplier": 3, "collector": 0, "tier_shift": 0},
        }
        # Exact Le Bandit cluster pays in base AND bonus (do not dilute the table).
        # RTP levers: shorter strip runs (fewer tumbles), trigger rarity — not pay scales.
        self.bonus_cluster_pay_scale = 1.0
        # Exact Jul 2 Le Bandit cluster pays (× total bet). Scale 1.0 = screenshot $1 table — DO NOT dilute.
        self.paytable_scale = 1.0
        # Always pay face as labeled (1.0). Do not soft-scale coin values.
        self.coin_tile_scale_by_mode = {
            "base": 1.0,
            "base_ante": 1.0,
            "feature_spin": 1.0,
            "peak_spin": 1.0,
            "bonus_see": 1.0,
            "bonus_hear": 1.0,
            "bonus_madness": 1.0,
            "bonus_mystery": 1.0,
        }
        # Every lit tile pays a virtual coin. None = no sample cap.
        self.max_activation_coins_by_mode = {
            "base": None,
            "base_ante": None,
            "feature_spin": None,
            "peak_spin": None,
            "bonus_see": None,
            "bonus_hear": None,
            "bonus_madness": None,
            "bonus_mystery": None,
        }
        # Dead once Hear is uncapped.
        self.hear_coin_cap_boost_chance = 0.0
        # PEAK: light every cell gold (level 3) before the drop. Progress still starts at 0.
        self.peak_spin_seed_gold = True
        self.peak_spin_cost = 1400.0
        self.gamble_buy_cost = GAMBLE_BUY_COST
        self.gamble_dead_bait_rate = GAMBLE_DEAD_BAIT_RATE
        self.see_buy_cost = SEE_BUY_COST
        self.bonus_spins = 10
        self.scatter_pays = {}
        self.freespin_triggers = {
            self.basegame_type: {3: 10, 4: 10, 5: 10, 6: 10},
            self.freegame_type: {},
        }
        self.anticipation_triggers = {
            self.basegame_type: min(self.freespin_triggers[self.basegame_type].keys()) - 1,
            self.freegame_type: 99,
        }
        self.max_tumbles_per_spin = 100
        self.max_initial_wilds = 4
        self.min_feature_cost_win = 0.01

        # Organic bonus entry via forced-scatter criteria (scatters are not on base strips).
        self.bonus_hit_rate_base = BASE_FREEGAME_QUOTA
        self.bonus_hit_rate_ante = ANTE_FREEGAME_QUOTA
        self.scatter_triggers = SCATTER_TRIGGERS
        self.scatter_triggers_ante = SCATTER_TRIGGERS_ANTE
        self.bonus_variant_map = {3: "see", 4: "hear", 5: "madness", 6: "madness"}
        self.ante_bet_cost = 1.4

        self.symbol_weights_initial = {
            "T": 11.0,
            "J": 11.0,
            "Q": 11.0,
            "K": 11.0,
            "A": 11.0,
            "LE": 7.0,
            "CO": 7.0,
            "OR": 6.0,
            "GR": 6.0,
            "BA": 5.0,
            "MW": 2.0,
            "ST": 1.0,
        }
        # Feature Spin and free-spin strips. Base and TRIFECTA stay virtual-only.
        # Landed coins are rarer than the shrunk-face build, and gold is the rarest.
        self.physical_coin_weights = {"CB": 1.0, "CS": 0.4, "CG": 0.12}
        # Refill: exclude MW / ST.
        self.symbol_weights_refill = {
            symbol: weight
            for symbol, weight in self.symbol_weights_initial.items()
            if symbol
            not in {
                self.standard_wild,
                self.scatter_symbol,
            }
        }
        # Base refill: NO coins (same as generic refill now).
        self.symbol_weights_base_refill = dict(self.symbol_weights_refill)
        self.symbol_weights_no_scatter_initial = {
            symbol: weight
            for symbol, weight in self.symbol_weights_initial.items()
            if symbol != self.scatter_symbol
        }
        # TRIFECTA (FEATURE) stays virtual. Feature Spin strips add physical coins below.
        self.symbol_weights_feature_initial = dict(self.symbol_weights_no_scatter_initial)
        self.symbol_weights_feature_refill = dict(self.symbol_weights_base_refill)
        # Base initial: NO coins; ST forced-only (exclude from strips).
        self.symbol_weights_base_initial = {
            symbol: weight
            for symbol, weight in self.symbol_weights_initial.items()
            if symbol != self.scatter_symbol and symbol not in self.coin_symbols
        }
        self.symbol_weights_bonus_initial = dict(self.symbol_weights_base_initial)
        # Slightly fewer wilds on FS/feature strips (buy ≡ organic) to hold ~96% without pay dilution.
        if "MW" in self.symbol_weights_bonus_initial:
            self.symbol_weights_bonus_initial["MW"] = 1.30
        if "MW" in self.symbol_weights_feature_initial:
            self.symbol_weights_feature_initial["MW"] = 1.35
        # Phase A: sticky HEAR / SEE weights unused — bonus uses INITIAL_BONUS only.
        self.symbol_weights_bonus_hear_initial = dict(self.symbol_weights_bonus_initial)
        self.max_sticky_wilds = 0
        # Free spins and Feature Spin can land CB/CS/CG. Base and TRIFECTA cannot.
        self.symbol_weights_bonus_initial.update(self.physical_coin_weights)
        self.symbol_weights_bonus_refill = dict(self.symbol_weights_base_refill)
        self.symbol_weights_bonus_refill.update(self.physical_coin_weights)
        self.symbol_weights_feature_spin_initial = dict(self.symbol_weights_feature_initial)
        self.symbol_weights_feature_spin_initial.update(self.physical_coin_weights)
        self.symbol_weights_feature_spin_refill = dict(self.symbol_weights_feature_refill)
        self.symbol_weights_feature_spin_refill.update(self.physical_coin_weights)

        self.paytable = self._build_paytable()
        self.reels = {
            "INITIAL": self.build_reel_strips(self.symbol_weights_initial, seed=101),
            # Base: shorter runs → fewer easy tumbles on dead spins.
            "INITIAL_BASE": self.build_reel_strips(
                self.symbol_weights_base_initial,
                seed=111,
                run_weights=(45, 45, 10),
            ),
            "INITIAL_NO_SCATTER": self.build_reel_strips(
                self.symbol_weights_no_scatter_initial, seed=151
            ),
            # Bonus / FS (buy ≡ organic): same short-run bias as base after uncap
            # (every lit tile pays). Denser (25, 45, 30) overshoots 96% with full boards.
            "INITIAL_BONUS": self.build_reel_strips(
                self.symbol_weights_bonus_initial,
                seed=161,
                run_weights=(45, 45, 10),
            ),
            "REFILL": self.build_reel_strips(self.symbol_weights_refill, seed=202),
            "REFILL_BASE": self.build_reel_strips(
                self.symbol_weights_base_refill,
                seed=212,
                run_weights=(45, 45, 10),
            ),
            "REFILL_BONUS": self.build_reel_strips(
                self.symbol_weights_bonus_refill,
                seed=222,
                run_weights=(45, 45, 10),
            ),
            # PEAK keeps the original Feature density.
            "FEATURE": self.build_reel_strips(
                self.symbol_weights_feature_initial,
                seed=303,
                run_weights=(25, 45, 30),
            ),
            "FEATURE_REFILL": self.build_reel_strips(
                self.symbol_weights_feature_refill,
                seed=313,
                run_weights=(25, 45, 30),
            ),
            # 50× Feature Spin: denser runs so boards connect and cascade more often.
            "FEATURE_SPIN": self.build_reel_strips(
                self.symbol_weights_feature_spin_initial,
                seed=323,
                run_weights=(10, 35, 55),
            ),
            "FEATURE_SPIN_REFILL": self.build_reel_strips(
                self.symbol_weights_feature_spin_refill,
                seed=333,
                run_weights=(10, 35, 55),
            ),
        }
        self._build_variety_reels()
        self.tumble_refill_reel_ids = {
            "INITIAL": "REFILL",
            "INITIAL_BASE": "REFILL_BASE",
            "INITIAL_NO_SCATTER": "REFILL",
            "INITIAL_BONUS": "REFILL_BONUS",
            "FEATURE": "FEATURE_REFILL",
            "FEATURE_SPIN": "FEATURE_SPIN_REFILL",
        }
        for set_name in self.reel_set_weights_flat:
            self.tumble_refill_reel_ids[set_name] = f"{set_name}_REFILL"

        self.bet_modes = self._build_bet_modes()

    def _coin_symbol_for_tile_level(self, level: int) -> str:
        """1=bronze/CB, 2=silver/CS, 3=gold/CG."""
        if level <= 1:
            return "CB"
        if level == 2:
            return "CS"
        return "CG"

    def _build_activation_coin_pools(self) -> dict[int, list[int]]:
        """Map tile levels to integer coin face pools."""
        pools: dict[int, list[int]] = {}
        for level in range(1, self.max_tile_level + 1):
            symbol = self._coin_symbol_for_tile_level(level)
            pools[level] = list(self.coin_values[symbol])
        return pools

    def _build_activation_coin_weights(self) -> dict[int, list[int]]:
        """Per-level weights aligned with activation_coin_value_pools."""
        weights: dict[int, list[int]] = {}
        for level in range(1, self.max_tile_level + 1):
            symbol = self._coin_symbol_for_tile_level(level)
            weights[level] = list(self.coin_value_weights[symbol])
        return weights

    def _build_paytable(self) -> dict[tuple[int, str], float]:
        """Full Jul 2 Le Bandit paytable — 7 size bands."""
        payouts = {
            "T": [0.10, 0.20, 0.30, 0.50, 1.50, 5.00, 15.00],
            "J": [0.10, 0.20, 0.30, 0.50, 1.50, 5.00, 15.00],
            "Q": [0.10, 0.20, 0.30, 0.50, 1.50, 5.00, 15.00],
            "K": [0.10, 0.20, 0.30, 0.50, 1.50, 5.00, 15.00],
            "A": [0.10, 0.20, 0.30, 0.50, 1.50, 5.00, 15.00],
            "LE": [0.30, 0.40, 0.50, 0.70, 2.50, 7.50, 25.00],
            "CO": [0.30, 0.40, 0.50, 0.70, 2.50, 7.50, 25.00],
            "OR": [0.50, 0.70, 1.00, 1.50, 5.00, 15.00, 50.00],
            "GR": [0.50, 0.70, 1.00, 1.50, 5.00, 15.00, 50.00],
            "BA": [1.00, 1.50, 2.00, 3.00, 10.00, 30.00, 100.00],
        }
        band_to_index = {5: 0, 6: 1, 7: 2, 8: 3, 9: 4, 11: 5, 13: 6}
        scale = float(getattr(self, "paytable_scale", 1.0))
        table: dict[tuple[int, str], float] = {}
        for symbol, values in payouts.items():
            for size in range(5, 31):
                band = self.cluster_pay_tier(size)
                payout = round(values[band_to_index[band]] * scale, 6)
                table[(size, symbol)] = payout
                # Also key by band size used by GameCluster.paytable_size lookups.
                table[(band, symbol)] = payout
        return table

    @staticmethod
    def cluster_pay_tier(size: int) -> int:
        if size <= 5:
            return 5
        if size == 6:
            return 6
        if size == 7:
            return 7
        if size == 8:
            return 8
        if size <= 10:
            return 9
        if size <= 12:
            return 11
        return 13

    def build_capped_reel_strips(
        self,
        weights: dict[str, float],
        seed: int,
        strip_len: int = 96,
        run_lengths: tuple[int, ...] = (1, 2),
        run_weights: tuple[int, ...] = (64, 36),
        max_run: int = 2,
    ) -> list[list[str]]:
        """Run-based strips whose longest same-symbol stack is `max_run`.

        Consecutive runs never repeat a symbol, and the wrap from the bottom
        of the strip back to the top counts toward the same cap. A 5-row
        window therefore cannot be a straight column of one symbol. Clusters
        have to form as irregular blobs across reels.
        """
        symbols = list(weights)
        strips: list[list[str]] = []
        for reel in range(self.num_reels):
            rng = random.Random(seed + reel * 997)
            strip: list[str] = []
            prev = None
            while len(strip) < strip_len:
                choices = [symbol for symbol in symbols if symbol != prev] or symbols
                choice_w = [weights[symbol] for symbol in choices]
                symbol = rng.choices(choices, weights=choice_w, k=1)[0]
                run_len = rng.choices(list(run_lengths), weights=list(run_weights), k=1)[0]
                run_len = min(int(run_len), max_run, strip_len - len(strip))
                strip.extend([symbol] * run_len)
                prev = symbol
            self._cap_symbol_runs(strip, max_run, symbols)
            if self._longest_run(strip) > max_run:
                raise RuntimeError(f"reel {reel} run exceeded {max_run}")
            strips.append(strip)
        return strips

    @staticmethod
    def _cap_symbol_runs(strip: list[str], max_run: int, symbols: list[str]) -> None:
        """Split any linear or wrap-around run that is longer than max_run."""
        n = len(strip)
        index = 0
        while index < n:
            end = index
            while end < n and strip[end] == strip[index]:
                end += 1
            if end - index > max_run:
                alts = [symbol for symbol in symbols if symbol != strip[index]]
                for cursor in range(index + max_run, end):
                    strip[cursor] = alts[(cursor - index) % len(alts)]
            index = max(end, index + 1)
        if strip[0] != strip[-1]:
            return
        left = 0
        while left < n and strip[left] == strip[0]:
            left += 1
        right = 0
        while right < n and strip[-1 - right] == strip[0]:
            right += 1
        if left + right <= max_run:
            return
        # One different face at the seam splits the wrap. It must not extend
        # the run that now sits beside it.
        blocked = {strip[0], strip[1], strip[-2]}
        alt = next(symbol for symbol in symbols if symbol not in blocked)
        strip[-1] = alt

    @staticmethod
    def _longest_run(strip: list[str]) -> int:
        longest = 1
        run = 1
        for index in range(1, len(strip)):
            if strip[index] == strip[index - 1]:
                run += 1
                longest = max(longest, run)
            else:
                run = 1
        if strip[0] == strip[-1]:
            left = 0
            while left < len(strip) and strip[left] == strip[0]:
                left += 1
            right = 0
            while right < len(strip) and strip[-1 - right] == strip[0]:
                right += 1
            longest = max(longest, left + right)
        return longest

    def build_reel_strips(
        self,
        weights: dict[str, float],
        seed: int,
        strip_len: int = 50,
        run_weights: tuple[int, int, int] = (40, 45, 15),
    ) -> list[list[str]]:
        """Build six independent run-based strips.

        `run_weights` is relative weight for run lengths 1 / 2 / 3.
        Base uses shorter bias (fewer dead-spin tumbles); bonus/feature denser.
        """
        rng = random.Random(seed)
        symbols = list(weights.keys())
        weight_values = [weights[symbol] for symbol in symbols]
        strips: list[list[str]] = []
        for reel in range(self.num_reels):
            reel_rng = random.Random(seed + reel * 997)
            strip: list[str] = []
            while len(strip) < strip_len:
                symbol = reel_rng.choices(symbols, weights=weight_values, k=1)[0]
                run_len = reel_rng.choices([1, 2, 3], weights=list(run_weights), k=1)[0]
                strip.extend([symbol] * run_len)
            strip = strip[:strip_len]
            self._light_shuffle_runs(strip, rng=random.Random(seed + reel * 37))
            self._ensure_coin_stop(strip, weights, rng=random.Random(seed + reel * 73))
            strips.append(strip)
        return strips

    @staticmethod
    def _light_shuffle_runs(strip: list[str], rng: random.Random) -> None:
        """Swap a few same-run chunks without destroying the run-based feel."""
        for _ in range(4):
            a = rng.randrange(0, len(strip))
            b = rng.randrange(0, len(strip))
            strip[a], strip[b] = strip[b], strip[a]

    @staticmethod
    def _ensure_coin_stop(strip: list[str], weights: dict[str, float], rng: random.Random) -> None:
        coin_symbols = [symbol for symbol in ("CB", "CS", "CG") if symbol in weights]
        if not coin_symbols or any(symbol in coin_symbols for symbol in strip):
            return
        coin_weights = [weights[symbol] for symbol in coin_symbols]
        strip[rng.randrange(0, len(strip))] = rng.choices(coin_symbols, weights=coin_weights, k=1)[0]

    def _build_variety_reels(self) -> None:
        """Weighted strip sets. Base/ante share four. See, Hear, and Madness have three each."""
        pays = self.paying_symbols

        def even(**extra: float) -> dict[str, float]:
            weights = {symbol: 8.0 for symbol in pays}
            weights.update(extra)
            return weights

        def hot(wild: float) -> dict[str, float]:
            return {
                "T": 3.0,
                "J": 3.0,
                "Q": 16.0,
                "K": 16.0,
                "A": 4.0,
                "LE": 6.0,
                "CO": 15.0,
                "OR": 5.0,
                "GR": 14.0,
                "BA": 16.0,
                "MW": wild,
            }

        # (weights, initial run lengths, seed, refill run lengths)
        # Base hot connects, then a quiet refill so most chains stop at 3–4 clusters
        # and do not fill the coin-game bar.
        specs: dict[str, tuple] = {
            "base_quiet": (even(MW=0.02), (96, 3, 1), 411, (97, 2, 1)),
            "base_normal": (even(OR=8, GR=8, BA=7, MW=0.15), (88, 10, 2), 422, (92, 7, 1)),
            "base_hot": (even(Q=12, K=12, BA=9, MW=1.2), (36, 40, 24), 433, (55, 32, 13)),
            "base_teaser": (even(MW=0.2), (80, 18, 2), 444, (85, 12, 3)),
            # Slow spins rarely fill the bar. Steady / burst are the spotlight third.
            "see_slow": (even(MW=0.16), (84, 13, 3), 511, (88, 10, 2)),
            "see_steady": (even(BA=10, MW=0.9), (46, 38, 16), 522, (56, 32, 12)),
            "see_burst": (even(Q=12, K=12, BA=11, MW=1.4), (32, 42, 26), 533, (42, 38, 20)),
            "hear_slow": (even(MW=0.06), (92, 7, 1), 611, (94, 5, 1)),
            "hear_steady": (even(OR=12, GR=12, BA=13, MW=2.0), (26, 40, 34), 622, (34, 40, 26)),
            "hear_burst": (even(Q=14, BA=15, MW=2.8), (16, 38, 46), 633, (22, 40, 38)),
            # Madness is a coin game every spin. Keep the fill steady so the
            # 2,000× floor does not select only the 5,000× tail.
            "madness_low": (even(MW=0.30), (76, 20, 4), 711, (82, 16, 2)),
            "madness_mid": (even(BA=10, MW=1.05), (48, 38, 14), 722, (58, 32, 10)),
            "madness_high": (hot(1.5), (34, 42, 24), 733, (44, 38, 18)),
            "feature_mild": (even(BA=12, MW=2.2), (28, 42, 30), 811, (36, 40, 24)),
            "feature_rich": (hot(5.6), (12, 28, 60), 822, (14, 30, 56)),
            "peak_a": (even(MW=1.0), (40, 40, 20), 911, (50, 36, 14)),
            "peak_b": (hot(2.0), (20, 40, 40), 922, (30, 40, 30)),
        }
        self.reel_set_weights = {
            "base": {"base_quiet": 52, "base_normal": 16, "base_hot": 26, "base_teaser": 6},
            "see": {"see_slow": 56, "see_steady": 34, "see_burst": 10},
            "hear": {"hear_slow": 68, "hear_steady": 26, "hear_burst": 6},
            "madness": {"madness_low": 88, "madness_mid": 10, "madness_high": 2},
            "feature": {"feature_mild": 30, "feature_rich": 70},
            "peak": {"peak_a": 55, "peak_b": 45},
            "gamble_dead": {"base_quiet": 1},
        }
        self.reel_set_weights_flat = set(specs)
        for name, (weights, runs, seed, refill_runs) in specs.items():
            self.reels[name] = self.build_reel_strips(weights, seed=seed, run_weights=runs)
            refill = {symbol: weight for symbol, weight in weights.items() if symbol not in {"MW", "ST"}}
            self.reels[f"{name}_REFILL"] = self.build_reel_strips(
                refill, seed=seed + 17, run_weights=refill_runs
            )
        # Teaser refills stay quiet so the planted 3–4 clusters do not chain to 5.
        self.reels["base_teaser_REFILL"] = self.reels["base_quiet_REFILL"]
        # Hot refills drop short runs so a win often continues for a few tumbles.
        chain_symbols = ["T", "J", "Q", "K", "A", "LE", "CO", "OR", "GR", "BA"]
        for reel_index in range(self.num_reels):
            reel_rng = random.Random(9000 + reel_index)
            strip: list[str] = []
            while len(strip) < 50:
                reel_rng.shuffle(chain_symbols)
                for symbol in chain_symbols:
                    strip.extend([symbol] * 2)
            self.reels["base_hot_REFILL"][reel_index] = strip[:50]
        self._build_base_natural_reels()

    def _build_base_natural_reels(self) -> None:
        """Base and ante draw these stops. Mystery keeps the planted sets above.

        Opening runs are only 1–2 symbols, so a 5-high window cannot be one
        face. Refills are a little stickier (runs of 1–3, lows heavier) so a
        win can tumble again without dropping a whole column of one symbol.
        Weights are set so a random stop wins about one spin in five.
        """
        initial = {
            "T": 11.2,
            "J": 11.2,
            "Q": 10.6,
            "K": 8.5,
            "A": 7.5,
            "LE": 5.2,
            "CO": 4.4,
            "OR": 2.4,
            "GR": 1.9,
            "BA": 1.3,
            "MW": 0.7,
        }
        refill = {
            "T": 34.0,
            "J": 31.0,
            "Q": 27.0,
            "K": 19.0,
            "A": 17.0,
            "LE": 3.2,
            "CO": 2.7,
            "OR": 0.9,
            "GR": 0.7,
            "BA": 0.5,
        }
        self.reels["base_natural"] = self.build_capped_reel_strips(
            initial,
            seed=2401,
            run_lengths=(1, 2),
            run_weights=(64, 36),
            max_run=2,
        )
        self.reels["base_natural_REFILL"] = self.build_capped_reel_strips(
            refill,
            seed=2417,
            run_lengths=(1, 2, 3),
            run_weights=(8, 46, 46),
            max_run=3,
        )
        self.reel_set_weights["base_play"] = {"base_natural": 1}
        self.reel_set_weights_flat.add("base_natural")

    def pick_reel_set(self, family: str) -> str:
        weights = self.reel_set_weights[family]
        names = list(weights)
        return random.choices(names, weights=[weights[name] for name in names], k=1)[0]

    def initial_reelstrip_id(
        self,
        betmode: str,
        gametype: str | None = None,
        bonus_variant: str | None = None,
    ) -> str:
        if betmode in ("base", "base_ante"):
            if gametype == self.freegame_type:
                return "INITIAL_BONUS"
            return "INITIAL_BASE"
        if betmode == "feature_spin":
            return "FEATURE_SPIN"
        if betmode == "peak_spin":
            # Same Feature strips / run lengths as Feature Spin — gold is chrome + coins only.
            return "FEATURE"
        if betmode in ("bonus_see", "bonus_hear", "bonus_madness") or bonus_variant in (
            "see",
            "hear",
            "madness",
        ):
            return "INITIAL_BONUS"
        if betmode == "bonus_mystery":
            if gametype == self.freegame_type or bonus_variant in ("see", "hear", "madness"):
                return "INITIAL_BONUS"
            return "INITIAL_BASE"
        if gametype == self.freegame_type:
            return "INITIAL_BONUS"
        return "INITIAL"

    def _distribution(self, criteria: str, quota: float, **conditions) -> Distribution:
        base_conditions = {
            "reel_weights": {
                self.basegame_type: {"INITIAL": 1},
                self.freegame_type: {"INITIAL": 1},
            },
            "force_wincap": False,
            "force_freegame": False,
        }
        base_conditions.update(conditions)
        return Distribution(criteria=criteria, quota=quota, conditions=base_conditions)

    def _build_bet_modes(self) -> list[BetMode]:
        bonus_base = self.bonus_hit_rate_base
        bonus_ante = self.bonus_hit_rate_ante
        freegame_base = {
            "scatter_triggers": self.scatter_triggers,
            "force_freegame": True,
        }
        freegame_ante = {
            "scatter_triggers": self.scatter_triggers_ante,
            "force_freegame": True,
        }
        return [
            BetMode("base", 1.0, self.rtp, self.wincap, False, True, False, [
                self._distribution("basegame", 1.0 - bonus_base - BASE_CAP_QUOTA),
                self._distribution("freegame", bonus_base, **freegame_base),
                self._distribution("cap", BASE_CAP_QUOTA, force_wincap=True),
            ]),
            BetMode("base_ante", self.ante_bet_cost, self.rtp, self.wincap, False, True, False, [
                self._distribution("basegame", 1.0 - bonus_ante - ANTE_CAP_QUOTA),
                self._distribution("freegame", bonus_ante, **freegame_ante),
                self._distribution("cap", ANTE_CAP_QUOTA, force_wincap=True),
            ]),
            BetMode("feature_spin", FEATURE_BUY_COST, self.rtp, self.wincap, False, True, False, [
                self._distribution("dead_juicy", FEATURE_DEAD_QUOTA),
                self._distribution("nibble", FEATURE_NIBBLE_QUOTA),
                self._distribution("run", FEATURE_RUN_QUOTA),
                self._distribution("cap", FEATURE_CAP_QUOTA, force_wincap=True),
            ]),
            BetMode("peak_spin", self.peak_spin_cost, self.rtp, self.wincap, False, True, False, [
                self._distribution("dead_juicy", PEAK_DEAD_QUOTA),
                self._distribution("nibble", PEAK_NIBBLE_QUOTA),
                self._distribution("run", PEAK_RUN_QUOTA),
                self._distribution("clip", PEAK_CLIP_QUOTA),
                self._distribution("tease", PEAK_TEASE_QUOTA),
                self._distribution("cap", PEAK_CAP_QUOTA, force_wincap=True),
            ]),
            BetMode("bonus_see", self.see_buy_cost, self.rtp, self.wincap, False, True, True, [
                self._distribution("bonus_see", 1.0 - SEE_CAP_QUOTA, bonus_variant="see"),
                self._distribution("cap", SEE_CAP_QUOTA, force_wincap=True, bonus_variant="see"),
            ]),
            BetMode("bonus_hear", HEAR_BUY_COST, self.rtp, self.wincap, False, True, True, [
                self._distribution("bonus_hear", 1.0 - HEAR_CAP_QUOTA, bonus_variant="hear"),
                self._distribution("cap", HEAR_CAP_QUOTA, force_wincap=True, bonus_variant="hear"),
            ]),
            BetMode("bonus_mystery", self.gamble_buy_cost, self.rtp, self.wincap, False, True, False, [
                self._distribution("gamble_dead", GAMBLE_DEAD_QUOTA - GAMBLE_CAP_QUOTA),
                self._distribution(
                    "gamble_hear",
                    GAMBLE_HEAR_QUOTA,
                    force_freegame=True,
                    scatter_triggers={4: 1},
                ),
                self._distribution(
                    "gamble_madness",
                    GAMBLE_MADNESS_QUOTA,
                    force_freegame=True,
                    scatter_triggers={5: 1},
                ),
                self._distribution("cap", GAMBLE_CAP_QUOTA, force_wincap=True),
            ]),
        ]
