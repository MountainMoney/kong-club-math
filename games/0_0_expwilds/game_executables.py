from .game_calculations import GameCalculations
from src.calculations.statistics import get_random_outcome
from src.events.events import reveal_event
import random


class GameExecutables(GameCalculations):
    """Executable functions used for expanding wild game."""

    def update_with_existing_wilds(self) -> None:
        """Replace drawn boards with existing sticky-wilds."""
        for reel, _ in enumerate(self.expanding_wilds):
            if len(self.expanding_wilds[reel]) > 0:
                for row, _ in enumerate(self.board[self.expanding_wilds[reel][0]["reel"]]):
                    self.board[reel][row] = self.create_symbol("W")
                    self.board[reel][row].assign_attribute({"mult": self.expanding_wilds[reel][0]["mult"]})

        reveal_event(self)

    def assign_new_wilds(self, max_num_new_wilds: int):
        """Assign unused reels to have sticky symbol."""
        for _ in range(max_num_new_wilds):
            if len(self.avaliable_reels) > 0:
                chosen_reel = random.choice(self.avaliable_reels)
                self.avaliable_reels.remove(chosen_reel)
                wr_mult = get_random_outcome(
                    self.get_current_distribution_conditions()["mult_values"][self.gametype]
                )
                chosen_row = random.choice([i for i in range(self.config.num_rows[chosen_reel])])
                expwild_details = {"reel": chosen_reel, "row": chosen_row, "mult": wr_mult}
                self.expanding_wilds[chosen_reel].append(expwild_details)
