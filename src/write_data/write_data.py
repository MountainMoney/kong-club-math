"""Handles writing all game game files"""

import time
import hashlib
import json
import ast
from multiprocessing import Process, Manager
import zstandard
import cProfile
from collections import defaultdict
from warnings import warn
import shutil
import asyncio
from typing import Dict
import os

from src.calculations.statistics import *
from src.config.paths import *


def get_sha_256(file_to_hash: str):
    """Get human readable hash of file."""
    try:
        with open(file_to_hash, "rb") as f:
            sha256_file = hashlib.sha256()
            while True:
                data = f.read(65536)
                if not data:
                    break
                sha256_file.update(data)
        sha256_hexRep = sha256_file.hexdigest()
    except:
        warn(f"{file_to_hash} is empty.\nCould not create hash")
        sha256_hexRep = ""
    return sha256_hexRep


def makeForceJson(gamestate: object):
    """Construct fore-file from recorded description keys."""
    folder_path = gamestate.config.force_path
    force_file_path = str.join("/", [folder_path, "force.json"])

    if os.path.isfile(force_file_path) and os.path.getsize(force_file_path) > 0:
        try:
            with open(force_file_path, "r", encoding="utf-8") as forcefile:
                force_data = json.load(forcefile)
        except json.JSONDecodeError:
            print("Error decoding JSON: The file may be corrupted or empty.")
            force_data = {}
    else:
        force_data = {}

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        if os.path.isfile(file_path) and filename.endswith(".json") and filename.startswith("force_for_rob_"):
            with open(file_path, mode="r", encoding="utf-8") as file:
                data = json.load(file)

                modename = filename[len("force_for_rob_") : -len(".json")]
                force_data[modename] = {}

                if isinstance(data, list):
                    for item in data:
                        for key, value in item["search"].items():
                            if key not in force_data[modename]:
                                force_data[modename][key] = []
                            if value not in force_data[modename][key]:
                                force_data[modename][key] += [value]
                else:
                    print("Expected a list, found:", type(data))

    with open(force_file_path, "w", encoding="utf-8") as forcefile:
        json.dump(force_data, forcefile, indent=4)


def get_force_options(force_results: dict):
    """Return JSON ready force keys."""
    force_keys = defaultdict(set)
    for force in force_results.keys():
        for key, val in force:
            force_keys[str(key)].add(val)
    return {key: list(val) for key, val in force_keys.items()}


def make_lookup_tables(gamestate: object, name: str):
    """Write lookup tables for all simulations."""
    file = open(str.join("/", [gamestate.config.temp_path, name]), "w")
    sims = list(gamestate.library.keys())
    sims.sort()
    for sim in sims:
        file.write(
            "{},1,{:.2f}\n".format(gamestate.library[sim]["id"], gamestate.library[sim]["payoutMultiplier"])
        )
    file.close()


def make_lookup_to_criteria(gamestate: object, name: str):
    """Record distribution criteria for a given simulation."""
    file = open(str.join("/", [gamestate.config.temp_path, name]), "w")
    sims = list(gamestate.library.keys())
    sims.sort()
    for sim in sims:
        file.write(str(gamestate.library[sim]["id"]) + "," + str(gamestate.library[sim]["criteria"]) + "\n")
    file.close()


def make_lookup_pay_split(gamestate: object, name: str):
    """Record win values from basegame and freegame types."""
    file = open(str.join("/", [gamestate.config.temp_path, name]), "w")
    sims = list(gamestate.library.keys())
    sims.sort()
    for sim in sims:
        file.write(
            str(gamestate.library[sim]["id"])
            + ","
            + str(round(gamestate.library[sim]["baseGameWins"], 2))
            + ","
            + str(round(gamestate.library[sim]["freeGameWins"], 2))
            + "\n"
        )
    file.close()


def write_library_events(gamestate: object, library: list, gametype: str):
    """Write all unique events within a given mode - with one example application."""
    unique_event = []
    event_items = {}
    for event in library:
        for instance in event["events"]:
            lib_event = instance["type"]
            if lib_event not in unique_event:
                unique_event.append(lib_event)
                item_keys = instance.keys()
                dict_details = {key: instance[key] for key in item_keys if key != "index"}
                event_items[lib_event] = dict_details
    json_object = json.dumps(event_items, indent=4)
    with open(
        str.join("/", [gamestate.config.config_path, "event_config_" + gametype + ".json"]),
        "w",
    ) as f:
        f.write(json_object)


def output_lookup_and_force_files(
    threads: int,
    batching_size: int,
    game_id: str,
    betmode: str,
    gamestate: object,
    num_sims: int = 1000000,
    compress: bool = True,
):
    """Combine temporary lookup tables and force files into a single output."""
    print("Saving books for", game_id, "in", betmode)
    num_repeats = max(int(round(num_sims / threads / batching_size, 0)), 1)
    file_list = []
    for repeat_index in range(num_repeats):
        for thread in range(threads):
            file_list.append(
                str.join(
                    "/",
                    [
                        gamestate.config.temp_path,
                        "books_"
                        + betmode
                        + "_"
                        + str(thread)
                        + "_"
                        + str(repeat_index)
                        + ".json"
                        + ".zst" * compress,
                    ],
                )
            )

    if compress:
        with open(
            str.join(
                "/",
                [
                    gamestate.config.compressed_path,
                    "books_" + betmode + ".json.zst",
                ],
            ),
            "wb",
        ) as outfile:
            for filename in file_list:
                with open(filename, "rb") as infile:
                    outfile.write(infile.read())
    else:
        with open(
            str.join("/", [gamestate.config.book_path, "books_" + betmode + ".json"]),
            "w",
        ) as outfile:
            for filename in file_list:
                with open(filename, "r") as infile:
                    outfile.write(infile.read())

    print("Saving force files for", game_id, "in", betmode)
    force_results_dict = {}
    file_list = []
    for repeat_index in range(num_repeats):
        for thread in range(threads):
            file_list.append(
                str.join(
                    "/",
                    [
                        gamestate.config.temp_path,
                        "force_" + betmode + "_" + str(thread) + "_" + str(repeat_index) + ".json",
                    ],
                )
            )

    for filename in file_list:
        force_chunk = ast.literal_eval(json.load(open(filename, "r")))
        for key in force_chunk:
            if force_results_dict.get(key) != None:
                force_results_dict[key]["timesTriggered"] += force_chunk[key]["timesTriggered"]
                force_results_dict[key]["bookIds"] += force_chunk[key]["bookIds"]
            else:
                force_results_dict[key] = force_chunk[key]

    force_results_dict_just_for_rob = []
    for force_combination in force_results_dict:
        search_dict = {}
        for key in force_combination:
            search_dict[key[0]] = key[1]
        force_dict = {
            "search": search_dict,
            "timesTriggered": force_results_dict[force_combination]["timesTriggered"],
            "bookIds": force_results_dict[force_combination]["bookIds"],
        }
        force_results_dict_just_for_rob.append(force_dict)
    json_object_for_rob = json.dumps(force_results_dict_just_for_rob, indent=4)
    file = open(
        str.join("/", [gamestate.config.force_path, "force_for_rob_" + betmode + ".json"]),
        "w",
    )
    file.write(json_object_for_rob)
    file.close()

    forceResultKeys = get_force_options(force_results_dict)
    json_file_path = str.join("/", [gamestate.config.force_path, "force.json"])
    try:
        with open(json_file_path, "r") as file:
            data = json.load(file)
    except:
        data = {}
    data[gamestate.get_current_betmode().get_name()] = forceResultKeys
    json_object = json.dumps(data, indent=4)
    file = open(str.join("/", [gamestate.config.force_path, "force.json"]), "w")
    file.write(json_object)
    file.close()
    weights_plus_wins_file_list = []
    id_to_criteria_file_list = []
    segmented_lut_file_list = []
    print("Saving LUTs for", game_id, "in", betmode)
    for repeat_index in range(num_repeats):
        for thread in range(threads):
            weights_plus_wins_file_list += [
                str.join(
                    "/",
                    [
                        gamestate.config.temp_path,
                        "lookUpTable_" + betmode + "_" + str(thread) + "_" + str(repeat_index),
                    ],
                )
            ]
            id_to_criteria_file_list += [
                str.join(
                    "/",
                    [
                        gamestate.config.temp_path,
                        "lookUpTableIdToCriteria_" + betmode + "_" + str(thread) + "_" + str(repeat_index),
                    ],
                )
            ]
            segmented_lut_file_list += [
                str.join(
                    "/",
                    [
                        gamestate.config.temp_path,
                        "lookUpTableSegmented_" + betmode + "_" + str(thread) + "_" + str(repeat_index),
                    ],
                )
            ]
    with open(
        str.join("/", [gamestate.config.lookup_path, "lookUpTable_" + betmode + ".csv"]),
        "w",
    ) as outfile:
        for filename in weights_plus_wins_file_list:
            with open(filename, "r") as infile:
                outfile.write(infile.read())
    with open(
        str.join(
            "/",
            [gamestate.config.lookup_path, "lookUpTableSegmented_" + betmode + ".csv"],
        ),
        "w",
    ) as outfile:
        for filename in segmented_lut_file_list:
            with open(filename, "r") as infile:
                outfile.write(infile.read())
    with open(
        str.join(
            "/",
            [
                gamestate.config.lookup_path,
                "lookUpTableIdToCriteria_" + betmode + ".csv",
            ],
        ),
        "w",
    ) as outfile:
        for filename in id_to_criteria_file_list:
            with open(filename, "r") as infile:
                outfile.write(infile.read())


def write_json(
    gamestate: object,
    library: dict,
    name: str,
    frist_file_write: bool,
    last_file_write: bool,
    compress: bool,
):
    """Convert the list of dictionaries to a JSON-encoded string and compress it in chunks."""
    chunk = json.dumps(library)
    if not (frist_file_write):
        chunk = chunk[1:]
    if not (last_file_write):
        chunk = chunk[:-1] + ","
    if compress:
        file = open(str.join("/", [gamestate.config.library_path, name + ".zst"]), "wb")
        compressed_chunk = zstandard.compress(chunk.encode("utf-8"))
        file.write(compressed_chunk)
    else:
        file = open(str.join("/", [gamestate.config.library_path, name]), "w")
        file.write(chunk)
    file.close()


def print_recorded_wins(gamestate: object, name: str = ""):
    """Temporary file generation for wins/recorded results."""
    json_object = json.dumps(str(gamestate.recorded_events), indent=4)
    file = open(str.join("/", [gamestate.config.temp_path, "force_" + name + ".json"]), "w")
    file.write(json_object)
    file.close()


def create_books(
    gamestate: object,
    config: object,
    num_sim_args: dict,
    batch_size: int,
    threads: int,
    compress: bool,
    profiling: bool,
):
    """Main run-function for simulating game outcomes and outputting all files."""
    for ns in num_sim_args.values():
        if all([ns > 0, ns > batch_size * batch_size]):
            assert (
                ns % (threads * batch_size) == 0
            ), "mode-sims/(batch * threads) must be divisible with no remainder"

    if not compress and sum(num_sim_args.values()) > 1e4:
        warn("Generating large number of uncompressed books!")

    if profiling and threads > 1:
        raise RuntimeError("Multithread profiling not supported, threads must = 1 with profiling enabled")

    startTime = time.time()
    print("\nCreating books...")
    for betmode_name in num_sim_args:
        if num_sim_args[betmode_name] > 0:
            gamestate.betmode = betmode_name
            run_multi_process_sims(
                threads,
                batch_size,
                config.game_id,
                betmode_name,
                gamestate,
                num_sims=num_sim_args[betmode_name],
                compress=compress,
                write_event_list=config.write_event_list,
                profiling=profiling,
            )
            output_lookup_and_force_files(
                threads,
                batch_size,
                config.game_id,
                betmode_name,
                gamestate,
                num_sims=num_sim_args[betmode_name],
                compress=compress,
            )  # , write_event_list=config.write_event_list)
    shutil.rmtree(config.temp_path)
    print("\nFinished creating books in", time.time() - startTime, "seconds.\n")


def get_sim_splits(gamestate: object, num_sims: int, betmode_name: str) -> Dict[str, int]:
    """Ensure assignment of criteria to all simulations numbers."""
    betmode_distributions = gamestate.get_betmode(betmode_name).get_distributions()
    num_sims_criteria = {d._criteria: max(int(num_sims * d._quota), 1) for d in betmode_distributions}
    total_sims = sum(num_sims_criteria.values())
    reduce_sims = total_sims > num_sims
    listedCriteria = [d._criteria for d in betmode_distributions]
    criteria_weights = [d._quota for d in betmode_distributions]
    random.seed(0)
    while sum(num_sims_criteria.values()) != num_sims:
        c = random.choices(listedCriteria, criteria_weights)[0]
        if reduce_sims and num_sims_criteria[c] > 1:
            num_sims_criteria[c] -= 1
        elif not reduce_sims:
            num_sims_criteria[c] += 1

    return num_sims_criteria


def assign_sim_criteria(num_sims_criteria: Dict[str, int], sims: int) -> Dict[int, str]:
    """Assign criteria randomly to simulations based on quota defined in config."""
    simAllocation = [criteria for criteria, count in num_sims_criteria.items() for _ in range(count)]
    random.shuffle(simAllocation)
    return {i: simAllocation[i] for i in range(min(sims, len(simAllocation)))}


async def profile_and_visualize(
    game_id,
    gamestate,
    all_betmode_configs,
    betmode,
    sim_allocation,
    threads,
    num_repeats,
    sims_per_thread,
    repeat,
    compress,
    write_event_list,
):
    """Create flame-graph, automatically opens output on localhost."""
    output_string = f"games/{game_id}/simulationProfile_{betmode}.prof"
    cProfile.runctx(
        "gamestate.run_sims(all_betmode_configs, betmode, sim_allocation, threads, num_repeats, sims_per_thread, 0, repeat, compress, write_event_list)",
        globals(),
        locals(),
        output_string,
    )
    await asyncio.create_subprocess_exec("snakeviz", output_string)


def run_multi_process_sims(
    threads: int,
    batching_size: int,
    game_id: str,
    betmode: str,
    gamestate: object,
    num_sims: int = 1000000,
    compress: bool = True,
    write_event_list: bool = False,
    profiling: bool = False,
):
    """Setup multiprocessing manager for running all game-mode simulations."""
    print("\nCreating books for", game_id, "in", betmode)
    num_repeats = max(int(round(num_sims / threads / batching_size, 0)), 1)
    sims_per_thread = int(num_sims / threads / num_repeats)
    num_sims_criteria = get_sim_splits(gamestate, num_sims, betmode)
    sim_allocation = assign_sim_criteria(num_sims_criteria, num_sims)
    for repeat in range(num_repeats):
        print("Batch", repeat + 1, "of", num_repeats)
        processes = []
        manager = Manager()
        all_betmode_configs = manager.list()
        if profiling:
            asyncio.run(
                profile_and_visualize(
                    game_id=game_id,
                    gamestate=gamestate,
                    all_betmode_configs=all_betmode_configs,
                    betmode=betmode,
                    sim_allocation=sim_allocation,
                    threads=threads,
                    num_repeats=num_repeats,
                    sims_per_thread=sims_per_thread,
                    repeat=repeat,
                    compress=compress,
                    write_event_list=write_event_list,
                )
            )
        elif threads == 1:
            gamestate.run_sims(
                all_betmode_configs,
                betmode,
                sim_allocation,
                threads,
                num_repeats,
                sims_per_thread,
                0,
                repeat,
                compress,
                write_event_list,
            )
        else:
            for thread in range(threads):
                process = Process(
                    target=gamestate.run_sims,
                    args=(
                        all_betmode_configs,
                        betmode,
                        sim_allocation,
                        threads,
                        num_repeats,
                        sims_per_thread,
                        thread,
                        repeat,
                        compress,
                        write_event_list,
                    ),
                )
                print("Started thread", thread)
                process.start()
                processes += [process]
            print("All threads are online.")
            for process in processes:
                process.join()
            print("Finished joining threads.")
            gamestate.combine(all_betmode_configs, betmode)
            gamestate.get_betmode(betmode).lock_force_keys()
