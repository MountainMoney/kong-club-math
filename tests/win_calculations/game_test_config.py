"""Game-specific configuration file, inherits from src/config/config.py"""

from src.config.distributions import Distribution
from src.config.betmode import BetMode


class GameConfig:
    """Testing game functions"""

    def __init__(self):
        super().__init__()
        self.game_id = "0_test_class"
        self.rtp = 0.9700

        # Game Dimensions
        self.num_reels = 5
        self.num_rows = [5] * self.num_reels
        # Board and Symbol Properties
        self.paytable = {(25, "W"): 100, (25, "H1"): 100}

        self.paylines = {
            1: [
                0,
                0,
                0,
                0,
                0,
            ],
            2: [
                0,
                1,
                2,
                1,
                2,
            ],
            3: [
                4,
                3,
                2,
                3,
                4,
            ],
            4: [
                4,
                4,
                4,
                4,
                4,
            ],
        }

        self.special_symbols = {"wild": ["W"], "scatter": ["S"], "multiplier": ["M"]}
