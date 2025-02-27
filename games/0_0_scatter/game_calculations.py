"""Scatter pays game calculations"""

from src.executables.executables import Executables


class GameCalculations(Executables):
    """Game specific calculations for Scatter sample game."""

    def get_board_multipliers(self, multiplier_key: str = "multiplier") -> list:
        """Find multiplier from board using winning positions."""
        board_mult = 0
        mult_info = []
        for reel, _ in enumerate(self.board):
            for row, _ in enumerate(self.board[reel]):
                if self.board[reel][row].check_attribute(multiplier_key):
                    board_mult += self.board[reel][row].get_attribute(multiplier_key)
                    mult_info.append(
                        {"reel": reel, "row": row, "value": self.board[reel][row].get_attribute(multiplier_key)}
                    )

        return max(1, board_mult), mult_info
