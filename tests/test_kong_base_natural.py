"""Base and ante draw real stops. Mystery still uses the planted layouts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "games" / "kong_club"))

from game_coin_feature import base_coin_game_scale, resolve_coin_game
from game_config import GameConfig
from gamestate import GameState


def _play_names(gs) -> list[list[str]]:
    return [[symbol.name for symbol in column] for column in gs.board]


def _full_columns(columns: list[list[str]]) -> int:
    count = 0
    for column in columns:
        if len(column) == 5 and len(set(column)) == 1 and column[0] not in {"MW", "ST"}:
            count += 1
    return count


def test_base_natural_strips_cap_runs_and_skip_specials():
    config = GameConfig()
    assert config.reel_set_weights["base_play"] == {"base_natural": 1}
    assert config.tumble_refill_reel_ids["base_natural"] == "base_natural_REFILL"
    for strip in config.reels["base_natural"]:
        assert len(strip) == 96
        assert config._longest_run(strip) <= 2
        assert "ST" not in strip
        assert not any(symbol in config.coin_symbols for symbol in strip)
    for strip in config.reels["base_natural_REFILL"]:
        assert config._longest_run(strip) <= 3
        assert "MW" not in strip
        assert "ST" not in strip
        assert not any(symbol in config.coin_symbols for symbol in strip)


def test_base_and_ante_draw_random_stops():
    config = GameConfig()
    planted = 0
    columns = 0
    for mode in ("base", "base_ante"):
        for seed in range(40):
            gs = GameState(config)
            gs.betmode = mode
            gs.criteria = "basegame"
            gs.reset_book()
            gs.gametype = config.basegame_type
            gs.use_reel_family("base_play")
            gs.draw_prepared_board()
            if gs.reel_positions == [0, 0, 0, 0, 0, 0]:
                planted += 1
            columns += _full_columns(_play_names(gs))
            assert gs.reel_set_name == "base_natural"
            assert not any(symbol.name == "ST" for column in gs.board for symbol in column)
            assert not any(symbol.name in config.coin_symbols for column in gs.board for symbol in column)
    # Planted boards always used stop 0. Random stops should not.
    assert planted < 2
    assert columns == 0


def test_base_pay_scales_leave_bonus_table_alone():
    """Every mode pays the plain cluster table and the labeled coin faces."""
    config = GameConfig()
    assert config.paytable_scale == 1.0
    assert config.bonus_cluster_pay_scale == 1.0
    assert config.base_cluster_pay_scale == 1.0
    assert config.base_coin_game_scale == 1.0
    assert not hasattr(config, "base_locked_coin_values")
    assert config.multiplier_table == [2, 5, 10]
    assert config.coin_values == {
        "CB": [0.2, 0.5, 1, 2, 3, 4],
        "CS": [5, 10, 15, 20],
        "CG": [25, 50, 100, 250, 500, 1000],
    }
    assert config.coin_value_weights["CB"] == [72, 18, 6, 2, 1, 1]
    assert config.coin_value_weights["CS"] == [84, 10, 4, 2]
    assert config.coin_value_weights["CG"] == [1600, 80, 20, 4, 2, 1]
    assert config.coin_value_weights["CG"][-1] < min(config.coin_value_weights["CG"][:-1])
    assert config.coin_game_multi_values == [2, 3, 4, 5, 10, 20]
    assert config.coin_game_multi_weights == [180, 90, 36, 12, 2, 1]
    assert config.coin_game_power_by_tile_level[1] == {"multiplier": 3, "collector": 0, "tier_shift": 0}
    assert config.coin_game_power_by_tile_level[2] == {"multiplier": 6, "collector": 2, "tier_shift": 0}
    assert config.coin_game_power_by_tile_level[3] == {"multiplier": 8, "collector": 3, "tier_shift": 0}
    assert config.progress_thresholds["base"] == 5
    assert config.progress_thresholds["base_ante"] == 5
    assert config.progress_thresholds["bonus_see"] == 5
    assert config.progress_thresholds["bonus_hear"] == 5
    assert config.progress_thresholds["bonus_madness"] == 5
    assert not hasattr(config, "max_activation_coins_by_mode")
    assert config.paytable[(5, "T")] == round(0.10 * 0.67, 6)
    assert config.paytable[(5, "BA")] == round(1.00 * 0.67, 6)
    assert config.paytable[(11, "BA")] == round(30.00 * 0.67, 6)
    assert config.paytable[(13, "BA")] == round(100.00 * 0.67, 6)
    assert config.wincap == 25000.0

    base = GameState(config)
    base.betmode = "base"
    base.gametype = config.basegame_type
    assert base_coin_game_scale(base) == 1.0

    ante = GameState(config)
    ante.betmode = "base_ante"
    ante.gametype = config.basegame_type
    assert base_coin_game_scale(ante) == 1.0

    free = GameState(config)
    free.betmode = "base"
    free.gametype = config.freegame_type
    assert base_coin_game_scale(free) == 1.0

    bonus = GameState(config)
    bonus.betmode = "bonus_hear"
    bonus.gametype = config.freegame_type
    assert base_coin_game_scale(bonus) == 1.0


def test_mystery_shared_entry_still_plants():
    config = GameConfig()
    gs = GameState(config)
    gs.betmode = "bonus_mystery"
    gs.criteria = "bonus_mystery_hear"
    gs.reset_book()
    gs.gametype = config.basegame_type
    gs.use_reel_family("base", "base_quiet")
    gs.draw_prepared_board()
    assert gs.reel_positions == [0, 0, 0, 0, 0, 0]
    assert gs.reel_set_name == "base_quiet"


def test_coin_game_flips_every_lit_tile():
    """Every connected cell flips. No mode samples a subset."""
    config = GameConfig()
    for betmode in ("base", "base_ante", "bonus_see", "bonus_hear", "peak_spin", "feature_spin"):
        gs = GameState(config)
        gs.betmode = betmode
        gs.gametype = config.basegame_type
        gs.simulation_seed = 11
        gs.progress_activation_count = 0
        gs.reset_grid_mults()
        for reel in range(6):
            for row in range(5):
                gs.seed_tile_to_level(reel, row, 1 + (reel + row) % 3)
        lit = [(reel, row) for reel in range(6) for row in range(5)]
        _total, items, _rounds = resolve_coin_game(gs)
        first_round = [(item["reel"], item["row"]) for item in items if item.get("round") == 1]
        assert sorted(first_round) == lit
