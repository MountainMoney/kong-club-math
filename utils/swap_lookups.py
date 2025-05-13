"""Utility function for replacing default lookup table with outputs from optimization tool."""

from pathlib import Path
import argparse
import sys
import os
import json

ABS_PATH = Path(__file__).parent.parent
sys.path.append(ABS_PATH)
os.chdir(ABS_PATH)


def swap_tables(game_name: str, game_mode: str, target_file_number: int):
    """Replace default optimization table."""

    target_file = game_mode + "_0_" + str(target_file_number) + ".csv"
    lut_name = str.join("_", ["lookUpTable", game_mode, "0.csv"])
    new_lut_file = os.path.join("library", "publish_files", lut_name)
    new_opt_file = os.path.join("library", "optimization_files", target_file)

    start_recording = False
    new_lut = open(new_lut_file, "w", encoding="UTF-8")

    with open(new_opt_file, "r", encoding="UTF-8") as file:
        for line in file:
            if start_recording:
                new_lut.write(line)
            if line.strip() == "Distribution":
                start_recording = True

    new_lut.close()


def process_many_files(game_id, file_dict: dict) -> None:
    """Swap out multiple optimization files."""
    assert isinstance(file_dict, dict), "Multiple inputs must be of the form {'mode1': number1,  'mode2': number2}"

    for mode, val in file_dict.items():
        swap_tables(game_id, mode, val)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument("-g", dest="game_id", type=str, help="Enter str format for game_id: '0_0_0'")
    parser.add_argument("-m", dest="game_mode", type=str, help="Enter str format: 'base', 'bonus', etc... ")
    parser.add_argument("-n", dest="table_number")

    # Alter multiple files
    parser.add_argument("-d", dest="args_dict", type=str, help="Must pass JSON string: '{'mode':num, ...}'")

    arguments = parser.parse_args()

    if arguments.args_dict is not None:
        args_dict = json.loads(arguments.args_dict)
        print(args_dict)
        process_many_files(arguments.game_id, args_dict)
    else:
        swap_tables(arguments.game_id, arguments.game_mode, arguments.table_number)
