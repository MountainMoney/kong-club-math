"""Main file for generating results for sample expanding wilds and prize game."""

from gamestate import GameState
from game_config import GameConfig
from game_optimization import OptimizationSetup
from optimization_program.run_script import OptimizationExecution
from utils.game_analytics.run_analysis import run
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":

    num_threads = 10
    rust_threads = 20
    batching_size = 50000
    compression = True
    profiling = False

    num_sim_args = {"base": int(1e4), "bonus": int(1e4), "superspin": int(1e4)}

    run_conditions = {
        "run_sims": True,
        "run_optimization": True,
        "run_analysis": True,
        "upload_data": False,
    }

    config = GameConfig()
    gamestate = GameState(config)
    if run_conditions["run_optimization"] or run_conditions["run_analysis"]:
        optimization_setup_class = OptimizationSetup(config)

    if run_conditions["run_sims"]:
        create_books(
            gamestate,
            config,
            num_sim_args,
            batching_size,
            num_threads,
            compression,
            profiling,
        )

    generate_configs(gamestate)

    if run_conditions["run_optimization"]:
        optimization_modes_to_run = ["base", "bonus"]
        OptimizationExecution().run_all_modes(config, optimization_modes_to_run, rust_threads)

    if run_conditions["run_analysis"]:
        custom_keys = [{"symbol": "scatter"}]
        run(config.game_id, custom_keys=custom_keys)
