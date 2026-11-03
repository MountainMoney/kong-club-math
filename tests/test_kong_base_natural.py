"""Base and ante draw real stops. Mystery still uses the planted layouts."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "games" / "kong_club"))

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


def test_mystery_shared_entry_still_plants():
    config = GameConfig()
    gs = GameState(config)
    gs.betmode = "bonus_mystery"
    gs.criteria = "gamble_hear"
    gs.reset_book()
    gs.gametype = config.basegame_type
    gs.use_reel_family("base", "base_quiet")
    gs.draw_prepared_board()
    assert gs.reel_positions == [0, 0, 0, 0, 0, 0]
    assert gs.reel_set_name == "base_quiet"
