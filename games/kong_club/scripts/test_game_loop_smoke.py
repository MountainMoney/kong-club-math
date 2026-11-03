"""All-mode loop smoke: cascade must be idle before coins / setWin.

Fails Feature nibble books that abort after tumble 1 while a 5-cluster remains.
Peak is the exception (silent land, no cluster pay, no cascade).
"""

from __future__ import annotations

from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import sys

GAME_ROOT = Path(__file__).resolve().parents[1]
SDK_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SDK_ROOT))
sys.path.insert(0, str(GAME_ROOT))

from game_cluster import GameCluster
from game_config import GameConfig
from gamestate import GameState


def _types(book) -> list[str]:
    return [event["type"] for event in book.events]


def _event_name(cell) -> str:
    if isinstance(cell, dict):
        return str(cell.get("name") or "")
    return str(getattr(cell, "name", "") or "")


def board_from_result_board(gs: GameState, result_board: list) -> list:
    """Strip padding (top/bottom) so GameCluster sees the 6×5 playfield."""
    play = []
    rows = gs.config.num_rows[0]
    for reel, column in enumerate(result_board):
        cells = list(column or [])
        if gs.config.include_padding and len(cells) >= rows + 2:
            cells = cells[1 : 1 + rows]
        elif len(cells) > rows:
            cells = cells[:rows]
        play.append([gs.create_symbol(_event_name(cell)) for cell in cells])
    return play


def leftover_clusters(gs: GameState, result_board) -> list:
    if not result_board:
        return []
    board = board_from_result_board(gs, result_board)
    return GameCluster.find_winning_clusters(board, gs.config)


def tumble_stops(events: list[dict]) -> list[dict]:
    """Last tumbleBoard before each boardActivation or setWin."""
    last_tb = None
    stops = []
    for event in events:
        kind = event.get("type")
        if kind == "tumbleBoard":
            last_tb = event
        elif kind in ("boardActivation", "setWin") and last_tb is not None:
            stops.append(last_tb)
            last_tb = None
    return stops


def assert_no_leftover_clusters(gs: GameState, book, label: str) -> None:
    for stop in tumble_stops(book.events):
        leftover = leftover_clusters(gs, stop.get("resultBoard"))
        assert not leftover, (
            f"{label}: leftover 5-cluster after cascade stop "
            f"{GameCluster.format_cluster_log(leftover[0])}"
        )


def assert_activation_after_idle(types: list[str], label: str) -> None:
    if "boardActivation" not in types:
        return
    idx = types.index("boardActivation")
    before = types[:idx]
    if "tumbleBoard" not in before:
        return
    last_tb = len(before) - 1 - before[::-1].index("tumbleBoard")
    assert "winInfo" not in types[last_tb:idx], (
        f"{label}: winInfo after last tumble before boardActivation, "
        f"got {types[max(0, last_tb): idx + 2]}"
    )


def run_book(mode: str, criteria: str, seed: int) -> tuple[GameState, object]:
    GameConfig._instance = None
    gs = GameState(GameConfig())
    gs.betmode = mode
    gs.criteria = criteria
    with redirect_stdout(StringIO()):
        gs.run_spin(seed)
    return gs, gs.book


def smoke_feature_spin() -> None:
    multi_tumble = 0
    for criteria in ("nibble", "run"):
        for seed in range(20_000, 20_040):
            gs, book = run_book("feature_spin", criteria, seed)
            types = _types(book)
            label = f"feature_spin {criteria} seed={seed}"
            assert "dead_juicy" not in (gs.criteria, criteria)
            assert "winInfo" in types, f"{label}: missing winInfo"
            assert "tumbleBoard" in types, f"{label}: missing tumbleBoard"
            assert "boardActivation" in types, f"{label}: missing boardActivation"
            assert "setTotalWin" in types, f"{label}: missing setTotalWin"
            assert_activation_after_idle(types, label)
            assert_no_leftover_clusters(gs, book, label)
            idx = types.index("boardActivation")
            if types[:idx].count("tumbleBoard") >= 2:
                multi_tumble += 1
    assert multi_tumble >= 1, "feature_spin: need at least one 2+ tumble book before coins"


def smoke_base_modes() -> None:
    for mode, criteria, seeds in (
        ("base", "basegame", range(1, 21)),
        ("base_ante", "basegame", range(1, 16)),
        ("base", "freegame", range(100, 106)),
    ):
        for seed in seeds:
            gs, book = run_book(mode, criteria, seed)
            types = _types(book)
            label = f"{mode} {criteria} seed={seed}"
            assert "reveal" in types, f"{label}: missing reveal"
            assert "setTotalWin" in types, f"{label}: missing setTotalWin"
            assert_activation_after_idle(types, label)
            assert_no_leftover_clusters(gs, book, label)


def smoke_peak_spin() -> None:
    saw_dead = False
    saw_connect = False
    for criteria, seeds in (
        ("dead_juicy", range(1, 16)),
        ("nibble", range(1, 12)),
        ("run", range(1, 8)),
    ):
        for seed in seeds:
            gs, book = run_book("peak_spin", criteria, seed)
            types = _types(book)
            label = f"peak_spin {criteria} seed={seed}"
            assert "setTotalWin" in types, f"{label}: missing setTotalWin"
            assert "winInfo" not in types, f"{label}: Peak must not pay clusters"
            if "boardActivation" in types:
                saw_connect = True
                assert "tumbleBoard" not in types, f"{label}: Peak must not cascade"
            else:
                saw_dead = True
                assert "tumbleBoard" not in types, f"{label}: dead Peak must not tumble"
    assert saw_dead, "peak_spin: need a dead_juicy book"
    assert saw_connect, "peak_spin: need a connecting book"


def smoke_bonus_modes() -> None:
    for mode, criteria, seeds in (
        ("bonus_see", "bonus_see", range(1, 6)),
        ("bonus_hear", "bonus_hear", range(1, 6)),
    ):
        for seed in seeds:
            gs, book = run_book(mode, criteria, seed)
            types = _types(book)
            label = f"{mode} seed={seed}"
            assert "updateFreeSpin" in types or "freeSpinTrigger" in types, (
                f"{label}: missing FS counter / trigger"
            )
            assert "setTotalWin" in types, f"{label}: missing setTotalWin"
            assert_activation_after_idle(types, label)
            assert_no_leftover_clusters(gs, book, label)


def smoke_bonus_mystery() -> None:
    saw_dead = False
    saw_hear = False
    for criteria, seeds in (
        ("gamble_dead", range(1, 8)),
        ("gamble_hear", range(1, 6)),
    ):
        for seed in seeds:
            gs, book = run_book("bonus_mystery", criteria, seed)
            types = _types(book)
            label = f"bonus_mystery {criteria} seed={seed}"
            assert "setTotalWin" in types, f"{label}: missing setTotalWin"
            assert_no_leftover_clusters(gs, book, label)
            if "freeSpinTrigger" in types or any(
                event.get("type") == "kongClubMode"
                and str(event.get("state", "")).startswith("start_bonus_")
                for event in book.events
            ):
                saw_hear = True
            else:
                saw_dead = True
    assert saw_dead, "bonus_mystery: need a dead book"
    assert saw_hear, "bonus_mystery: need a Hear trigger book"


def main() -> None:
    smoke_feature_spin()
    smoke_base_modes()
    smoke_peak_spin()
    smoke_bonus_modes()
    smoke_bonus_mystery()
    print("test_game_loop_smoke: all passed")


if __name__ == "__main__":
    main()
