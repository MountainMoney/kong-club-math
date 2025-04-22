"""Test basic ways-calculation functionality."""

import pytest
from tests.win_calculations.game_test_config import GamestateTest, create_blank_board
from src.calculations.ways import Ways


class GameWaysConfig:
    """Testing game functions"""

    def __init__(self):
        self.game_id = "0_test_class"
        self.rtp = 0.9700

        # Game Dimensions
        self.num_reels = 5
        self.num_rows = [3] * self.num_reels
        # Board and Symbol Properties
        self.paytable = {
            (5, "H1"): 70,
            (4, "H1"): 60,
            (3, "H1"): 50,
            (5, "H2"): 30,
            (4, "H2"): 20,
            (3, "H2"): 10,
        }

        self.special_symbols = {"wild": ["W"], "scatter": ["S"], "blank": ["X"]}
        self.bet_modes = []
        self.basegame_type = "basegame"
        self.freegame_type = "freegame"


def create_test_lines_gamestate():
    """Boilerplate gamestate for testing."""
    test_config = GameWaysConfig()
    test_gamestate = GamestateTest(test_config)
    test_gamestate.create_symbol_map()
    test_gamestate.assign_special_sym_function()
    test_gamestate.board = create_blank_board(test_config.num_reels, test_config.num_rows)

    return test_gamestate


@pytest.fixture
def gamestate():
    """Initialise test state."""
    return create_test_lines_gamestate()


def test_basic_ways(gamestate):
    totalWays = len(gamestate.board[0]) ** len(gamestate.board)  # Assume all reels have equal rows
    for idx, _ in enumerate(gamestate.board):
        for idy, _ in enumerate(gamestate.board[idx]):
            if idx < len(gamestate.board) - 1:
                gamestate.board[idx][idy] = gamestate.create_symbol("H1")
            else:
                gamestate.board[idx][idy] = gamestate.create_symbol("W")

    windata = Ways.get_ways_data(gamestate.config, gamestate.board)
    assert windata["totalWin"] == totalWays * gamestate.config.paytable[(5, "H1")]


def test_mixed_ways(gamestate):
    sym1Ways = (len(gamestate.board[0]) - 1) ** len(gamestate.board)
    sym2Ways = 1
    for idx, _ in enumerate(gamestate.board):
        for idy, _ in enumerate(gamestate.board[idx]):
            if idy == 0:
                gamestate.board[idx][idy] = gamestate.create_symbol("H1")
            else:
                gamestate.board[idx][idy] = gamestate.create_symbol("H2")

    windata = Ways.get_ways_data(gamestate.config, gamestate.board)
    assert windata["wins"][0]["meta"]["ways"] == sym2Ways
    assert windata["wins"][1]["meta"]["ways"] == sym1Ways
    assert windata["totalWin"] == windata["wins"][0]["win"] + windata["wins"][1]["win"]
