from gamestate import GameState
from game_config import GameConfig
from game_optimization import OptimizationSetup
from optimization_program.run_script import OptimizationExecution
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs
from uploads.aws_upload import upload_to_aws

if __name__ == "__main__":

    num_threads = 10
    rust_threads = 20
    batching_size = 5000
    compression = True
    profiling = False

    num_sim_args = {
        "base": int(1e4),
        "bonus": int(1e4),
        "superspin": int(1e4),
    }

    config = GameConfig()
    gamestate = GameState(config)
    optimization_setup = OptimizationSetup(config)

    upload_objects = {
        "books": True,
        "lookupTables": True,
        "forceFiles": True,
        "configFiles": True,
    }

    # create_books(
    #     gamestate,
    #     config,
    #     num_sim_args,
    #     batching_size,
    #     num_threads,
    #     compression,
    #     profiling,
    # )

    generate_configs(gamestate)
    upload_to_aws(gamestate, ["base", "bonus", "superspin"], upload_objects, override_check=False)

    # optimization_modes_to_run = ["base", "bonus", "superspin"]
    # OptimizationExecution().run_all_modes(config, optimization_modes_to_run, rust_threads)
