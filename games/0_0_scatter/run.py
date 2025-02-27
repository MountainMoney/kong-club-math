"""Main file for generating results for sample scatter-pay game."""

from gamestate import GameState
from game_config import GameConfig
from src.state.run_sims import create_books
from src.write_data.write_configs import generate_configs

if __name__ == "__main__":

    num_threads = 1
    rust_threaeds = 20
    batching_size = 5000
    compression = False
    profiling = False

    num_sim_args = {
        "base": int(20),
        "bonus": int(20),
    }

    config = GameConfig()
    gamestate = GameState(config)

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
