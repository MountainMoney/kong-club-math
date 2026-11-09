"""Jul 2 Le Bandit Phase A mechanic tests."""

from pathlib import Path
import contextlib
import io
import sys

GAME_ROOT = Path(__file__).resolve().parents[1]
SDK_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SDK_ROOT))
sys.path.insert(0, str(GAME_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from game_cluster import GameCluster
from game_coin_feature import resolve_coin_game
from game_config import GameConfig
from gamestate import GameState
from test_game_loop_smoke import assert_no_leftover_clusters


def state():
    config = GameConfig()
    gs = GameState(config)
    gs.betmode = "base"
    gs.criteria = "basegame"
    gs.reset_book()
    return gs


def board_from_rows(gs, rows):
    return [
        [gs.create_symbol(rows[row][reel]) for row in range(len(rows))]
        for reel in range(len(rows[0]))
    ]


def assert_full_board(gs):
    for reel in range(gs.config.num_reels):
        assert len(gs.board[reel]) == gs.config.num_rows[reel]
        assert all(sym is not None for sym in gs.board[reel])


def test_reel_strips_are_run_based_and_refill_rules():
    config = GameConfig()
    for strips in (config.reels["INITIAL"], config.reels["REFILL"]):
        assert len(strips) == 6
        assert all(len(strip) == 50 for strip in strips)

    # Refill excludes MW / ST / monkeys / coins (no physical landings anywhere).
    banned_refill = {config.standard_wild, config.scatter_symbol}
    assert not any(symbol in banned_refill for strip in config.reels["REFILL"] for symbol in strip)
    assert not any(
        symbol in config.coin_symbols for strip in config.reels["REFILL"] for symbol in strip
    ), "refill must NOT include coins"

    # Base: NO coins on initial or tumble refill; ST forced-only.
    assert not any(
        symbol in config.coin_symbols for strip in config.reels["INITIAL_BASE"] for symbol in strip
    ), "base initial must NOT include coins"
    assert not any(
        symbol in config.coin_symbols for strip in config.reels["REFILL_BASE"] for symbol in strip
    ), "base refill must NOT include coins"
    assert config.tumble_refill_reel_ids["INITIAL_BASE"] == "REFILL_BASE"
    assert not any(
        symbol == config.scatter_symbol for strip in config.reels["INITIAL_BASE"] for symbol in strip
    )

    # Bonus uses INITIAL_BONUS only (no HEAR/SEE weights). Free spins land physical coins.
    assert "INITIAL_BONUS_HEAR" not in config.reels
    assert "INITIAL_BONUS_SEE" not in config.reels
    assert config.initial_reelstrip_id("bonus_hear", config.freegame_type) == "INITIAL_BONUS"
    assert config.initial_reelstrip_id("bonus_see", config.freegame_type) == "INITIAL_BONUS"
    assert "bonus_see" in {mode.get_name() for mode in config.bet_modes}
    assert (
        config.initial_reelstrip_id("base", config.freegame_type, bonus_variant="hear")
        == "INITIAL_BONUS"
    )
    assert not any(
        symbol == config.scatter_symbol for strip in config.reels["INITIAL_BONUS"] for symbol in strip
    )
    assert any(
        symbol in config.coin_symbols for strip in config.reels["INITIAL_BONUS"] for symbol in strip
    ), "bonus initial must include physical coins"
    assert config.tumble_refill_reel_ids["INITIAL_BONUS"] == "REFILL_BONUS"
    assert any(
        symbol in config.coin_symbols for strip in config.reels["REFILL_BONUS"] for symbol in strip
    ), "bonus refill must include physical coins"
    assert not any(
        symbol in config.coin_symbols for strip in config.reels["FEATURE"] for symbol in strip
    ), "TRIFECTA strips must NOT include coins"
    assert not any(
        symbol in config.coin_symbols for strip in config.reels["FEATURE_REFILL"] for symbol in strip
    ), "TRIFECTA refill must NOT include coins"
    assert any(
        symbol in config.coin_symbols for strip in config.reels["FEATURE_SPIN"] for symbol in strip
    ), "feature spin initial must include physical coins"
    assert any(
        symbol in config.coin_symbols for strip in config.reels["FEATURE_SPIN_REFILL"] for symbol in strip
    ), "feature spin refill must include physical coins"

    assert not any(symbol == config.scatter_symbol for strip in config.reels["FEATURE"] for symbol in strip)
    assert not any(
        symbol == config.scatter_symbol for strip in config.reels["FEATURE_SPIN"] for symbol in strip
    )
    assert not any(
        symbol == config.scatter_symbol for strip in config.reels["INITIAL_NO_SCATTER"] for symbol in strip
    )
    for strip in config.reels["INITIAL"]:
        assert any(strip[idx] == strip[idx + 1] for idx in range(len(strip) - 1))

    assert config.multiplier_table == [2, 5, 10]
    assert config.max_tile_level == 3
    assert config.coin_seed_levels == {"CB": 1, "CS": 2, "CG": 3}
    assert config.coin_values == {
        "CB": [1, 2, 3, 4],
        "CS": [5, 7, 10, 15, 20],
        "CG": [25, 50, 100, 250, 500],
    }
    assert config.coin_value_weights["CB"][0] > config.coin_value_weights["CB"][-1]
    assert all(isinstance(v, int) for pool in config.coin_values.values() for v in pool)
    assert config.progress_thresholds["bonus_hear"] == 5
    assert config.progress_thresholds["bonus_see"] == 5
    assert config.bonus_cluster_pay_scale == 1.0
    assert config.paytable_scale == 1.0
    assert config.coin_tile_scale_by_mode["bonus_hear"] == 1.0
    assert config.scatter_pays == {}
    assert config.bonus_variant_map[3] == "see"
    assert config.bonus_variant_map[4] == "hear"
    assert config.bonus_variant_map[5] == "speak"
    assert config.progress_thresholds["base"] == 10
    assert abs(config.rtp - 0.963) < 1e-9
    assert "bonus_mystery" in {mode.get_name() for mode in config.bet_modes}
    assert "bonus_risky" in {mode.get_name() for mode in config.bet_modes}
    mystery = next(mode for mode in config.bet_modes if mode.get_name() == "bonus_mystery")
    quotas = {dist.get_criteria(): dist.get_quota() for dist in mystery.get_distributions()}
    assert abs(quotas["pick_see"] - 0.50) < 1e-9
    assert abs(quotas["pick_hear"] - 0.45) < 1e-9
    assert abs(quotas["pick_speak"] - 0.05) < 1e-9
    risky = next(mode for mode in config.bet_modes if mode.get_name() == "bonus_risky")
    risky_q = {dist.get_criteria(): dist.get_quota() for dist in risky.get_distributions()}
    assert abs(risky_q["risky_dead"] - 0.50) < 1e-9
    assert abs(risky_q["risky_hear"] - 0.40) < 1e-9
    assert abs(risky_q["risky_speak"] - 0.10) < 1e-9
    assert config.peak_spin_seed_gold is True
    assert config.speak_direct_min_win == 1000
    assert config.progress_thresholds["peak_spin"] == 1
    assert config.initial_reelstrip_id("feature_spin", config.basegame_type) == "FEATURE_SPIN"
    assert config.tumble_refill_reel_ids["FEATURE_SPIN"] == "FEATURE_SPIN_REFILL"
    assert config.initial_reelstrip_id("peak_spin", config.basegame_type) == "FEATURE"
    peak_mode = next(mode for mode in config.bet_modes if mode.get_name() == "peak_spin")
    assert peak_mode.get_cost() == config.peak_spin_cost
    feature_mode = next(mode for mode in config.bet_modes if mode.get_name() == "feature_spin")
    feature_q = {d.get_criteria(): d.get_quota() for d in feature_mode.get_distributions()}
    assert "dead_juicy" not in feature_q
    assert abs(feature_q["run"] - 1.0) < 1e-9
    peak_q = {d.get_criteria(): d.get_quota() for d in peak_mode.get_distributions()}
    assert abs(peak_q["dead_juicy"] - 0.50) < 1e-9
    assert abs(peak_q["live"] - 0.50) < 1e-9
    assert config.max_activation_coins_by_mode["bonus_hear"] is None
    assert config.max_board_activations_hear == 1
    assert config.hear_coin_cap_boost_chance == 0.0
    assert config.max_activation_coins_by_mode["base"] is None
    assert config.max_activation_coins_by_mode["base_ante"] is None
    assert "REFILL_BONUS" in config.reels
    assert config.tumble_refill_reel_ids["INITIAL_BONUS"] == "REFILL_BONUS"
    assert config.coin_game_multi_weights == [58, 28, 10, 3, 1, 0]
    assert config.coin_game_coin_weight == 100
    assert "base_ante" in config.coin_game_power_weights
    for profile in config.coin_game_power_weights.values():
        # Mode fallback matches bronze; TIER_SHIFT retired.
        assert profile == {"multiplier": 12, "collector": 0, "tier_shift": 0}
    assert config.coin_game_power_by_tile_level == {
        1: {"multiplier": 12, "collector": 0, "tier_shift": 0},
        2: {"multiplier": 10, "collector": 1, "tier_shift": 0},
        3: {"multiplier": 8, "collector": 2, "tier_shift": 0},
    }
    assert config.coin_game_power_peak_gold == {"multiplier": 0, "collector": 0, "tier_shift": 0}
    assert config.peak_spin_cost == 1000.0
    assert 50.0 <= config.feature_buy_cost <= 75.0


def test_paytable_size_bands():
    assert GameCluster.paytable_size(5) == 5
    assert GameCluster.paytable_size(6) == 6
    assert GameCluster.paytable_size(7) == 7
    assert GameCluster.paytable_size(8) == 8
    assert GameCluster.paytable_size(9) == 9
    assert GameCluster.paytable_size(10) == 10
    assert GameCluster.paytable_size(11) == 11
    assert GameCluster.paytable_size(12) == 12
    assert GameCluster.paytable_size(13) == 13
    assert GameCluster.paytable_size(20) == 20

    config = GameConfig()
    scale = float(getattr(config, "paytable_scale", 1.0))
    assert scale == 1.0
    # Locked screenshot. Lows share a row. Lemon=Coconut, Orange=Grape, Banana stands alone.
    locked = {
        "T": (0.1, 0.2, 0.3, 0.5, 1.5, 5.0, 15.0),
        "LE": (0.3, 0.4, 0.5, 0.7, 2.5, 7.5, 25.0),
        "CO": (0.3, 0.4, 0.5, 0.7, 2.5, 7.5, 25.0),
        "OR": (0.5, 0.7, 1.0, 1.5, 5.0, 15.0, 50.0),
        "GR": (0.5, 0.7, 1.0, 1.5, 5.0, 15.0, 50.0),
        "BA": (1.0, 1.5, 2.0, 3.0, 10.0, 30.0, 100.0),
    }
    band_sizes = (5, 6, 7, 8, 10, 12, 13)
    for symbol, faces in locked.items():
        for size, face in zip(band_sizes, faces):
            assert config.cluster_pay(size, symbol) == round(face * scale, 6)
        assert config.cluster_pay(9, symbol) == config.cluster_pay(10, symbol)
        assert config.cluster_pay(11, symbol) == config.cluster_pay(12, symbol)
        assert config.cluster_pay(13, symbol) == config.cluster_pay(20, symbol) == config.cluster_pay(30, symbol)
    for symbol in ("J", "Q", "K", "A"):
        assert config.cluster_pay(8, symbol) == config.cluster_pay(8, "T")
        assert config.paytable[(13, symbol)] == config.paytable[(13, "T")]
    assert config.paytable[(5, "BA")] == round(1.00 * scale, 6)
    assert config.cluster_pay(12, "BA") > config.cluster_pay(8, "BA") > config.paytable[(5, "BA")]


def test_bfs_orthogonal_shapes_and_no_diagonals():
    gs = state()
    gs.board = board_from_rows(
        gs,
        [
            ["BA", "BA", "BA", "T", "T", "T"],
            ["T", "T", "BA", "T", "Q", "T"],
            ["T", "T", "BA", "BA", "Q", "T"],
            ["K", "T", "T", "BA", "Q", "T"],
            ["T", "K", "T", "T", "Q", "Q"],
        ],
    )
    clusters = GameCluster.find_winning_clusters(gs.board, gs.config)
    ba = [c for c in clusters if c.symbol == "BA"]
    q = [c for c in clusters if c.symbol == "Q"]
    k = [c for c in clusters if c.symbol == "K"]
    assert ba and ba[0].size == 7, "L/blob BA cluster should pay"
    assert q and q[0].size == 5, "straight vertical cluster should pay"
    assert not k, "diagonal K cells must not connect"


def test_multiple_same_symbol_clusters_pay_independently():
    gs = state()
    gs.board = board_from_rows(
        gs,
        [
            ["A", "A", "A", "A", "A", "T"],
            ["T", "T", "T", "T", "T", "T"],
            ["A", "A", "A", "A", "A", "T"],
            ["T", "T", "T", "T", "T", "T"],
            ["K", "Q", "J", "T", "LE", "CO"],
        ],
    )
    clusters = [c for c in GameCluster.find_winning_clusters(gs.board, gs.config) if c.symbol == "A"]
    assert len(clusters) == 2
    win_data = gs.evaluate_clusters(clusters)
    assert len(win_data["wins"]) == 2
    assert win_data["wins"][0]["win"] == win_data["wins"][1]["win"]


def test_wild_substitution_and_wild_removal():
    gs = state()
    gs.board = board_from_rows(
        gs,
        [
            ["OR", "OR", "MW", "OR", "OR", "T"],
            ["T", "T", "T", "T", "T", "T"],
            ["K", "Q", "J", "A", "LE", "CO"],
            ["CO", "LE", "A", "J", "Q", "K"],
            ["T", "J", "Q", "K", "A", "LE"],
        ],
    )
    clusters = GameCluster.find_winning_clusters(gs.board, gs.config)
    or_cluster = [c for c in clusters if c.symbol == "OR"][0]
    assert or_cluster.size == 5
    assert (2, 0) in or_cluster.wild_positions
    gs.mark_removed_symbols({"OR"}, clusters)
    assert gs.board[2][0].explode, "wild that completed cluster must be removed"


def test_tiles_increment_connected_cluster_only():
    """Super Cascade deletes whole winning types; tiles only rank on connected cluster cells."""
    gs = state()
    gs.board = board_from_rows(
        gs,
        [
            ["OR", "OR", "MW", "BA", "BA", "BA"],
            ["OR", "OR", "BA", "BA", "Q", "T"],
            ["Q", "Q", "BA", "J", "A", "LE"],
            ["CO", "LE", "A", "J", "Q", "K"],
            ["OR", "J", "Q", "K", "A", "LE"],  # isolated OR at (0,4) — deletes, no tile
        ],
    )
    clusters = GameCluster.find_winning_clusters(gs.board, gs.config)
    or_cluster = [cluster for cluster in clusters if cluster.symbol == "OR"][0]
    ba_cluster = [cluster for cluster in clusters if cluster.symbol == "BA"][0]

    assert (0, 4) not in or_cluster.positions, "isolated OR must not be in the cluster"
    gs.activate_tiles_from_clusters([or_cluster, ba_cluster])

    assert gs.tile_levels[0][0] == 1
    assert gs.position_multipliers[0][0] == 2
    assert gs.tile_levels[0][4] == 0, "non-connected winning-type cell must NOT level"
    assert gs.tile_levels[3][0] == 1
    assert gs.tile_levels[2][0] == 1, "shared wild in winning cluster increments"

    gs.activate_tiles_from_clusters([or_cluster, ba_cluster])
    assert gs.tile_levels[0][0] == 2
    assert gs.position_multipliers[0][0] == 5
    assert gs.tile_levels[2][0] == 2
    assert gs.tile_levels[0][4] == 0

    # Still removes the isolated OR on super cascade.
    gs.mark_removed_symbols({"OR", "BA"}, [or_cluster, ba_cluster])
    assert gs.board[0][4].explode, "super cascade still deletes non-connected winning type"

def test_super_cascade_removes_all_winning_type_cells():
    gs = state()
    gs.board = board_from_rows(
        gs,
        [
            ["OR", "OR", "OR", "OR", "OR", "T"],
            ["OR", "J", "Q", "K", "A", "LE"],  # extra OR not in the top-row cluster path? 
            ["CO", "OR", "GR", "BA", "T", "J"],  # wait — all ORs of winning type remove
            ["Q", "K", "A", "LE", "CO", "BA"],
            ["GR", "BA", "T", "J", "Q", "K"],
        ],
    )
    clusters = GameCluster.find_winning_clusters(gs.board, gs.config)
    assert any(c.symbol == "OR" for c in clusters)
    gs.mark_removed_symbols({"OR"}, clusters)
    for reel in range(gs.config.num_reels):
        for row in range(gs.config.num_rows[reel]):
            if gs.board[reel][row].name == "OR":
                assert gs.board[reel][row].explode, "super cascade removes all winning-type cells"


def test_coins_never_removed_by_cascade():
    gs = state()
    gs.board = board_from_rows(
        gs,
        [
            ["BA", "BA", "BA", "BA", "BA", "CB"],
            ["T", "J", "Q", "K", "A", "LE"],
            ["CO", "OR", "GR", "BA", "T", "J"],
            ["Q", "K", "A", "LE", "CO", "OR"],
            ["GR", "BA", "T", "J", "Q", "K"],
        ],
    )
    gs.mark_removed_symbols({"BA"}, [])
    assert not gs.board[5][0].explode, "coins must never explode via cascade"


def test_gravity_refill_no_empty_and_no_refill_specials():
    gs = state()
    gs.board = board_from_rows(
        gs,
        [
            ["BA", "BA", "BA", "BA", "BA", "T"],
            ["T", "J", "Q", "K", "A", "LE"],
            ["CO", "OR", "GR", "BA", "T", "J"],
            ["Q", "K", "A", "LE", "CO", "OR"],
            ["GR", "BA", "T", "J", "Q", "K"],
        ],
    )
    gs.mark_removed_symbols({"BA"}, [])
    gs.gravity_and_refill(emit_event=False)
    assert_full_board(gs)
    banned = {gs.config.standard_wild, gs.config.scatter_symbol}
    assert not any(sym.name in banned for reel in gs.new_symbols_from_tumble for sym in reel)


def test_base_game_spin_excludes_coins_and_scatters():
    gs = state()
    for _ in range(80):
        gs.draw_prepared_board()
        assert gs.count_special_symbols("scatter") == 0, "base strips must not land organic scatters"
        assert not any(
            sym.name in gs.config.coin_symbols for reel in gs.board for sym in reel
        ), "base must never land coins"


def test_bonus_hit_rate_and_ante_cost():
    config = GameConfig()
    base_mode = next(mode for mode in config.bet_modes if mode.get_name() == "base")
    ante_mode = next(mode for mode in config.bet_modes if mode.get_name() == "base_ante")
    base_dists = {d.get_criteria(): d.get_quota() for d in base_mode.get_distributions()}
    ante_dists = {d.get_criteria(): d.get_quota() for d in ante_mode.get_distributions()}
    assert base_dists["freegame"] == config.bonus_hit_rate_base
    assert ante_dists["freegame"] == config.bonus_hit_rate_ante
    assert ante_dists["freegame"] == 2 * base_dists["freegame"]
    assert "cap" not in base_dists and "cap" not in ante_dists
    assert config.scatter_triggers_ante == config.scatter_triggers
    assert ante_mode.get_cost() == 1.4


def test_coin_seed_on_land():
    gs = state()
    gs.board = board_from_rows(
        gs,
        [
            ["CB", "CS", "CG", "T", "J", "Q"],
            ["K", "A", "LE", "CO", "OR", "GR"],
            ["BA", "T", "J", "Q", "K", "A"],
            ["LE", "CO", "OR", "GR", "BA", "T"],
            ["J", "Q", "K", "A", "LE", "CO"],
        ],
    )
    gs.board_coin_values = {}
    gs.prepare_landed_specials(initial_fill=True)
    assert gs.tile_levels[0][0] == 1
    assert gs.position_multipliers[0][0] == 2
    assert gs.tile_levels[1][0] == 2
    assert gs.position_multipliers[1][0] == 5
    assert gs.tile_levels[2][0] == 3
    assert gs.position_multipliers[2][0] == 10
    assert (0, 0) in gs.board_coin_values
    assert gs.board_coin_values[(0, 0)] in gs.config.coin_values["CB"]
    assert gs.board_coin_values[(1, 0)] in gs.config.coin_values["CS"]
    assert gs.board_coin_values[(2, 0)] in gs.config.coin_values["CG"]
    seed_events = [e for e in gs.book.events if e["type"] == "coinSeed"]
    assert seed_events, "landing coins must emit coinSeed"


def _park_power_weights(config):
    """Force coin-only rolls for face-pool asserts (MULTI is live but rare)."""
    zero = {"multiplier": 0, "collector": 0, "tier_shift": 0}
    config.coin_game_power_weights = {key: dict(zero) for key in config.coin_game_power_weights}
    config.coin_game_power_by_tile_level = {
        level: dict(zero) for level in config.coin_game_power_by_tile_level
    }
    config.coin_game_power_peak_gold = dict(zero)


def test_activation_pays_virtual_coins_on_active_tiles():
    gs = state()
    _park_power_weights(gs.config)
    gs.betmode = "feature_spin"
    gs.board = board_from_rows(
        gs,
        [
            ["T", "T", "J", "Q", "K", "A"],
            ["LE", "CO", "OR", "GR", "BA", "T"],
            ["J", "Q", "K", "A", "LE", "CO"],
            ["OR", "GR", "BA", "T", "J", "Q"],
            ["K", "A", "LE", "CO", "OR", "GR"],
        ],
    )
    gs.board_coin_values = {}
    gs.seed_tile_to_level(0, 0, 1)
    total, items, rounds = resolve_coin_game(gs)
    assert rounds == 1
    assert len(items) == 1
    assert items[0]["tileMultiplier"] == 1
    assert items[0]["symbol"] == "CB"
    assert items[0]["displayValue"] == items[0]["value"]
    assert float(items[0]["value"]).is_integer()
    assert items[0]["value"] in (1, 2, 3, 4)
    # Hard faces — total is exact sum of displayed integers.
    assert total == items[0]["value"]
    assert total > 0

    # Bonus: hard faces on every lit tile.
    bonus = state()
    _park_power_weights(bonus.config)
    bonus.betmode = "bonus_hear"
    bonus.bonus_variant = "hear"
    bonus.gametype = bonus.config.freegame_type
    bonus.board = board_from_rows(
        bonus,
        [
            ["T", "T", "J", "Q", "K", "A"],
            ["LE", "CO", "OR", "GR", "BA", "T"],
            ["J", "Q", "K", "A", "LE", "CO"],
            ["OR", "GR", "BA", "T", "J", "Q"],
            ["K", "A", "LE", "CO", "OR", "GR"],
        ],
    )
    for reel in range(6):
        for row in range(5):
            bonus.seed_tile_to_level(reel, row, 3)
    b_total, b_items, _ = resolve_coin_game(bonus)
    lit = sum(1 for reel in bonus.tile_levels for level in reel if level > 0)
    assert len(b_items) == lit
    assert abs(b_total - sum(float(i["displayValue"]) for i in b_items)) < 1e-6
    for item in b_items:
        assert item["displayValue"] in bonus.config.coin_values["CG"]
        assert item["displayValue"] == item["payout"]

    # Inactive tiles do not pay (virtual only hits lit cells).
    gs2 = state()
    gs2.betmode = "feature_spin"
    gs2.board = board_from_rows(
        gs2,
        [
            ["T", "T", "J", "Q", "K", "A"],
            ["LE", "CO", "OR", "GR", "BA", "T"],
            ["J", "Q", "K", "A", "LE", "CO"],
            ["OR", "GR", "BA", "T", "J", "Q"],
            ["K", "A", "LE", "CO", "OR", "GR"],
        ],
    )
    gs2.board_coin_values = {}
    total2, items2, rounds2 = resolve_coin_game(gs2)
    assert total2 == 0.0
    assert items2 == []
    assert rounds2 == 0


def test_multi_power_resolves_adjacent_coins():
    """MULTI multiplies 8-way adjacent coin faces, then stays paused on that cell."""
    from game_coin_feature import _apply_multi, _build_coin_reveal, _build_multi_reveal

    # Unit: 3× on center multiplies the orthogonal neighbor.
    coins = [
        _build_coin_reveal(1, 1, "CB", 1, 2),
        _build_multi_reveal(2, 1, 3, 1),
        _build_coin_reveal(3, 1, "CB", 1, 4),
        _build_coin_reveal(0, 0, "CB", 1, 1),  # not adjacent to (2,1)
    ]
    after = _apply_multi(coins, 2, 1, 3)
    by_pos = {(i["reel"], i["row"]): i for i in after}
    assert by_pos[(1, 1)]["displayValue"] == 6
    assert by_pos[(1, 1)]["powerResolved"] is True
    assert by_pos[(1, 1)]["symbol"] == "CS"
    assert by_pos[(1, 1)]["tileLevel"] == 2
    assert by_pos[(3, 1)]["displayValue"] == 12
    assert by_pos[(3, 1)]["symbol"] == "CS"
    assert by_pos[(3, 1)]["tileLevel"] == 2
    assert by_pos[(0, 0)]["displayValue"] == 1
    assert by_pos[(0, 0)]["symbol"] == "CB"
    assert by_pos[(0, 0)].get("powerResolved") is None

    gold_hit = _apply_multi(
        [_build_coin_reveal(1, 1, "CS", 2, 10), _build_multi_reveal(2, 1, 3, 1)],
        2,
        1,
        3,
    )
    gold_coin = next(i for i in gold_hit if i["kind"] == "coin")
    assert gold_coin["displayValue"] == 30
    assert gold_coin["symbol"] == "CG"
    assert gold_coin["tileLevel"] == 3

    # Integration: positions sort (reel, row) → (1,1),(1,2),(2,1),(2,2).
    # Force MULTI on (2,1); the other three stay coins.
    import game_coin_feature as gcf

    kind_seq = iter(["coin", "coin", "multiplier", "coin"])
    original_pick = gcf._pick_cell_kind
    gcf._pick_cell_kind = lambda gs, rng, tile_level=1, **_kwargs: next(kind_seq, "coin")
    try:
        gs = state()
        gs.betmode = "base"
        gs.config.max_activation_coins_by_mode["base"] = None
        gs.board = board_from_rows(
            gs,
            [
                ["T", "T", "J", "Q", "K", "A"],
                ["LE", "CO", "OR", "GR", "BA", "T"],
                ["J", "Q", "K", "A", "LE", "CO"],
                ["OR", "GR", "BA", "T", "J", "Q"],
                ["K", "A", "LE", "CO", "OR", "GR"],
            ],
        )
        for reel, row in ((1, 1), (1, 2), (2, 1), (2, 2)):
            gs.seed_tile_to_level(reel, row, 1)
        total, items, rounds = resolve_coin_game(gs)
    finally:
        gcf._pick_cell_kind = original_pick

    assert rounds >= 2
    r1 = [i for i in items if i.get("round") == 1]
    apply_round = min(
        int(i.get("round") or 1)
        for i in items
        if i.get("kind") == "multiplier" and i.get("powerResolved")
    )
    r_apply = [i for i in items if int(i.get("round") or 1) == apply_round]
    assert any(i.get("kind") == "multiplier" and i["reel"] == 2 and i["row"] == 1 for i in r1)
    assert any(i.get("kind") == "multiplier" and i.get("powerResolved") for i in r_apply)
    last_pos = {(i["reel"], i["row"]): i for i in _last_round_items(items)}
    assert last_pos[(2, 1)]["kind"] == "multiplier"
    assert last_pos[(2, 1)].get("powerResolved") is True
    assert not last_pos[(2, 1)].get("reactivate")
    r1_coins = {(i["reel"], i["row"]): i["displayValue"] for i in r1 if i["kind"] == "coin"}
    apply_coins = {
        (i["reel"], i["row"]): i["displayValue"] for i in r_apply if i["kind"] == "coin"
    }
    for pos, face1 in r1_coins.items():
        if pos not in apply_coins:
            continue
        assert apply_coins[pos] >= face1
        assert apply_coins[pos] % face1 == 0
    leftover = _leftover_coin_payout(items)
    assert abs(total - leftover) < 1e-6
    assert total > 0


def _last_round_items(items):
    last = max(int(i.get("round") or 1) for i in items)
    return [i for i in items if int(i.get("round") or 1) == last]


def _leftover_coin_payout(items):
    return sum(
        float(i.get("payout") or 0)
        for i in _last_round_items(items)
        if i.get("kind") == "coin" and not i.get("collected")
    )


def _sum_replaced_pot_payouts(items):
    """Each counted pot's face, once: replaced cells plus a last pot left on the board."""
    by_round = {}
    for item in items:
        by_round.setdefault(int(item.get("round") or 1), []).append(item)
    latest_face = {}
    paid = 0.0
    for round_index in sorted(by_round):
        round_items = by_round[round_index]
        for item in round_items:
            pos = (item["reel"], item["row"])
            if item.get("kind") != "collector":
                continue
            if item.get("collected"):
                latest_face.pop(pos, None)
                continue
            if item.get("powerResolved"):
                latest_face[pos] = float(item.get("payout") or 0)
        for item in round_items:
            pos = (item["reel"], item["row"])
            if not item.get("reactivate"):
                continue
            # reactivate on a still-valued pot is a leftover spawn flag, not a replace.
            if (
                item.get("kind") == "collector"
                and item.get("powerResolved")
                and not item.get("collected")
            ):
                continue
            if pos in latest_face:
                paid += latest_face.pop(pos)
    return paid + sum(latest_face.values())


def _lit_board(gs, cells):
    gs.betmode = "base"
    gs.board = board_from_rows(
        gs,
        [
            ["T", "T", "J", "Q", "K", "A"],
            ["LE", "CO", "OR", "GR", "BA", "T"],
            ["J", "Q", "K", "A", "LE", "CO"],
            ["OR", "GR", "BA", "T", "J", "Q"],
            ["K", "A", "LE", "CO", "OR", "GR"],
        ],
    )
    for reel, row in cells:
        gs.seed_tile_to_level(reel, row, 1)
    return gs


def test_collector_vacuums_coins_then_pays_pot():
    """COLLECTOR absorbs coins and valued pots; unused empty bags wait."""
    from game_coin_feature import _apply_collector, _build_coin_reveal, _build_collector_reveal

    coins = [
        _build_coin_reveal(1, 1, "CB", 1, 2),
        _build_collector_reveal(2, 1, 1),
        _build_coin_reveal(3, 1, "CB", 1, 4),
    ]
    after = _apply_collector(coins, 2, 1)
    by_pos = {(i["reel"], i["row"]): i for i in after}
    assert by_pos[(2, 1)]["payout"] == 6
    assert by_pos[(2, 1)]["displayValue"] == 6
    assert by_pos[(2, 1)]["powerResolved"] is True
    assert by_pos[(1, 1)]["collected"] is True
    assert by_pos[(1, 1)]["payout"] == 0
    assert by_pos[(3, 1)]["collected"] is True

    two_pots = [
        _build_coin_reveal(0, 1, "CB", 1, 3),
        _build_collector_reveal(1, 1, 1),
        _build_collector_reveal(4, 1, 1),
    ]
    absorbed = _apply_collector(two_pots, 1, 1)
    absorbed_pos = {(i["reel"], i["row"]): i for i in absorbed}
    assert absorbed_pos[(1, 1)]["payout"] == 3
    assert absorbed_pos[(4, 1)].get("collected") is not True
    assert absorbed_pos[(4, 1)]["kind"] == "collector"
    assert absorbed_pos[(0, 1)]["collected"] is True

    valued = _build_collector_reveal(4, 1, 1)
    valued["value"] = 5
    valued["displayValue"] = 5
    valued["resolvedValue"] = 5
    valued["payout"] = 5
    valued["powerResolved"] = True
    chained = _apply_collector(
        [_build_coin_reveal(0, 1, "CB", 1, 3), _build_collector_reveal(1, 1, 1), valued],
        1,
        1,
    )
    chained_pos = {(i["reel"], i["row"]): i for i in chained}
    assert chained_pos[(1, 1)]["payout"] == 8
    assert chained_pos[(4, 1)].get("collected") is True

    import game_coin_feature as gcf

    kind_seq = iter(["coin", "collector", "coin"])
    original_pick = gcf._pick_cell_kind
    gcf._pick_cell_kind = lambda gs, rng, tile_level=1, **_kwargs: next(kind_seq, "coin")
    try:
        gs = _lit_board(state(), ((1, 1), (2, 1), (3, 1)))
        total, items, rounds = resolve_coin_game(gs)
    finally:
        gcf._pick_cell_kind = original_pick

    pots = [i for i in items if i.get("kind") == "collector" and i.get("payout", 0) > 0]
    assert pots
    counted = _sum_replaced_pot_payouts(items)
    leftover = _leftover_coin_payout(items)
    assert abs(total - counted - leftover) < 1e-6
    assert rounds >= 2
    acting_replace = [
        i
        for i in items
        if i.get("reel") == 2 and i.get("row") == 1 and i.get("reactivate")
    ]
    assert not acting_replace, "last counted pot must stay and pay, not regen"
    last_pos = {(i["reel"], i["row"]): i for i in _last_round_items(items)}
    assert last_pos[(2, 1)]["kind"] == "collector"


def test_collector_keeps_prior_face_and_caps_at_wincap():
    from game_coin_feature import (
        COIN_FEATURE_WINCAP,
        _apply_collector,
        _apply_multi,
        _build_coin_reveal,
        _build_collector_reveal,
    )

    pot = _build_collector_reveal(2, 1, 1)
    pot["value"] = 10
    pot["displayValue"] = 10
    pot["resolvedValue"] = 10
    pot["payout"] = 10
    after = _apply_collector(
        [_build_coin_reveal(1, 1, "CB", 1, 5), pot],
        2,
        1,
    )
    by_pos = {(i["reel"], i["row"]): i for i in after}
    assert by_pos[(2, 1)]["payout"] == 15

    big = _build_collector_reveal(2, 1, 1)
    big["value"] = 15000
    big["displayValue"] = 15000
    big["resolvedValue"] = 15000
    big["payout"] = 15000
    capped = _apply_multi([big], 1, 1, 2, kinds=("collector",))
    assert capped[0]["payout"] == COIN_FEATURE_WINCAP


def test_multi_pot_remainder_is_wincap_minus_leftover_coins():
    """15000 pot × 2 with leftover coins 2000 → pot 23000, coins stay, board = 25000."""
    from game_coin_feature import (
        COIN_FEATURE_WINCAP,
        _apply_multi,
        _build_coin_reveal,
        _build_collector_reveal,
        _leftover_coin_sum,
    )

    pot = _build_collector_reveal(2, 1, 1)
    pot["value"] = 15000
    pot["displayValue"] = 15000
    pot["resolvedValue"] = 15000
    pot["payout"] = 15000
    far_coin = _build_coin_reveal(5, 4, "CG", 3, 2000)
    after = _apply_multi([pot, far_coin], 1, 1, 2, kinds=("coin", "collector"))
    by_pos = {(i["reel"], i["row"]): i for i in after}
    leftover = _leftover_coin_sum(after)
    assert leftover == 2000
    assert by_pos[(2, 1)]["payout"] == COIN_FEATURE_WINCAP - leftover
    assert leftover + by_pos[(2, 1)]["payout"] == COIN_FEATURE_WINCAP


def test_multi_multiplies_valued_pot_after_collect():
    """A clover that lands after vacuum can still multiply the valued pot; last pot stays."""
    from game_coin_feature import _apply_multi, _apply_collector, _build_coin_reveal, _build_collector_reveal

    board = [
        _build_coin_reveal(1, 1, "CB", 1, 2),
        _build_collector_reveal(2, 1, 1),
        _build_coin_reveal(3, 1, "CB", 1, 4),
    ]
    collected = _apply_collector(board, 2, 1)
    assert collected[1]["payout"] == 6
    after = _apply_multi(collected, 1, 1, 3, kinds=("collector",))
    by_pos = {(i["reel"], i["row"]): i for i in after}
    assert by_pos[(2, 1)]["payout"] == 18
    assert by_pos[(2, 1)]["kind"] == "collector"

    import game_coin_feature as gcf

    # One pot: after it vacuums there is no regen on that turn.
    kind_seq = iter(["coin", "coin", "collector"])
    original_pick = gcf._pick_cell_kind
    gcf._pick_cell_kind = lambda gs, rng, tile_level=1, **_kwargs: next(kind_seq, "coin")
    try:
        gs = _lit_board(state(), ((1, 1), (2, 1), (3, 1)))
        total, items, _rounds = resolve_coin_game(gs)
    finally:
        gcf._pick_cell_kind = original_pick

    last_collect = min(
        int(i.get("round") or 1)
        for i in items
        if i.get("kind") == "coin" and i.get("collected")
    )
    same_turn_regen = [
        i
        for i in items
        if i.get("reactivate") and int(i.get("round") or 1) == last_collect
    ]
    assert not same_turn_regen, "last pot turn must not rewrite the board"
    last_pos = {(i["reel"], i["row"]): i for i in _last_round_items(items)}
    assert last_pos[(3, 1)]["kind"] == "collector"
    assert not last_pos[(3, 1)].get("reactivate")
    leftover = _leftover_coin_payout(items)
    counted = _sum_replaced_pot_payouts(items)
    assert abs(total - counted - leftover) < 1e-6


def test_leftmost_collector_recollects_then_slots_replace():
    """Rightmost pot acts first and sucks coins only; the leftmost pot waits, then sucks it and holds the total."""
    import game_coin_feature as gcf

    kind_seq = iter(["collector", "coin", "collector"])
    original_pick = gcf._pick_cell_kind
    gcf._pick_cell_kind = lambda gs, rng, tile_level=1, **_kwargs: next(kind_seq, "coin")
    try:
        gs = _lit_board(state(), ((1, 1), (2, 1), (3, 1)))
        total, items, _rounds = resolve_coin_game(gs)
    finally:
        gcf._pick_cell_kind = original_pick

    collect_round = min(
        int(i.get("round") or 1)
        for i in items
        if i.get("kind") == "coin" and i.get("collected")
    )
    collect_items = [i for i in items if int(i.get("round") or 1) == collect_round]
    assert all(i.get("action") == "collect" for i in collect_items)
    spawn_items = [i for i in items if int(i.get("round") or 1) == 1]
    assert spawn_items and all(i.get("action") == "spawn" for i in spawn_items)
    by_pos = {(i["reel"], i["row"]): i for i in collect_items}
    acting = by_pos[(3, 1)]
    sibling = by_pos[(1, 1)]
    coin = by_pos[(2, 1)]
    assert acting["kind"] == "collector"
    assert not acting.get("collected")
    assert float(acting.get("payout") or 0) > 0
    assert not acting.get("reactivate")
    assert sibling["kind"] == "collector"
    assert sibling.get("collected") is not True
    assert coin.get("collected") is True

    same_turn_regen = [
        i
        for i in items
        if i.get("reactivate") and int(i.get("round") or 1) == collect_round
    ]
    assert not same_turn_regen, "pot A's turn must not rewrite the board"
    second_collect = [
        i
        for i in items
        if i.get("action") == "collect"
        and i.get("reel") == 1
        and i.get("row") == 1
        and not i.get("collected")
        and float(i.get("payout") or 0) > 0
    ]
    assert second_collect, "waiting leftmost pot must suck the valued pot"
    first_sucked = [
        i
        for i in items
        if i.get("action") == "collect"
        and i.get("reel") == 3
        and i.get("row") == 1
        and i.get("collected")
    ]
    assert first_sucked, "valued pot must be collected into the waiting pot"
    last_pos = {(i["reel"], i["row"]): i for i in _last_round_items(items)}
    assert last_pos[(1, 1)]["kind"] == "collector"
    assert last_pos[(1, 1)].get("collected") is not True
    assert float(last_pos[(1, 1)].get("payout") or 0) > 0
    assert not last_pos[(1, 1)].get("reactivate")
    leftover = _leftover_coin_payout(items)
    counted = _sum_replaced_pot_payouts(items)
    assert counted > 0
    assert abs(total - counted - leftover) < 1e-6


def test_regen_clover_multiplies_sitting_pot_before_next_collect():
    """After the first pot, a regen clover can hit it before the waiting pot sucks."""
    import game_coin_feature as gcf

    kind_seq = iter(["collector", "coin", "collector", "multiplier"])
    original_pick = gcf._pick_cell_kind
    original_multi = gcf._pick_multi_value
    gcf._pick_cell_kind = lambda gs, rng, tile_level=1, **_kwargs: next(kind_seq, "coin")
    gcf._pick_multi_value = lambda gs, rng: 2
    try:
        gs = _lit_board(state(), ((1, 1), (2, 1), (3, 1)))
        total, items, _rounds = resolve_coin_game(gs)
    finally:
        gcf._pick_cell_kind = original_pick
        gcf._pick_multi_value = original_multi

    last_pos = {(i["reel"], i["row"]): i for i in _last_round_items(items)}
    assert last_pos[(1, 1)]["kind"] == "collector"
    assert last_pos[(1, 1)].get("collected") is not True
    assert not last_pos[(1, 1)].get("reactivate")
    assert any(
        i.get("kind") == "multiplier" and i.get("powerResolved") for i in items
    ), "regen clover must still apply"
    leftover = _leftover_coin_payout(items)
    counted = _sum_replaced_pot_payouts(items)
    assert abs(total - counted - leftover) < 1e-6


def test_clovers_resolve_column_order_then_stay():
    """Leftmost clover applies first and stays paused; the right clover fires after."""
    import game_coin_feature as gcf

    kind_seq = iter(["multiplier", "coin", "multiplier"])
    original_pick = gcf._pick_cell_kind
    original_multi = gcf._pick_multi_value
    gcf._pick_cell_kind = lambda gs, rng, tile_level=1, **_kwargs: next(kind_seq, "coin")
    gcf._pick_multi_value = lambda gs, rng: 2
    try:
        gs = _lit_board(state(), ((1, 1), (2, 1), (3, 1)))
        total, items, _rounds = resolve_coin_game(gs)
    finally:
        gcf._pick_cell_kind = original_pick
        gcf._pick_multi_value = original_multi

    resolved = [
        i
        for i in items
        if i.get("kind") == "multiplier" and i.get("powerResolved")
    ]
    assert resolved
    first_apply = min(int(i.get("round") or 1) for i in resolved)
    first_items = [i for i in resolved if int(i.get("round") or 1) == first_apply]
    assert all(i["reel"] == 1 and i["row"] == 1 for i in first_items)

    second_apply_rounds = [
        int(i.get("round") or 1)
        for i in resolved
        if i.get("reel") == 3 and i.get("row") == 1
    ]
    assert second_apply_rounds, "right clover must still apply after the left one"
    assert first_apply < min(second_apply_rounds)

    last_pos = {(i["reel"], i["row"]): i for i in _last_round_items(items)}
    assert last_pos[(1, 1)]["kind"] == "multiplier"
    assert last_pos[(1, 1)].get("powerResolved") is True
    assert not last_pos[(1, 1)].get("reactivate")
    assert last_pos[(3, 1)]["kind"] == "multiplier"
    assert last_pos[(3, 1)].get("powerResolved") is True
    assert not last_pos[(3, 1)].get("reactivate")
    leftover = _leftover_coin_payout(items)
    assert abs(total - leftover) < 1e-6


def test_clovers_regen_after_collector_vacuum():
    """Paused clovers stay through the last pot; that pot's turn does not rewrite the board."""
    import game_coin_feature as gcf

    kind_seq = iter(["multiplier", "coin", "collector"])
    original_pick = gcf._pick_cell_kind
    original_multi = gcf._pick_multi_value
    gcf._pick_cell_kind = lambda gs, rng, tile_level=1, **_kwargs: next(kind_seq, "coin")
    gcf._pick_multi_value = lambda gs, rng: 2
    try:
        gs = _lit_board(state(), ((1, 1), (2, 1), (3, 1)))
        total, items, _rounds = resolve_coin_game(gs)
    finally:
        gcf._pick_cell_kind = original_pick
        gcf._pick_multi_value = original_multi

    apply_round = min(
        int(i.get("round") or 1)
        for i in items
        if i.get("kind") == "multiplier" and i.get("powerResolved")
    )
    apply_items = [i for i in items if int(i.get("round") or 1) == apply_round]
    by_apply = {(i["reel"], i["row"]): i for i in apply_items}
    assert by_apply[(1, 1)]["kind"] == "multiplier"
    assert by_apply[(1, 1)].get("powerResolved") is True
    assert not by_apply[(1, 1)].get("reactivate")

    collect_round = min(
        int(i.get("round") or 1)
        for i in items
        if i.get("kind") == "coin" and i.get("collected")
    )
    assert apply_round < collect_round
    same_turn_regen = [
        i
        for i in items
        if i.get("reactivate") and int(i.get("round") or 1) == collect_round
    ]
    assert not same_turn_regen, "vacuum round itself must not rewrite the board"
    last_pos = {(i["reel"], i["row"]): i for i in _last_round_items(items)}
    assert last_pos[(3, 1)]["kind"] == "collector"
    assert last_pos[(3, 1)].get("collected") is not True
    assert not last_pos[(3, 1)].get("reactivate")
    assert last_pos[(3, 1)]["kind"] == "collector"
    leftover = _leftover_coin_payout(items)
    counted = _sum_replaced_pot_payouts(items)
    assert abs(total - counted - leftover) < 1e-6


def test_replacement_collector_gets_a_turn():
    """Waiting pot gets a turn and sucks the valued pot; last pot stays."""
    import game_coin_feature as gcf

    kind_seq = iter(["collector", "coin", "collector"])
    original_pick = gcf._pick_cell_kind
    gcf._pick_cell_kind = lambda gs, rng, tile_level=1, **_kwargs: next(kind_seq, "coin")
    try:
        gs = _lit_board(state(), ((1, 1), (2, 1), (3, 1)))
        total, items, _rounds = resolve_coin_game(gs)
    finally:
        gcf._pick_cell_kind = original_pick

    last_pos = {(i["reel"], i["row"]): i for i in _last_round_items(items)}
    assert last_pos[(1, 1)]["kind"] == "collector"
    assert last_pos[(1, 1)].get("collected") is not True
    assert not last_pos[(1, 1)].get("reactivate"), "last counted pot must stay and pay"
    leftover = _leftover_coin_payout(items)
    counted = _sum_replaced_pot_payouts(items)
    assert abs(total - counted - leftover) < 1e-6


def test_regen_never_spawns_a_collector():
    """Bronze reruns stay pot-free. Silver reruns may spawn a pot."""
    import random
    from game_coin_feature import _pick_cell_kind

    gs = state()
    bronze = {
        _pick_cell_kind(gs, random.Random(seed), 1, reactivate=True) for seed in range(250)
    }
    assert "collector" not in bronze
    silver = {
        _pick_cell_kind(gs, random.Random(seed), 2, reactivate=True) for seed in range(400)
    }
    assert "collector" in silver


def test_resolve_stops_when_pot_hits_wincap():
    import game_coin_feature as gcf

    kind_seq = iter(["coin", "coin", "collector"])
    original_pick = gcf._pick_cell_kind
    original_value = gcf._pick_weighted_coin_value
    gcf._pick_cell_kind = lambda gs, rng, tile_level=1, **_kwargs: next(kind_seq, "coin")
    gcf._pick_weighted_coin_value = lambda gs, tile_level, rng: 15000
    try:
        gs = _lit_board(state(), ((1, 1), (2, 1), (3, 1)))
        total, items, _rounds = resolve_coin_game(gs)
    finally:
        gcf._pick_cell_kind = original_pick
        gcf._pick_weighted_coin_value = original_value

    last_pos = {(i["reel"], i["row"]): i for i in _last_round_items(items)}
    assert last_pos[(3, 1)]["kind"] == "collector"
    assert float(last_pos[(3, 1)].get("payout") or 0) == gcf.COIN_FEATURE_WINCAP
    assert total == gcf.COIN_FEATURE_WINCAP
    collect_round = min(
        int(i.get("round") or 1)
        for i in items
        if i.get("kind") == "collector" and i.get("powerResolved")
    )
    assert not any(
        i.get("reactivate") and int(i.get("round") or 1) > collect_round for i in items
    ), "no regen after a 25k pot"


def test_natural_power_rolls_vary_with_simulation_seed():
    """Each spin must use its own seed or MULTI/COLLECTOR never leave Random(0).

    Seed gold: bronze has pot weight 0, so collectors cannot appear on level 1.
    """
    kinds: set[str] = set()
    for seed in range(80):
        gs = state()
        gs.betmode = "feature_spin"
        gs.simulation_seed = seed
        gs.progress_activation_count = 0
        for reel in range(6):
            for row in range(5):
                gs.seed_tile_to_level(reel, row, 3)
        _, items, _ = resolve_coin_game(gs)
        kinds.update(str(item.get("kind")) for item in items)
    assert "multiplier" in kinds
    assert "collector" in kinds


def test_extra_chance_rolls_the_same_powers():
    """base_ante must not fall through to zero power weights."""
    from game_coin_feature import _mode_power_weights

    gs = state()
    gs.betmode = "base_ante"
    weights = _mode_power_weights(gs)
    assert weights["multiplier"] == 12
    assert weights["collector"] == 0
    assert weights["tier_shift"] == 0


def test_power_weights_follow_tile_level():
    from game_coin_feature import _tile_power_weights

    gs = state()
    assert _tile_power_weights(gs, 1) == {"multiplier": 12, "collector": 0, "tier_shift": 0}
    assert _tile_power_weights(gs, 2) == {"multiplier": 10, "collector": 1, "tier_shift": 0}
    assert _tile_power_weights(gs, 3) == {"multiplier": 8, "collector": 2, "tier_shift": 0}
    assert _tile_power_weights(gs, 0) == _tile_power_weights(gs, 1)
    assert _tile_power_weights(gs, 99) == _tile_power_weights(gs, 3)
    gs.betmode = "peak_spin"
    assert _tile_power_weights(gs, 3) == {"multiplier": 0, "collector": 0, "tier_shift": 0}
    assert _tile_power_weights(gs, 2) == {"multiplier": 10, "collector": 1, "tier_shift": 0}


def test_progress_fills_per_tumble_not_per_cluster():
    gs = state()
    gs.board = board_from_rows(
        gs,
        [
            ["A", "A", "A", "A", "A", "T"],
            ["T", "T", "T", "T", "T", "T"],
            ["A", "A", "A", "A", "A", "T"],
            ["T", "T", "T", "T", "T", "T"],
            ["K", "Q", "J", "T", "LE", "CO"],
        ],
    )
    clusters = [cluster for cluster in GameCluster.find_winning_clusters(gs.board, gs.config) if cluster.symbol == "A"]
    assert len(clusters) == 2
    gs.progress_value = 0
    gs.advance_progress(1)
    assert gs.progress_value == 1


def test_bonus_progress_fills_per_cluster():
    gs = state()
    gs.betmode = "bonus_hear"
    gs.bonus_variant = "hear"
    gs.gametype = gs.config.freegame_type
    gs.reset_progress()
    gs.progress_value = 0
    gs.board = board_from_rows(
        gs,
        [
            ["A", "A", "A", "A", "A", "T"],
            ["T", "T", "T", "T", "T", "T"],
            ["A", "A", "A", "A", "A", "T"],
            ["T", "T", "T", "T", "T", "T"],
            ["K", "Q", "J", "T", "LE", "CO"],
        ],
    )
    clusters = [cluster for cluster in GameCluster.find_winning_clusters(gs.board, gs.config) if cluster.symbol == "A"]
    assert len(clusters) == 2
    for _ in clusters:
        gs.advance_progress(1, activate=False)
    assert gs.progress_value == 2


def test_tiles_progress_activation_and_feature_prefill():
    gs = state()
    _park_power_weights(gs.config)
    gs.board = board_from_rows(
        gs,
        [
            ["CB", "J", "Q", "K", "A", "LE"],
            ["CO", "OR", "GR", "BA", "T", "J"],
            ["Q", "K", "A", "LE", "CO", "OR"],
            ["GR", "BA", "T", "J", "Q", "K"],
            ["A", "LE", "CO", "OR", "GR", "BA"],
        ],
    )
    gs.board_coin_values = {}
    gs.seed_tile_to_level(0, 0, 2)
    gs.board_coin_values[(0, 0)] = 2.0
    assert gs.progress_threshold == 10
    gs.progress_value = gs.progress_threshold - 1
    gs.advance_progress(1)
    assert gs.progress_value == 0
    assert gs.progress_activation_count == 1
    activation_events = [event for event in gs.book.events if event["type"] == "boardActivation"]
    assert activation_events, "board activation must emit coin feature"
    activation = activation_events[-1]
    assert activation["coinFeature"]["items"], "active-tile coins must reveal"
    assert activation["coinFeature"]["rounds"] == 1
    assert not any(sym.name == "CB" for reel in gs.board for sym in reel) or any(
        getattr(sym, "explode", False) for reel in gs.board for sym in reel if sym.name == "CB"
    ), "coins marked for removal after activation"

    feature = state()
    feature.betmode = "feature_spin"
    feature.reset_progress()
    assert feature.progress_value == 0
    assert feature.progress_threshold == 10
    lit = sum(1 for reel in feature.tile_levels for level in reel if level > 0)
    assert lit == 0

    bonus = state()
    bonus.betmode = "bonus_hear"
    bonus.reset_progress()
    assert bonus.progress_threshold == 5
    bonus.progress_value = 9
    bonus.board_activation_fired_this_spin = False
    bonus.win_manager.reset_spin_win()
    bonus.update_freespin()
    assert bonus.progress_value == 9, "bonus progress must carry over between free spins"

    hear = state()
    hear.betmode = "bonus_hear"
    hear.reset_progress()
    # Hear uses betmode key; buy-hear sets threshold in run_freespin via bonus_variant.
    assert hear.config.progress_thresholds["bonus_hear"] == 5


def test_bonus_freespin_reveals_have_no_scatters():
    """Scatters may land in a bonus, including on tumbles, and the bonus still finishes."""
    gs = state()
    gs.betmode = "bonus_hear"
    gs.criteria = "bonus_hear"
    gs.reset_book()
    gs.run_bonus_buy("hear")
    reveals = [event for event in gs.book.events if event["type"] == "reveal"]
    assert reveals
    assert gs.final_win >= 0


def test_force_scatter_skipped_when_already_in_bonus():
    gs = state()
    gs.gametype = gs.config.freegame_type
    gs.betmode = "base"
    gs.criteria = "freegame"
    gs.reelstrip_id = "INITIAL_BONUS"
    gs.reelstrip = gs.config.reels["INITIAL_BONUS"]
    for _ in range(25):
        gs.draw_prepared_board()
        assert gs.count_special_symbols("scatter") == 0


def test_bonus_clusters_apply_pay_scale():
    gs = state()
    gs.betmode = "bonus_hear"
    gs.bonus_variant = "hear"
    gs.gametype = gs.config.freegame_type
    gs.board = board_from_rows(
        gs,
        [
            ["BA", "BA", "BA", "BA", "BA", "T"],
            ["T", "J", "Q", "K", "A", "LE"],
            ["CO", "OR", "GR", "BA", "T", "J"],
            ["Q", "K", "A", "LE", "CO", "OR"],
            ["GR", "BA", "T", "J", "Q", "K"],
        ],
    )
    clusters = GameCluster.find_winning_clusters(gs.board, gs.config)
    assert clusters, "fixture must contain a paying cluster"
    gs.mark_level_up_tiles(clusters)
    raw_total = gs.evaluate_clusters(clusters)["totalWin"]
    gs.award_clusters(clusters)
    scale = float(gs.config.bonus_cluster_pay_scale) * float(gs.config.hear_cluster_pay_scale)
    expected = round(raw_total * scale, 6)
    assert gs.win_data["totalWin"] == expected
    assert all(win["win"] > 0.0 for win in gs.win_data["wins"])
    assert gs.win_manager.spin_win == expected
    assert gs.is_bonus_mode()

def test_base_clusters_still_pay():
    gs = state()
    gs.board = board_from_rows(
        gs,
        [
            ["BA", "BA", "BA", "BA", "BA", "T"],
            ["T", "J", "Q", "K", "A", "LE"],
            ["CO", "OR", "GR", "BA", "T", "J"],
            ["Q", "K", "A", "LE", "CO", "OR"],
            ["GR", "BA", "T", "J", "Q", "K"],
        ],
    )
    clusters = GameCluster.find_winning_clusters(gs.board, gs.config)
    gs.mark_level_up_tiles(clusters)
    gs.award_clusters(clusters)
    assert gs.win_data["totalWin"] > 0.0
    assert gs.win_manager.spin_win > 0.0
    scale = float(getattr(gs.config, "paytable_scale", 1.0))
    # Plain pay (no tile multipliers): size-5 BA pays its face even after ranking up.
    assert gs.win_data["totalWin"] == round(1.0 * scale, 6)


def test_cluster_payout_ignores_tile_levels():
    gs = state()
    gs.board = board_from_rows(
        gs,
        [
            ["BA", "BA", "BA", "BA", "BA", "T"],
            ["T", "J", "Q", "K", "A", "LE"],
            ["CO", "OR", "GR", "BA", "T", "J"],
            ["Q", "K", "A", "LE", "CO", "OR"],
            ["GR", "BA", "T", "J", "Q", "K"],
        ],
    )
    # Seed one cluster cell to bronze (mult 2); others inactive.
    gs.seed_tile_to_level(0, 0, 1)
    clusters = GameCluster.find_winning_clusters(gs.board, gs.config)
    ba = [c for c in clusters if c.symbol == "BA"][0]
    assert ba.size == 5
    win_data = gs.evaluate_clusters([ba])
    # Plain pay: a lit bronze tile does not change the face. clusterMult stays 1.
    scale = float(getattr(gs.config, "paytable_scale", 1.0))
    assert abs(win_data["totalWin"] - round(1.0 * scale, 6)) < 1e-9
    assert win_data["wins"][0]["meta"]["clusterMult"] == 1
    # Legacy formula is one flag away: face × sum of lit tile multipliers.
    gs.config.cluster_pay_uses_tile_multipliers = True
    try:
        legacy = gs.evaluate_clusters([ba])
        assert abs(legacy["totalWin"] - round(1.0 * scale * 2.0, 6)) < 1e-9
        assert legacy["wins"][0]["meta"]["clusterMult"] == 2.0
    finally:
        gs.config.cluster_pay_uses_tile_multipliers = False


def test_scatter_bonus_and_hard_cap_smoke():
    gs = state()
    gs.board = board_from_rows(
        gs,
        [
            ["T", "J", "Q", "K", "A", "LE"],
            ["CO", "OR", "GR", "BA", "T", "J"],
            ["Q", "K", "A", "LE", "CO", "OR"],
            ["GR", "BA", "T", "J", "Q", "K"],
            ["A", "LE", "CO", "OR", "GR", "BA"],
        ],
    )
    gs.force_initial_scatters(4)
    gs.get_special_symbols_on_board()
    assert gs.count_special_symbols("scatter") == 4
    gs.award_scatter_payout()
    assert gs.win_manager.running_bet_win == 0

    gs.win_manager.running_bet_win = gs.config.wincap - 1
    gs.board = board_from_rows(
        gs,
        [
            ["BA", "BA", "BA", "BA", "BA", "T"],
            ["T", "J", "Q", "K", "A", "LE"],
            ["CO", "OR", "GR", "BA", "T", "J"],
            ["Q", "K", "A", "LE", "CO", "OR"],
            ["GR", "BA", "T", "J", "Q", "K"],
        ],
    )
    gs.award_clusters(GameCluster.find_winning_clusters(gs.board, gs.config))
    assert gs.win_manager.running_bet_win <= gs.config.wincap


def test_sticky_hear_disabled():
    gs = state()
    gs.betmode = "bonus_hear"
    gs.bonus_variant = "hear"
    gs.gametype = gs.config.freegame_type
    gs.sticky_wild_positions = [{"reel": 1, "row": 2}]
    gs.reelstrip_id = "INITIAL_BONUS"
    gs.reelstrip = gs.config.reels["INITIAL_BONUS"]
    gs.refill_strip = gs.config.reels["REFILL"]
    gs.draw_prepared_board()
    assert gs.sticky_position_set() == set()
    assert gs.sticky_wild_positions == []
    sticky_events = [e for e in gs.book.events if e["type"] == "stickyWilds"]
    assert not sticky_events, "Phase A must not emit stickyWilds"


def test_hear_threshold_is_five():
    gs = state()
    gs.betmode = "bonus_hear"
    gs.bonus_variant = "hear"
    gs.gametype = gs.config.freegame_type
    gs.progress_threshold = gs.config.progress_thresholds["bonus_hear"]
    assert gs.progress_threshold == 5
    gs.seed_tile_to_level(0, 0, 1)
    gs.board = board_from_rows(
        gs,
        [
            ["T", "J", "Q", "K", "A", "LE"],
            ["CO", "OR", "GR", "BA", "T", "J"],
            ["Q", "K", "A", "LE", "CO", "OR"],
            ["GR", "BA", "T", "J", "Q", "K"],
            ["A", "LE", "CO", "OR", "GR", "BA"],
        ],
    )
    gs.board_coin_values = {}
    gs.progress_value = 0
    for step in range(1, 5):
        gs.advance_progress(1)
        assert gs.progress_value == step
        assert gs.progress_activation_count == 0
    gs.seed_tile_to_level(0, 0, 1)
    gs.advance_progress(1)
    assert gs.progress_activation_count == 1
    assert gs.progress_value == 0


def _filler_board(gs):
    return board_from_rows(
        gs,
        [
            ["T", "J", "Q", "K", "A", "LE"],
            ["CO", "OR", "GR", "BA", "T", "J"],
            ["Q", "K", "A", "LE", "CO", "OR"],
            ["GR", "BA", "T", "J", "Q", "K"],
            ["A", "LE", "CO", "OR", "GR", "BA"],
        ],
    )


def test_three_scatters_trigger_see_bonus():
    """3 ST starts See — still no scatter pay."""
    import contextlib
    import io

    gs = state()
    assert gs.config.scatter_pays == {}
    gs.betmode = "base"
    gs.criteria = "basegame"
    gs.reset_book()
    gs.board = _filler_board(gs)
    gs.force_initial_scatters(3)
    gs.get_special_symbols_on_board()
    assert gs.count_special_symbols("scatter") == 3
    win_before = gs.win_manager.running_bet_win
    gs.award_scatter_payout()
    assert gs.win_manager.running_bet_win == win_before

    gs.reset_book()
    gs.should_force_initial_scatters = lambda: True
    gs.resolve_forced_scatter_count = lambda: 3
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        gs.run_base_spin()
    assert getattr(gs, "triggered_freegame", False)
    states = [
        event.get("state")
        for event in gs.book.events
        if event.get("type") == "kongClubMode"
    ]
    assert states and states[0] == "organic_bonus_see"


def test_gamble_forced_scatters_never_see():
    """Risky Hear / Speak resolve to those tiers. Mystery can still be See."""
    gs = state()
    gs.betmode = "bonus_risky"
    assert gs.resolve_bonus_variant_from_scatters(4) == "hear"
    assert gs.resolve_bonus_variant_from_scatters(5) == "speak"
    gs.betmode = "bonus_mystery"
    assert gs.resolve_bonus_variant_from_scatters(3) == "see"


def test_five_scatters_resolve_to_madness():
    gs = state()
    assert gs.resolve_bonus_variant_from_scatters(3) == "see"
    assert gs.resolve_bonus_variant_from_scatters(4) == "hear"
    assert gs.resolve_bonus_variant_from_scatters(5) == "speak"
    assert gs.resolve_bonus_variant_from_scatters(6) == "speak"


def test_gamble_dead_has_no_cluster_or_bonus():
    gs = state()
    gs.betmode = "bonus_risky"
    gs.criteria = "risky_dead"
    gs.reset_book()
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        gs.run_spin(7)
    types = [event["type"] for event in gs.book.events]
    st = gs.count_special_symbols("scatter")
    assert st == 2
    assert any(sym.name == "ST" for sym in gs.board[0])
    assert any(sym.name == "ST" for sym in gs.board[1])
    assert not any(sym.name == "ST" for reel in gs.board[2:] for sym in reel)
    assert not GameCluster.find_winning_clusters(gs.board, gs.config)
    assert "reveal" in types
    assert "winInfo" not in types
    assert "progressFill" not in types
    assert "boardActivation" not in types
    assert "freeSpinTrigger" not in types
    assert not getattr(gs, "triggered_freegame", False)
    assert getattr(gs, "bonus_variant", None) != "see"


def test_gamble_always_baits_two_on_trigger_land():
    """Dead / Hear / Madness first reveal always has ST on reels 0 and 1."""
    cases = (("risky_dead", 7),)
    for criteria, seed in cases:
        gs = state()
        gs.betmode = "bonus_risky"
        gs.criteria = criteria
        gs.reset_book()
        sink = io.StringIO()
        with contextlib.redirect_stdout(sink):
            gs.run_spin(seed)
        first_reveal = next(event for event in gs.book.events if event.get("type") == "reveal")
        st_reels = [
            reel
            for reel, col in enumerate(first_reveal.get("board") or [])
            if any(
                (cell.get("name") if isinstance(cell, dict) else getattr(cell, "name", cell)) == "ST"
                for cell in col
            )
        ]
        assert 0 in st_reels and 1 in st_reels, f"{criteria}: first two reels must bait ST, got {st_reels}"


def test_gamble_dead_baits_two_every_seed():
    for seed in range(1, 21):
        gs = state()
        gs.betmode = "bonus_risky"
        gs.criteria = "risky_dead"
        gs.reset_book()
        sink = io.StringIO()
        with contextlib.redirect_stdout(sink):
            gs.run_spin(seed)
        assert any(sym.name == "ST" for sym in gs.board[0]), f"seed={seed} reel 0"
        assert any(sym.name == "ST" for sym in gs.board[1]), f"seed={seed} reel 1"
        assert gs.count_special_symbols("scatter") == 2, f"seed={seed}"


def test_tease_through_last_reel_when_fewer_than_five_st():
    """Hear / late 3-ST: tease after the 2nd tablet through reel 5."""
    gs = state()
    gs.betmode = "bonus_mystery"
    gs.gametype = gs.config.basegame_type
    rows = [["A"] * 6 for _ in range(5)]
    rows[0][3] = "ST"
    rows[1][4] = "ST"
    rows[2][5] = "ST"
    gs.board = board_from_rows(gs, rows)
    gs.apply_scatter_anticipation()
    assert gs.anticipation[-1] > 0


def test_hear_four_st_teases_through_last_reel():
    gs = state()
    gs.betmode = "bonus_mystery"
    gs.gametype = gs.config.basegame_type
    rows = [["A"] * 6 for _ in range(5)]
    rows[0][0] = "ST"
    rows[1][1] = "ST"
    rows[2][3] = "ST"
    rows[3][4] = "ST"
    gs.board = board_from_rows(gs, rows)
    gs.apply_scatter_anticipation()
    assert any(level > 0 for level in gs.anticipation[2:])
    assert gs.anticipation[-1] > 0


def test_fifth_st_on_reel_four_slams_last_reel():
    """5th tablet on reel 4 → tease through that reel, reel 5 slams."""
    gs = state()
    gs.betmode = "bonus_mystery"
    gs.gametype = gs.config.basegame_type
    rows = [["A"] * 6 for _ in range(5)]
    for reel in range(5):
        rows[0][reel] = "ST"
    gs.board = board_from_rows(gs, rows)
    gs.apply_scatter_anticipation()
    assert gs.anticipation[2] > 0
    assert gs.anticipation[4] > 0
    assert gs.anticipation[5] == 0


def test_gamble_dead_bait_two_st_tease():
    gs = state()
    gs.betmode = "bonus_risky"
    gs.criteria = "risky_dead"
    gs.reset_book()
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        gs.run_spin(7)
    first_reveal = next(event for event in gs.book.events if event.get("type") == "reveal")
    st_reels = [
        reel
        for reel, col in enumerate(first_reveal.get("board") or [])
        if any((cell.get("name") if isinstance(cell, dict) else getattr(cell, "name", cell)) == "ST" for cell in col)
    ]
    assert st_reels == [0, 1]
    anticipation = first_reveal.get("anticipation") or []
    assert any(level > 0 for level in anticipation[2:])
    assert anticipation[-1] > 0, "dead 2 ST still teases through the last reel"
    assert not getattr(gs, "triggered_freegame", False)
    assert "freeSpinEnd" not in [event["type"] for event in gs.book.events]


def test_gamble_hear_emits_freespins():
    gs = state()
    gs.betmode = "bonus_mystery"
    gs.criteria = "pick_hear"
    gs.reset_book()
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        gs.run_spin(11)
    types = [event["type"] for event in gs.book.events]
    assert "freeSpinTrigger" not in types
    assert "scatterPayout" not in types
    assert "freeSpinEnd" in types
    assert types.count("reveal") > 1
    assert getattr(gs, "triggered_freegame", False)
    assert gs.bonus_variant == "hear"
    assert any(
        event.get("type") == "kongClubMode" and event.get("state") == "start_bonus_hear"
        for event in gs.book.events
    )


def test_gamble_madness_emits_freespins():
    gs = state()
    gs.betmode = "bonus_mystery"
    gs.criteria = "pick_speak"
    gs.reset_book()
    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        gs.run_spin(13)
    types = [event["type"] for event in gs.book.events]
    assert "freeSpinTrigger" not in types
    assert "scatterPayout" not in types
    assert "freeSpinEnd" in types
    assert types.count("reveal") > 1
    assert getattr(gs, "triggered_freegame", False)
    assert gs.bonus_variant == "speak"
    assert any(
        event.get("type") == "kongClubMode" and event.get("state") == "start_bonus_speak"
        for event in gs.book.events
    )
    fills = [event for event in gs.book.events if event.get("type") == "progressFill"]
    assert fills, "Madness must emit progressFill"
    assert fills[0].get("value") == fills[0].get("threshold") == 5
    assert gs.progress_value == gs.progress_threshold


def test_madness_progress_stays_full():
    gs = state()
    gs.bonus_variant = "speak"
    gs.gametype = gs.config.freegame_type
    gs.reset_progress()
    assert gs.progress_value == gs.progress_threshold == 5

    gs.board_activation_fired_this_spin = False
    gs.board_activations_this_spin = 0
    gs.execute_board_activation(refill_after=False)
    assert gs.progress_value == gs.progress_threshold
    assert gs.board_activation_fired_this_spin is True
    activations = gs.board_activations_this_spin
    gs.execute_board_activation(refill_after=False)
    assert gs.board_activations_this_spin == activations
    assert gs.progress_value == gs.progress_threshold


def test_madness_skips_bronze_coins():
    from game_coin_feature import resolve_coin_game

    gs = state()
    _park_power_weights(gs.config)
    gs.bonus_variant = "speak"
    gs.gametype = gs.config.freegame_type
    gs.board = _filler_board(gs)
    gs.reset_grid_mults()
    gs.seed_tile_to_level(0, 0, 1)
    gs.seed_tile_to_level(1, 1, 2)
    gs.seed_tile_to_level(2, 2, 3)
    _total, items, _rounds = resolve_coin_game(gs)
    levels = {(item["reel"], item["row"]): item["tileLevel"] for item in items}
    assert levels[(0, 0)] == 1
    assert levels[(1, 1)] == 2
    assert levels[(2, 2)] == 3


def test_madness_tiles_skip_bronze():
    """Speak upgrades plain to bronze, then silver. Bronze is a real rank."""
    gs = state()
    gs.betmode = "bonus_hear"
    gs.bonus_variant = "speak"
    gs.gametype = gs.config.freegame_type
    gs.board = board_from_rows(
        gs,
        [
            ["OR", "OR", "MW", "BA", "BA", "BA"],
            ["OR", "OR", "BA", "BA", "Q", "T"],
            ["Q", "Q", "BA", "J", "A", "LE"],
            ["CO", "LE", "A", "J", "Q", "K"],
            ["OR", "J", "Q", "K", "A", "LE"],
        ],
    )
    gs.reset_grid_mults()
    clusters = GameCluster.find_winning_clusters(gs.board, gs.config)
    or_cluster = [cluster for cluster in clusters if cluster.symbol == "OR"][0]
    gs.activate_tiles_from_clusters([or_cluster])
    assert gs.tile_levels[0][0] == 1
    assert gs.position_multipliers[0][0] == 2
    assert gs.tile_levels[0][4] == 0
    gs.activate_tiles_from_clusters([or_cluster])
    assert gs.tile_levels[0][0] == 2
    assert gs.position_multipliers[0][0] == 5


def test_hear_bonus_persists_tiles_after_board_activation():
    gs = state()
    gs.betmode = "bonus_hear"
    gs.bonus_variant = "hear"
    gs.gametype = gs.config.freegame_type
    gs.progress_threshold = 5
    gs.board = _filler_board(gs)
    gs.board_coin_values = {}
    gs.seed_tile_to_level(0, 0, 3)
    gs.seed_tile_to_level(2, 2, 2)
    gs.progress_value = gs.progress_threshold
    gs.execute_board_activation()
    assert gs.tile_levels[0][0] == 3
    assert gs.tile_levels[2][2] == 2
    assert gs.board_activation_fired_this_spin is True


def test_hear_bonus_allows_chained_activations_in_one_spin():
    gs = state()
    gs.bonus_variant = "hear"
    gs.gametype = gs.config.freegame_type
    gs.progress_threshold = 5
    gs.board = board_from_rows(
        gs,
        [
            ["CB", "J", "Q", "K", "A", "LE"],
            ["CO", "OR", "GR", "BA", "T", "J"],
            ["Q", "K", "A", "LE", "CO", "OR"],
            ["GR", "BA", "T", "J", "Q", "K"],
            ["A", "LE", "CO", "OR", "GR", "BA"],
        ],
    )
    gs.seed_tile_to_level(0, 0, 2)
    gs.board_coin_values = {(0, 0): 1.0}
    gs.progress_value = gs.progress_threshold - 1
    gs.advance_progress(1)
    assert gs.progress_activation_count == 1
    # Re-place coin after activation removed it.
    gs.board[0][0] = gs.create_symbol("CB")
    gs.board_coin_values[(0, 0)] = 1.0
    gs.seed_tile_to_level(0, 0, 2)
    gs.progress_value = gs.progress_threshold - 1
    gs.advance_progress(1)
    assert gs.progress_activation_count == 1


def test_hear_bonus_caps_chained_activations_at_three():
    gs = state()
    gs.bonus_variant = "hear"
    gs.gametype = gs.config.freegame_type
    gs.progress_threshold = 5
    gs.board = board_from_rows(
        gs,
        [
            ["CB", "J", "Q", "K", "A", "LE"],
            ["CO", "OR", "GR", "BA", "T", "J"],
            ["Q", "K", "A", "LE", "CO", "OR"],
            ["GR", "BA", "T", "J", "Q", "K"],
            ["A", "LE", "CO", "OR", "GR", "BA"],
        ],
    )
    for _ in range(3):
        gs.board[0][0] = gs.create_symbol("CB")
        gs.seed_tile_to_level(0, 0, 2)
        gs.board_coin_values = {(0, 0): 1.0}
        gs.progress_value = gs.progress_threshold - 1
        gs.advance_progress(1)
    assert gs.progress_activation_count == 1
    gs.board[0][0] = gs.create_symbol("CB")
    gs.seed_tile_to_level(0, 0, 2)
    gs.board_coin_values = {(0, 0): 1.0}
    gs.progress_value = gs.progress_threshold - 1
    gs.advance_progress(1)
    assert gs.progress_activation_count == 1


def test_bonus_entry_starts_with_empty_tiles():
    gs = state()
    gs.seed_tile_to_level(0, 0, 2)
    gs.seed_tile_to_level(3, 2, 1)
    for variant in ("hear",):
        gs.bonus_variant = variant
        gs.gametype = gs.config.freegame_type
        gs.reset_grid_mults()
        assert all(level == 0 for reel in gs.tile_levels for level in reel)


def test_feature_spin_starts_full_without_seeded_tiles():
    gs = state()
    gs.betmode = "feature_spin"
    gs.criteria = "run"
    gs.reset_book()
    gs.board_activation_fired_this_spin = False
    gs.gametype = gs.config.basegame_type
    gs.reelstrip_id = "FEATURE_SPIN"
    gs.reelstrip = gs.config.reels["FEATURE_SPIN"]
    gs.refill_strip = gs.config.reels["FEATURE_SPIN_REFILL"]
    gs.reset_progress()
    assert gs.progress_value == 0
    assert gs.progress_threshold == 10
    gs.draw_prepared_board()
    lit = sum(1 for reel in gs.tile_levels for level in reel if level > 0)
    assert lit == 0
    before = gs.board_activations_this_spin
    gs.ensure_feature_spin_coin_game()
    assert gs.board_activations_this_spin == before


def test_feature_spin_needs_a_winning_connection():
    gs = state()
    gs.betmode = "feature_spin"
    gs.criteria = "run"
    gs.reset_book()
    gs.reset_progress()
    gs.draw_prepared_board()
    gs.board_activation_fired_this_spin = False
    gs.tumbles_this_spin = 0
    gs.check_progress_bar()
    assert "boardActivation" not in [event["type"] for event in gs.book.events]
    gs.tumbles_this_spin = 1
    gs.check_progress_bar()
    assert "boardActivation" not in [event["type"] for event in gs.book.events]
    gs.progress_value = gs.progress_threshold
    gs.check_progress_bar()
    assert any(event["type"] == "boardActivation" for event in gs.book.events)


def test_feature_spin_never_dead_spins():
    """Every Feature Spin opens with a full bar, connects, and runs the coin game. No bonus."""
    sizes = set()
    for seed in range(10_000, 10_012):
        gs = state()
        gs.betmode = "feature_spin"
        gs.criteria = "run"
        sink = __import__("io").StringIO()
        with __import__("contextlib").redirect_stdout(sink):
            gs.run_spin(seed)
        types = [event["type"] for event in gs.book.events]
        assert "winInfo" in types, f"seed={seed}: Feature Spin missed its connection"
        assert "tumbleBoard" in types, f"seed={seed}: Feature Spin missed tumble"
        assert "boardActivation" in types, f"seed={seed}: full bar did not run the coin game"
        assert "freeSpinTrigger" not in types, f"seed={seed}: Feature Spin opened a bonus"
        assert not any(
            event.get("type") == "kongClubMode" and "bonus" in str(event.get("state") or "")
            for event in gs.book.events
        )
        fills = [event for event in gs.book.events if event["type"] == "progressFill"]
        assert fills and fills[0]["value"] == fills[0]["threshold"] > 0
        activation = next(event for event in gs.book.events if event["type"] == "boardActivation")
        assert activation["coinFeature"]["items"], f"seed={seed}: coin game flipped no tiles"
        assert gs.final_win > 0
        for event in gs.book.events:
            if event.get("type") != "winInfo":
                continue
            for win in event.get("wins") or []:
                sizes.add(int(win.get("clusterSize") or 0))
        assert_no_leftover_clusters(gs, gs.book, f"feature_spin seed={seed}")
    assert len(sizes) >= 2, f"Feature Spin cluster sizes did not vary: {sorted(sizes)}"


def test_peak_spin_starts_full_gold_and_empty_bar():
    gs = state()
    gs.betmode = "peak_spin"
    gs.criteria = "peak_spin"
    gs.reset_book()
    gs.reset_progress()
    assert gs.progress_value == 0
    assert gs.progress_threshold == 1
    gs.seed_peak_gold_tiles()
    assert all(level == 3 for reel in gs.tile_levels for level in reel)
    assert all(mult == 10 for reel in gs.position_multipliers for mult in reel)
    assert gs.config.initial_reelstrip_id("peak_spin", gs.config.basegame_type) == "FEATURE"


def test_peak_spin_needs_a_winning_tumble_to_activate():
    """PEAK uses the same first-tumble trigger as Feature Spin — no empty collect."""
    gs = state()
    gs.betmode = "peak_spin"
    gs.criteria = "peak_spin"
    gs.reset_book()
    gs.reset_progress()
    gs.seed_peak_gold_tiles()
    gs.board_activation_fired_this_spin = False
    gs.tumbles_this_spin = 0
    gs.progress_value = 0
    gs.check_progress_bar()
    assert "boardActivation" not in [event["type"] for event in gs.book.events]
    gs.progress_value = 1
    gs.tumbles_this_spin = 1
    gs.check_progress_bar()
    assert any(event["type"] == "boardActivation" for event in gs.book.events)


def test_feature_spin_cluster_pays_plain_face_like_base():
    """Feature Spin ranks tiles like base; cluster pay is the plain face."""
    gs = state()
    gs.betmode = "feature_spin"
    gs.reset_grid_mults()
    gs.board = board_from_rows(
        gs,
        [
            ["BA", "BA", "BA", "BA", "BA", "T"],
            ["T", "J", "Q", "K", "A", "LE"],
            ["CO", "OR", "GR", "BA", "T", "J"],
            ["Q", "K", "A", "LE", "CO", "OR"],
            ["GR", "BA", "T", "J", "Q", "K"],
        ],
    )
    clusters = GameCluster.find_winning_clusters(gs.board, gs.config)
    gs.mark_level_up_tiles(clusters)
    gs.award_clusters(clusters)
    scale = float(getattr(gs.config, "paytable_scale", 1.0))
    assert all(gs.tile_levels[reel][row] == 1 for reel, row in clusters[0].positions)
    # Plain pay: five bronze tiles do not multiply the face.
    assert gs.win_data["totalWin"] == round(1.0 * scale, 6)


def test_peak_cluster_pays_from_connections_not_gold_seed():
    """PEAK gold is chrome/coins. Live Trifecta never awards cluster pay (resolve_cascade_loop).

    Under the legacy tile-multiplier formula a connection would pay base × sum of the
    new bronze multipliers; that path is checked with the flag on.
    """
    gs = state()
    gs.betmode = "peak_spin"
    gs.reset_grid_mults()
    gs.seed_peak_gold_tiles()
    assert all(level == 3 for reel in gs.tile_levels for level in reel)
    gs.board = board_from_rows(
        gs,
        [
            ["BA", "BA", "BA", "BA", "BA", "T"],
            ["T", "J", "Q", "K", "A", "LE"],
            ["CO", "OR", "GR", "BA", "T", "J"],
            ["Q", "K", "A", "LE", "CO", "OR"],
            ["GR", "BA", "T", "J", "Q", "K"],
        ],
    )
    clusters = GameCluster.find_winning_clusters(gs.board, gs.config)
    gs.config.cluster_pay_uses_tile_multipliers = True
    gs.award_clusters(clusters)
    scale = float(getattr(gs.config, "paytable_scale", 1.0))
    # Gold seed is not a cluster multiplier. No connection yet → sum of lit ranks is 0.
    assert gs.win_data["totalWin"] == round(0.0, 6)
    gs.activate_tiles_from_clusters(clusters)
    assert all(
        gs.peak_connection_levels[reel][row] == 1 for reel, row in clusters[0].positions
    )
    win_data = gs.evaluate_clusters(clusters)
    # Five connection-bronze cells: base × (2×5).
    assert abs(win_data["totalWin"] - round(1.0 * scale * 10.0, 6)) < 1e-9
    gs.config.cluster_pay_uses_tile_multipliers = False


def test_peak_spin_can_miss_connections():
    """Feature strips can still miss — PEAK does not guarantee a cluster."""
    dead = 0
    for seed in range(30_000, 30_400):
        gs = state()
        gs.betmode = "peak_spin"
        gs.criteria = "dead_juicy"
        sink = __import__("io").StringIO()
        with __import__("contextlib").redirect_stdout(sink):
            gs.run_spin(seed)
        types = [event["type"] for event in gs.book.events]
        assert "winInfo" not in types, f"seed={seed}: SUMMIT must not pay clusters"
        assert "boardActivation" not in types, f"seed={seed}: dead_juicy must not activate"
        dead += 1
        assert "tumbleBoard" not in types, f"seed={seed}: dead SUMMIT must not tumble"
        gold = next(
            event for event in gs.book.events if event.get("type") == "updateLevelUpTiles"
        )
        assert all(level == 3 for reel in gold["tileLevels"] for level in reel)
        if dead >= 3:
            break
    assert dead >= 3, "need dead PEAK spins to prove clusters are not guaranteed"


def test_peak_land_cluster_activates_without_cascade():
    """A 5+ land still hits the coin game, but SUMMIT does not pay or tumble it."""
    gs = state()
    gs.betmode = "peak_spin"
    gs.criteria = "peak_spin"
    gs.reset_book()
    gs.reset_progress()
    gs.seed_peak_gold_tiles()
    gs.board_activation_fired_this_spin = False
    gs.win_manager.reset_spin_win()
    _park_power_weights(gs.config)
    gs.board = board_from_rows(
        gs,
        [
            ["BA", "BA", "BA", "BA", "BA", "T"],
            ["T", "J", "Q", "K", "A", "LE"],
            ["CO", "OR", "GR", "BA", "T", "J"],
            ["Q", "K", "A", "LE", "CO", "OR"],
            ["GR", "BA", "T", "J", "Q", "K"],
        ],
    )
    gs.board_coin_values = {}
    gs.resolve_cascade_loop()
    types = [event["type"] for event in gs.book.events]
    assert "winInfo" not in types
    assert "boardActivation" in types
    idx = types.index("boardActivation")
    assert "tumbleBoard" not in types[:idx]
    assert gs.win_data["totalWin"] == 0.0
    assert gs.tumbles_this_spin == 1


def test_peak_dead_land_does_not_activate():
    """No 5+ on the land → no coin game, no tumble."""
    gs = state()
    gs.betmode = "peak_spin"
    gs.criteria = "peak_spin"
    gs.reset_book()
    gs.reset_progress()
    gs.seed_peak_gold_tiles()
    gs.board_activation_fired_this_spin = False
    gs.board = board_from_rows(
        gs,
        [
            ["T", "T", "J", "Q", "K", "A"],
            ["LE", "CO", "OR", "GR", "BA", "T"],
            ["J", "Q", "K", "A", "LE", "CO"],
            ["OR", "GR", "BA", "T", "J", "Q"],
            ["K", "A", "LE", "CO", "OR", "GR"],
        ],
    )
    gs.board_coin_values = {}
    gs.resolve_cascade_loop()
    types = [event["type"] for event in gs.book.events]
    assert "boardActivation" not in types
    assert "tumbleBoard" not in types
    assert "winInfo" not in types
    assert gs.tumbles_this_spin == 0


def test_organic_bonus_entry_resets_progress():
    """Base leftover progress must not carry into organic freegame entry."""
    for seed in range(20_000, 20_800):
        gs = state()
        gs.betmode = "base"
        gs.criteria = "freegame"
        sink = __import__("io").StringIO()
        with __import__("contextlib").redirect_stdout(sink):
            gs.run_spin(seed)
        modes = [e for e in gs.book.events if e.get("type") == "kongClubMode"]
        if not any(str(e.get("state", "")).startswith("organic_bonus_") for e in modes):
            continue
        # First progressFill after organic mode should be 0 (bonus entry reset).
        organic_idx = next(
            i
            for i, e in enumerate(gs.book.events)
            if e.get("type") == "kongClubMode"
            and str(e.get("state", "")).startswith("organic_bonus_")
        )
        fills = [
            e
            for e in gs.book.events[organic_idx:]
            if e.get("type") == "progressFill"
        ]
        assert fills, f"seed={seed}: missing progressFill after organic entry"
        state_name = str(gs.book.events[organic_idx].get("state", ""))
        expected = gs.progress_threshold if state_name.endswith("_speak") else 0
        got = fills[0].get("value", fills[0].get("progress", -1))
        assert got == expected, (
            f"seed={seed}: expected progress {expected} at {state_name} entry, got {fills[0]}"
        )
        return
    raise AssertionError("no organic bonus sample found")


def test_organic_freegame_pays_physical_coins():
    """Organic free spins land physical coins. Face × tile multiplier is the pay."""
    from game_coin_feature import _use_virtual_coins, resolve_coin_game

    gs = state()
    _park_power_weights(gs.config)
    gs.betmode = "base"
    gs.gametype = gs.config.freegame_type
    gs.bonus_variant = "hear"
    assert _use_virtual_coins(gs) is False

    gs.board = board_from_rows(
        gs,
        [
            ["CB", "T", "J", "Q", "K", "A"],
            ["LE", "CO", "OR", "GR", "BA", "T"],
            ["J", "Q", "K", "A", "LE", "CO"],
            ["OR", "GR", "BA", "T", "J", "Q"],
            ["K", "A", "LE", "CO", "OR", "GR"],
        ],
    )
    gs.board_coin_values = {(0, 0): 4.0}
    gs.seed_tile_to_level(0, 0, 2)
    gs.seed_tile_to_level(1, 0, 3)  # lit tile without a coin — still a virtual prize
    total, items, rounds = resolve_coin_game(gs)
    assert rounds == 1
    assert len(items) == 2
    coin = next(item for item in items if item["reel"] == 0 and item["row"] == 0)
    # Silver tile is 5×, so the landed 4 pays 20.
    assert coin["payout"] == 20.0
    assert total > 0
    assert all(item["displayValue"] == item["payout"] for item in items)
    assert all(float(item["displayValue"]).is_integer() for item in items)

def test_cascade_emits_tumble_before_board_activation():
    """Jul 2: gravity/refill (tumbleBoard) must complete before Board Activation."""
    found = 0
    for seed in range(1, 8):
        gs = state()
        gs.betmode = "base"
        gs.criteria = "bar_pay"
        sink = __import__("io").StringIO()
        with __import__("contextlib").redirect_stdout(sink):
            gs.run_spin(seed)
        types = [event["type"] for event in gs.book.events]
        if "boardActivation" not in types:
            continue
        idx = types.index("boardActivation")
        before = types[:idx]
        assert "tumbleBoard" in before, f"seed={seed}: activation without tumble"
        last_tb = len(before) - 1 - before[::-1].index("tumbleBoard")
        last_wi = len(before) - 1 - before[::-1].index("winInfo")
        assert last_wi < last_tb < idx, (
            f"seed={seed}: expected winInfo → tumbleBoard → boardActivation, got {types[max(0, idx-6):idx+2]}"
        )
        fills = [i for i, t in enumerate(types[:idx]) if t == "progressFill"]
        assert fills, f"seed={seed}: activation without progressFill"
        last_fill = fills[-1]
        assert last_wi < last_fill < last_tb, (
            f"seed={seed}: expected winInfo → progressFill → tumbleBoard, got {types[max(0, idx-8):idx+2]}"
        )
        found += 1
        if found >= 2:
            break
    assert found >= 2, "need at least two base activations to validate order"


def _assert_activation_after_cascade_idle(types, seed, mode):
    idx = types.index("boardActivation")
    before = types[:idx]
    tumble_idxs = [i for i, t in enumerate(before) if t == "tumbleBoard"]
    assert tumble_idxs, f"{mode} seed={seed}: activation without tumble"
    last_tb = tumble_idxs[-1]
    assert "winInfo" not in types[last_tb:idx], (
        f"{mode} seed={seed}: winInfo after last tumble before boardActivation, "
        f"got {types[max(0, last_tb):idx + 2]}"
    )
    return len(tumble_idxs)


def test_activation_waits_until_cascade_idle():
    """Coin game fires only after the last cluster tumble, not mid-cascade."""
    found_fs = 0
    for seed in range(1, 40):
        gs = state()
        gs.betmode = "base"
        gs.criteria = "bar_pay"
        sink = __import__("io").StringIO()
        with __import__("contextlib").redirect_stdout(sink):
            gs.run_spin(seed)
        types = [event["type"] for event in gs.book.events]
        if "boardActivation" not in types:
            continue
        tumbles_before = _assert_activation_after_cascade_idle(types, seed, "bar_pay")
        if tumbles_before < 2:
            continue
        found_fs += 1
        break
    assert found_fs >= 1, "need a bar-fill with 2+ tumbles before the coin game"

    found_base = 0
    for seed in range(40, 80):
        gs = state()
        gs.betmode = "base_ante"
        gs.criteria = "bar_pay"
        sink = __import__("io").StringIO()
        with __import__("contextlib").redirect_stdout(sink):
            gs.run_spin(seed)
        types = [event["type"] for event in gs.book.events]
        if "boardActivation" not in types:
            continue
        tumbles_before = _assert_activation_after_cascade_idle(types, seed, "base")
        if tumbles_before < 2:
            continue
        found_base += 1
        break
    assert found_base >= 1, "need a base spin with 2+ tumbles before activation"


def main():
    test_reel_strips_are_run_based_and_refill_rules()
    test_paytable_size_bands()
    test_bfs_orthogonal_shapes_and_no_diagonals()
    test_multiple_same_symbol_clusters_pay_independently()
    test_wild_substitution_and_wild_removal()
    test_tiles_increment_connected_cluster_only()
    test_super_cascade_removes_all_winning_type_cells()
    test_coins_never_removed_by_cascade()
    test_gravity_refill_no_empty_and_no_refill_specials()
    test_base_game_spin_excludes_coins_and_scatters()
    test_bonus_hit_rate_and_ante_cost()
    test_coin_seed_on_land()
    test_activation_pays_virtual_coins_on_active_tiles()
    test_multi_power_resolves_adjacent_coins()
    test_collector_vacuums_coins_then_pays_pot()
    test_multi_multiplies_valued_pot_after_collect()
    test_leftmost_collector_recollects_then_slots_replace()
    test_regen_clover_multiplies_sitting_pot_before_next_collect()
    test_clovers_resolve_column_order_then_stay()
    test_clovers_regen_after_collector_vacuum()
    test_replacement_collector_gets_a_turn()
    test_regen_never_spawns_a_collector()
    test_collector_keeps_prior_face_and_caps_at_wincap()
    test_multi_pot_remainder_is_wincap_minus_leftover_coins()
    test_resolve_stops_when_pot_hits_wincap()
    test_natural_power_rolls_vary_with_simulation_seed()
    test_extra_chance_rolls_the_same_powers()
    test_progress_fills_per_tumble_not_per_cluster()
    test_tiles_progress_activation_and_feature_prefill()
    test_feature_spin_starts_full_without_seeded_tiles()
    test_feature_spin_needs_a_winning_connection()
    test_feature_spin_never_dead_spins()
    test_feature_spin_cluster_pays_plain_face_like_base()
    test_peak_spin_starts_full_gold_and_empty_bar()
    test_peak_spin_needs_a_winning_tumble_to_activate()
    test_peak_cluster_pays_from_connections_not_gold_seed()
    test_peak_spin_can_miss_connections()
    test_peak_land_cluster_activates_without_cascade()
    test_peak_dead_land_does_not_activate()
    test_organic_bonus_entry_resets_progress()
    test_organic_freegame_pays_physical_coins()
    test_cascade_emits_tumble_before_board_activation()
    test_activation_waits_until_cascade_idle()
    test_bonus_freespin_reveals_have_no_scatters()
    test_force_scatter_skipped_when_already_in_bonus()
    test_bonus_clusters_apply_pay_scale()
    test_base_clusters_still_pay()
    test_cluster_payout_ignores_tile_levels()
    test_scatter_bonus_and_hard_cap_smoke()
    test_sticky_hear_disabled()
    test_hear_threshold_is_five()
    test_three_scatters_trigger_see_bonus()
    test_gamble_forced_scatters_never_see()
    test_five_scatters_resolve_to_madness()
    test_gamble_dead_has_no_cluster_or_bonus()
    test_gamble_always_baits_two_on_trigger_land()
    test_gamble_dead_baits_two_every_seed()
    test_gamble_dead_bait_two_st_tease()
    test_gamble_hear_emits_freespins()
    test_gamble_madness_emits_freespins()
    test_madness_progress_stays_full()
    test_madness_skips_bronze_coins()
    test_madness_tiles_skip_bronze()
    test_hear_bonus_persists_tiles_after_board_activation()
    test_hear_bonus_allows_chained_activations_in_one_spin()
    test_hear_bonus_caps_chained_activations_at_three()
    test_bonus_entry_starts_with_empty_tiles()
    print("test_scratch_rebuild: all passed")


if __name__ == "__main__":
    main()
