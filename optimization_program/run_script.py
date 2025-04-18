import json
import subprocess
import os
from src.config.paths import PATH_TO_GAMES, SETUP_PATH, OPTIMIZATION_PATH, PROJECT_PATH


class OptimizationExecution:
    """Handles execution of Rust optimization algorithm from python."""

    @staticmethod
    def load_math_config(filename: str) -> dict:
        """Load optimization parameter config file."""
        with open(filename, "r", encoding="UTF-8") as f:
            data = json.load(f)
        return data

    @staticmethod
    def run_opt_single_mode(game_config, mode, threads):
        """Create setup txt file for a single mode and run Rust executable binary."""
        os.chdir(PROJECT_PATH)
        filename = os.path.join(PATH_TO_GAMES, game_config.game_id, "library", "configs", "math_config.json")
        opt_config = OptimizationExecution.load_math_config(filename)

        opt_config = game_config.opt_params
        params = None
        for idx, obj in opt_config.items():
            if idx == mode:
                params = obj["parameters"]

        assert params is not None, "Could not load optimization parameters."

        setup_file = open(SETUP_PATH, "w", encoding="UTF-8")
        setup_file.write("game_name;" + game_config.game_id + "\n")
        setup_file.write("bet_type;" + mode + "\n")
        setup_file.write("num_show_pigs;" + str(params["num_show_pigs"]) + "\n")
        setup_file.write("num_pigs_per_fence;" + str(params["num_pigs_per_fence"]) + "\n")
        setup_file.write("threads_for_fence_construction;" + str(threads) + "\n")
        setup_file.write("threads_for_show_construction;" + str(threads) + "\n")
        setup_file.write("score_type;" + params["score_type"] + "\n")
        setup_file.write("test_spins;" + str(params["test_spins"]).replace(" ", "") + "\n")
        setup_file.write("test_spins_weights;" + str(params["test_spins_weights"]).replace(" ", "") + "\n")
        setup_file.write("simulation_trials;" + str(params["simulation_trials"]) + "\n")
        setup_file.write("graph_indexes;" + str(0) + "\n")
        setup_file.write("run_1000_batch;" + str(False) + "\n")
        setup_file.write("path_to_games;" + PATH_TO_GAMES + "\n")
        setup_file.write("pmb_rtp;" + str(params["pmb_rtp"]) + "\n")
        setup_file.close()
        print(f"Running optimization for mode: {mode}")
        OptimizationExecution.run_rust_script()

    @staticmethod
    def run_all_modes(game_config, modes_to_run, rust_threads):
        """Loop through all game modes to run"""
        for mode in modes_to_run:
            OptimizationExecution.run_opt_single_mode(game_config, mode, rust_threads)

    @staticmethod
    def run_rust_script():
        """Run compiled binary and pip results to terminal."""
        cargo_bin_path = os.path.join(os.path.expanduser("~"), ".cargo", "bin")
        updated_path = cargo_bin_path + os.pathsep + os.environ.get("PATH", "")
        result = subprocess.run(
            ["cargo", "run", "--release"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=OPTIMIZATION_PATH,
            check=True,
            env={**os.environ, "PATH": updated_path},
        )
        if result.returncode == 0:
            print(result.stdout)
        else:
            print("Error in optimization program.")
            print(result.stderr)
