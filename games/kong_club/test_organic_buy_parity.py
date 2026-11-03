"""Organic free-spin profile must equal buy free-spin profile (RTP playbook).

Fails if See/Hear spin-in uses different strips, coin pools, caps, or cluster scale
than the matching buy mode.
"""

from __future__ import annotations

import sys
from pathlib import Path

GAME_ROOT = Path(__file__).resolve().parent
SDK_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SDK_ROOT))
sys.path.insert(0, str(GAME_ROOT))

from game_coin_feature import _mode_coin_scale, resolve_coin_game
from game_config import GameConfig
from gamestate import GameState


def fresh_config() -> GameConfig:
    GameConfig._instance = None
    return GameConfig()


def state(betmode: str = "base") -> GameState:
    gs = GameState(fresh_config())
    gs.betmode = betmode
    gs.criteria = "basegame"
    return gs


def test_coin_tile_scale_locked_at_one():
    config = fresh_config()
    for mode, scale in config.coin_tile_scale_by_mode.items():
        assert scale == 1.0, f"{mode} coin_tile_scale must be 1.0 (hard faces), got {scale}"


def test_bonus_strip_ids_match_organic_and_buy():
    config = fresh_config()
    buy_hear = config.initial_reelstrip_id("bonus_hear", config.freegame_type)
    organic_hear = config.initial_reelstrip_id("base", config.freegame_type, bonus_variant="hear")
    buy_see = config.initial_reelstrip_id("bonus_see", config.freegame_type)
    organic_see = config.initial_reelstrip_id("base", config.freegame_type, bonus_variant="see")
    assert buy_hear == organic_hear == "INITIAL_BONUS"
    assert buy_see == organic_see == "INITIAL_BONUS"
    assert config.tumble_refill_reel_ids["INITIAL_BONUS"] == "REFILL_BONUS"
    assert "bonus_see" in {mode.get_name() for mode in config.bet_modes}


def test_no_organic_only_weight_fork():
    config = fresh_config()
    assert config.symbol_weights_bonus_hear_initial == config.symbol_weights_bonus_initial
    assert config.initial_reelstrip_id("bonus_hear", config.freegame_type) == config.initial_reelstrip_id(
        "base", config.freegame_type, bonus_variant="hear"
    )


def test_hear_scales_identical_for_buy_and_organic():
    """Buy betmode and organic freegame+variant pay the same coin scale."""
    config = fresh_config()
    assert not hasattr(config, "max_activation_coins_by_mode")

    buy_hear = state("bonus_hear")
    buy_hear.gametype = buy_hear.config.freegame_type
    buy_hear.bonus_variant = "hear"
    organic_hear = state("base")
    organic_hear.gametype = organic_hear.config.freegame_type
    organic_hear.bonus_variant = "hear"

    assert _mode_coin_scale(buy_hear) == _mode_coin_scale(organic_hear) == 1.0


def test_shared_bonus_cluster_pay_scale():
    config = fresh_config()
    assert config.bonus_cluster_pay_scale == 1.0
    assert config.paytable_scale == 1.0


def test_coin_pools_identical_across_modes():
    config = fresh_config()
    assert config.activation_coin_value_pools[1] == config.coin_values["CB"]
    assert config.activation_coin_value_pools[2] == config.coin_values["CS"]
    assert config.activation_coin_value_pools[3] == config.coin_values["CG"]


def test_organic_and_buy_activation_use_same_hard_faces():
    """Same lit board + seed → same face pool membership and cap count."""

    def primed(betmode: str, variant: str) -> GameState:
        gs = state(betmode)
        gs.reset_book()
        gs.gametype = gs.config.freegame_type
        gs.bonus_variant = variant
        zero = {"multiplier": 0, "collector": 0, "tier_shift": 0}
        gs.config.coin_game_power_weights = {
            key: dict(zero) for key in gs.config.coin_game_power_weights
        }
        gs.config.coin_game_power_by_tile_level = {
            level: dict(zero) for level in gs.config.coin_game_power_by_tile_level
        }
        gs.config.coin_game_power_peak_gold = dict(zero)
        gs.board = [
            [gs.create_symbol("T") for _ in range(5)] for _ in range(6)
        ]
        gs.reset_grid_mults()
        for reel in range(6):
            for row in range(5):
                gs.seed_tile_to_level(reel, row, 3)
        gs.simulation_seed = 4242
        gs.progress_activation_count = 1
        return gs

    buy = primed("bonus_hear", "hear")
    organic = primed("base", "hear")
    buy_total, buy_items, _ = resolve_coin_game(buy)
    org_total, org_items, _ = resolve_coin_game(organic)

    lit = [(reel, row) for reel in range(6) for row in range(5) if buy.tile_levels[reel][row] > 0]
    buy_first = [(item["reel"], item["row"]) for item in buy_items if item.get("round") == 1]
    org_first = [(item["reel"], item["row"]) for item in org_items if item.get("round") == 1]
    assert sorted(buy_first) == sorted(org_first) == lit
    assert buy_total == org_total
    for b, o in zip(buy_items, org_items):
        assert b["value"] == o["value"]
        assert b["value"] in buy.config.coin_values["CG"]
        assert float(b["value"]).is_integer()


def test_fs_strips_have_no_scatters():
    config = fresh_config()
    for strip_id in (
        "INITIAL_BONUS",
        "REFILL_BONUS",
        "FEATURE",
        "FEATURE_REFILL",
        "FEATURE_SPIN",
        "FEATURE_SPIN_REFILL",
    ):
        for strip in config.reels[strip_id]:
            assert config.scatter_symbol not in strip, f"{strip_id} must not contain scatters"


if __name__ == "__main__":
    test_coin_tile_scale_locked_at_one()
    test_bonus_strip_ids_match_organic_and_buy()
    test_no_organic_only_weight_fork()
    test_hear_caps_identical_for_buy_and_organic()
    test_shared_bonus_cluster_pay_scale()
    test_coin_pools_identical_across_modes()
    test_organic_and_buy_activation_use_same_hard_faces()
    test_fs_strips_have_no_scatters()
    print("test_organic_buy_parity: all passed")
