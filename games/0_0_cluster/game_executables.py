from game_calculations import GameCalculations
from game_events import updateGridMultiplierEvent


class GameExecutables(GameCalculations):

    def reset_grid_mults(self):
        self.position_multipliers = [
            [0 for _ in range(self.config.num_rows[reel])] for reel in range(self.config.num_reels)
        ]

    def reset_grid_bool(self):
        self.position_bool = [
            [False for _ in range(self.config.num_rows[reel])] for reel in range(self.config.num_reels)
        ]

    def update_grid_mults(self):
        """All positions start with 1x. If there is a win in that position, the grid point
        is 'activated' and all subsequent wins on that position will double the grid value."""
        if self.win_data["totalWin"] > 0:
            for win in self.win_data["wins"]:
                for pos in win["positions"]:
                    if self.position_multipliers[pos["reel"]][pos["row"]] == 0:
                        self.position_multipliers[pos["reel"]][pos["row"]] = 1
                    else:
                        self.position_multipliers[pos["reel"]][pos["row"]] *= 2
                        self.position_multipliers[pos["reel"]][pos["row"]] = min(
                            self.position_multipliers[pos["reel"]][pos["row"]], self.config.maximum_board_mult
                        )
            updateGridMultiplierEvent(self)
