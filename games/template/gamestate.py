import os, sys
from game_override import *
from src.state.state import *
from src.events.events import (
    setTotalWinEvent,
    tumbleBoardEvent,
    setWinEvent,
    updateGlobalMultEvent,
)

if os.getcwd() not in sys.path:
    sys.path.append(os.getcwd())
from game_config import *
from game_executables import *
from game_calculations import *


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
