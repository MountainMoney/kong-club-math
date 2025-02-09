from gamestate import GameConfig, GameState
from src.write_data.write_data import create_books

if __name__ == "__main__":

    num_threads = 1
    rust_threaeds = 20
    batching_size = 5000
    compression = False
    profiling = False

    num_sim_args = {
        "base": int(1e2),
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
