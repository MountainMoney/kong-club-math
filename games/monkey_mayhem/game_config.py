"""Monkey Mayhem math configuration — classic 3-tier tiles + Jul 2 cascade.

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
    BASE_CAP_QUOTA,
    FEATURE_NIBBLE_QUOTA,
    FEATURE_RUN_QUOTA,
    PEAK_CAP_QUOTA,
    PEAK_CLIP_QUOTA,
    PEAK_DEAD_QUOTA,
    PEAK_NIBBLE_QUOTA,
    PEAK_RUN_QUOTA,
    PEAK_TEASE_QUOTA,
)


STAKE_SLUG = "monkey-mayhem"

# Organic bonus entry — same pattern as Football Fiesta:
# quota picks "freegame" criteria → force N scatters from weighted table → no organic land on base strips.
SCATTER_TRIGGERS = {3: 70, 4: 25, 5: 5}
# Ante: 2× weight on higher scatter counts (more Hear bonuses when forced).
SCATTER_TRIGGERS_ANTE = {3: 140, 4: 50, 5: 10}
# 2× ante trigger rate (same ratio as Football Fiesta base vs ante).
BASE_FREEGAME_QUOTA = 1 / 220  # ~0.45%
ANTE_FREEGAME_QUOTA = 1 / 128  # ~0.78% (~1.7× base access)

# Gamble buy — 50% dead / 40% 4 ST Hear / 10% 5 ST Monkey Madness.
# Cost is a working placeholder until the RTP pass (Cole 2026-09-01).
GAMBLE_BUY_COST = 100.0
SEE_BUY_COST = 100.0
GAMBLE_DEAD_QUOTA = 0.50
GAMBLE_HEAR_QUOTA = 0.40
GAMBLE_MADNESS_QUOTA = 0.10
# Dead spins: always plant 2 ST on reels 0–1 and tease the rest (no bonus).
GAMBLE_DEAD_BAIT_RATE = 1.0


class GameConfig(Config):
    """Source-of-truth configuration for Monkey Mayhem (3-tier tiles)."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "monkey_mayhem"
        self.provider_name = "Trifecta"
        self.provider_number = 0
        self.working_name = "Monkey Mayhem"
        self.rtp = 0.9601
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
        self.see_wild_symbol = "SEE"
        self.sticky_wild_symbol = "HEAR"
        self.speak_wild_symbol = "SPEAK"
        self.three_monkeys = [
            self.see_wild_symbol,
            self.sticky_wild_symbol,
            self.speak_wild_symbol,
        ]

        # Phase A: only MW is a cluster wild (SEE/HEAR parked).
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
        # Integer bet-multiples only — same face pools, heavily skewed to the low end.
        self.coin_values = {
            "CB": [1, 2, 3, 4],
            "CS": [5, 7, 10, 15, 20],
            "CG": [25, 50, 100, 250, 500],
        }
        self.coin_value_weights = {
            "CB": [75, 18, 5, 2],
            "CS": [70, 18, 8, 3, 1],
            "CG": [72, 18, 7, 2, 1],
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
            "bonus_gamble": 5,
        }
        # Hear bonus: coin game chains at most this many times per spin.
        self.max_board_activations_hear = 3
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
        # Mode fallback matches bronze so Extra Chance / unknown modes do not invent pots.
        self.coin_game_power_weights = {
            "base": {"multiplier": 3, "collector": 0, "tier_shift": 0},
            "base_ante": {"multiplier": 3, "collector": 0, "tier_shift": 0},
            "feature_spin": {"multiplier": 3, "collector": 0, "tier_shift": 0},
            "peak_spin": {"multiplier": 3, "collector": 0, "tier_shift": 0},
            "bonus_see": {"multiplier": 3, "collector": 0, "tier_shift": 0},
            "bonus_hear": {"multiplier": 3, "collector": 0, "tier_shift": 0},
            "bonus_madness": {"multiplier": 3, "collector": 0, "tier_shift": 0},
            "bonus_gamble": {"multiplier": 3, "collector": 0, "tier_shift": 0},
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
            "bonus_gamble": 1.0,
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
            "bonus_gamble": None,
        }
        # Dead once Hear is uncapped.
        self.hear_coin_cap_boost_chance = 0.0
        # Feature Spin: bronze floor; ranks still only grow on connected clusters.
        self.feature_spin_seed_tiles = 24
        # PEAK: light every cell gold (level 3) before the drop. Progress still starts at 0.
        self.peak_spin_seed_gold = True
        self.peak_spin_cost = 1000.0
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
        self.max_initial_wilds = 2
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
            # No physical CB/CS/CG — Board Activation always virtual-fills lit tiles.
        }
        # Refill: exclude MW / ST / three_monkeys / coins.
        self.symbol_weights_refill = {
            symbol: weight
            for symbol, weight in self.symbol_weights_initial.items()
            if symbol
            not in {
                self.standard_wild,
                self.scatter_symbol,
                *self.three_monkeys,
            }
        }
        # Base refill: NO coins (same as generic refill now).
        self.symbol_weights_base_refill = dict(self.symbol_weights_refill)
        self.symbol_weights_no_scatter_initial = {
            symbol: weight
            for symbol, weight in self.symbol_weights_initial.items()
            if symbol != self.scatter_symbol
        }
        # Feature / bonus: no physical coins (virtual collect only).
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
                self.symbol_weights_base_refill,
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
                self.symbol_weights_feature_initial,
                seed=323,
                run_weights=(10, 35, 55),
            ),
            "FEATURE_SPIN_REFILL": self.build_reel_strips(
                self.symbol_weights_feature_refill,
                seed=333,
                run_weights=(10, 35, 55),
            ),
        }
        self.tumble_refill_reel_ids = {
            "INITIAL": "REFILL",
            "INITIAL_BASE": "REFILL_BASE",
            "INITIAL_NO_SCATTER": "REFILL",
            "INITIAL_BONUS": "REFILL_BONUS",
            "FEATURE": "FEATURE_REFILL",
            "FEATURE_SPIN": "FEATURE_SPIN_REFILL",
        }

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
        if betmode == "bonus_gamble":
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
                self._distribution("basegame", 1.0 - bonus_ante),
                self._distribution("freegame", bonus_ante, **freegame_ante),
            ]),
            BetMode("feature_spin", 50.0, self.rtp, self.wincap, False, True, True, [
                self._distribution("nibble", FEATURE_NIBBLE_QUOTA),
                self._distribution("run", FEATURE_RUN_QUOTA),
            ]),
            BetMode("peak_spin", self.peak_spin_cost, self.rtp, self.wincap, False, True, True, [
                self._distribution("dead_juicy", PEAK_DEAD_QUOTA),
                self._distribution("nibble", PEAK_NIBBLE_QUOTA),
                self._distribution("run", PEAK_RUN_QUOTA),
                self._distribution("clip", PEAK_CLIP_QUOTA),
                self._distribution("tease", PEAK_TEASE_QUOTA),
                self._distribution("cap", PEAK_CAP_QUOTA, force_wincap=True),
            ]),
            BetMode("bonus_see", self.see_buy_cost, self.rtp, self.wincap, False, True, True, [
                self._distribution("bonus_see", 1.0, bonus_variant="see"),
            ]),
            BetMode("bonus_hear", 200.0, self.rtp, self.wincap, False, True, True, [
                self._distribution("bonus_hear", 1.0, bonus_variant="hear"),
            ]),
            BetMode("bonus_gamble", self.gamble_buy_cost, self.rtp, self.wincap, False, True, True, [
                self._distribution("gamble_dead", GAMBLE_DEAD_QUOTA),
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
            ]),
        ]
