"""Define relevant paths to games, logic endine and optimisation."""

import os

ABS_PATH = os.path.abspath("../")
ABS_PATH = ABS_PATH.replace("\\", "/")

PATH_TO_ENGINE = os.path.join(ABS_PATH, "zuck-engine")
PATH_TO_GAMES = os.path.join(PATH_TO_ENGINE, "games/")
