from tests.win_calculations.game_test_config import GameConfig
from src.state.state import GeneralGameState
from src.calculations.scatter import Scatter
from src.calculations.symbol import Symbol
from src.calculations.board import Board


class TestGamestate(GeneralGameState):
    """Simple gamestate setup with abstract methods defined."""

    def __init__(self, config):
        self.config = config

    def assign_special_sym_function(self):
        self.special_symbol_functions = {
            "M": [self.assign_mult_property],
        }

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


def create_test_gamestate():
    """Boilerplate gamestate for testing."""
    test_config = GameConfig()
    test_gamestate = TestGamestate(test_config)
    test_gamestate.create_symbol_map()
    test_gamestate.assign_special_sym_function()

    return test_gamestate


def test_scatterpay():
    gamestate = create_test_gamestate()
    gamestate.board = [
        [[] for _ in range(gamestate.config.num_rows[x])] for x in range(gamestate.config.num_reels)
    ]
    for idx, _ in enumerate(gamestate.board):
        for idy, _ in enumerate(gamestate.board[idx]):
            if idy == 0:
                gamestate.board[idx][idy] = gamestate.create_symbol("W")
            else:
                gamestate.board[idx][idy] = gamestate.create_symbol("H1")

    windata = Scatter.get_scatterpay_wins(gamestate.config, gamestate.board, global_multiplier=1)

    print(gamestate)


test_scatterpay()
