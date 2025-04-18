"""Define relevant paths to games, logic engine and optimization."""

import os

ABS_PATH = os.path.abspath(os.getcwd())
PROJECT_PATH = os.path.abspath(os.getcwd())
PATH_TO_ENGINE = PROJECT_PATH
PATH_TO_GAMES = os.path.join(PROJECT_PATH, "games")
OPTIMIZATION_PATH = os.path.join(PROJECT_PATH, "optimization_program")
SETUP_PATH = os.path.join(OPTIMIZATION_PATH, "src", "setup.txt")
