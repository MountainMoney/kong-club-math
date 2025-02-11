import os, sys
from game_override import GameStateOverride

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())


class GameState(GameStateOverride):

    def run_spin(self, sim):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()

            self.evaluate_finalwin()

        self.imprint_wins()

    def run_freespin(self):
        self.reset_fs_spin()
        pass
