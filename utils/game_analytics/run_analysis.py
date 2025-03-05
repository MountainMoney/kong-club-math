"""Print .xlsx format summary document.
Args:
    - game-id, must match folder_name in src/games/<game-id>
    - Define search keys as listed in force_record_<mode>.json file. Partial keys in the force-file are matched to search keys
    """

from utils.game_analytics.retrieve_game_information import GameInformation
from utils.game_analytics.print_all_results import PrintJSON, PrintXLSX


if __name__ == "__main__":

    game_to_analyse = "0_0_lines"
    custom_keys = [{"symbol": "scatter"}]
    GameObject = GameInformation(game_to_analyse, custom_keys=custom_keys)

    PrintObject = PrintJSON(GameObject)
    PrintXLSX(GameObject)
    print("Printed All Data Successfully.")
