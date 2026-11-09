"""Kong Club math configuration — classic 3-tier tiles + Jul 2 cascade.

Symbol IDs align with the art pipeline:
T/J/Q/K/A, LE/CO/OR/GR/BA, MW, ST, CB/CS/CG.
Tile ranks: 0=none, 1=bronze, 2=silver, 3=gold (mults 2/5/10).
Powers: MULTI + COLLECTOR live (rare; pots rarer than clovers). TIER_SHIFT retired.
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

from src.config.betmode import BetMode
from src.config.config import Config
from src.config.distributions import Distribution
from game_criteria import (
    FEATURE_RUN_QUOTA,
    HUNT_COSTS,
    MYSTERY_HEAR_QUOTA,
    MYSTERY_SEE_QUOTA,
    MYSTERY_SPEAK_QUOTA,
    PEAK_DEAD_QUOTA,
    PEAK_LIVE_QUOTA,
    RISKY_DEAD_QUOTA,
    RISKY_HEAR_QUOTA,
    RISKY_SPEAK_QUOTA,
    SPEAK_DIRECT_MIN_WIN,
    hunt_freegame_quota,
)


STAKE_SLUG = "kong-club"

# Organic bonus entry. 3 ST = See, 4 = Hear, 5+ = Speak No Evil.
# Ante is exactly twice the base trigger rate. Scatter faces are not a lever.
SCATTER_TRIGGERS = {3: 989, 4: 10, 5: 1}
SCATTER_TRIGGERS_ANTE = {3: 989, 4: 10, 5: 1}
# Certified rates are much rarer; the book file oversamples so 500 books
# still contain bonuses and bar fills. Lookup weights put the rate back.
BASE_FREEGAME_QUOTA = 24 / 500
ANTE_FREEGAME_QUOTA = 48 / 500
BASE_PAY_BOOK_QUOTA = 8 / 500
ANTE_PAY_BOOK_QUOTA = 8 / 500

# Buy costs are placeholders until books re-solve them onto 96.3%.
# mode_prices.json overrides these after the solve step.
SEE_BUY_COST = 115.0
HEAR_BUY_COST = 250.0
FEATURE_BUY_COST = 75.0
PEAK_SPIN_COST = 1000.0
MYSTERY_BUY_COST = 180.0
RISKY_BUY_COST = 220.0
GAMBLE_DEAD_BAIT_RATE = 1.0

# Locked pay table (Ryan screenshot). Multiples of total bet, before tile multipliers.
# Bands: 5, 6, 7, 8, 9–10, 11–12, 13+. Cluster size is uncapped; 13 and above share one face.
# Cluster pay = this face × the sum of lit tile multipliers (bronze 2 / silver 5 / gold 10).
CLUSTER_PAY_BANDS = {
    "T": (0.1, 0.2, 0.3, 0.5, 1.5, 5.0, 15.0),
    "J": (0.1, 0.2, 0.3, 0.5, 1.5, 5.0, 15.0),
    "Q": (0.1, 0.2, 0.3, 0.5, 1.5, 5.0, 15.0),
    "K": (0.1, 0.2, 0.3, 0.5, 1.5, 5.0, 15.0),
    "A": (0.1, 0.2, 0.3, 0.5, 1.5, 5.0, 15.0),
    "LE": (0.3, 0.4, 0.5, 0.7, 2.5, 7.5, 25.0),
    "CO": (0.3, 0.4, 0.5, 0.7, 2.5, 7.5, 25.0),
    "OR": (0.5, 0.7, 1.0, 1.5, 5.0, 15.0, 50.0),
    "GR": (0.5, 0.7, 1.0, 1.5, 5.0, 15.0, 50.0),
    "BA": (1.0, 1.5, 2.0, 3.0, 10.0, 30.0, 100.0),
}
# Silver-lean keeps gold faces on the 25. Gold-lean lets 100–500 show up.
COIN_SPREADS = {
    # Silver-lean: mass sits on silver faces; gold almost always pays 25.
    "silver": {
        "CB": [78, 14, 5, 3],
        "CS": [18, 22, 28, 20, 12],
        "CG": [960, 28, 8, 2, 2],
    },
    # Gold-lean: the rich faces (100 / 250 / 500) show up, still below a full-board cap.
    "gold": {
        "CB": [52, 26, 14, 8],
        "CS": [22, 24, 24, 18, 12],
        "CG": [46, 24, 16, 9, 5],
    },
}


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
        self.rtp = 0.963
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
        # Cluster pay is the plain size-scaled face (Ryan, Nov 8 2026: "there are no
        # tile multipliers"). Tiles still rank up and drive coin-game flips.
        # True restores the PR #7 formula: face × sum of lit tile multipliers.
        self.cluster_pay_uses_tile_multipliers = False
        # Coin game (locked spec l.17/19): tiers only change spawn odds; a coin pays
        # its own value and a pot pays the plain sum. True restores the old rule where
        # a landed CB/CS/CG paid face × tile multiplier (2 / 5 / 10).
        self.coin_pay_uses_tile_multipliers = False
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
        spread_name = os.environ.get("MM_COIN_SPREAD", "silver")
        if spread_name not in COIN_SPREADS:
            spread_name = "silver"
        self.coin_spread_name = spread_name
        self.coin_value_weights = {key: list(values) for key, values in COIN_SPREADS[spread_name].items()}
        # Face pools keyed by tile level (1→CB, 2→CS, 3→CG).
        self.activation_coin_value_pools = self._build_activation_coin_pools()
        self.activation_coin_value_weights = self._build_activation_coin_weights()

        # Base, Ante, Hunt, and Feature fill at 10. Bonuses keep bar 5.
        # Trifecta fires one coin game on the connecting spin (threshold 1).
        self.progress_thresholds = {
            "base": 10,
            "base_ante": 10,
            "feature_spin": 10,
            "peak_spin": 1,
            "bonus_see": 5,
            "bonus_hear": 5,
            "bonus_speak": 5,
            "bonus_mystery": 5,
            "bonus_risky": 5,
        }
        for hunt_name in HUNT_COSTS:
            self.progress_thresholds[hunt_name] = 10
        self.base_like_modes = {"base", "base_ante", *HUNT_COSTS}
        # Within a basegame spin: miss / small cluster bait / bar-fill pay.
        # Tuned so a basegame spin averages TARGET_BASE_SPIN_EV. Pay spins are
        # the rare bar fills; small spins move the bar and stop short of 10.
        # Share of non-pay basegame spins that award a short cluster (the bait).
        self.base_small_rate = float(os.environ.get("MM_BASE_SMALL", "0.46"))
        self.base_pay_rate = float(os.environ.get("MM_BASE_PAY", "0.0"))
        self.base_miss_rate = max(0.0, 1.0 - self.base_small_rate - self.base_pay_rate)
        self.hear_to_speak_rate = 1 / 500
        self.speak_direct_min_win = SPEAK_DIRECT_MIN_WIN
        self.tumble_wild_chance = 0.012
        self.tumble_scatter_chance_base = 0.004
        self.tumble_scatter_chance_bonus = 0.018
        # One coin game per spin. The old Hear cap of 3 is not used.
        self.max_board_activations_hear = 1
        self.coin_game_max_reruns = 10
        # MULTI faces — LOCKED Cole 2026-07-18 (COIN_POWERS_LOCKED.md).
        # Weights sit on 2x and 3x. The 10x and 20x faces stay legal but almost never
        # roll, which pays for clovers showing up on small coin games.
        self.coin_game_multi_values = [2, 3, 4, 5, 10, 20]
        self.coin_game_multi_weights = [58, 28, 10, 3, 1, 0]
        # Baseline vs power weights when rolling each lit cell's prize kind.
        self.coin_game_coin_weight = 100
        # Bronze clovers are common (a 2x on a short stack). Silver clovers are a bit
        # more common than before, and the pot rate is trimmed to fund that.
        # Gold clover rate stays put. TIER_SHIFT stays retired.
        self.coin_game_power_by_tile_level = {
            1: {"multiplier": 12, "collector": 0, "tier_shift": 0},
            2: {"multiplier": 10, "collector": 1, "tier_shift": 0},
            3: {"multiplier": 8, "collector": 2, "tier_shift": 0},
        }
        # Trifecta live boards are composed (several clovers and one pot) rather than
        # rolled from this table. Its reruns roll the gold rerun row below like every
        # other mode (spec l.20: pots can appear in reruns).
        self.coin_game_power_peak_gold = {"multiplier": 0, "collector": 0, "tier_shift": 0}
        self.peak_coin_value_weights = [1, 0, 0, 0, 0]
        # Locked spec l.20: pots CAN appear in reruns, so every tier (bronze too) has a
        # rerun pot rate. Bronze 0.5 = half of silver, kept below silver/gold so better
        # tiers stay likelier; it is a placeholder the rebalance may retune.
        self.coin_game_rerun_power_by_tile_level = {
            1: {"coin": 100, "multiplier": 12, "collector": 0.5, "tier_shift": 0},
            2: {"coin": 100, "multiplier": 10, "collector": 1, "tier_shift": 0},
            3: {"coin": 100, "multiplier": 8, "collector": 2, "tier_shift": 0},
        }
        # Trifecta reruns flip most of an all-gold board at once, so the gold row above
        # would spawn a pot on nearly every rerun and run every live spin to the cap
        # (measured: 168/500 books at 25,000x). Its own row keeps pots possible on
        # every rerun at a low per-tile rate (~7% chance per 30-tile rerun). Placeholder
        # for the rebalance; clovers stay off as before.
        self.coin_game_rerun_power_peak = {"coin": 100, "multiplier": 0, "collector": 0.25, "tier_shift": 0}
        # Mode fallback matches bronze so Extra Chance / unknown modes do not invent pots.
        self.coin_game_power_weights = {
            "base": {"multiplier": 12, "collector": 0, "tier_shift": 0},
            "base_ante": {"multiplier": 12, "collector": 0, "tier_shift": 0},
            "feature_spin": {"multiplier": 12, "collector": 0, "tier_shift": 0},
            "peak_spin": {"multiplier": 12, "collector": 0, "tier_shift": 0},
            "bonus_see": {"multiplier": 12, "collector": 0, "tier_shift": 0},
            "bonus_hear": {"multiplier": 12, "collector": 0, "tier_shift": 0},
            "bonus_speak": {"multiplier": 12, "collector": 0, "tier_shift": 0},
            "bonus_mystery": {"multiplier": 12, "collector": 0, "tier_shift": 0},
            "bonus_risky": {"multiplier": 12, "collector": 0, "tier_shift": 0},
        }
        for hunt_name in HUNT_COSTS:
            self.coin_game_power_weights[hunt_name] = {
                "multiplier": 12,
                "collector": 0,
                "tier_shift": 0,
            }
        # Exact Le Bandit cluster pays in base AND bonus (do not dilute the table).
        # RTP levers: shorter strip runs (fewer tumbles), trigger rarity — not pay scales.
        self.bonus_cluster_pay_scale = 1.0
        # Priced buys only. Base, Ante, Hunt, Feature, and Trifecta keep their spreads.
        # These levers pull See toward 100x, Hear toward 300x, and the two Speaks
        # toward the Mystery (330x) and Risky (500x) mixes.
        self.buy_cluster_pay_scale = 1.0
        self.buy_power_scale = 1.0
        # See only needs a light trim (about 100x). Hear needs the clover/pot tail cut (about 300x).
        self.see_power_scale = 0.85
        self.see_cluster_pay_scale = 0.96
        self.hear_power_scale = 0.62
        self.hear_cluster_pay_scale = 0.90
        # Direct Speak (Mystery / Risky) is lifted so it averages with a Hear→Speak
        # upgrade. Upgrades drop carried gold and silver to bronze, which takes the
        # other side of that gap. Prices stay put via the lookup weights.
        self.mystery_speak_power_scale = 0.72
        self.risky_speak_power_scale = 1.12
        self.mystery_speak_cluster_scale = 0.98
        self.risky_speak_cluster_scale = 1.02
        self.buy_coin_value_weights = {
            "CB": [84, 10, 4, 2],
            "CS": [28, 26, 24, 14, 8],
            "CG": [975, 16, 5, 3, 1],
        }
        self.mystery_speak_coin_weights = {
            "CB": [78, 14, 5, 3],
            "CS": [22, 26, 26, 16, 10],
            "CG": [955, 28, 10, 5, 2],
        }
        self.risky_speak_coin_weights = {
            "CB": [74, 16, 6, 4],
            "CS": [18, 24, 28, 18, 12],
            "CG": [945, 32, 14, 6, 3],
        }
        # Share of base-game hits that stop at 8/10 on the bar (4 of 5 full).
        # Fraction of ordinary basegame spins that walk the bar to about 8/10.
        self.base_near_miss_share = 0.05
        # Locked screenshot faces (× total bet). Scale stays 1.0 — do not dilute the table.
        self.paytable_scale = 1.0
        # Always pay face as labeled (1.0). Do not soft-scale coin values.
        self.coin_tile_scale_by_mode = {
            "base": 1.0,
            "base_ante": 1.0,
            "feature_spin": 1.0,
            "peak_spin": 1.0,
            "bonus_see": 1.0,
            "bonus_hear": 1.0,
            "bonus_speak": 1.0,
            "bonus_mystery": 1.0,
            "bonus_risky": 1.0,
        }
        for hunt_name in HUNT_COSTS:
            self.coin_tile_scale_by_mode[hunt_name] = 1.0
        # Every lit tile pays a virtual coin. None = no sample cap.
        self.max_activation_coins_by_mode = {
            "base": None,
            "base_ante": None,
            "feature_spin": None,
            "peak_spin": None,
            "bonus_see": None,
            "bonus_hear": None,
            "bonus_speak": None,
            "bonus_mystery": None,
            "bonus_risky": None,
        }
        for hunt_name in HUNT_COSTS:
            self.max_activation_coins_by_mode[hunt_name] = None
        # Dead once Hear is uncapped.
        self.hear_coin_cap_boost_chance = 0.0
        # PEAK: light every cell gold (level 3) before the drop. Progress still starts at 0.
        self.peak_spin_seed_gold = True
        prices = self._load_mode_prices()
        self.peak_spin_cost = float(prices.get("peak_spin", PEAK_SPIN_COST))
        self.feature_buy_cost = float(prices.get("feature_spin", FEATURE_BUY_COST))
        self.see_buy_cost = float(prices.get("bonus_see", SEE_BUY_COST))
        self.hear_buy_cost = float(prices.get("bonus_hear", HEAR_BUY_COST))
        # Mystery was published as `bonus_pick` through pr7-963; read either key.
        self.mystery_buy_cost = float(
            prices.get("bonus_mystery", prices.get("bonus_pick", MYSTERY_BUY_COST))
        )
        self.risky_buy_cost = float(prices.get("bonus_risky", RISKY_BUY_COST))
        self.gamble_buy_cost = self.mystery_buy_cost
        self.gamble_dead_bait_rate = GAMBLE_DEAD_BAIT_RATE
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
        # No wild cap. Weights keep five-plus wilds rare; the draw does not reject them.
        self.max_initial_wilds = None
        self.min_feature_cost_win = 0.01

        # Organic bonus entry via forced-scatter criteria (scatters are not on base strips).
        self.bonus_hit_rate_base = BASE_FREEGAME_QUOTA
        self.bonus_hit_rate_ante = ANTE_FREEGAME_QUOTA
        self.scatter_triggers = SCATTER_TRIGGERS
        self.scatter_triggers_ante = SCATTER_TRIGGERS_ANTE
        self.bonus_variant_map = {3: "see", 4: "hear", 5: "speak", 6: "speak"}
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
        # Scatters can land, including on tumbles, and count toward retriggers.
        self.symbol_weights_bonus_initial["ST"] = 0.55
        self.symbol_weights_bonus_refill = dict(self.symbol_weights_base_refill)
        self.symbol_weights_bonus_refill.update(self.physical_coin_weights)
        self.symbol_weights_bonus_refill["ST"] = 0.35
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

    @staticmethod
    def cluster_pay_band(size: int) -> int:
        """0=5, 1=6, 2=7, 3=8, 4=9–10, 5=11–12, 6=13+."""
        size = int(size)
        if size <= 5:
            return 0
        if size == 6:
            return 1
        if size == 7:
            return 2
        if size == 8:
            return 3
        if size <= 10:
            return 4
        if size <= 12:
            return 5
        return 6

    def cluster_pay(self, size: int, symbol: str) -> float:
        """Locked band face. 13 and every larger cluster share the 13+ face."""
        bands = CLUSTER_PAY_BANDS.get(symbol)
        if not bands:
            return 0.0
        scale = float(getattr(self, "paytable_scale", 1.0))
        return round(bands[self.cluster_pay_band(size)] * scale, 6)

    def _build_paytable(self) -> dict[tuple[int, str], float]:
        """Per-size pays from 5 through 30 (the full board). 13+ repeats one face."""
        table: dict[tuple[int, str], float] = {}
        for symbol in CLUSTER_PAY_BANDS:
            for size in range(5, 31):
                table[(size, symbol)] = self.cluster_pay(size, symbol)
        return table

    @staticmethod
    def _load_mode_prices() -> dict:
        path = Path(__file__).with_name("mode_prices.json")
        if not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}

    @staticmethod
    def cluster_pay_tier(size: int) -> int:
        """Identity size key. Pays are no longer collapsed into bands."""
        return max(5, int(size))

    def build_reel_strips(
        self,
        weights: dict[str, float],
        seed: int,
        strip_len: int = 50,
        run_weights: tuple[int, int, int] = (40, 45, 15),
        *,
        organic: bool = False,
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
                if organic and strip and symbol == strip[-1]:
                    for _ in range(5):
                        symbol = reel_rng.choices(symbols, weights=weight_values, k=1)[0]
                        if symbol != strip[-1]:
                            break
                    if symbol == strip[-1]:
                        alternatives = [
                            name
                            for name, weight in zip(symbols, weight_values)
                            if weight > 0 and name != strip[-1]
                        ]
                        if alternatives:
                            symbol = alternatives[reel_rng.randrange(len(alternatives))]
                run_len = reel_rng.choices([1, 2, 3], weights=list(run_weights), k=1)[0]
                strip.extend([symbol] * min(run_len, 3))
            strip = strip[:strip_len]
            self._light_shuffle_runs(strip, rng=random.Random(seed + reel * 37))
            self._ensure_coin_stop(strip, weights, rng=random.Random(seed + reel * 73))
            if organic:
                # A window of 5 cannot be a solid column. Runs of 4 still cascade.
                self._cap_runs(strip, 4)
            strips.append(strip)
        return strips

    @staticmethod
    def _cap_runs(strip: list[str], limit: int = 3) -> None:
        """No reel window of 5 is a solid stack. Runs stay at 3."""
        pool = list(dict.fromkeys(strip))
        if len(pool) < 2:
            return
        for _ in range(6):
            run = 1
            changed = False
            for index in range(1, len(strip)):
                if strip[index] == strip[index - 1]:
                    run += 1
                    if run > limit:
                        for alt in pool:
                            if alt != strip[index] and (index + 1 == len(strip) or alt != strip[index + 1]):
                                strip[index] = alt
                                changed = True
                                run = 1
                                break
                else:
                    run = 1
            if not changed:
                break
        if len(strip) > limit + 1 and strip[0] == strip[-1]:
            left = 0
            while left < len(strip) and strip[left] == strip[0]:
                left += 1
            right = 0
            while right < len(strip) and strip[-1 - right] == strip[0]:
                right += 1
            if limit < left + right < len(strip):
                strip[0] = next(symbol for symbol in pool if symbol != strip[1])

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
        """Weighted strip sets. Base/ante share four. See, Hear, and Speak have three each."""
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
            # Small irregular clusters. Lows dominate so a hit is usually under 1x,
            # and runs stay short so a column is never painted solid.
            "base_small": (
                even(T=16, J=16, Q=14, K=12, A=12, LE=5, CO=4, OR=2, GR=1, BA=1, MW=0.04),
                (40, 45, 15),
                466,
                (70, 24, 6),
            ),
            # Busier lows. The refill keeps connecting, so some spins walk the bar
            # up without a scripted column chain.
            "base_link": (
                even(T=18, J=16, Q=14, K=12, A=10, LE=4, CO=3, OR=2, GR=1, BA=1, MW=0.12),
                (12, 38, 50),
                477,
                (10, 34, 56),
            ),
            "base_hot": (even(Q=12, K=12, BA=9, MW=1.2), (36, 40, 24), 433, (55, 32, 13)),
            "base_teaser": (even(MW=0.2), (80, 18, 2), 444, (85, 12, 3)),
            # Slow spins rarely fill the bar. Steady / burst are the spotlight third.
            "see_slow": (even(MW=0.05, ST=0.28), (96, 3, 1), 511, (97, 2, 1)),
            "see_steady": (even(BA=10, MW=0.9, ST=0.45), (46, 38, 16), 522, (56, 32, 12)),
            "see_burst": (even(Q=12, K=12, BA=11, MW=1.4, ST=0.45), (32, 42, 26), 533, (42, 38, 20)),
            "hear_slow": (even(MW=0.06, ST=0.22), (92, 7, 1), 611, (94, 5, 1)),
            "hear_steady": (even(OR=12, GR=12, BA=13, MW=2.0, ST=0.22), (26, 40, 34), 622, (34, 40, 26)),
            "hear_burst": (even(Q=14, BA=15, MW=2.8, ST=0.22), (16, 38, 46), 633, (22, 40, 38)),
            # Speak No Evil is a coin game every spin. Ranks carry, so later spins
            # are the rich ones. The 1,000× floor applies only to direct entry.
            "speak_low": (even(MW=0.30, ST=0.2), (76, 20, 4), 711, (82, 16, 2)),
            "speak_mid": (even(BA=10, MW=1.05, ST=0.2), (48, 38, 14), 722, (58, 32, 10)),
            "speak_high": (hot(1.5), (34, 42, 24), 733, (44, 38, 18)),
            # Feature Spin always connects and always runs the coin game, so the
            # strips — not the price — keep the spin near 50–75x. Mild is one short
            # low cluster. Rich is the rare wild chain.
            "feature_mild": (
                even(T=22, J=20, Q=16, K=14, A=12, LE=3, CO=2, OR=1, GR=1, BA=0.6, MW=0.15),
                (70, 24, 6),
                811,
                (96, 3, 1),
            ),
            "feature_rich": (hot(6.4), (10, 28, 62), 822, (14, 32, 54)),
            "peak_a": (even(MW=1.0), (40, 40, 20), 911, (50, 36, 14)),
            "peak_b": (hot(2.0), (20, 40, 40), 922, (30, 40, 30)),
        }
        self.reel_set_weights = {
            "base": {"base_quiet": 52, "base_normal": 16, "base_hot": 26, "base_teaser": 6},
            "see": {"see_slow": 94, "see_steady": 5, "see_burst": 1},
            "hear": {"hear_slow": 86, "hear_steady": 12, "hear_burst": 2},
            "speak": {"speak_low": 55, "speak_mid": 35, "speak_high": 10},
            "feature": {"feature_mild": 78, "feature_rich": 22},
            "peak": {"peak_a": 55, "peak_b": 45},
            "gamble_dead": {"base_quiet": 1},
        }
        self.reel_set_weights_flat = set(specs)
        for name, (weights, runs, seed, refill_runs) in specs.items():
            self.reels[name] = self.build_reel_strips(weights, seed=seed, run_weights=runs, organic=True)
            refill = {symbol: weight for symbol, weight in weights.items() if symbol not in {"MW", "ST"}}
            self.reels[f"{name}_REFILL"] = self.build_reel_strips(
                refill, seed=seed + 17, run_weights=refill_runs, organic=True
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
        if betmode in self.base_like_modes:
            if gametype == self.freegame_type:
                return "INITIAL_BONUS"
            return "INITIAL_BASE"
        if betmode == "feature_spin":
            return "FEATURE_SPIN"
        if betmode == "peak_spin":
            # Same Feature strips / run lengths as Feature Spin — gold is chrome + coins only.
            return "FEATURE"
        if betmode in ("bonus_see", "bonus_hear", "bonus_speak") or bonus_variant in (
            "see",
            "hear",
            "speak",
        ):
            return "INITIAL_BONUS"
        if betmode in ("bonus_mystery", "bonus_risky"):
            if gametype == self.freegame_type or bonus_variant in ("see", "hear", "speak"):
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
        modes = [
            BetMode("base", 1.0, self.rtp, self.wincap, False, True, False, [
                self._distribution("basegame", 1.0 - bonus_base - BASE_PAY_BOOK_QUOTA),
                self._distribution("bar_pay", BASE_PAY_BOOK_QUOTA),
                self._distribution("freegame", bonus_base, **freegame_base),
            ]),
            BetMode("base_ante", self.ante_bet_cost, self.rtp, self.wincap, False, True, False, [
                self._distribution("basegame", 1.0 - bonus_ante - ANTE_PAY_BOOK_QUOTA),
                self._distribution("bar_pay", ANTE_PAY_BOOK_QUOTA),
                self._distribution("freegame", bonus_ante, **freegame_ante),
            ]),
        ]
        for hunt_name, cost in HUNT_COSTS.items():
            quota = hunt_freegame_quota(cost)
            pay_q = min(BASE_PAY_BOOK_QUOTA, max(0.0, 0.9 - quota))
            modes.append(
                BetMode(hunt_name, cost, self.rtp, self.wincap, False, True, False, [
                    self._distribution("basegame", 1.0 - quota - pay_q),
                    self._distribution("bar_pay", pay_q),
                    self._distribution("freegame", quota, **freegame_base),
                ])
            )
        modes.extend([
            BetMode("feature_spin", self.feature_buy_cost, self.rtp, self.wincap, False, True, False, [
                self._distribution("run", FEATURE_RUN_QUOTA),
            ]),
            BetMode("peak_spin", self.peak_spin_cost, self.rtp, self.wincap, False, True, False, [
                self._distribution("dead_juicy", PEAK_DEAD_QUOTA),
                self._distribution("live", PEAK_LIVE_QUOTA),
            ]),
            BetMode("bonus_see", self.see_buy_cost, self.rtp, self.wincap, False, True, True, [
                self._distribution("bonus_see", 1.0, bonus_variant="see"),
            ]),
            BetMode("bonus_hear", self.hear_buy_cost, self.rtp, self.wincap, False, True, True, [
                self._distribution("bonus_hear", 1.0, bonus_variant="hear"),
            ]),
            BetMode("bonus_mystery", self.mystery_buy_cost, self.rtp, self.wincap, False, True, True, [
                self._distribution("pick_see", MYSTERY_SEE_QUOTA, bonus_variant="see"),
                self._distribution("pick_hear", MYSTERY_HEAR_QUOTA, bonus_variant="hear"),
                self._distribution("pick_speak", MYSTERY_SPEAK_QUOTA, bonus_variant="speak"),
            ]),
            BetMode("bonus_risky", self.risky_buy_cost, self.rtp, self.wincap, False, True, True, [
                self._distribution("risky_dead", RISKY_DEAD_QUOTA),
                self._distribution("risky_hear", RISKY_HEAR_QUOTA, bonus_variant="hear"),
                self._distribution("risky_speak", RISKY_SPEAK_QUOTA, bonus_variant="speak"),
            ]),
        ])
        return modes
