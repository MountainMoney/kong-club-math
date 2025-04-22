from tests.win_calculations.game_test_config import GameConfig
from src.state.state import GeneralGameState
from src.calculations.scatter import Scatter


class GamestateTest(GeneralGameState):
    """Simple gamestate setup with abstract methods defined."""

    def __init__(self, config):
        super().__init__(config)
        self.config = config

    def assign_special_sym_function(self):
        self.special_symbol_functions = {"M": [self.assign_mult_property], "WM": [self.assign_mult_property]}

    def assign_mult_property(self, symbol) -> dict:
        symbol.assign_attribute({"multiplier": 3})

    def create_symbol(self, name: str) -> object:
        if name not in self.symbol_storage.symbols:
            raise ValueError(f"Symbol '{name}' is not registered.")
        symObject = self.symbol_storage.create_symbol_state(name)
        if name in self.special_symbol_functions:
            for func in self.special_symbol_functions[name]:
                func(symObject)

        return symObject

    def run_spin(self):
        pass

    def run_freespin(self):
        pass


def create_blank_board(reels, rows):
    board = [[[] for _ in range(rows[x])] for x in range(reels)]
    return board


def create_test_gamestate():
    """Boilerplate gamestate for testing."""
    test_config = GameConfig()
    test_gamestate = GamestateTest(test_config)
    test_gamestate.create_symbol_map()
    test_gamestate.assign_special_sym_function()
    test_gamestate.board = create_blank_board(test_config.num_reels, test_config.num_rows)

    return test_gamestate


def test_scatterpay_nowilds():
    gamestate = create_test_gamestate()
    for idx, _ in enumerate(gamestate.board):
        for idy, _ in enumerate(gamestate.board[idx]):
            gamestate.board[idx][idy] = gamestate.create_symbol("H1")

    windata = Scatter.get_scatterpay_wins(gamestate.config, gamestate.board, global_multiplier=1)

    assert windata["totalWin"] == 80


def test_scatterpay_mults():
    """Test wins with multipliers"""
    gamestate = create_test_gamestate()
    mult_count = 0
    for idx, _ in enumerate(gamestate.board):
        for idy, _ in enumerate(gamestate.board[idx]):
            # if idx % 2 == 0:
            # gamestate.board[idx][idy] = gamestate.create_symbol("H1")
            if (idx + idy) % 5 == 0:
                gamestate.board[idx][idy] = gamestate.create_symbol("WM")
                mult_count += 1
            else:
                gamestate.board[idx][idy] = gamestate.create_symbol("H1")

    windata = Scatter.get_scatterpay_wins(gamestate.config, gamestate.board, global_multiplier=1)
    print(windata)


def test_scatterpay_wilds():
    gamestate = create_test_gamestate()
    for idx, _ in enumerate(gamestate.board):
        for idy, _ in enumerate(gamestate.board[idx]):
            if idx == 0:
                gamestate.board[idx][idy] = gamestate.create_symbol("W")
            elif idx == 1:
                gamestate.board[idx][idy] = gamestate.create_symbol("H2")
            else:
                gamestate.board[idx][idy] = gamestate.create_symbol("H1")

    windata = Scatter.get_scatterpay_wins(gamestate.config, gamestate.board, global_multiplier=1)

    for wd in windata["wins"]:
        if wd["symbol"] == "H1":
            assert wd["win"] == 50
        elif wd["symbol"] == "H2":
            assert wd["win"] == 3

    assert windata["totalWin"] == 53


if __name__ == "__main__":

    test_scatterpay_mults()
    test_scatterpay_nowilds()
    test_scatterpay_wilds()
