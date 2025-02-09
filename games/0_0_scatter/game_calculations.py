import sys
sys.path.append('./')
from src.executables.executables import Executables

class GameCalculations(Executables):

    def get_board_multipliers(self, multiplier_key: str = "multiplier") -> list:
        board_mult = 0
        num_mults = 0
        mult_info = []
        for reel in range(len(self.board)):
            for row in range(len(self.board[reel])):
                if self.board[reel][row].check_attribute(multiplier_key):
                    board_mult += self.board[reel][row].get_attribute(multiplier_key)
                    num_mults += 1
                    mult_info.append({'reel': reel, 'row': row, 'value': self.board[reel][row].get_attribute(multiplier_key)})
    
        return max(1, board_mult), mult_info