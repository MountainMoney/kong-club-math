from gamestate import GameState
from game_config import GameConfig
from src.state.run_sims import create_books

if __name__ == "__main__":

    num_threads = 10
    rust_threaeds = 20
    batching_size = 5000
    compression = False
    profiling = False

    num_sim_args = {"base": int(1e4), "bonus": int(1e4)}

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
