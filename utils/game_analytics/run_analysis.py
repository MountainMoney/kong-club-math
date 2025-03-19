"""Print .xlsx format summary document.
Args:
    - game-id, must match folder_name in src/games/<game-id>
    - Define search keys as listed in force_record_<mode>.json file. Partial keys in the force-file are matched to search keys

"""

from typing import List, Dict
from utils.game_analytics.retrieve_game_information import GameInformation
from utils.game_analytics.print_all_results import PrintJSON, PrintXLSX


def run(game: str, custom_keys: List[Dict] = None):
    """Function executed from run file."""
    game_obj = GameInformation(game, custom_keys=custom_keys)
    PrintJSON(game_obj)
    PrintXLSX(game_obj)


# if __name__ == "__main__":

#     game_to_analyze = "0_0_lines"
#     user_keys = [
#         {"symbol": "scatter"},
#         {"symbol": "scatter", "kind": 3},
#         {"symbol": "scatter", "kind": 4},
#         {"symbol": "scatter", "kind": 5},
#     ]
#     game_object = GameInformation(game_id=game_to_analyze, custom_keys=user_keys)
#     PrintJSON(game_object)
#     PrintXLSX(game_object)
#     print("Printed All Data Successfully.")
