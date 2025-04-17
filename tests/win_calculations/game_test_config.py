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
        self.paytable = {
            (25, "W"): 100,
            (20, "W"): 80,
            (15, "W"): 50,
            (25, "H1"): 80,
            (20, "H1"): 50,
            (15, "H1"): 20,
            (10, "H1"): 10,
            (25, "H2"): 70,
            (20, "H2"): 15,
            (15, "H2"): 5,
            (10, "H2"): 3,
        }

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

        self.bet_modes = []
        self.basegame_type = "basegame"
        self.freegame_type = "freegame"
