import json
from src.config.paths import PATH_TO_GAMES, SETUP_PATH


class OptimizationExecution:
    """Handles execution of Rust optimization algorithm from python."""

    @staticmethod
    def load_math_config(filename: str) -> dict:
        """Load optimsation parameter config file."""
        return json.load(open(filename, "r", encoding="UTF-8"))

    @staticmethod
    def run_opt_single_mode(gamestate, mode, threads):

        filename = str.join("/", [gamestate.config.config_path, "math_config.json"])
        opt_config = OptimizationExecution.load_math_config(filename)

        mode_details = None
        for m in opt_config["bet_modes"]:
            if m["bet_mode"] == mode:
                mode_details = m

        assert mode_details is not None, "Could not load optimization parameters."

        params = mode_details["opt_params"]
        setup_file = open(SETUP_PATH, "w", encoding="UTF-8")
        setup_file.write("game_name;" + gamestate.config.game_id + "\n")
        setup_file.write("bet_type;" + mode + "\n")
        setup_file.write("num_show_pigs;" + str(params["num_show_pigs"]) + "\n")
        setup_file.write("num_pigs_per_fence;" + str(params["num_pigs_per_fence"]) + "\n")
        setup_file.write("threads_for_fence_construction;" + str(threads) + "\n")
        setup_file.write("threads_for_show_construction;" + str(threads) + "\n")
        setup_file.write("score_type;" + params["score_type"] + "\n")
        setup_file.write("test_spins;" + str(params["test_spins"]) + "\n")
        setup_file.write("test_spins_weights;" + str(params["test_spins_weights"]) + "\n")
        setup_file.write("simulation_trials;" + str(params["simulation_trials"]) + "\n")
        setup_file.write("graph_indexes;" + str(0) + "\n")
        setup_file.write("run_1000_batch;" + str(False) + "\n")
        setup_file.write("path_to_games;" + PATH_TO_GAMES + "\n")
        setup_file.write("pmb_rtp;" + str(params["pmb_rtp"]) + "\n")
        setup_file.close()
        # runRustScript()

    @staticmethod
    def run_all_modes(gamestate, modes_to_run, rust_threads):
        for mode in modes_to_run:
            OptimizationExecution.run_opt_single_mode(gamestate, mode, rust_threads)
