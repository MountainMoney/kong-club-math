from game_calculations import GameCalculations
from game_events import updateGridMultiplierEvent

class GameExecutables(GameCalculations):

    def reset_grid_mults(self):
        self.position_multipliers = [[1 for _ in range(self.config.num_rows[reel])] for reel in range(self.config.num_reels)]

    def update_grid_mults(self):
        if self.win_data['totalWin'] > 0:
            for win in self.win_data['wins']:
                for pos in win['positions']:
                    self.position_multipliers[pos['reel']][pos['row']] *= 2
            updateGridMultiplierEvent(self)





























