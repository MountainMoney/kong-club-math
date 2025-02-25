"""Define relevant paths to games, logic engine and optimization."""

import os

ABS_PATH = os.path.abspath("../")
ABS_PATH = ABS_PATH.replace("\\", "/")

PATH_TO_ENGINE = os.path.join(ABS_PATH, "CarrotMathEngine")
PATH_TO_GAMES = os.path.join(PATH_TO_ENGINE, "games/")
